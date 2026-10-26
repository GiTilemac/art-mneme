"""Searching and filtering one's own artworks (`q` and the filters of `GET /api/artworks`)."""

import pytest
from sqlalchemy import text
from test_artworks import THIS_YEAR, add_entry, folder, user  # noqa: F401
from test_auth import NOT_LOGGED_IN, device, register, token_of
from test_tags import add_tag

URL = "/api/artworks"
BAD = {"detail": "Filter values are not valid."}


def me(client):
    return client.get("/api/auth/me").json()["id"]


def add(conn, user_id, state="COLLECTION", tags=(), **fields):
    """An artwork inserted directly; `fields` are artworks columns. Returns its id."""
    fields = {"title": "", "museum": "", "notes": "", **fields}
    columns = ", ".join(["user_id", "collection_state", "artwork_photo_path", *fields])
    placeholders = ", ".join([":user_id", ":state", "CASE WHEN :state = 'COLLECTION' THEN 'p.jpg' END", *(f":{name}" for name in fields)])
    id = conn.execute(
        text(f"INSERT INTO artworks ({columns}) VALUES ({placeholders}) RETURNING id"),
        {"user_id": user_id, "state": state, **fields},
    ).scalar()
    for tag in tags:
        conn.execute(text("INSERT INTO artwork_tags (artwork_id, tag_id) VALUES (:a, :t)"), {"a": id, "t": tag})
    return id


def found(client, state="COLLECTION", **params):
    response = client.get(URL, params={"state": state, **params})
    assert response.status_code == 200, response.text
    return sorted(item["id"] for item in response.json()["items"])


@pytest.fixture
def night_watch(user, conn):
    """The issue's example artwork, plus one that matches nothing."""
    rembrandt = add_entry(conn, "artists", "Rembrandt van Rijn")
    portrait = add_entry(conn, "subjects", "Group portrait")
    golden = add_tag(conn, "dutch golden age")
    id = add(conn, me(user), title="The Night Watch", artist_id=rembrandt, subject_id=portrait, museum="Rijksmuseum",
             tags=[golden], notes="zebra")
    other = add(conn, me(user), title="Other")
    return id, other


# Search q


@pytest.mark.parametrize("q", ["night", "REMBR", "portrait", "golden", "rijks"])
def test_search_matches_part_of_a_word_in_each_searched_field(user, night_watch, q):
    assert found(user, q=q) == [night_watch[0]]


@pytest.mark.parametrize("q, hit", [("night rembrandt", True), ("night vermeer", False), ("  night   watch ", True)])
def test_every_word_of_the_search_must_be_found(user, night_watch, q, hit):
    assert found(user, q=q) == ([night_watch[0]] if hit else [])


def test_notes_and_movement_are_not_searched(user, conn, night_watch):
    movement = conn.execute(text("SELECT id, name FROM movements LIMIT 1")).one()
    add(conn, me(user), movement_id=movement.id, are_notes_discoverable=True, notes="zebra")

    assert found(user, q="zebra") == []
    assert found(user, q=movement.name) == []


def test_search_ignores_capitals_but_not_accents(user, conn):
    durer = add(conn, me(user), artist_id=add_entry(conn, "artists", "Albrecht Dürer"))

    assert found(user, q="durer") == []
    assert found(user, q="DÜRER") == [durer]


def test_an_empty_search_does_not_narrow_the_list(user, night_watch):
    assert found(user, q="   ") == sorted(night_watch)


def test_search_goes_through_the_shared_cleaning(user, conn):
    percent = add(conn, me(user), title="100% oil")
    add(conn, me(user), title="1000 oil")

    assert found(user, q="0%") == [percent]
    response = user.get(URL, params={"state": "COLLECTION", "q": "a\x07b"})
    assert (response.status_code, response.json()) == (422, {"detail": "Search contains characters that are not allowed."})


