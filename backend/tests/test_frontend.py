"""Serving the built frontend from FRONTEND_DIR (any address outside /api)."""

import pytest


@pytest.fixture
def built(tmp_path, monkeypatch):
    (tmp_path / "_shell.html").write_text("<html>shell</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("secret")
    monkeypatch.setenv("FRONTEND_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize("path", ["/", "/collection", "/artworks/12/explore"])
def test_any_page_address_gets_the_app_page(client, built, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.text == "<html>shell</html>"


def test_a_built_file_is_served_as_it_is(client, built):
    response = client.get("/assets/app.js")

    assert (response.status_code, response.text) == (200, "console.log(1)")


def test_files_outside_the_frontend_folder_are_never_served(client, built):
    response = client.get("/..%2Fsecret.txt")

    assert "secret" not in response.text


@pytest.mark.parametrize("path", ["/api", "/api/nothing-here"])
def test_an_unknown_api_address_is_a_json_404_not_the_page(client, built, path):
    response = client.get(path)

    assert (response.status_code, response.json()) == (404, {"detail": "Not Found"})


def test_without_frontend_dir_nothing_is_served(client, monkeypatch):
    monkeypatch.delenv("FRONTEND_DIR", raising=False)

    assert client.get("/").status_code == 404
