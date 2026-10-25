"""The community-wide lists of artists, movements and subjects (`/api/artists`, `/api/movements`, `/api/subjects`)."""

import threading

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of

from main import app, cleaned, get_connection, refuse_characters_not_allowed

KINDS = ["artists", "movements", "subjects"]
SEEDED_MOVEMENTS = 16
EMPTY_PAGE = {"items": [], "total": 0, "page": 1, "page_size": 50}


@pytest.fixture
def user(client):
    """`client` logged in as a new user."""
    register(client)
    return client


@pytest.fixture(params=KINDS)
def kind(request):
    return request.param


def create(client, kind, name):
    return client.post(f"/api/{kind}", json={"name": name})


def search(client, kind, **params):
    return client.get(f"/api/{kind}", params=params)


def names(response):
    return [item["name"] for item in response.json()["items"]]


def rows(conn, kind):
    return conn.execute(text(f"SELECT id, name FROM {kind} ORDER BY id")).all()


def added_rows(conn, kind):
    """The rows of `kind`, without the seeded movements."""
    return rows(conn, kind)[SEEDED_MOVEMENTS:] if kind == "movements" else rows(conn, kind)


def insert(conn, kind, names):
    for name in names:
        conn.execute(text(f"INSERT INTO {kind} (name) VALUES (:name)"), {"name": name})


# Login required


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_searching_while_logged_out_is_refused(client, conn, kind, case):
    response = device(case(client, conn)).get(f"/api/{kind}")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_creating_while_logged_out_is_refused_and_creates_nothing(client, conn, kind, case):
    before = rows(conn, kind)

    response = create(device(case(client, conn)), kind, "Caravaggio")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN
    assert rows(conn, kind) == before


@pytest.mark.parametrize("method", ["get", "post"])
def test_a_logged_in_request_sends_the_session_cookie_again_for_30_days(client, kind, method):
    token = token_of(register(client))

    response = device(token).request(method, f"/api/{kind}", json={"name": "Caravaggio"})

    assert response.status_code in (200, 201)
    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# Create


def test_a_new_name_is_created_and_another_user_finds_it(user, conn, kind):
    response = create(user, kind, "Caravaggio")

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "name": "Caravaggio"}
    other = device(token_of(register(device(), email="bo@example.com")))
    assert search(other, kind, q="Caravaggio").json()["items"] == [body]
    assert added_rows(conn, kind) == [(body["id"], "Caravaggio")]


@pytest.mark.parametrize(
    "typed", ["  Rembrandt   van Rijn ", "\tRembrandt\nvan\r\nRijn\t", " Rembrandt van  Rijn"]
)
def test_extra_spaces_in_a_name_are_removed(user, conn, kind, typed):
    response = create(user, kind, typed)

    assert response.status_code == 201
    assert response.json()["name"] == "Rembrandt van Rijn"
    assert [row.name for row in added_rows(conn, kind)] == ["Rembrandt van Rijn"]


def test_a_name_keeps_the_capital_letters_as_typed(user, conn, kind):
    response = create(user, kind, "rembrandt van Rijn")

    assert response.status_code == 201
    assert response.json()["name"] == "rembrandt van Rijn"
    assert [row.name for row in added_rows(conn, kind)] == ["rembrandt van Rijn"]


@pytest.mark.parametrize("typed", ["rembrandt van rijn", "REMBRANDT VAN RIJN", " Rembrandt  van Rijn", "Rembrandt van Rijn"])
def test_creating_an_existing_name_in_other_capitals_or_spaces_returns_it(user, conn, kind, typed):
    existing = create(user, kind, "Rembrandt van Rijn").json()

    response = create(user, kind, typed)

    assert response.status_code == 200
    assert response.json() == existing
    assert added_rows(conn, kind) == [(existing["id"], "Rembrandt van Rijn")]


def test_a_seeded_movement_is_returned_when_created_again(user, conn):
    seeded = conn.execute(text("SELECT id FROM movements WHERE name = 'Baroque'")).scalar()

    response = create(user, "movements", "baroque")

    assert response.status_code == 200
    assert response.json() == {"id": seeded, "name": "Baroque"}
    assert len(rows(conn, "movements")) == SEEDED_MOVEMENTS


def test_the_three_lists_are_independent(user):
    for kind in KINDS:
        assert create(user, kind, "Cat").status_code == 201

    artists = search(user, "artists").json()
    assert artists["items"] == [{"id": artists["items"][0]["id"], "name": "Cat"}]
    assert artists["total"] == 1
    assert "Baroque" not in names(search(user, "artists", q="Baroque"))


def test_names_that_differ_by_more_than_capitals_and_spaces_are_separate(user, conn, kind):
    assert create(user, kind, "Rembrandt").status_code == 201
    assert create(user, kind, "Rembrandt van Rijn").status_code == 201
    assert len(added_rows(conn, kind)) == 2


