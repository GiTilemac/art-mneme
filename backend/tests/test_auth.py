"""Registration, login, logout and the session cookie (`/api/auth/*`)."""

import base64
import hashlib
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from main import app, current_user

ANA = {"email": "ana@example.com", "password": "password1"}
THIRTY_DAYS = 2592000
NOT_LOGGED_IN = {"detail": "Please sign in again."}


def device(token=None):
    """Another client, like a second device; it sends `token` as its session cookie. Needs the `client` fixture."""
    return TestClient(app, base_url="https://testserver", cookies={"session": token} if token else None)


def cookie(response):
    """The `session` cookie from the `Set-Cookie` header: its value and its attributes, names in lower case."""
    value, *attributes = response.headers["set-cookie"].split("; ")
    name, _, token = value.partition("=")
    assert name == "session"
    parsed = {}
    for attribute in attributes:
        key, _, setting = attribute.partition("=")
        parsed[key.lower()] = setting
    return token, parsed


def token_of(response):
    return cookie(response)[0]


def register(client, email="ana@example.com", password="password1"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def login(client, email="ana@example.com", password="password1"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def session_row(conn, token):
    return conn.execute(
        text("SELECT * FROM sessions WHERE token_hash = :hash"), {"hash": hashlib.sha256(token.encode()).hexdigest()}
    ).one_or_none()


def set_expiry(conn, token, expression):
    conn.execute(
        text(f"UPDATE sessions SET expires_at = {expression} WHERE token_hash = :hash"),
        {"hash": hashlib.sha256(token.encode()).hexdigest()},
    )


def count_users(conn):
    return conn.execute(text("SELECT count(*) FROM users")).scalar()


def password_hash(conn, email):
    return conn.execute(text("SELECT password_hash FROM users WHERE email = :email"), {"email": email}).scalar()


# Register


def test_registering_answers_with_the_new_user_and_logs_them_in(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "email": "ana@example.com"}
    assert isinstance(body["id"], int)
    me = device(token_of(response)).get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == body


def test_registering_stores_the_email_without_surrounding_spaces_and_in_lower_case(client, conn):
    response = register(client, "  Ana@Example.COM ")

    assert response.status_code == 201
    assert response.json()["email"] == "ana@example.com"
    assert conn.execute(text("SELECT email FROM users")).scalars().all() == ["ana@example.com"]


@pytest.mark.parametrize("email", ["ana@example.com", "ANA@example.com", " ana@example.com"])
def test_registering_an_email_that_exists_is_refused(client, email):
    register(client)

    response = register(client, email, "other-password")

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists."}
    assert "set-cookie" not in response.headers
    assert login(client).status_code == 200


@pytest.mark.parametrize("password", ["12345678", "pass word", "        ", "παράδειγμα", "αβγδεζηθ"])
def test_password_of_at_least_8_characters_is_accepted(client, password):
    assert register(client, password=password).status_code == 201
    assert login(client, password=password).status_code == 200


def test_spaces_in_a_password_are_not_trimmed(client):
    register(client, password=" pass word ")

    assert login(client, password="pass word").status_code == 401
    assert login(client, password=" pass word ").status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"email": "ana@example.com", "password": "1234567"},
        {"email": "ana@example.com", "password": "αβγδεζη"},
        {"email": "ana@example.com", "password": ""},
        {"email": "ana@example.com"},
    ],
)
def test_registering_with_a_short_or_missing_password_is_refused(client, conn, body):
    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422
    assert response.json() == {"detail": "Password must be at least 8 characters."}
    assert count_users(conn) == 0


@pytest.mark.parametrize(
    "body",
    [
        {"email": "ana", "password": "password1"},
        {"email": "ana@", "password": "password1"},
        {"email": "@example.com", "password": "password1"},
        {"email": "ana@example", "password": "password1"},
        {"email": "", "password": "password1"},
        {"password": "password1"},
    ],
)
def test_registering_with_an_invalid_email_is_refused(client, conn, body):
    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422
    assert response.json() == {"detail": "Enter a valid email address."}
    assert count_users(conn) == 0


