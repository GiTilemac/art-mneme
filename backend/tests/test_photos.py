"""Photo storage (issue #6): the local folder is tested for real, R2 with botocore's Stubber (no network)."""

import io
import logging
import re
from unittest import mock

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ConnectTimeoutError, EndpointConnectionError
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi.testclient import TestClient

import photos
from main import app

real_r2_client = photos.r2_client
JPEG = b"\xff\xd8\xff\xe0" + b"photo bytes" * 100
SECRET = "super-secret-value"
BUCKET = "test-bucket"
KEY = "0123456789abcdef0123456789abcdef.jpg"
R2_ENVIRONMENT = {
    "R2_ACCOUNT_ID": "account123",
    "R2_BUCKET": BUCKET,
    "R2_ACCESS_KEY_ID": "access-key-id",
    "R2_SECRET_ACCESS_KEY": SECRET,
}


@pytest.fixture(autouse=True)
def no_real_storage(monkeypatch):
    """Whatever the machine has set, no test reaches a real folder or a real R2 account."""
    for name in ("PHOTO_DIR", *photos.R2_VARIABLES):
        monkeypatch.delenv(name, raising=False)
    real_r2_client.cache_clear()
    yield
    real_r2_client.cache_clear()


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path / "photos"))
    return tmp_path / "photos"


