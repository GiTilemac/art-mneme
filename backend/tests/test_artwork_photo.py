"""Uploading, replacing and getting the artwork photo (`PUT`, `GET /api/artworks/{artwork_id}/photo`)."""

import pytest
from fastapi.testclient import TestClient
from test_artworks import JPEG, folder, post, row, user, watch  # noqa: F401
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of

import photos
from main import app

NOT_FOUND = {"detail": "Artwork not found."}
PHOTO_NOT_FOUND = {"detail": "Photo not found."}
CHOOSE = {"detail": "Choose a photo to upload."}
UNAVAILABLE = {"detail": "Photos are unavailable right now. Please try again later."}
NEW_JPEG = b"\xff\xd8\xff\xe0" + b"new photo" * 100
IMMUTABLE = "private, max-age=31536000, immutable"


def url(id):
    return f"/api/artworks/{id}/photo"


def upload(client, id, photo=NEW_JPEG, **extra):
    return client.put(url(id), files={"photo": ("p.jpg", photo, "image/jpeg"), **extra})


def collection(client):
    response = post(client, {"title": "Mona"}, photo=JPEG)
    assert response.status_code == 201, response.text
    return response.json()


def watchlist(client, photo=None):
    response = watch(client, {"title": "Mona"}, photo=photo)
    assert response.status_code == 201, response.text
    return response.json()


def files(folder):
    return sorted(p.name for p in folder.glob("*")) if folder.exists() else []


def storage_down(monkeypatch):
    def unavailable(*args, **kwargs):
        raise photos.StorageUnavailable

    for name in ("save", "read", "delete"):
        monkeypatch.setattr(photos, name, unavailable)


# Login and ownership


@pytest.mark.parametrize("method", ["put", "get"])
@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_without_a_valid_session_it_is_refused(client, conn, folder, method, case):
    register(client, "ben@example.com")
    artwork = watchlist(client)
    before = (row(conn, artwork["id"]), files(folder))

    stranger = device(case(client, conn))
    response = upload(stranger, artwork["id"]) if method == "put" else stranger.get(url(artwork["id"]))

    assert (response.status_code, response.json()) == (401, NOT_LOGGED_IN)
    assert (row(conn, artwork["id"]), files(folder)) == before


@pytest.mark.parametrize("method", ["put", "get"])
@pytest.mark.parametrize("id", ["other", "missing", "0", "-1", "abc", "1.5", "99999999999"])
def test_an_unknown_id_or_another_users_artwork_is_not_found_and_unchanged(client, conn, folder, method, id):
    owner = device(token_of(register(client, "a@example.com")))
    artwork = collection(owner)
    before = (row(conn, artwork["id"]), files(folder))
    other = device(token_of(register(client, "b@example.com")))
    id = {"other": artwork["id"], "missing": artwork["id"] + 1000}.get(id, id)

    # A bad file too: ownership is checked before the file is looked at.
    response = upload(other, id, b"not a photo") if method == "put" else other.get(url(id))

    assert (response.status_code, response.json()) == (404, NOT_FOUND)
    assert (row(conn, artwork["id"]), files(folder)) == before


def test_a_valid_session_is_renewed_for_30_days(client):
    token = token_of(register(client))
    artwork = watchlist(client)

    response = upload(device(token), artwork["id"])

    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# Upload


def test_photo_upload_moves_watchlist_artwork_to_collection(user, conn):
    artwork = watchlist(user)

    response = upload(user, artwork["id"])

    assert response.status_code == 200
    assert response.json()["state"] == "COLLECTION" and response.json()["has_photo"] is True
    assert user.get(f"/api/artworks/{artwork['id']}").json() == response.json()
    assert user.get(url(artwork["id"])).content == NEW_JPEG


def test_only_state_photo_and_updated_at_change(user, conn):
    artwork = watchlist(user)
    before = row(conn, artwork["id"])._asdict()

    upload(user, artwork["id"], state=(None, "WATCHLIST"), is_discoverable=(None, "true"))

    after = row(conn, artwork["id"])._asdict()
    assert after["collection_state"] == "COLLECTION"
    changed = {name for name in before if before[name] != after[name]}
    assert changed == {"collection_state", "artwork_photo_path", "updated_at"}


@pytest.mark.parametrize("start", ["watchlist_with_photo", "collection"])
def test_replacing_photo_deletes_the_old_file(user, conn, folder, start):
    artwork = watchlist(user, JPEG) if start == "watchlist_with_photo" else collection(user)
    old = row(conn, artwork["id"]).artwork_photo_path

    response = upload(user, artwork["id"])

    assert response.json()["state"] == "COLLECTION"
    assert files(folder) == [row(conn, artwork["id"]).artwork_photo_path] != [old]
    with pytest.raises(photos.PhotoNotFound):
        photos.read(old)


def test_the_same_photo_again_gets_a_new_photo_version(user):
    artwork = collection(user)

    response = upload(user, artwork["id"], JPEG)

    assert response.json()["photo_version"] != artwork["photo_version"]