def assert_error_shape(response):
    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert isinstance(response.json()["detail"], str)
    assert response.json()["detail"].endswith(".")


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "",
        '{"email": "ana@example.com", "password": 12345678}',
        '{"email": 5, "password": "password1"}',
        "[]",
        "null",
    ],
)
def test_registering_with_a_body_that_is_not_valid_is_refused_in_the_error_shape(client, conn, content):
    response = client.post("/api/auth/register", content=content, headers={"Content-Type": "application/json"})

    assert_error_shape(response)
    assert count_users(conn) == 0


def test_registering_with_a_body_that_is_not_json_text_is_refused_in_the_error_shape(client, conn):
    response = client.post("/api/auth/register", content="hello", headers={"Content-Type": "text/plain"})

    assert_error_shape(response)
    assert count_users(conn) == 0


@pytest.mark.parametrize("path", ["/api/auth/register", "/api/auth/login"])
def test_body_that_is_not_valid_utf8_is_refused_in_the_error_shape(client, conn, path):
    response = client.post(path, content=b'{"email":"\xff"}', headers={"Content-Type": "application/json"})

    assert_error_shape(response)
    assert count_users(conn) == 0


# Validation errors in the Error shape, for the whole API


def test_validation_errors_use_the_error_shape_on_more_than_one_endpoint(client):
    register_wrong_type = client.post("/api/auth/register", json={"email": "ana@example.com", "password": 12345678})
    login_not_json = client.post("/api/auth/login", content="not json", headers={"Content-Type": "application/json"})

    assert_error_shape(register_wrong_type)
    assert_error_shape(login_not_json)


def test_password_hash_does_not_contain_the_password(client, conn):
    register(client)

    assert "password1" not in password_hash(conn, "ana@example.com")


def test_two_users_with_the_same_password_have_different_hashes(client, conn):
    register(client, "ana@example.com")
    register(client, "bob@example.com")

    assert password_hash(conn, "ana@example.com") != password_hash(conn, "bob@example.com")


def test_registering_while_logged_in_switches_to_the_new_user(client):
    register(client, "ana@example.com")

    response = register(client, "bob@example.com")

    assert response.status_code == 201
    assert client.get("/api/auth/me").json()["email"] == "bob@example.com"


# Login


def test_login_with_correct_email_and_password_logs_the_user_in(client):
    user = register(client).json()

    response = login(device())

    assert response.status_code == 200
    assert response.json() == user
    me = device(token_of(response)).get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == user


def test_login_matches_the_email_ignoring_capitals_and_surrounding_spaces(client):
    user = register(client).json()

    response = login(device(), " ANA@example.com")

    assert response.status_code == 200
    assert response.json() == user


def test_login_with_the_password_in_other_capitals_is_refused(client):
    register(client)

    assert login(device(), password="Password1").status_code == 401


def test_login_with_wrong_password_and_with_unknown_email_give_the_same_answer(client):
    register(client)

    wrong_password = login(device(), password="password2")
    unknown_email = login(device(), "bob@example.com")

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json() == {"detail": "Email or password is incorrect."}
        assert "set-cookie" not in response.headers
    assert wrong_password.content == unknown_email.content


@pytest.mark.parametrize(
    "content",
    ['{"password": "password1"}', "not json", '{"email": "ana@example.com", "password": "1234567"}'],
)
def test_login_with_missing_or_malformed_fields_is_refused_in_the_error_shape(client, content):
    register(client)

    response = client.post("/api/auth/login", content=content, headers={"Content-Type": "application/json"})

    assert_error_shape(response)


def test_logging_in_twice_gives_two_separate_sessions_that_both_work(client):
    register(client)

    first, second = token_of(login(device())), token_of(login(device()))

    assert first != second
    assert device(first).get("/api/auth/me").status_code == 200
    assert device(second).get("/api/auth/me").status_code == 200


