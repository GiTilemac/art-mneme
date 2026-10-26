"""Integration tests: the docker-compose.yaml stack, used only over HTTP like a browser.

Run with `make integration` from the repository root. It starts the stack with empty volumes,
sets INTEGRATION_URL and COMPOSE_PROJECT_NAME, and removes everything afterwards.
"""

import os
import time
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("INTEGRATION_URL", "http://localhost:8092")
JPEG = b"\xff\xd8\xff\xe0" + b"integration photo" * 100


def wait_until_up(timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if httpx.get(f"{BASE_URL}/api/health").status_code == 200:
                return
        except httpx.TransportError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(f"The app at {BASE_URL} did not start in {timeout} seconds.")
        time.sleep(1)


def logged_in(client: httpx.Client, response: httpx.Response) -> httpx.Client:
    """Sends the session cookie by hand: httpx keeps Secure cookies to https, and the stack runs on http."""
    assert response.status_code in (200, 201), response.text
    client.headers["Cookie"] = f"session={response.cookies['session']}"
    return client


def new_user(email: str | None = None, password: str = "password1") -> httpx.Client:
    """A client logged in as a newly registered user."""
    client = httpx.Client(base_url=BASE_URL)
    email = email or f"{uuid.uuid4().hex[:12]}@example.com"
    return logged_in(client, client.post("/api/auth/register", json={"email": email, "password": password}))


@pytest.fixture(scope="session", autouse=True)
def stack():
    wait_until_up()


@pytest.fixture
def user():
    client = new_user()
    yield client
    client.close()