@pytest.mark.parametrize(
    "photo, detail",
    [(b"\x89PNG\r\n\x1a\n", "This file type is not supported."), (b"", "This file type is not supported."),
     (JPEG + b"x" * photos.MAX_PHOTO_BYTES, "This photo is too large.")],
)
def test_png_upload_is_refused_and_old_photo_stays(user, conn, folder, photo, detail):
    artwork = collection(user)
    before = (row(conn, artwork["id"]), files(folder))

    response = upload(user, artwork["id"], photo)

    assert (response.status_code, response.json()) == (422, {"detail": detail})
    assert (row(conn, artwork["id"]), files(folder)) == before


@pytest.mark.parametrize(
    "request_kwargs",
    [{"files": {"other": ("p.jpg", JPEG, "image/jpeg")}}, {"files": {"photo": (None, "text")}}, {"json": {"photo": "x"}}],
    ids=["no_photo_part", "photo_as_text", "not_multipart"],
)
def test_a_request_without_a_photo_file_is_refused(user, conn, folder, request_kwargs):
    artwork = watchlist(user)
    before = (row(conn, artwork["id"]), files(folder))

    response = user.put(url(artwork["id"]), **request_kwargs)

    assert (response.status_code, response.json()) == (422, CHOOSE)
    assert (row(conn, artwork["id"]), files(folder)) == before


def test_new_photo_is_removed_when_the_database_step_fails(user, conn, folder, monkeypatch):
    artwork = collection(user)
    before = (row(conn, artwork["id"]), files(folder))

    def fail(connection, artwork_id):
        raise RuntimeError("database step failed")

    monkeypatch.setattr("main.artwork_response", fail)
    failing = TestClient(app, base_url="https://testserver", cookies=user.cookies, raise_server_exceptions=False)

    assert upload(failing, artwork["id"]).status_code == 500
    assert (row(conn, artwork["id"]), files(folder)) == before


def test_an_old_file_that_cannot_be_deleted_stays_behind_and_the_upload_succeeds(user, conn, folder, monkeypatch):
    artwork = collection(user)
    old = row(conn, artwork["id"]).artwork_photo_path

    def unavailable(path):
        raise photos.StorageUnavailable

    monkeypatch.setattr(photos, "delete", unavailable)
    response = upload(user, artwork["id"])

    assert response.status_code == 200
    assert old in files(folder) and len(files(folder)) == 2


def test_a_missing_old_file_does_not_stop_the_upload(user, conn, folder):
    artwork = collection(user)
    (folder / row(conn, artwork["id"]).artwork_photo_path).unlink()

    assert upload(user, artwork["id"]).status_code == 200


def test_unreachable_storage_gives_503_and_changes_nothing(user, conn, folder, monkeypatch):
    artwork = collection(user)
    before = (row(conn, artwork["id"]), files(folder))
    storage_down(monkeypatch)

    response = upload(user, artwork["id"])

    assert (response.status_code, response.json()) == (503, UNAVAILABLE)
    assert (row(conn, artwork["id"]), files(folder)) == before


# Get


def test_the_owner_gets_the_exact_photo_without_caching(user):
    artwork = collection(user)

    response = user.get(url(artwork["id"]))

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("v, cache", [("current", IMMUTABLE), ("", "private, no-store"), ("old", "private, no-store")])
def test_only_the_current_photo_version_may_be_kept_by_the_browser(user, v, cache):
    artwork = collection(user)
    v = artwork["photo_version"] if v == "current" else v

    response = user.get(url(artwork["id"]), params={"v": v})

    assert (response.status_code, response.headers["cache-control"]) == (200, cache)


def test_a_watchlist_artwork_without_photo_has_no_photo_even_while_storage_is_down(user, monkeypatch):
    artwork = watchlist(user)
    storage_down(monkeypatch)

    response = user.get(url(artwork["id"]))

    assert (response.status_code, response.json()) == (404, PHOTO_NOT_FOUND)


def test_a_photo_missing_from_storage_is_not_found(user, conn, folder):
    artwork = collection(user)
    (folder / row(conn, artwork["id"]).artwork_photo_path).unlink()

    response = user.get(url(artwork["id"]), params={"v": artwork["photo_version"]})

    assert (response.status_code, response.json()) == (404, PHOTO_NOT_FOUND)
    assert "max-age" not in response.headers.get("cache-control", "")


def test_unreachable_storage_gives_503_when_getting_the_photo(user, monkeypatch):
    artwork = collection(user)
    storage_down(monkeypatch)

    response = user.get(url(artwork["id"]), params={"v": artwork["photo_version"]})

    assert (response.status_code, response.json()) == (503, UNAVAILABLE)
    assert "max-age" not in response.headers.get("cache-control", "")


def test_the_photo_cannot_be_deleted(user, conn):
    artwork = collection(user)

    assert user.delete(url(artwork["id"])).status_code in (404, 405)
    assert row(conn, artwork["id"]).artwork_photo_path is not None
