from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_path_returns_not_found():
    assert client.get("/api/does-not-exist").status_code == 404


def test_health_without_api_prefix_returns_not_found():
    assert client.get("/health").status_code == 404


def test_posting_to_health_is_refused():
    assert client.post("/api/health").status_code == 405


def test_documentation_page_loads():
    assert client.get("/api/docs").status_code == 200