def test_a_search_longer_than_200_characters_is_refused(user):
    assert user.get(URL, params={"state": "COLLECTION", "q": "a" * 200}).status_code == 200
    response = user.get(URL, params={"state": "COLLECTION", "q": "a" * 201})

    assert (response.status_code, response.json()) == (422, {"detail": "Search must be at most 200 characters."})


def test_an_artwork_found_through_several_tags_is_listed_and_counted_once(user, conn):
    id = add(conn, me(user), title="cat", tags=[add_tag(conn, "cat one"), add_tag(conn, "cat two")])
    add(conn, me(user))  # nothing to find: no title, artist, tags or museum

    response = user.get(URL, params={"state": "COLLECTION", "q": "cat"}).json()

    assert [item["id"] for item in response["items"]] == [id] and response["total"] == 1


def test_other_users_artworks_and_the_other_state_are_never_found(client, conn):
    ben = device(token_of(register(client, "ben@example.com")))
    add(conn, me(ben), title="Night")
    ana = device(token_of(register(client, "ana@example.com")))
    add(conn, me(ana), state="WATCHLIST", title="Night")
    mine = add(conn, me(ana), title="Night", is_discoverable=True)

    assert found(ana, q="night") == [mine]


# Filters


def test_artist_movement_museum_and_tag_filters(user, conn):
    rembrandt, vermeer = add_entry(conn, "artists", "Rembrandt"), add_entry(conn, "artists", "Vermeer")
    baroque = conn.execute(text("SELECT id FROM movements LIMIT 1")).scalar()
    cat, dog = add_tag(conn, "cat"), add_tag(conn, "dog")
    a = add(conn, me(user), artist_id=rembrandt, movement_id=baroque, museum="Rijksmuseum", tags=[cat, dog])
    b = add(conn, me(user), artist_id=vermeer, museum="Louvre", tags=[cat])
    add(conn, me(user))

    assert found(user, artist_id=rembrandt) == [a]
    assert found(user, movement_id=baroque) == [a]
    assert found(user, museum=" rijksMUSEUM  ") == [a]
    assert found(user, museum="rijks") == []
    assert found(user, tag_ids=[cat]) == sorted([a, b])
    assert found(user, tag_ids=[cat, dog]) == [a]


@pytest.mark.parametrize("params", [{"artist_id": "99999"}, {"movement_id": "0"}, {"tag_ids": "99999"}])
def test_an_unknown_id_gives_an_empty_page(user, conn, params):
    add(conn, me(user), artist_id=add_entry(conn, "artists", "Rembrandt"), tags=[add_tag(conn, "cat")])

    assert found(user, **params) == []


@pytest.mark.parametrize(
    "params",
    [{"artist_id": "abc"}, {"movement_id": "1.5"}, {"artist_id": ""}, {"tag_ids": "x"}, {"from_year": "0"},
     {"from_year": "abc"}, {"to_year": "100001"}, {"from_bc": "maybe"}, {"artist_id": "99999999999"}],
)
def test_bad_filter_values_are_refused(user, params):
    response = user.get(URL, params={"state": "COLLECTION", **params})

    assert (response.status_code, response.json()) == (422, BAD)


# Date range