@pytest.fixture
def r2(monkeypatch):
    """R2 with a client that answers only what the test tells the Stubber."""
    for name, value in R2_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)
    client = boto3.client(
        "s3",
        region_name="auto",
        aws_access_key_id="x",
        aws_secret_access_key="x",
        endpoint_url="https://nowhere.invalid",
    )
    monkeypatch.setattr(photos, "r2_client", lambda: client)
    with Stubber(client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def body_of(data: bytes) -> StreamingBody:
    return StreamingBody(io.BytesIO(data), len(data))


# Choosing the storage


def test_missing_storage_variables_are_all_named(monkeypatch):
    monkeypatch.setenv("R2_BUCKET", BUCKET)
    with pytest.raises(SystemExit) as stopped:
        photos.read(KEY)
    message = str(stopped.value)
    assert all(name in message for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    assert "R2_BUCKET," not in message and "PHOTO_DIR" in message


def test_backend_and_health_work_with_no_storage_variables():
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


def test_photo_folder_is_created_when_missing(folder):
    assert not folder.exists()
    photos.save(JPEG)
    assert folder.is_dir()


def test_r2_address_is_built_from_the_account_id_with_a_10_second_timeout(monkeypatch):
    for name, value in R2_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)
    client = photos.r2_client()
    assert client.meta.endpoint_url == "https://account123.r2.cloudflarestorage.com"
    config: Config = client.meta.config
    assert (config.connect_timeout, config.read_timeout) == (10, 10)
    assert config.retries["total_max_attempts"] == 1


# Saving


def test_saved_photo_path_is_32_hex_characters_and_jpg(folder):
    assert re.fullmatch(r"[0-9a-f]{32}\.jpg", photos.save(JPEG))


def test_saved_photo_reads_back_unchanged(folder):
    assert b"".join(photos.read(photos.save(JPEG))) == JPEG


def test_saving_the_same_photo_twice_gives_two_paths_and_two_files(folder):
    first, second = photos.save(JPEG), photos.save(JPEG)
    assert first != second
    assert sorted(file.name for file in folder.iterdir()) == sorted([first, second])


@pytest.mark.parametrize(
    "data", [b"\x89PNG\r\n\x1a\n" + b"x" * 50, b"just some text", b"", b"\xff\xd8"], ids=["png", "text", "empty", "short"]
)
def test_file_that_is_not_a_jpeg_is_refused_as_not_supported(folder, data):
    with pytest.raises(photos.InvalidPhoto) as refused:
        photos.save(data)
    assert str(refused.value) == "This file type is not supported."
    assert not folder.exists() or list(folder.iterdir()) == []


def test_photo_over_10_mb_is_refused(folder):
    with pytest.raises(photos.InvalidPhoto) as refused:
        photos.save(JPEG[:3] + b"0" * (10 * 1024 * 1024 - 2))
    assert str(refused.value) == "This photo is too large."
    assert not folder.exists() or list(folder.iterdir()) == []


def test_photo_of_exactly_10_mb_is_accepted(folder):
    data = JPEG[:3] + b"0" * (10 * 1024 * 1024 - 3)
    assert len(data) == 10 * 1024 * 1024
    assert b"".join(photos.read(photos.save(data))) == data


# Reading and deleting


def test_photo_is_read_in_chunks(folder):
    data = JPEG[:3] + b"0" * 200_000
    chunks = list(photos.read(photos.save(data)))
    assert len(chunks) > 1 and b"".join(chunks) == data


def test_reading_a_missing_photo_says_not_found(folder):
    with pytest.raises(photos.PhotoNotFound):
        photos.read(KEY)


def test_deleted_photo_cannot_be_read(folder):
    path = photos.save(JPEG)
    photos.delete(path)
    with pytest.raises(photos.PhotoNotFound):
        photos.read(path)


def test_deleting_a_missing_photo_is_not_an_error(folder):
    path = photos.save(JPEG)
    photos.delete(path)
    photos.delete(path)
    photos.delete(KEY)


@pytest.mark.parametrize("path", ["../secret", "a/b.jpg", "ABC.jpg", "", KEY + "\n", "/etc/passwd", KEY[:-4] + ".png"])
def test_path_outside_the_photo_folder_is_refused(folder, tmp_path, path):
    (tmp_path / "secret").write_bytes(b"keep")
    with pytest.raises(ValueError):
        photos.read(path)
    with pytest.raises(ValueError):
        photos.delete(path)
    assert (tmp_path / "secret").read_bytes() == b"keep"


def test_malformed_path_is_refused_before_r2_is_asked(r2):
    with pytest.raises(ValueError):
        photos.read("../secret")
    with pytest.raises(ValueError):
        photos.delete("a/b.jpg")


# R2, simulated


def test_r2_save_stores_one_jpeg_object_with_content_type_image_jpeg(r2):
    r2.add_response("put_object", {}, {"Bucket": BUCKET, "Key": mock.ANY, "Body": JPEG, "ContentType": "image/jpeg"})
    path = photos.save(JPEG)
    assert re.fullmatch(r"[0-9a-f]{32}\.jpg", path)


def test_r2_read_returns_the_saved_bytes(r2):
    r2.add_response("get_object", {"Body": body_of(JPEG)}, {"Bucket": BUCKET, "Key": KEY})
    assert b"".join(photos.read(KEY)) == JPEG


def test_r2_read_of_a_missing_photo_says_not_found(r2):
    r2.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
    with pytest.raises(photos.PhotoNotFound):
        photos.read(KEY)


def test_r2_delete_sends_one_delete_for_the_path(r2):
    r2.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": KEY})
    photos.delete(KEY)


def test_r2_deleting_a_missing_photo_is_not_an_error(r2):
    r2.add_client_error("delete_object", service_error_code="NoSuchKey", http_status_code=404)
    photos.delete(KEY)


@pytest.mark.parametrize("failure", [EndpointConnectionError(endpoint_url="x"), ConnectTimeoutError(endpoint_url="x")])
def test_unreachable_r2_says_storage_unavailable(monkeypatch, failure):
    for name, value in R2_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)

    class Unreachable:
        def __getattr__(self, name):
            def fail(**arguments):
                raise failure

            return fail

    monkeypatch.setattr(photos, "r2_client", Unreachable)
    for action in (lambda: photos.save(JPEG), lambda: photos.read(KEY), lambda: photos.delete(KEY)):
        with pytest.raises(photos.StorageUnavailable):
            action()


def test_r2_error_answer_says_storage_unavailable(r2):
    r2.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)
    with pytest.raises(photos.StorageUnavailable):
        photos.read(KEY)


# The 503 answer


def test_unreachable_storage_gives_503(monkeypatch):
    @app.get("/api/test-photo")
    def use_storage():
        raise photos.StorageUnavailable

    try:
        answer = TestClient(app).get("/api/test-photo")
    finally:
        app.router.routes.pop()
    assert answer.status_code == 503
    assert answer.json() == {"detail": "Photos are unavailable right now. Please try again later."}


# Privacy


def test_r2_secret_never_appears_in_an_error_or_a_log(r2, caplog):
    r2.add_client_error(
        "get_object", service_error_code="InvalidAccessKeyId", service_message=f"bad {SECRET}", http_status_code=403
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(photos.StorageUnavailable) as failed:
            photos.read(KEY)
    assert SECRET not in str(failed.value) and SECRET not in repr(failed.value)
    assert SECRET not in caplog.text
    assert failed.value.__cause__ is None and failed.value.__suppress_context__


def test_storage_module_makes_no_public_or_presigned_link():
    source = open(photos.__file__).read()
    assert "generate_presigned" not in source and "ACL" not in source