def test_names_that_differ_only_by_accents_are_separate(user, conn, kind):
    assert create(user, kind, "Dürer").status_code == 201
    assert create(user, kind, "Durer").status_code == 201
    assert len(added_rows(conn, kind)) == 2


def test_the_same_letter_in_two_unicode_forms_is_the_same_name(user, conn, kind):
    composed, decomposed = "François Boucheré", "François Boucheré"

    first = create(user, kind, decomposed)
    second = create(user, kind, composed)

    assert first.status_code == 201
    assert first.json()["name"] == composed
    assert second.status_code == 200
    assert second.json() == first.json()
    assert [row.name for row in added_rows(conn, kind)] == [composed]


@pytest.mark.parametrize("name", ["Θεοτοκόπουλος", "Jan van Eyck (workshop)"])
def test_non_latin_names_and_punctuation_are_accepted_as_typed(user, kind, name):
    response = create(user, kind, name)

    assert response.status_code == 201
    assert response.json()["name"] == name


def test_a_hyphenated_subject_is_accepted_as_typed(user):
    response = create(user, "subjects", "Post-Impressionism")

    assert response.status_code == 201
    assert response.json()["name"] == "Post-Impressionism"


def test_a_non_latin_name_in_other_capitals_returns_the_existing_entry(user, kind):
    existing = create(user, kind, "Θεοτοκόπουλος").json()

    response = create(user, kind, "θεοτοκόπουλος")

    assert response.status_code == 200
    assert response.json() == existing


@pytest.mark.parametrize("name", ["", "   ", "\t\n", " "])
def test_blank_name_is_refused(user, conn, kind, name):
    before = rows(conn, kind)

    response = create(user, kind, name)

    assert response.status_code == 422
    assert response.json() == {"detail": "Name cannot be empty."}
    assert rows(conn, kind) == before


@pytest.mark.parametrize("name", ["a" * 200, "  " + "a" * 200 + "\t ", "θ" * 200, "a" * 100 + "   " + "b" * 99])
def test_name_of_200_characters_after_cleaning_is_accepted(user, kind, name):
    response = create(user, kind, name)

    assert response.status_code == 201
    assert len(response.json()["name"]) == 200


@pytest.mark.parametrize("name", ["a" * 201, "θ" * 201, "a" * 100 + " " + "b" * 100])
def test_name_longer_than_200_characters_is_refused(user, conn, kind, name):
    before = rows(conn, kind)

    response = create(user, kind, name)

    assert response.status_code == 422
    assert response.json() == {"detail": "Name must be at most 200 characters."}
    assert rows(conn, kind) == before


@pytest.mark.parametrize("name", ["Ca\u0000ravaggio", "Ca\u0007ravaggio", "Caravaggio\u007f", "\u009bCaravaggio"])
def test_name_with_a_control_character_is_refused(user, conn, kind, name):
    before = rows(conn, kind)

    response = create(user, kind, name)

    assert response.status_code == 422
    assert response.json() == {"detail": "Name contains characters that are not allowed."}
    assert rows(conn, kind) == before