@pytest.mark.parametrize(
    "start, end, params, hit",
    [
        (1600, 1605, {"from_year": 1602, "to_year": 1610}, True),
        (1600, 1605, {"from_year": 1605, "to_year": 1610}, True),
        (1600, 1605, {"from_year": 1606, "to_year": 1610}, False),
        (-500, -450, {"from_year": 480, "from_bc": "true", "to_year": 460, "to_bc": "true"}, True),
        (-500, -450, {"from_year": 440, "from_bc": "true", "to_year": 400, "to_bc": "true"}, False),
        (-30, 14, {"from_year": 10, "to_year": 20}, True),
        (-30, 14, {"from_year": 1, "from_bc": "true", "to_year": 1}, True),
        (-30, 14, {"from_year": 50, "from_bc": "true", "to_year": 40, "to_bc": "true"}, False),
        (1600, None, {"from_year": 1600, "to_year": 1600}, True),
        (1600, None, {"from_year": 1601}, False),
        (1600, 1605, {"from_year": 1605}, True),
        (1600, 1605, {"to_year": 1600}, True),
        (1600, 1605, {"to_year": 1599, "from_bc": "true"}, False),
    ],
    ids=["overlap", "touching", "after", "bc", "bc_after", "bc_into_ad", "around_year_1", "bc_before",
         "one_year", "one_year_after", "only_from", "only_to", "only_to_with_lone_from_bc"],
)
def test_date_filter_finds_overlapping_ranges(user, conn, start, end, params, hit):
    id = add(conn, me(user), year_start=start, year_end=end, date_is_circa=True)

    assert found(user, **params) == ([id] if hit else [])


def test_an_artwork_without_date_is_found_only_without_a_date_filter(user, conn):
    id = add(conn, me(user))

    assert found(user, from_year=1) == []
    assert found(user) == [id]


@pytest.mark.parametrize(
    "params, detail",
    [
        ({"from_year": 1605, "to_year": 1600}, "The end year cannot be before the start year."),
        ({"from_year": 14, "to_year": 30, "to_bc": "true"}, "The end year cannot be before the start year."),
        ({"from_year": THIS_YEAR + 1}, "A year cannot be in the future."),
    ],
)
def test_a_wrong_date_range_is_refused(user, params, detail):
    response = user.get(URL, params={"state": "COLLECTION", **params})

    assert (response.status_code, response.json()) == (422, {"detail": detail})


# Combining, paging, order of checks, safety


def test_search_and_filters_are_combined_with_and(user, conn):
    rembrandt, vermeer = add_entry(conn, "artists", "Rembrandt"), add_entry(conn, "artists", "Vermeer")
    cat, dog = add_tag(conn, "cat"), add_tag(conn, "dog")
    fits = add(conn, me(user), title="Night", artist_id=rembrandt, museum="Rijksmuseum", tags=[cat, dog],
               year_start=1642)
    add(conn, me(user), title="Night", artist_id=rembrandt, museum="Rijksmuseum", tags=[cat], year_start=1642)

    assert found(user, q="night", artist_id=vermeer) == []
    assert found(user, artist_id=rembrandt, museum="rijksmuseum", tag_ids=[cat, dog], from_year=1600,
                 to_year=1700) == [fits]


def test_paging_counts_only_matching_artworks(user, conn):
    created = [add(conn, me(user), title="match") for _ in range(120)]
    add(conn, me(user), title="other")

    pages = [user.get(URL, params={"state": "COLLECTION", "q": "match", "page": n}).json() for n in (1, 2, 3, 4)]

    assert [len(page["items"]) for page in pages] == [50, 50, 20, 0]
    assert {page["total"] for page in pages} == {120}
    assert sorted(item["id"] for page in pages for item in page["items"]) == created


def test_no_match_is_an_empty_first_page(user):
    response = user.get(URL, params={"state": "COLLECTION", "q": "nothing"})

    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_checks_run_login_then_state_then_page_then_filters(client, user):
    def detail(client, **params):
        return client.get(URL, params={"artist_id": "abc", **params}).json()["detail"]

    assert detail(device(), page="0") == NOT_LOGGED_IN["detail"]
    assert detail(user, page="0") == "Choose Collection or Watchlist."
    assert detail(user, state="COLLECTION", page="0") == "Page must be a whole number of 1 or more."
    assert detail(user, state="COLLECTION") == BAD["detail"]


def test_quotes_and_sql_in_search_values_are_plain_text(user, conn):
    id = add(conn, me(user), title="it's")

    assert found(user, q="it's") == [id]
    assert found(user, q="'; DROP TABLE artworks; --", museum="'; DROP TABLE artworks; --") == []
    assert found(user) == [id]
