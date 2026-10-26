"""Listing one's own artworks of one state, newest first, 50 per page (`GET /api/artworks`)."""

import pytest
from sqlalchemy import event, text
from test_artworks import JPEG, folder, post, user, watch  # noqa: F401
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of

import photos

URL = "/api/artworks"
CHOOSE = {"detail": "Choose Collection or Watchlist."}


def me(client):
    return client.get("/api/auth/me").json()["id"]


def insert(conn, user_id, count, state="WATCHLIST", created_at="2026-01-01"):
    """`count` artworks with the same `created_at`, inserted directly; returns their ids in insert order."""
    return conn.execute(
        text(
            "INSERT INTO artworks (user_id, collection_state, artwork_photo_path, created_at) "
            "SELECT :user_id, :state, CASE WHEN :state = 'COLLECTION' THEN 'p.jpg' END, :created_at "
            "FROM generate_series(1, :count) ORDER BY 1 RETURNING id"
        ),
        {"user_id": user_id, "state": state, "count": count, "created_at": created_at},
    ).scalars().all()


def listed(client, state="WATCHLIST", **params):
    response = client.get(URL, params={"state": state, **params})
    assert response.status_code == 200, response.text
    return response.json()


def ids(page):
    return [item["id"] for item in page["items"]]


# Login


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_without_a_valid_session_it_is_refused_before_the_state_is_checked(client, conn, case):
    response = device(case(client, conn)).get(URL)

    assert (response.status_code, response.json()) == (401, NOT_LOGGED_IN)


def test_a_valid_session_is_renewed_for_30_days(client):
    token = token_of(register(client))

    renewed, attributes = cookie(device(token).get(URL, params={"state": "COLLECTION"}))

    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# Own artworks, split by state


def test_each_list_shows_only_own_artworks_of_its_state(client, conn):
    ben = device(token_of(register(client, "ben@example.com")))
    insert(conn, me(ben), 4, "COLLECTION")
    ana = device(token_of(register(client, "ana@example.com")))
    collection = insert(conn, me(ana), 2, "COLLECTION")
    watchlist = insert(conn, me(ana), 3)

    assert sorted(ids(listed(ana, "COLLECTION"))) == collection and listed(ana, "COLLECTION")["total"] == 2
    assert sorted(ids(listed(ana, "WATCHLIST"))) == watchlist and listed(ana, "WATCHLIST")["total"] == 3


def test_an_empty_list_is_an_empty_first_page(user):
    assert listed(user, "COLLECTION") == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_an_artwork_moved_to_the_collection_is_listed_there(user):
    artwork = watch(user, {}).json()

    user.put(f"{URL}/{artwork['id']}/photo", files={"photo": ("p.jpg", JPEG, "image/jpeg")})

    assert ids(listed(user, "COLLECTION")) == [artwork["id"]]
    assert ids(listed(user, "WATCHLIST")) == []


# Order


def test_newest_first_then_highest_id_and_editing_does_not_move_an_artwork(user, conn):
    old = insert(conn, me(user), 1, created_at="2026-01-01")
    same_moment = insert(conn, me(user), 2, created_at="2026-02-01")
    new = insert(conn, me(user), 1, created_at="2026-03-01")

    user.patch(f"{URL}/{old[0]}", json={"title": "Edited"})

    assert ids(listed(user)) == [new[0], same_moment[1], same_moment[0], old[0]]


# Pages


def test_pages_hold_50_each_and_every_artwork_exactly_once(user, conn):
    created = insert(conn, me(user), 120)

    pages = [listed(user), listed(user, page=2), listed(user, page=3), listed(user, page=4)]

    assert [len(page["items"]) for page in pages] == [50, 50, 20, 0]
    assert [page["page"] for page in pages] == [1, 2, 3, 4]
    assert {page["total"] for page in pages} == {120}
    assert sorted(id for page in pages for id in ids(page)) == created


@pytest.mark.parametrize("count, second_page", [(50, 0), (51, 1)])
def test_the_second_page_starts_after_50(user, conn, count, second_page):
    insert(conn, me(user), count)

    assert len(listed(user, page=2)["items"]) == second_page


@pytest.mark.parametrize("page", ["1000000", "100000000000000000000"])
def test_a_far_page_is_empty(user, conn, page):
    insert(conn, me(user), 1)

    response = user.get(URL, params={"state": "WATCHLIST", "page": page})

    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.json()["items"] == [] and response.json()["total"] == 1


@pytest.mark.parametrize("page", ["0", "-1", "abc", "1.5", ""])
def test_a_bad_page_is_refused(user, page):
    response = user.get(URL, params={"state": "WATCHLIST", "page": page})

    assert response.status_code == 422
    assert list(response.json()) == ["detail"] and isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("state", [None, "", "collection", "DONE"])
def test_a_missing_or_wrong_state_is_refused(user, state):
    response = user.get(URL, params={} if state is None else {"state": state})

    assert (response.status_code, response.json()) == (422, CHOOSE)


# Items


def test_list_item_equals_the_single_artwork_response(user, conn):
    tags = [user.post("/api/tags", json={"name": name}).json()["id"] for name in ("zebra", "apple")]
    full = post(user, {"title": "Mona", "notes": "mine", "tag_ids": tags}, photo=JPEG).json()
    empty = watch(user, {}).json()
    conn.execute(text("INSERT INTO detail_photos (artwork_id, path) VALUES (:id, 'd.jpg')"), {"id": full["id"]})

    collection, watchlist = listed(user, "COLLECTION")["items"], listed(user, "WATCHLIST")["items"]

    assert collection == [user.get(f"{URL}/{full['id']}").json()]
    assert watchlist == [user.get(f"{URL}/{empty['id']}").json()]
    assert [tag["name"] for tag in collection[0]["tags"]] == ["apple", "zebra"]
    assert watchlist[0]["photo_version"] is None and len(collection[0]["photo_version"]) == 16


def test_search_and_filter_parameters_are_ignored_for_now(user, conn):
    created = insert(conn, me(user), 2)

    assert sorted(ids(listed(user, q="nothing", artist_id="1", museum="x"))) == created


def test_the_list_works_while_photo_storage_is_down(user, monkeypatch):
    post(user, {}, photo=JPEG)

    def unavailable(*args, **kwargs):
        raise photos.StorageUnavailable

    for name in ("save", "read", "delete"):
        monkeypatch.setattr(photos, name, unavailable)

    assert len(listed(user, "COLLECTION")["items"]) == 1


def test_the_number_of_queries_does_not_grow_with_the_number_of_artworks(user, conn):
    def queries_for(count):
        conn.execute(text("DELETE FROM artworks"))
        insert(conn, me(user), count)
        statements = []
        listener = lambda *args: statements.append(1)  # noqa: E731
        event.listen(conn, "before_cursor_execute", listener)
        listed(user)
        event.remove(conn, "before_cursor_execute", listener)
        return len(statements)

    assert queries_for(5) == queries_for(50)