@pytest.mark.parametrize("content", ["{}", '{"name": 123}', '{"name": null}', '{"name": []}', "", "not json", "[]"])
def test_a_body_without_a_valid_name_is_refused_in_the_error_shape(user, conn, kind, content):
    before = rows(conn, kind)

    response = user.post(f"/api/{kind}", content=content, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert isinstance(response.json()["detail"], str)
    assert rows(conn, kind) == before


def test_extra_fields_in_the_body_are_ignored(user, conn, kind):
    taken = max([row.id for row in rows(conn, kind)], default=0) + 1000

    response = user.post(f"/api/{kind}", json={"name": "Ship", "id": taken})

    assert response.status_code == 201
    assert response.json()["id"] != taken
    assert response.json() == {"id": response.json()["id"], "name": "Ship"}


@pytest.fixture
def committed_client(engine):
    """A client whose requests each commit in their own connection, like the real backend. Cleans up afterwards."""

    def connection():
        with engine.begin() as connection:
            yield connection

    app.dependency_overrides[get_connection] = connection
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE email = 'ana@example.com'"))  # its sessions go with it


def test_simultaneous_creates_of_the_same_name_give_one_entry(committed_client, engine, kind):
    token = token_of(register(committed_client))
    start = threading.Barrier(2)
    responses = {}

    def send(name):
        client = device(token)
        start.wait()
        responses[name] = create(client, kind, name)

    try:
        threads = [threading.Thread(target=send, args=(name,)) for name in ("Vermeer", "vermeer")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(response.status_code for response in responses.values()) == [200, 201]
        first, second = (response.json() for response in responses.values())
        assert first == second
        with engine.connect() as connection:
            assert connection.execute(
                text(f"SELECT id, name FROM {kind} WHERE lower(name) = 'vermeer'")
            ).all() == [(first["id"], first["name"])]
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {kind} WHERE lower(name) = 'vermeer'"))


# Search


@pytest.mark.parametrize("q", ["REMBR", "van r", "rijn", "Rembrandt van Rijn"])
def test_search_matches_anywhere_in_the_name_ignoring_capitals(user, kind, q):
    create(user, kind, "Rembrandt van Rijn")

    assert names(search(user, kind, q=q)) == ["Rembrandt van Rijn"]


def test_search_for_text_not_in_any_name_finds_nothing(user, kind):
    create(user, kind, "Rembrandt van Rijn")

    assert search(user, kind, q="xyz").json() == EMPTY_PAGE


@pytest.mark.parametrize("q", [" van   Rijn ", "\tvan Rijn\n"])
def test_search_text_is_cleaned_like_a_name(user, kind, q):
    create(user, kind, "Rembrandt van Rijn")

    assert names(search(user, kind, q=q)) == ["Rembrandt van Rijn"]


def test_search_text_in_another_unicode_form_finds_the_name(user, kind):
    create(user, kind, "François")

    assert names(search(user, kind, q="ço")) == ["François"]


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "   "}])
def test_search_without_text_lists_every_entry(user, kind, params):
    create(user, kind, "Caravaggio")
    create(user, kind, "Vermeer")
    expected = 2 + (SEEDED_MOVEMENTS if kind == "movements" else 0)

    response = search(user, kind, **params)

    assert response.status_code == 200
    assert response.json()["total"] == expected
    assert {"Caravaggio", "Vermeer"} <= set(names(response))
    assert len(names(response)) == expected


def test_search_without_text_on_a_fresh_database_lists_the_16_seeded_movements(user):
    response = search(user, "movements")

    assert response.status_code == 200
    assert response.json()["total"] == SEEDED_MOVEMENTS
    assert len(response.json()["items"]) == SEEDED_MOVEMENTS
    assert "Baroque" in names(response)


@pytest.mark.parametrize("q", ["%", "_", "\\"])
def test_percent_and_underscore_and_backslash_in_search_are_plain_characters(user, kind, q):
    create(user, kind, "Caravaggio")

    assert search(user, kind, q=q).json() == EMPTY_PAGE


@pytest.mark.parametrize("name, q", [("100% Abstract", "0% a"), ("Snake_Case", "e_c"), ("Back\\slash", "k\\s")])
def test_percent_and_underscore_and_backslash_in_search_match_themselves(user, kind, name, q):
    create(user, kind, name)
    create(user, kind, "100 Abstract Snake Case Back slash")

    assert names(search(user, kind, q=q)) == [name]


def test_search_does_not_ignore_accents(user, kind):
    create(user, kind, "Dürer")

    assert search(user, kind, q="durer").json() == EMPTY_PAGE
    assert names(search(user, kind, q="dürer")) == ["Dürer"]


def test_results_are_sorted_alphabetically_ignoring_capitals(user, kind):
    for name in ["zebra painter", "Apple painter", "abstract expressionism painter", "Banana painter"]:
        create(user, kind, name)

    assert names(search(user, kind, q="painter")) == [
        "abstract expressionism painter",
        "Apple painter",
        "Banana painter",
        "zebra painter",
    ]


def test_seeded_movements_are_sorted_alphabetically(user):
    create(user, "movements", "abstract art")

    found = names(search(user, "movements"))

    assert found[:2] == ["abstract art", "Abstract Expressionism"]
    assert found == sorted(found, key=str.lower)


def test_the_same_search_always_returns_the_same_order(user, conn, kind):
    insert(conn, kind, [f"Painter {number}" for number in range(60)])

    first = [search(user, kind, q="painter", page=page).json()["items"] for page in (1, 2)]
    again = [search(user, kind, q="painter", page=page).json()["items"] for page in (1, 2)]

    assert first == again


def test_every_search_response_has_the_entity_page_shape(user, kind):
    create(user, kind, "Caravaggio")

    body = search(user, kind, q="Caravaggio").json()

    assert set(body) == {"items", "total", "page", "page_size"}
    assert [set(item) for item in body["items"]] == [{"id", "name"}]
    assert (body["total"], body["page"], body["page_size"]) == (1, 1, 50)


# Pages


