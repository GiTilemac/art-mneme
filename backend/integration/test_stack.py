"""End-to-end scenarios against the running docker-compose.yaml stack."""

import json
import os
import re
import subprocess
from pathlib import Path

import httpx
from conftest import BASE_URL, JPEG, logged_in, new_user, wait_until_up

REPOSITORY = Path(__file__).resolve().parents[2]


def create(client, artwork, state="WATCHLIST", photo=None):
    files = {"artwork": (None, json.dumps(artwork)), "state": (None, state)}
    if photo:
        files["photo"] = ("photo.jpg", photo, "image/jpeg")
    response = client.post("/api/artworks", files=files)
    assert response.status_code == 201, response.text
    return response.json()


def artist(client, name):
    response = client.post("/api/artists", json={"name": name})
    assert response.status_code in (200, 201), response.text
    return response.json()


# 1. Start-up on an empty database


def test_the_app_starts_and_builds_the_schema_on_an_empty_database():
    assert httpx.get(f"{BASE_URL}/api/health").json() == {"status": "ok"}
    # Registering and listing need every table and the seeded movements.
    client = new_user()
    assert client.get("/api/artworks", params={"state": "COLLECTION"}).json()["total"] == 0
    assert client.get("/api/movements").json()["total"] > 0


# 2. Frontend served by the backend


def test_the_backend_serves_the_frontend_and_keeps_api_errors_as_json():
    home = httpx.get(f"{BASE_URL}/")
    assert home.status_code == 200 and home.headers["content-type"].startswith("text/html")
    assert httpx.get(f"{BASE_URL}/collection").text == home.text

    for asset in re.findall(r'(?:src|href)="(/assets/[^"]+)"', home.text):
        assert httpx.get(f"{BASE_URL}{asset}").status_code == 200, asset

    missing = httpx.get(f"{BASE_URL}/api/nothing-here")
    assert (missing.status_code, missing.json()) == (404, {"detail": "Not Found"})


# 3. Full user journey


def test_a_user_can_collect_find_explore_edit_and_delete_an_artwork(user):
    rembrandt = artist(user, "Rembrandt Integration")
    date = {"from_year": 500, "to_year": 450, "from_bc": True, "to_bc": True}
    watched = create(user, {"title": "Night Watch", "artist_id": rembrandt["id"], "date": date})
    other = create(user, {"title": "Self Portrait", "artist_id": rembrandt["id"]}, state="COLLECTION", photo=JPEG)
    assert watched["date"]["display"] == "500–450 BC" and watched["has_photo"] is False

    uploaded = user.put(f"/api/artworks/{watched['id']}/photo", files={"photo": ("p.jpg", JPEG, "image/jpeg")}).json()
    assert uploaded["state"] == "COLLECTION"
    photo = user.get(f"/api/artworks/{watched['id']}/photo", params={"v": uploaded["photo_version"]})
    assert photo.content == JPEG and "immutable" in photo.headers["cache-control"]

    listed = user.get("/api/artworks", params={"state": "COLLECTION"}).json()
    assert {item["id"] for item in listed["items"]} == {watched["id"], other["id"]}
    found = user.get("/api/artworks", params={"state": "COLLECTION", "q": "night", "from_year": 480, "from_bc": "true"})
    assert [item["id"] for item in found.json()["items"]] == [watched["id"]]
    related = user.get(f"/api/artworks/{watched['id']}/related", params={"by": "artist"}).json()
    assert [item["id"] for item in related["collection"]] == [other["id"]]

    edited = user.patch(f"/api/artworks/{watched['id']}", json={"title": "The Night Watch"}).json()
    assert edited["title"] == "The Night Watch"

    assert user.delete(f"/api/artworks/{watched['id']}").status_code == 204
    assert user.get(f"/api/artworks/{watched['id']}").status_code == 404
    assert user.get(f"/api/artworks/{watched['id']}/photo").status_code == 404


# 4. Session


def test_the_login_lasts_across_requests_and_ends_at_logout():
    email = "session-integration@example.com"
    client = new_user(email)
    assert client.get("/api/auth/me").json()["email"] == email
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    # The client still sends the old cookie; the server no longer accepts it.
    assert client.get("/api/auth/me").status_code == 401

    again = httpx.Client(base_url=BASE_URL)
    logged_in(again, again.post("/api/auth/login", json={"email": email, "password": "password1"}))
    assert again.get("/api/auth/me").json()["email"] == email


# 5. Two users


def test_two_users_see_only_their_own_artworks_but_share_artists():
    ana, ben = new_user(), new_user()
    shared = artist(ana, "Vermeer Integration")
    mine = create(ana, {"title": "Ana's", "artist_id": shared["id"]})

    assert artist(ben, "vermeer integration")["id"] == shared["id"]
    assert ben.get("/api/artworks", params={"state": "WATCHLIST"}).json()["total"] == 0
    assert ben.get(f"/api/artworks/{mine['id']}").status_code == 404
    assert ben.get("/api/artworks", params={"state": "WATCHLIST", "q": "ana"}).json()["items"] == []


# 6. Data survives a restart


def test_artworks_and_photos_survive_a_restart_of_the_app(user):
    kept = create(user, {"title": "Kept"}, state="COLLECTION", photo=JPEG)

    subprocess.run(["docker", "compose", "restart", "app"], cwd=REPOSITORY, check=True, env=os.environ)
    wait_until_up()

    assert user.get(f"/api/artworks/{kept['id']}").json()["title"] == "Kept"
    assert user.get(f"/api/artworks/{kept['id']}/photo").content == JPEG
