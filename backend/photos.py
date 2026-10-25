"""Private photo storage: save, read and delete JPEG photos by their stored path.

Photos are kept in the local folder PHOTO_DIR when it is set (development and tests),
otherwise in a private Cloudflare R2 bucket (production). The stored path is a key
inside the folder or bucket, never a web address. No public or presigned link is made:
a photo's bytes only come out through `read`.
"""

import os
import re
import secrets
from collections.abc import Iterator
from functools import cache
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

MAX_PHOTO_BYTES = 10 * 1024 * 1024
TIMEOUT_SECONDS = 10
CHUNK_BYTES = 64 * 1024
JPEG_START = b"\xff\xd8\xff"
PATH_FORM = re.compile(r"[0-9a-f]{32}\.jpg")
R2_VARIABLES = ("R2_ACCOUNT_ID", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")


class InvalidPhoto(Exception):
    """The file is not an accepted photo; the message can be shown to the user."""


class PhotoNotFound(Exception):
    """No photo is stored under this path."""


class StorageUnavailable(Exception):
    """The photo storage cannot be reached, or does not answer in time."""


@cache
def r2_client():
    """Created on first use, so the backend starts without R2 variables. One request per call, no retries."""
    missing = [name for name in R2_VARIABLES if not os.environ.get(name)]
    if missing:
        raise SystemExit(
            f"Photo storage is not set up. Set PHOTO_DIR, or all of the R2 variables. Missing: {', '.join(missing)}. "
            "See README.md."
        )
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(connect_timeout=TIMEOUT_SECONDS, read_timeout=TIMEOUT_SECONDS, retries={"max_attempts": 0}),
    )


def checked_path(path: str) -> str:
    if not PATH_FORM.fullmatch(path):
        raise ValueError("This is not a stored photo path.")
    return path


def r2_call(operation, **arguments):
    """The answer of one R2 request. Library errors are not passed on (they could carry request details)."""
    try:
        return getattr(r2_client(), operation)(Bucket=os.environ["R2_BUCKET"], **arguments)
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
            raise PhotoNotFound from None
        raise StorageUnavailable from None
    except BotoCoreError:
        raise StorageUnavailable from None


def check(data: bytes) -> None:
    """Raises InvalidPhoto unless `data` is a JPEG of at most 10 MB. Looks at the bytes only."""
    if not data.startswith(JPEG_START):
        raise InvalidPhoto("This file type is not supported.")
    if len(data) > MAX_PHOTO_BYTES:
        raise InvalidPhoto("This photo is too large.")


def save(data: bytes) -> str:
    """Stores a JPEG photo and returns its new stored path."""
    check(data)
    path = secrets.token_hex(16) + ".jpg"
    folder = os.environ.get("PHOTO_DIR")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / path).write_bytes(data)
    else:
        r2_call("put_object", Key=path, Body=data, ContentType="image/jpeg")
    return path


def read(path: str) -> Iterator[bytes]:
    """The photo's bytes in chunks. Raises PhotoNotFound at once, before the first chunk."""
    checked_path(path)
    folder = os.environ.get("PHOTO_DIR")
    if folder:
        try:
            file = open(Path(folder) / path, "rb")
        except FileNotFoundError:
            raise PhotoNotFound from None
        return read_file(file)
    return read_body(r2_call("get_object", Key=path)["Body"])


def read_file(file) -> Iterator[bytes]:
    with file:
        while chunk := file.read(CHUNK_BYTES):
            yield chunk


def read_body(body) -> Iterator[bytes]:
    try:
        yield from body.iter_chunks(CHUNK_BYTES)
    except BotoCoreError:
        raise StorageUnavailable from None


def delete(path: str) -> None:
    """Deletes the photo. A photo that is not there is not an error."""
    checked_path(path)
    folder = os.environ.get("PHOTO_DIR")
    if folder:
        (Path(folder) / path).unlink(missing_ok=True)
    else:
        try:
            r2_call("delete_object", Key=path)
        except PhotoNotFound:
            pass