def test_120_matches_fill_two_full_pages_and_one_of_20(user, conn, kind):
    insert(conn, kind, [f"Painter {number:03}" for number in range(120)])

    pages = [search(user, kind, q="painter", page=page).json() for page in (1, 2, 3)]

    assert [len(page["items"]) for page in pages] == [50, 50, 20]
    assert [page["total"] for page in pages] == [120, 120, 120]
    assert [page["page"] for page in pages] == [1, 2, 3]
    found = [item["name"] for page in pages for item in page["items"]]
    assert found == [f"Painter {number:03}" for number in range(120)]


@pytest.mark.parametrize("matches, on_page_2", [(50, 0), (51, 1)])
def test_page_2_holds_what_does_not_fit_on_page_1(user, conn, kind, matches, on_page_2):
    insert(conn, kind, [f"Painter {number:03}" for number in range(matches)])

    assert len(search(user, kind, q="painter", page=1).json()["items"]) == 50
    page_2 = search(user, kind, q="painter", page=2).json()
    assert len(page_2["items"]) == on_page_2
    assert page_2["total"] == matches


def test_missing_page_means_page_1(user, conn, kind):
    insert(conn, kind, [f"Painter {number:03}" for number in range(60)])

    assert search(user, kind, q="painter").json() == search(user, kind, q="painter", page=1).json()
    assert search(user, kind, q="painter").json()["page"] == 1


@pytest.mark.parametrize("page", [4, 1000000, 100000000000000000000])
def test_page_after_the_last_is_empty(user, conn, kind, page):
    insert(conn, kind, [f"Painter {number:03}" for number in range(120)])

    response = search(user, kind, q="painter", page=page)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 120, "page": page, "page_size": 50}


@pytest.mark.parametrize("page", ["0", "-1", "abc", "1.5", ""])
def test_page_zero_is_refused(user, kind, page):
    response = user.get(f"/api/{kind}?page={page}")

    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert isinstance(response.json()["detail"], str)


# No editing or deleting


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_entries_cannot_be_edited_or_deleted(user, conn, kind, method):
    entry = create(user, kind, "Caravaggio").json()
    before = rows(conn, kind)

    for path in (f"/api/{kind}", f"/api/{kind}/{entry['id']}", f"/api/{kind}/1"):
        response = user.request(method, path, json={"name": "Changed"})
        assert response.status_code in (404, 405)
    assert rows(conn, kind) == before


# Characters that are not allowed (decided by the project owner on 2026-10-25)

NOT_ALLOWED = {"detail": "Name contains characters that are not allowed."}


@pytest.mark.parametrize("content", ['{"name": "a\\ud800b"}', '{"name": "\\udfff"}', '{"name": "Vermeer\\udbff"}'])
def test_name_with_a_lone_surrogate_is_refused(user, conn, kind, content):
    before = rows(conn, kind)

    response = user.post(f"/api/{kind}", content=content, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json() == NOT_ALLOWED
    assert rows(conn, kind) == before


@pytest.mark.parametrize("q", ["%00", "Ca%00ravaggio", "%07", "a%07b", "%7F", "%C2%9B"])
def test_search_text_with_a_control_character_is_refused(user, kind, q):
    response = user.get(f"/api/{kind}?q={q}")

    assert response.status_code == 422
    assert response.json() == NOT_ALLOWED


def test_search_text_with_a_lone_surrogate_is_refused_by_the_shared_check():
    # Search runs `q` through these two functions; a URL itself cannot carry a lone surrogate (see below).
    with pytest.raises(HTTPException) as refused:
        refuse_characters_not_allowed(cleaned("a\ud800b"))

    assert refused.value.status_code == 422
    assert refused.value.detail == NOT_ALLOWED["detail"]


def test_search_text_with_the_bytes_of_a_lone_surrogate_is_not_a_server_error(user, kind):
    # A URL carries UTF-8, which cannot hold a lone surrogate: such bytes arrive as replacement characters,
    # which are allowed, so the search finds nothing.
    response = user.get(f"/api/{kind}?q=a%ED%A0%80b")

    assert response.status_code == 200
    assert response.json() == EMPTY_PAGE


@pytest.mark.parametrize("space", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f", "\x85"])
def test_rare_whitespace_control_characters_count_as_spaces(user, kind, space):
    response = create(user, kind, f"{space}Rembrandt{space}van{space}{space}Rijn{space}")

    assert response.status_code == 201
    assert response.json()["name"] == "Rembrandt van Rijn"
    assert names(search(user, kind, q=f"van{space}Rijn")) == ["Rembrandt van Rijn"]


def test_rare_whitespace_in_a_name_and_in_search_counts_as_spaces(user, kind):
    response = create(user, kind, "Rembrandt\x0bvan\x85Rijn")

    assert response.status_code == 201
    assert response.json()["name"] == "Rembrandt van Rijn"
    assert names(user.get(f"/api/{kind}?q=van%0BRijn")) == ["Rembrandt van Rijn"]
