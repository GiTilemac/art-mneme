import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("E2E_URL", "http://localhost:8093")


@pytest.fixture(scope="session", autouse=True)
def stack_is_up():
    deadline = time.monotonic() + 60
    while True:
        try:
            if httpx.get(f"{BASE_URL}/api/health").status_code == 200:
                return
        except httpx.TransportError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(f"{BASE_URL} did not come up")
        time.sleep(1)
