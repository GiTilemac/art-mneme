import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Connection, text

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
