"""Exploring one's own artworks related to one artwork (`GET /api/artworks/{artwork_id}/related`)."""

import pytest
from sqlalchemy import text
from test_artwork_search import add, me
from test_artworks import add_entry, folder, user  # noqa: F401
from test_auth import NOT_LOGGED_IN, device, register, token_of

import photos

NOT_FOUND = {"detail": "Artwork not found."}
EMPTY = {"collection": [], "watchlist": []}


def url(id):
    return f"/api/artworks/{id}/related"


def related(client, id, **params):
    response = client.get(url(id), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(group):
    return [item["id"] for item in group]


@pytest.fixture
def rembrandt(conn):
    return add_entry(conn, "artists", "Rembrandt")


# Login and the starting artwork


def test_without_a_valid_session_it_is_refused(client, conn):
    response = device().get(url(1), params={"by": "artist"})

    assert (response.status_code, response.json()) == (401, NOT_LOGGED_IN)


@pytest.mark.parametrize("id", ["other", "missing", "0", "-1", "abc", "1.5", "99999999999"])
def test_an_unknown_id_or_another_users_artwork_is_not_found(client, conn, id):
    owner = device(token_of(register(client, "a@example.com")))
    artwork = add(conn, me(owner))
    other = device(token_of(register(client, "b@example.com")))
    id = {"other": artwork, "missing": artwork + 1000}.get(id, id)

    # A bad `by` too: the starting artwork is checked first.
    response = other.get(url(id), params={"by": "nonsense"})

    assert (response.status_code, response.json()) == (404, NOT_FOUND)


# Parameters


@pytest.mark.parametrize(
    "params, detail",
    [
        ({}, "Choose artist, subject, movement or museum."),
        ({"by": "title"}, "Choose artist, subject, movement or museum."),
        ({"by": "tags"}, "Exploring by tags is not available yet."),
        ({"by": "artist", "include_collection": "yes"}, "include_collection must be true or false."),
        ({"by": "artist", "include_watchlist": "2"}, "include_watchlist must be true or false."),
        ({"by": "artist", "include_watchlist": ""}, "include_watchlist must be true or false."),
    ],
)
def test_a_wrong_by_or_flag_is_refused(user, conn, params, detail):
    artwork = add(conn, me(user))

    response = user.get(url(artwork), params=params)

    assert (response.status_code, response.json()) == (422, {"detail": detail})


def test_both_sources_off_gives_two_empty_lists(user, conn, rembrandt):
    start = add(conn, me(user), artist_id=rembrandt)
    add(conn, me(user), artist_id=rembrandt)

    assert related(user, start, by="artist", include_collection="false") == EMPTY


# Matching


@pytest.mark.parametrize("by, table, column", [("artist", "artists", "artist_id"), ("subject", "subjects", "subject_id")])
def test_same_artist_or_subject_is_matched_by_id(user, conn, by, table, column):
    shared, other = add_entry(conn, table, "Shared"), add_entry(conn, table, "Other")
    start = add(conn, me(user), state="WATCHLIST", **{column: shared})
    match = add(conn, me(user), **{column: shared})
    add(conn, me(user), **{column: other})

    assert ids(related(user, start, by=by)["collection"]) == [match]


def test_same_movement_is_matched_by_id(user, conn):
    first, second = conn.execute(text("SELECT id FROM movements ORDER BY id LIMIT 2")).scalars().all()
    start = add(conn, me(user), movement_id=first)
    match = add(conn, me(user), movement_id=first)
    add(conn, me(user), movement_id=second)

    assert ids(related(user, start, by="movement")["collection"]) == [match]


def test_same_museum_ignores_capitals_but_not_accents_or_parts(user, conn):
    start = add(conn, me(user), museum="Rijksmuseum")
    match = add(conn, me(user), museum="rijksmuseum")
    add(conn, me(user), museum="Rijks")
    other = add(conn, me(user), museum="Musée")
    add(conn, me(user), museum="Musee")

    assert ids(related(user, start, by="museum")["collection"]) == [match]
    assert ids(related(user, other, by="museum")["collection"]) == []


@pytest.mark.parametrize("by", ["artist", "subject", "movement", "museum"])
def test_a_starting_artwork_without_that_value_finds_nothing(user, conn, by):
    start = add(conn, me(user))
    add(conn, me(user))

    assert related(user, start, by=by) == EMPTY


def test_the_starting_artwork_is_never_in_its_own_results(user, conn, rembrandt):
    start = add(conn, me(user), artist_id=rembrandt)

    assert related(user, start, by="artist", include_watchlist="true") == EMPTY


# Groups


def test_collection_by_default_and_watchlist_only_when_asked(user, conn, rembrandt):
    start = add(conn, me(user), artist_id=rembrandt)
    in_collection = add(conn, me(user), artist_id=rembrandt)
    in_watchlist = add(conn, me(user), state="WATCHLIST", artist_id=rembrandt)

    default = related(user, start, by="artist")
    both = related(user, start, by="artist", include_watchlist="true")

    assert (ids(default["collection"]), default["watchlist"]) == ([in_collection], [])
    assert (ids(both["collection"]), ids(both["watchlist"])) == ([in_collection], [in_watchlist])
    assert both["collection"] == [user.get(f"/api/artworks/{in_collection}").json()]


def test_other_users_artworks_never_appear(client, conn):
    ben = device(token_of(register(client, "ben@example.com")))
    artist = add_entry(conn, "artists", "Rembrandt")
    add(conn, me(ben), artist_id=artist, museum="Louvre")
    add(conn, me(ben), state="WATCHLIST", artist_id=artist, museum="Louvre")
    ana = device(token_of(register(client, "ana@example.com")))
    start = add(conn, me(ana), artist_id=artist, museum="Louvre")

    assert related(ana, start, by="artist", include_watchlist="true") == EMPTY
    assert related(ana, start, by="museum", include_watchlist="true") == EMPTY


# Order and size


def test_each_group_holds_the_50_newest_highest_id_first_on_ties(user, conn, rembrandt):
    start = add(conn, me(user), artist_id=rembrandt)
    oldest = add(conn, me(user), artist_id=rembrandt, created_at="2020-01-01")
    same_moment = [add(conn, me(user), artist_id=rembrandt, created_at="2026-01-01") for _ in range(50)]

    collection = ids(related(user, start, by="artist")["collection"])

    assert collection == sorted(same_moment, reverse=True)
    assert oldest not in collection


# Nothing else changes


def test_exploring_only_reads_and_works_while_storage_is_down(user, conn, rembrandt, monkeypatch):
    start = add(conn, me(user), artist_id=rembrandt)
    match = add(conn, me(user), artist_id=rembrandt)
    before = conn.execute(text("SELECT * FROM artworks ORDER BY id")).all()

    def unavailable(*args, **kwargs):
        raise photos.StorageUnavailable

    for name in ("save", "read", "delete"):
        monkeypatch.setattr(photos, name, unavailable)

    assert ids(related(user, start, by="artist")["collection"]) == [match]
    assert conn.execute(text("SELECT * FROM artworks ORDER BY id")).all() == before
