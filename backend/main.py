import hashlib
import json
import re
import secrets
import unicodedata
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import Connection, text
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

import photos
from db import get_engine

app = FastAPI(
    title="ArtMneme API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

SESSION_COOKIE = "session"
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 60 * 60
PAGE_SIZE = 50
NAME_MAX_LENGTH = 200

password_hasher = PasswordHasher()
# Checked against when the email has no account, so that case takes as long as a wrong password.
UNUSED_HASH = password_hasher.hash(secrets.token_urlsafe(32))


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, error: RequestValidationError):
    """Every invalid request is answered with one readable sentence, in the `Error` shape."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"][1:])
    if first["type"] == "json_invalid":
        detail = "The request body is not valid JSON."
    elif not field and first["type"] == "missing":
        detail = "The request body is missing."
    elif not field:
        detail = "The request body must be a JSON object."
    elif first["type"] == "missing":
        detail = f"The field '{field}' is required."
    else:
        detail = f"The field '{field}' is not valid: {first['msg']}."
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(StarletteHTTPException)
async def body_parsing_error(request: Request, error: StarletteHTTPException):
    """FastAPI answers a body it cannot read (such as one that is not UTF-8) with 400; it is invalid JSON too."""
    if error.status_code == 400 and error.detail == "There was an error parsing the body":
        return JSONResponse(status_code=422, content={"detail": "The request body is not valid JSON."})
    return await http_exception_handler(request, error)


@app.exception_handler(photos.StorageUnavailable)
def storage_unavailable(request: Request, error: photos.StorageUnavailable):
    return JSONResponse(
        status_code=503, content={"detail": "Photos are unavailable right now. Please try again later."}
    )


def get_connection():
    """A database connection whose changes are committed when the request ends."""
    with get_engine().begin() as connection:
        yield connection


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_SECONDS, path="/", secure=True, httponly=True, samesite="lax"
    )


def start_session(connection: Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    connection.execute(
        text(
            "INSERT INTO sessions (user_id, token_hash, expires_at) "
            "VALUES (:user_id, :token_hash, now() + make_interval(days => :days))"
        ),
        {"user_id": user_id, "token_hash": hash_token(token), "days": SESSION_DAYS},
    )
    set_session_cookie(response, token)


def current_user(request: Request, response: Response, connection: Connection = Depends(get_connection)) -> dict:
    """The login check: the calling user, with their session renewed for 30 days. Refuses with 401 otherwise."""
    token = request.cookies.get(SESSION_COOKIE)
    user = None
    if token:
        user = connection.execute(
            text(
                "UPDATE sessions SET expires_at = now() + make_interval(days => :days) FROM users "
                "WHERE users.id = sessions.user_id AND token_hash = :token_hash AND expires_at > now() "
                "RETURNING users.id, users.email"
            ),
            {"token_hash": hash_token(token), "days": SESSION_DAYS},
        ).one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    set_session_cookie(response, token)
    return {"id": user.id, "email": user.email}


class Credentials(BaseModel):
    # Missing fields are empty, so they get the same message as an empty value.
    email: str = ""
    password: str = ""


def checked(credentials: Credentials) -> tuple[str, str]:
    """The email (without surrounding spaces, in lower case) and password, or 422 when either breaks a rule."""
    email = credentials.email.strip().lower()
    if not re.fullmatch(r"\S+@\S+\.\S+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(credentials.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")
    return email, credentials.password


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", status_code=201)
def register(credentials: Credentials, response: Response, connection: Connection = Depends(get_connection)):
    email, password = checked(credentials)
    user_id = connection.execute(
        text(
            "INSERT INTO users (email, password_hash) VALUES (:email, :password_hash) "
            "ON CONFLICT DO NOTHING RETURNING id"
        ),
        {"email": email, "password_hash": password_hasher.hash(password)},
    ).scalar()
    if user_id is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    start_session(connection, response, user_id)
    return {"id": user_id, "email": email}


@app.post("/api/auth/login")
def login(credentials: Credentials, response: Response, connection: Connection = Depends(get_connection)):
    email, password = checked(credentials)
    user = connection.execute(
        text("SELECT id, email, password_hash FROM users WHERE lower(email) = :email"), {"email": email}
    ).one_or_none()
    try:
        password_hasher.verify(user.password_hash if user else UNUSED_HASH, password)
    except VerifyMismatchError:
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    start_session(connection, response, user.id)
    return {"id": user.id, "email": user.email}


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, user: dict = Depends(current_user), connection: Connection = Depends(get_connection)):
    connection.execute(
        text("DELETE FROM sessions WHERE token_hash = :token_hash"),
        {"token_hash": hash_token(request.cookies[SESSION_COOKIE])},
    )
    # A new response, so the renewed cookie from the login check is not sent; only the cleared one is.
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return user


class NewEntity(BaseModel):
    name: str


def cleaned(name: str) -> str:
    """In Unicode NFC, ends trimmed, and every run of spaces (tabs, line breaks, non-breaking spaces too) one space."""
    return " ".join(unicodedata.normalize("NFC", name).split())


def refuse_characters_not_allowed(name: str, label: str = "Name", allowed: str = "") -> None:
    """422 for a control character or a lone surrogate (which the database cannot store), except those in `allowed`."""
    if any(unicodedata.category(c) in ("Cc", "Cs") and c not in allowed for c in name):
        raise HTTPException(status_code=422, detail=f"{label} contains characters that are not allowed.")


def checked_name(name: str) -> str:
    """The cleaned name, or 422 when it breaks a rule."""
    name = cleaned(name)
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")
    refuse_characters_not_allowed(name)
    if len(name) > NAME_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"Name must be at most {NAME_MAX_LENGTH} characters.")
    return name


def add_entity_endpoints(table: str) -> None:
    """Search and create for one community-wide list. `table` comes from the fixed list below, never from a request."""

    @app.get(f"/api/{table}")
    def search(
        q: str = "",
        page: int = Query(1, ge=1),
        user: dict = Depends(current_user),
        connection: Connection = Depends(get_connection),
    ):
        q = cleaned(q)
        refuse_characters_not_allowed(q)
        # `%`, `_` and `\` are matched as themselves.
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        total = connection.execute(
            text(f"SELECT count(*) FROM {table} WHERE lower(name) LIKE lower(:pattern)"), {"pattern": pattern}
        ).scalar()
        offset = (page - 1) * PAGE_SIZE
        items = []
        # A page after the last is empty; not asking the database also keeps a huge offset away from it.
        if offset < total:
            items = connection.execute(
                text(
                    f"SELECT id, name FROM {table} WHERE lower(name) LIKE lower(:pattern) "
                    "ORDER BY lower(name), id LIMIT :limit OFFSET :offset"
                ),
                {"pattern": pattern, "limit": PAGE_SIZE, "offset": offset},
            ).all()
        return {
            "items": [{"id": item.id, "name": item.name} for item in items],
            "total": total,
            "page": page,
            "page_size": PAGE_SIZE,
        }

    @app.post(f"/api/{table}", status_code=201)
    def create(
        new: NewEntity,
        response: Response,
        user: dict = Depends(current_user),
        connection: Connection = Depends(get_connection),
    ):
        name = checked_name(new.name)
        entity = connection.execute(
            text(f"INSERT INTO {table} (name) VALUES (:name) ON CONFLICT DO NOTHING RETURNING id, name"),
            {"name": name},
        ).one_or_none()
        if entity is None:
            # The unique lower(name) index refused it: the name already exists.
            entity = connection.execute(
                text(f"SELECT id, name FROM {table} WHERE lower(name) = lower(:name)"), {"name": name}
            ).one()
            response.status_code = 200
        return {"id": entity.id, "name": entity.name}


for table in ("artists", "movements", "subjects"):
    add_entity_endpoints(table)


TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 50
SUGGESTION_LIMIT = 10
TAG_CHARACTERS_NOT_ALLOWED = "Tags may only contain letters, numbers, spaces and hyphens."


def allowed_in_tag(name: str) -> bool:
    """Only letters, numbers, marks (the parts of letters such as accents), spaces and hyphens."""
    return all(unicodedata.category(c)[0] in "LNM" or c in " -" for c in name)


def lowercased(name: str) -> str:
    """Cleaned, then lowercased (plain `lower`, not `casefold`, so `ß` stays `ß`)."""
    return cleaned(name).lower()


@app.post("/api/tags", status_code=201)
def create_tag(
    new: NewEntity,
    response: Response,
    user: dict = Depends(current_user),
    connection: Connection = Depends(get_connection),
):
    name = lowercased(new.name)
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")
    if not TAG_MIN_LENGTH <= len(name) <= TAG_MAX_LENGTH:
        raise HTTPException(status_code=422, detail="Tags must be 2–50 characters.")
    if not allowed_in_tag(name):
        raise HTTPException(status_code=422, detail=TAG_CHARACTERS_NOT_ALLOWED)
    if not any(unicodedata.category(c)[0] in "LN" for c in name):
        raise HTTPException(status_code=422, detail="A tag needs at least one letter or number.")
    tag = connection.execute(
        text("INSERT INTO tags (name) VALUES (:name) ON CONFLICT DO NOTHING RETURNING id, name"), {"name": name}
    ).one_or_none()
    if tag is None:
        # The unique lower(name) index refused it: the tag already exists.
        tag = connection.execute(text("SELECT id, name FROM tags WHERE name = :name"), {"name": name}).one()
        response.status_code = 200
    return {"id": tag.id, "name": tag.name}


@app.get("/api/tags/suggestions")
def suggest_tags(
    q: str = "", user: dict = Depends(current_user), connection: Connection = Depends(get_connection)
):
    q = lowercased(q)
    # No tag could contain such a q; the database is not asked, as it cannot hold a NUL character.
    if len(q) > TAG_MAX_LENGTH or not allowed_in_tag(q):
        return []
    tags = connection.execute(
        text(
            "SELECT id, name FROM tags WHERE usage_count >= 2 AND name LIKE :pattern "
            "ORDER BY usage_count DESC, name LIMIT :limit"
        ),
        {"pattern": "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%", "limit": SUGGESTION_LIMIT},
    ).all()
    return [{"id": tag.id, "name": tag.name} for tag in tags]


# Artworks

INT_MAX = 2**31 - 1
MAX_BC_YEAR = 100_000
TITLE_MAX_LENGTH = 300
MUSEUM_MAX_LENGTH = 200
NOTES_MAX_LENGTH = 10_000


class StrictInput(BaseModel):
    """Exact types (no "3" for 3). Extra fields are ignored."""

    model_config = ConfigDict(strict=True)


class DateInput(StrictInput):
    from_year: int
    to_year: int | None = None
    circa: bool = False
    from_bc: bool = False
    to_bc: bool = False


class ArtworkInput(StrictInput):
    title: str = ""
    artist_id: int | None = None
    date: DateInput | None = None
    subject_id: int | None = None
    movement_id: int | None = None
    museum: str = ""
    tag_ids: list[int] = []
    notes: str = ""


def date_display(year_start: int, year_end: int | None, circa: bool) -> str:
    """The date as shown, from the stored signed years (BC negative): `1642`, `500–450 BC`, `c. 30 BC – 14 AD`."""
    if year_end is None or year_end == year_start:
        shown = f"{-year_start} BC" if year_start < 0 else str(year_start)
    elif year_start < 0 < year_end:
        shown = f"{-year_start} BC – {year_end} AD"
    elif year_end < 0:
        shown = f"{-year_start}–{-year_end} BC"
    else:
        shown = f"{year_start}–{year_end}"
    return f"c. {shown}" if circa else shown


def checked_text(value: str, label: str, max_length: int, notes: bool = False) -> str:
    """Title and museum are cleaned like names; notes keep their layout. Refuses control characters and long text."""
    if notes:
        value = unicodedata.normalize("NFC", value)
        refuse_characters_not_allowed(value, label, allowed="\t\n\r")
    else:
        value = cleaned(value)
        refuse_characters_not_allowed(value, label)
    if len(value) > max_length:
        raise HTTPException(status_code=422, detail=f"{label} must be at most {max_length:,} characters.")
    return value


def checked_date(date: DateInput | None) -> tuple[int | None, int | None, bool, bool]:
    """The signed years (BC negative), Circa and the effective `to_bc`, or 422 when the date breaks a rule."""
    if date is None:
        return None, None, False, False
    this_year = datetime.now(UTC).year
    for year, bc in ((date.from_year, date.from_bc), (date.to_year, date.to_bc and date.to_year is not None)):
        if year is None:
            continue
        if year < 1:
            raise HTTPException(status_code=422, detail="A year must be 1 or more; use the BC box for years before 1 AD.")
        if bc and year > MAX_BC_YEAR:
            raise HTTPException(status_code=422, detail="A BC year cannot be above 100,000.")
        if not bc and year > this_year:
            raise HTTPException(status_code=422, detail="A year cannot be in the future.")
    to_bc = date.to_bc and date.to_year is not None
    year_start = -date.from_year if date.from_bc else date.from_year
    year_end = None if date.to_year is None else -date.to_year if to_bc else date.to_year
    if year_end is not None and year_end < year_start:
        raise HTTPException(status_code=422, detail="The end year cannot be before the start year.")
    return year_start, year_end, date.circa, to_bc


def photo_version(path: str | None) -> str | None:
    return None if path is None else hashlib.sha256(path.encode()).hexdigest()[:16]


def artwork_response(connection: Connection, artwork_id: int) -> dict:
    """The `Artwork` of one row, as in openapi.yaml."""
    row = connection.execute(
        text(
            "SELECT a.*, artists.name AS artist_name, subjects.name AS subject_name, movements.name AS movement_name "
            "FROM artworks a LEFT JOIN artists ON artists.id = a.artist_id "
            "LEFT JOIN subjects ON subjects.id = a.subject_id LEFT JOIN movements ON movements.id = a.movement_id "
            "WHERE a.id = :id"
        ),
        {"id": artwork_id},
    ).one()
    tags = connection.execute(
        text(
            "SELECT tags.id, tags.name FROM artwork_tags JOIN tags ON tags.id = tag_id "
            "WHERE artwork_id = :id ORDER BY lower(tags.name), tags.id"
        ),
        {"id": artwork_id},
    ).all()
    detail_photo_ids = connection.execute(
        text("SELECT id FROM detail_photos WHERE artwork_id = :id ORDER BY id"), {"id": artwork_id}
    ).scalars().all()
    date = None
    if row.year_start is not None:
        date = {
            "from_year": abs(row.year_start),
            "to_year": None if row.year_end is None else abs(row.year_end),
            "circa": row.date_is_circa,
            "from_bc": row.year_start < 0,
            "to_bc": row.year_end is not None and row.year_end < 0,
            "display": row.date_display,
        }

    def entry(id, name):
        return None if id is None else {"id": id, "name": name}

    return {
        "id": row.id,
        "state": row.collection_state,
        "title": row.title,
        "artist": entry(row.artist_id, row.artist_name),
        "date": date,
        "subject": entry(row.subject_id, row.subject_name),
        "movement": entry(row.movement_id, row.movement_name),
        "museum": row.museum,
        "tags": [{"id": tag.id, "name": tag.name} for tag in tags],
        "notes": row.notes,
        "has_photo": row.artwork_photo_path is not None,
        "photo_version": photo_version(row.artwork_photo_path),
        "detail_photo_ids": list(detail_photo_ids),
        "is_discoverable": row.is_discoverable,
        "are_notes_discoverable": row.are_notes_discoverable,
        "created_at": row.created_at,
    }


def refuse_unknown_entry(connection: Connection, table: str, id: int | None, label: str) -> None:
    """422 when `id` (an artist, subject or movement; `table` is fixed in the code below) does not exist."""
    if id is None:
        return
    if not 1 <= id <= INT_MAX or connection.execute(text(f"SELECT 1 FROM {table} WHERE id = :id"), {"id": id}).first() is None:
        raise HTTPException(status_code=422, detail=f"This {label} does not exist.")


def validated(sent: dict) -> ArtworkInput:
    """The artwork fields as sent, or 422 naming the first field with a wrong type."""
    try:
        return ArtworkInput.model_validate(sent)
    except ValidationError as error:
        first = error.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        detail = f"The field '{field}' is required." if first["type"] == "missing" else f"The field '{field}' is not valid: {first['msg']}."
        raise HTTPException(status_code=422, detail=detail) from None


def checked_tag_ids(connection: Connection, ids: list[int]) -> list[int]:
    """The different tag ids, sorted, or 422 when one of them does not exist."""
    tag_ids = sorted(set(ids))
    known = [id for id in tag_ids if 1 <= id <= INT_MAX]
    found = connection.execute(text("SELECT count(*) FROM tags WHERE id = ANY(:ids)"), {"ids": known}).scalar()
    if found != len(tag_ids):
        raise HTTPException(status_code=422, detail="One or more tags do not exist.")
    return tag_ids


def create_artwork(
    connection: Connection, user: dict, artwork_text: str | None, state: str | None, photo: bytes | None
) -> dict:
    """Checks everything that needs no storage, then stores the photo and saves the artwork in one step."""
    if artwork_text is None:
        raise HTTPException(status_code=422, detail="The 'artwork' part is missing.")
    try:
        sent = json.loads(artwork_text)
        if not isinstance(sent, dict):
            raise ValueError
    except (ValueError, RecursionError):
        raise HTTPException(status_code=422, detail="The 'artwork' part must be a JSON object.") from None
    artwork = validated(sent)
    state = "COLLECTION" if state is None else state
    if state not in ("COLLECTION", "WATCHLIST"):
        raise HTTPException(status_code=422, detail="State must be COLLECTION or WATCHLIST.")
    if state == "COLLECTION" and photo is None:
        raise HTTPException(status_code=422, detail="Add a photo to put this artwork in your collection.")
    if photo is not None:
        try:
            photos.check(photo)
        except photos.InvalidPhoto as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
    title = checked_text(artwork.title, "Title", TITLE_MAX_LENGTH)
    museum = checked_text(artwork.museum, "Museum", MUSEUM_MAX_LENGTH)
    notes = checked_text(artwork.notes, "Notes", NOTES_MAX_LENGTH, notes=True)
    year_start, year_end, circa, _ = checked_date(artwork.date)
    refuse_unknown_entry(connection, "artists", artwork.artist_id, "artist")
    refuse_unknown_entry(connection, "subjects", artwork.subject_id, "subject")
    refuse_unknown_entry(connection, "movements", artwork.movement_id, "movement")
    tag_ids = checked_tag_ids(connection, artwork.tag_ids)

    path = None if photo is None else photos.save(photo)
    try:
        with connection.begin_nested():
            artwork_id = connection.execute(
                text(
                    "INSERT INTO artworks (user_id, collection_state, title, artist_id, date_display, year_start, "
                    "year_end, date_is_circa, subject_id, movement_id, museum, notes, artwork_photo_path) "
                    "VALUES (:user_id, :state, :title, :artist_id, :date_display, :year_start, :year_end, :circa, "
                    ":subject_id, :movement_id, :museum, :notes, :path) RETURNING id"
                ),
                {
                    "user_id": user["id"],
                    "state": state,
                    "title": title,
                    "artist_id": artwork.artist_id,
                    "date_display": None if year_start is None else date_display(year_start, year_end, circa),
                    "year_start": year_start,
                    "year_end": year_end,
                    "circa": circa,
                    "subject_id": artwork.subject_id,
                    "movement_id": artwork.movement_id,
                    "museum": museum,
                    "notes": notes,
                    "path": path,
                },
            ).scalar()
            if tag_ids:
                connection.execute(
                    text("INSERT INTO artwork_tags (artwork_id, tag_id) SELECT :artwork_id, unnest(CAST(:ids AS integer[]))"),
                    {"artwork_id": artwork_id, "ids": tag_ids},
                )
            return artwork_response(connection, artwork_id)
    except Exception:
        if path is not None:
            photos.delete(path)
        raise


def text_of(part) -> str | None:
    """A form part as text: a plain field as it is, a file part (what a browser sends for a Blob) decoded as UTF-8."""
    if part is None or isinstance(part, str):
        return part
    try:
        return part.file.read().decode()
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="A part of the request is not valid UTF-8 text.") from None


@app.post("/api/artworks", status_code=201)
async def create_artwork_endpoint(
    request: Request, user: dict = Depends(current_user), connection: Connection = Depends(get_connection)
):
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise HTTPException(status_code=422, detail="The request must be multipart/form-data.")
    try:
        form = await request.form()
    except StarletteHTTPException:
        raise HTTPException(status_code=422, detail="The request is not valid multipart/form-data.") from None
    photo = form.get("photo")
    if isinstance(photo, UploadFile):
        photo = await photo.read()
    elif photo is not None:
        raise HTTPException(status_code=422, detail="The photo must be sent as a file.")
    return await run_in_threadpool(
        create_artwork, connection, user, text_of(form.get("artwork")), text_of(form.get("state")), photo
    )


NOT_FOUND = "Artwork not found."
KEEP_WHILE_DISCOVERABLE = "An artwork must keep its title, artist and date while it is discoverable."


def own_artwork(connection: Connection, user: dict, artwork_id: str):
    """The calling user's artwork row, or 404 (also for another user's artwork and for an id that is no valid number)."""
    row = None
    if artwork_id.isascii() and artwork_id.isdigit() and 1 <= int(artwork_id) <= INT_MAX:
        row = connection.execute(
            text("SELECT * FROM artworks WHERE id = :id AND user_id = :user_id"),
            {"id": int(artwork_id), "user_id": user["id"]},
        ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return row


@app.get("/api/artworks/{artwork_id}")
def get_artwork(artwork_id: str, user: dict = Depends(current_user), connection: Connection = Depends(get_connection)):
    return artwork_response(connection, own_artwork(connection, user, artwork_id).id)


@app.patch("/api/artworks/{artwork_id}")
async def edit_artwork_endpoint(
    artwork_id: str, request: Request, user: dict = Depends(current_user), connection: Connection = Depends(get_connection)
):
    artwork = own_artwork(connection, user, artwork_id)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="The request body is missing.")
    try:
        sent = json.loads(body.decode())
    except (ValueError, RecursionError):
        raise HTTPException(status_code=422, detail="The request body is not valid JSON.") from None
    if not isinstance(sent, dict):
        raise HTTPException(status_code=422, detail="The request body must be a JSON object.")
    return await run_in_threadpool(edit_artwork, connection, artwork, sent)


def edit_artwork(connection: Connection, artwork, sent: dict) -> dict:
    """Changes only the fields present in `sent` (even as null), all or nothing."""
    # Only the fields that were sent are checked, so a wrong type in one that was not sent cannot matter.
    fields = {name: sent[name] for name in ArtworkInput.model_fields if name in sent}
    new = validated(fields)
    changes = {}
    if "title" in fields:
        changes["title"] = checked_text(new.title, "Title", TITLE_MAX_LENGTH)
    if "museum" in fields:
        changes["museum"] = checked_text(new.museum, "Museum", MUSEUM_MAX_LENGTH)
    if "notes" in fields:
        changes["notes"] = checked_text(new.notes, "Notes", NOTES_MAX_LENGTH, notes=True)
    if "date" in fields:
        year_start, year_end, circa, _ = checked_date(new.date)
        changes["year_start"], changes["year_end"], changes["date_is_circa"] = year_start, year_end, circa
        changes["date_display"] = None if year_start is None else date_display(year_start, year_end, circa)
    for name, table, label in (("artist_id", "artists", "artist"), ("subject_id", "subjects", "subject"), ("movement_id", "movements", "movement")):
        if name in fields:
            refuse_unknown_entry(connection, table, getattr(new, name), label)
            changes[name] = getattr(new, name)
    tag_ids = checked_tag_ids(connection, new.tag_ids) if "tag_ids" in fields else None
    if artwork.is_discoverable:
        result = {**artwork._mapping, **changes}
        if not result["title"] or result["artist_id"] is None or result["year_start"] is None:
            raise HTTPException(status_code=422, detail=KEEP_WHILE_DISCOVERABLE)

    with connection.begin_nested():
        # Column names come from the fixed code above, never from the request.
        assignments = "".join(f"{column} = :{column}, " for column in changes)
        connection.execute(
            text(f"UPDATE artworks SET {assignments}updated_at = clock_timestamp() WHERE id = :id"),
            {**changes, "id": artwork.id},
        )
        if tag_ids is not None:
            connection.execute(
                text("DELETE FROM artwork_tags WHERE artwork_id = :id AND tag_id != ALL(CAST(:ids AS integer[]))"),
                {"id": artwork.id, "ids": tag_ids},
            )
            connection.execute(
                text(
                    "INSERT INTO artwork_tags (artwork_id, tag_id) SELECT :id, unnest(CAST(:ids AS integer[])) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"id": artwork.id, "ids": tag_ids},
            )
    return artwork_response(connection, artwork.id)


@app.delete("/api/artworks/{artwork_id}", status_code=204)
def delete_artwork(artwork_id: str, user: dict = Depends(current_user), connection: Connection = Depends(get_connection)):
    artwork = own_artwork(connection, user, artwork_id)
    with connection.begin_nested():
        paths = connection.execute(
            text("SELECT path FROM detail_photos WHERE artwork_id = :id ORDER BY id"), {"id": artwork.id}
        ).scalars().all()
        if artwork.artwork_photo_path is not None:
            paths = [artwork.artwork_photo_path, *paths]
        connection.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": artwork.id})
        # If storage fails, the database change is undone and the 503 handler answers.
        for path in paths:
            photos.delete(path)