# The session cookie


@pytest.mark.parametrize("action", [register, login])
def test_session_cookie_is_http_only_secure_lax_for_the_whole_site_and_lasts_30_days(client, action):
    if action is login:
        register(device())

    token, attributes = cookie(action(client))

    assert token
    assert "httponly" in attributes
    assert "secure" in attributes
    assert attributes["samesite"].lower() == "lax"
    assert attributes["path"] == "/"
    assert attributes["max-age"] == str(THIRTY_DAYS)


def test_session_token_is_random_and_does_not_contain_the_email(client):
    register(client)

    tokens = [token_of(login(device())) for _ in range(2)]

    assert tokens[0] != tokens[1]
    for token in tokens:
        assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) >= 32
        assert "ana@example.com" not in token


def test_database_stores_only_a_hash_of_the_token(client, conn):
    token = token_of(register(client))

    row = session_row(conn, token)

    assert row is not None
    assert token not in [str(value) for value in row]
    assert device(row.token_hash).get("/api/auth/me").status_code == 401


def test_using_a_session_renews_it_for_30_days(client, conn):
    token = token_of(register(client))
    set_expiry(conn, token, "now() + interval '1 day'")

    response = device(token).get("/api/auth/me")

    assert response.status_code == 200
    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)
    in_30_days = conn.execute(text("SELECT now() + interval '30 days'")).scalar()
    assert session_row(conn, token).expires_at == in_30_days


def test_session_used_29_days_after_its_last_use_still_works(client, conn):
    token = token_of(register(client))
    set_expiry(conn, token, "now() + interval '1 day'")

    assert device(token).get("/api/auth/me").status_code == 200


def test_expired_session_is_refused_and_not_renewed(client, conn):
    token = token_of(register(client))
    set_expiry(conn, token, "now() - interval '1 second'")
    expired_at = session_row(conn, token).expires_at

    response = device(token).get("/api/auth/me")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    assert session_row(conn, token).expires_at == expired_at


def test_me_and_logout_use_the_one_login_check():
    for path in ("/api/auth/me", "/api/auth/logout"):
        route = next(route for route in app.routes if getattr(route, "path", None) == path)
        assert current_user in [dependency.call for dependency in route.dependant.dependencies]


# Me


def test_me_answers_with_only_the_id_and_email_of_the_logged_in_user(client):
    user = register(client).json()

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == user
    assert set(response.json()) == {"id", "email"}


def no_cookie(client, conn):
    return None


def unknown_cookie(client, conn):
    return secrets.token_urlsafe(32)


def made_up_cookie(client, conn):
    return "made-up"


def expired_cookie(client, conn):
    token = token_of(register(client))
    set_expiry(conn, token, "now() - interval '1 second'")
    return token


def logged_out_cookie(client, conn):
    token = token_of(register(client))
    device(token).post("/api/auth/logout")
    return token


NOT_LOGGED_IN_CASES = [no_cookie, unknown_cookie, made_up_cookie, expired_cookie, logged_out_cookie]


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_me_without_a_valid_session_is_refused(client, conn, case):
    response = device(case(client, conn)).get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN


# Logout


def test_logout_ends_the_session(client, conn):
    token = token_of(register(client))

    response = device(token).post("/api/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    _, attributes = cookie(response)
    assert attributes["max-age"] == "0"
    assert session_row(conn, token) is None
    for _ in range(2):
        assert device(token).get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_logout_without_a_valid_session_is_refused(client, conn, case):
    response = device(case(client, conn)).post("/api/auth/logout")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN


def test_logout_ends_only_that_session(client):
    register(client)
    first, second = token_of(login(device())), token_of(login(device()))

    assert device(first).post("/api/auth/logout").status_code == 204

    assert device(first).get("/api/auth/me").status_code == 401
    assert device(second).get("/api/auth/me").status_code == 200
