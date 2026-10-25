"""Creating tags and suggesting them (`/api/tags`, `/api/tags/suggestions`), and the popularity count the database keeps."""

import importlib.util
import threading

import pytest
from conftest import BACKEND, run_schema_command
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of

from main import app, get_connection

MAY_ONLY_CONTAIN = {"detail": "Tags may only contain letters, numbers, spaces and hyphens."}
WRONG_LENGTH = {"detail": "Tags must be 2–50 characters."}
EMPTY_NAME = {"detail": "Name cannot be empty."}
NEEDS_LETTER = {"detail": "A tag needs at least one letter or number."}


@pytest.fixture
def user(client):
    """`client` logged in as a new user."""
    register(client)
    return client


def create(client, name):
    return client.post("/api/tags", json={"name": name})


def suggest(client, **params):
    return client.get("/api/tags/suggestions", params=params)


def suggested(response):
    return [item["name"] for item in response.json()]


def tag_rows(conn):
    return conn.execute(text("SELECT id, name, usage_count FROM tags ORDER BY id")).all()


def add_user(conn, name):
    return conn.execute(
        text("INSERT INTO users (email, password_hash) VALUES (:email, 'x') RETURNING id"), {"email": f"{name}@example.com"}
    ).scalar()


def add_artwork(conn, user_id, state="WATCHLIST"):
    return conn.execute(
        text(
            "INSERT INTO artworks (user_id, collection_state, artwork_photo_path) "
            "VALUES (:user_id, :state, CASE WHEN :state = 'COLLECTION' THEN 'p.jpg' END) RETURNING id"
        ),
        {"user_id": user_id, "state": state},
    ).scalar()


def add_tag(conn, name):
    return conn.execute(text("INSERT INTO tags (name) VALUES (:name) RETURNING id"), {"name": name}).scalar()


def link(conn, artwork_id, tag_id, source="USER"):
    conn.execute(
        text("INSERT INTO artwork_tags (artwork_id, tag_id, source) VALUES (:a, :t, :s)"),
        {"a": artwork_id, "t": tag_id, "s": source},
    )


def count(conn, tag_id):
    return conn.execute(text("SELECT usage_count FROM tags WHERE id = :id"), {"id": tag_id}).scalar()


def used_by(conn, name, users):
    """A tag called `name` that `users` (new users) each have on one artwork. Returns the tag id."""
    tag_id = add_tag(conn, name)
    for number in range(users):
        link(conn, add_artwork(conn, add_user(conn, f"{name.replace(' ', '')}{number}")), tag_id)
    return tag_id


# Login required


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_suggesting_while_logged_out_is_refused(client, conn, case):
    response = device(case(client, conn)).get("/api/tags/suggestions")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_creating_a_tag_while_logged_out_is_refused_and_creates_nothing(client, conn, case):
    before = tag_rows(conn)

    response = create(device(case(client, conn)), "chiaroscuro")

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN
    assert tag_rows(conn) == before


@pytest.mark.parametrize("method, path", [("get", "/api/tags/suggestions"), ("post", "/api/tags")])
def test_a_logged_in_request_sends_the_session_cookie_again_for_30_days(client, method, path):
    token = token_of(register(client))

    response = device(token).request(method, path, json={"name": "chiaroscuro"} if method == "post" else None)

    assert response.status_code in (200, 201)
    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# Create


def test_a_new_tag_is_created_and_another_user_gets_the_same_tag(user, conn):
    response = create(user, "chiaroscuro")

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "name": "chiaroscuro"}
    other = device(token_of(register(device(), email="bo@example.com")))
    again = create(other, "chiaroscuro")
    assert again.status_code == 200
    assert again.json() == body
    assert tag_rows(conn) == [(body["id"], "chiaroscuro", 0)]


@pytest.mark.parametrize("typed, stored", [("Chiaroscuro", "chiaroscuro"), ("CHIAROSCURO", "chiaroscuro"), ("ΘΑΛΑΣΣΑ", "θαλασσα")])
def test_tag_is_stored_in_lowercase(user, conn, typed, stored):
    response = create(user, typed)

    assert response.status_code == 201
    assert response.json()["name"] == stored
    assert [row.name for row in tag_rows(conn)] == [stored]


def test_lowercasing_does_not_fold_the_german_sharp_s(user, conn):
    first, second = create(user, "Straße"), create(user, "STRASSE")

    assert (first.status_code, first.json()["name"]) == (201, "straße")
    assert (second.status_code, second.json()["name"]) == (201, "strasse")
    assert len(tag_rows(conn)) == 2


@pytest.mark.parametrize("typed", ["  Still   Life ", "still\tlife", "still\nlife", "still life", "still\x1flife", "still\x0blife", "still\x85life"])
def test_spaces_in_a_tag_are_cleaned(user, conn, typed):
    response = create(user, typed)

    assert response.status_code == 201
    assert response.json()["name"] == "still life"
    assert [row.name for row in tag_rows(conn)] == ["still life"]


@pytest.mark.parametrize("typed", ["Cat", "CAT", " cat ", "cat"])
def test_creating_an_existing_tag_in_other_capitals_returns_it(user, conn, typed):
    existing = create(user, "cat").json()

    response = create(user, typed)

    assert response.status_code == 200
    assert response.json() == existing
    assert tag_rows(conn) == [(existing["id"], "cat", 0)]


def test_creating_a_tag_hidden_from_suggestions_returns_it(user, conn):
    tag_id = used_by(conn, "quiet", 1)

    response = create(user, "quiet")

    assert response.status_code == 200
    assert response.json() == {"id": tag_id, "name": "quiet"}


def test_the_same_letter_in_two_unicode_forms_is_the_same_tag(user, conn):
    first, second = create(user, "café"), create(user, "café")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert [row.name for row in tag_rows(conn)] == ["café"]


def test_tags_that_differ_only_by_accents_are_separate(user, conn):
    assert create(user, "cafe").status_code == 201
    assert create(user, "café").status_code == 201
    assert len(tag_rows(conn)) == 2


def test_tags_and_subjects_are_separate_lists(user):
    assert user.post("/api/subjects", json={"name": "Cat"}).status_code == 201
    assert create(user, "cat").status_code == 201
    assert create(user, "dog").status_code == 201
    assert user.post("/api/subjects", json={"name": "dog"}).status_code == 201


@pytest.mark.parametrize(
    "name", ["café", "θάλασσα", "日本", "17th century", "self-portrait", "चित्रकला", "ภาพวาด", "-cat", "cat-", "self--portrait"]
)
def test_allowed_characters_are_accepted_as_typed(user, name):
    response = create(user, name)

    assert response.status_code == 201
    assert response.json()["name"] == name


def test_a_capital_i_with_a_dot_is_stored_as_i_and_a_combining_dot(user):
    response = create(user, "İzmir")

    assert response.status_code == 201
    assert response.json()["name"] == "i̇zmir"


@pytest.mark.parametrize(
    "name",
    ["st. jerome", "cat!", "a/b", "rock'n roll", "#cat", "(workshop)", "still_life", "self–portrait", "self—portrait", "cat🐈", "50%", "a\\b"],
)
def test_tag_with_punctuation_or_other_characters_is_refused(user, conn, name):
    response = create(user, name)

    assert response.status_code == 422
    assert response.json() == MAY_ONLY_CONTAIN
    assert tag_rows(conn) == []


@pytest.mark.parametrize("name", ["ca\u0000t", "ca\u0007t", "ca\u007ft"])
def test_tag_with_a_control_character_is_refused(user, conn, name):
    response = create(user, name)

    assert response.status_code == 422
    assert response.json() == MAY_ONLY_CONTAIN
    assert tag_rows(conn) == []


def test_tag_with_a_broken_character_is_refused(user, conn):
    response = user.post("/api/tags", content='{"name": "ca\\ud800t"}', headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert response.json() == MAY_ONLY_CONTAIN
    assert tag_rows(conn) == []


@pytest.mark.parametrize("name", ["ox", "θ" * 50, "a" * 50, "  " + "θ" * 50 + "   ", "a" * 25 + "   " + "b" * 24])
def test_tag_of_2_to_50_characters_is_accepted(user, name):
    assert create(user, name).status_code == 201


@pytest.mark.parametrize("name", ["a", "a" * 51, "θ" * 51, "a" * 201, "a" * 1000, "a " * 100, " a "])
def test_tag_of_the_wrong_length_is_refused(user, conn, name):
    response = create(user, name)

    assert response.status_code == 422
    assert response.json() == WRONG_LENGTH
    assert tag_rows(conn) == []


def test_the_length_message_wins_over_the_character_message(user):
    assert create(user, "!").json() == WRONG_LENGTH


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_blank_tag_is_refused(user, conn, name):
    response = create(user, name)

    assert response.status_code == 422
    assert response.json() == EMPTY_NAME
    assert tag_rows(conn) == []


@pytest.mark.parametrize("name", ["--", "- -", "-- --"])
def test_tag_of_only_hyphens_is_refused(user, conn, name):
    response = create(user, name)

    assert response.status_code == 422
    assert response.json() == NEEDS_LETTER
    assert tag_rows(conn) == []


@pytest.mark.parametrize("content", ["{}", '{"name": 123}', '{"name": null}', '{"name": []}', "", "not json", b"{\"name\": \"\xff\"}"])
def test_a_body_without_a_valid_name_is_refused_in_the_error_shape(user, conn, content):
    response = user.post("/api/tags", content=content, headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert isinstance(response.json()["detail"], str)
    assert tag_rows(conn) == []


def test_extra_fields_in_the_body_are_ignored(user, conn):
    taken = 987654

    response = user.post("/api/tags", json={"name": "cat", "id": taken, "usage_count": 99})

    assert response.status_code == 201
    assert response.json()["id"] != taken
    assert [row.usage_count for row in tag_rows(conn)] == [0]


def test_creating_a_tag_does_not_change_any_usage_count(user, conn):
    tag_id = used_by(conn, "cat", 3)

    create(user, "cat")
    create(user, "dog")

    assert count(conn, tag_id) == 3


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
        connection.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))  # its sessions go with it
        connection.execute(text("DELETE FROM tags"))


def test_simultaneous_creates_of_the_same_tag_give_one_entry(committed_client, engine):
    token = token_of(register(committed_client))
    start = threading.Barrier(2)
    responses = {}

    def send(name):
        client = device(token)
        start.wait()
        responses[name] = create(client, name)

    threads = [threading.Thread(target=send, args=(name,)) for name in ("Vermeer", "vermeer")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(response.status_code for response in responses.values()) == [200, 201]
    first, second = (response.json() for response in responses.values())
    assert first == second
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id, name FROM tags")).all() == [(first["id"], "vermeer")]


# Popularity


def test_second_artwork_of_the_same_user_does_not_raise_the_count(conn):
    a, b, cat = add_user(conn, "a"), add_user(conn, "b"), add_tag(conn, "cat")
    assert count(conn, cat) == 0

    link(conn, add_artwork(conn, a), cat)
    assert count(conn, cat) == 1
    link(conn, add_artwork(conn, a), cat)
    assert count(conn, cat) == 1
    link(conn, add_artwork(conn, b), cat)
    assert count(conn, cat) == 2


def test_removing_a_tag_lowers_the_count_only_for_the_last_artwork_of_a_user(conn):
    a, b, cat = add_user(conn, "a"), add_user(conn, "b"), add_tag(conn, "cat")
    first, second = add_artwork(conn, a), add_artwork(conn, a)
    for artwork in (first, second, add_artwork(conn, b)):
        link(conn, artwork, cat)

    conn.execute(text("DELETE FROM artwork_tags WHERE artwork_id = :id"), {"id": first})
    assert count(conn, cat) == 2
    conn.execute(text("DELETE FROM artwork_tags WHERE artwork_id = :id"), {"id": second})
    assert count(conn, cat) == 1


def test_deleting_the_last_artwork_of_a_user_lowers_the_count(conn):
    a, b, cat, dog = add_user(conn, "a"), add_user(conn, "b"), add_tag(conn, "cat"), add_tag(conn, "dog")
    first, second, other = add_artwork(conn, a), add_artwork(conn, a), add_artwork(conn, b)
    for artwork in (first, second, other):
        link(conn, artwork, cat)
    link(conn, other, dog)
    assert (count(conn, cat), count(conn, dog)) == (2, 1)

    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": first})
    assert count(conn, cat) == 2
    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": second})
    assert count(conn, cat) == 1
    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": other})
    assert (count(conn, cat), count(conn, dog)) == (0, 0)


def test_deleting_an_artwork_updates_each_of_its_tags(conn):
    a, cat, dog = add_user(conn, "a"), add_tag(conn, "cat"), add_tag(conn, "dog")
    artwork = add_artwork(conn, a)
    link(conn, artwork, cat)
    link(conn, artwork, dog)
    assert (count(conn, cat), count(conn, dog)) == (1, 1)

    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": artwork})

    assert (count(conn, cat), count(conn, dog)) == (0, 0)


def test_changing_the_tag_of_a_link_updates_both_tags(conn):
    a, b, cat, dog = add_user(conn, "a"), add_user(conn, "b"), add_tag(conn, "cat"), add_tag(conn, "dog")
    first, second = add_artwork(conn, a), add_artwork(conn, b)
    link(conn, first, cat)
    link(conn, second, cat)
    link(conn, second, dog)
    assert (count(conn, cat), count(conn, dog)) == (2, 1)

    conn.execute(text("UPDATE artwork_tags SET tag_id = :dog WHERE artwork_id = :a"), {"dog": dog, "a": first})

    assert (count(conn, cat), count(conn, dog)) == (1, 2)


@pytest.mark.parametrize("state", ["WATCHLIST", "COLLECTION"])
@pytest.mark.parametrize("source", ["USER", "SYSTEM"])
def test_every_artwork_and_link_counts(conn, state, source):
    a, cat = add_user(conn, "a"), add_tag(conn, "cat")

    link(conn, add_artwork(conn, a, state), cat, source)

    assert count(conn, cat) == 1


def test_two_users_linking_the_same_tag_at_the_same_moment_give_a_count_of_2(engine):
    with engine.begin() as connection:
        artworks = [add_artwork(connection, add_user(connection, name)) for name in ("a", "b")]
        cat = add_tag(connection, "cat")
    start = threading.Barrier(2)

    def add_link(artwork):
        with engine.begin() as connection:
            start.wait()
            link(connection, artwork, cat)

    threads = [threading.Thread(target=add_link, args=(artwork,)) for artwork in artworks]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        with engine.connect() as connection:
            assert count(connection, cat) == 2
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM artworks"))
            connection.execute(text("DELETE FROM users"))
            connection.execute(text("DELETE FROM tags"))


def test_the_migration_counts_existing_links_and_a_second_upgrade_changes_nothing(conn, test_database_url):
    spec = importlib.util.spec_from_file_location("migration_0003", BACKEND / "migrations/versions/0003_tag_usage_count.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    a, b, cat = add_user(conn, "a"), add_user(conn, "b"), add_tag(conn, "cat")
    conn.execute(text("ALTER TABLE artwork_tags DISABLE TRIGGER artwork_tags_usage_count"))  # links as before the upgrade
    for artwork in [add_artwork(conn, a) for _ in range(3)] + [add_artwork(conn, b)]:
        link(conn, artwork, cat)
    assert count(conn, cat) == 0

    conn.execute(text(migration.BACKFILL))
    assert count(conn, cat) == 2
    conn.execute(text(migration.BACKFILL))
    assert count(conn, cat) == 2
    assert run_schema_command(test_database_url).returncode == 0  # the real command, on the committed data only


# Suggestions


def test_tag_used_by_one_user_is_not_suggested(user, conn):
    used_by(conn, "cat", 2)
    used_by(conn, "solo", 1)
    a = add_user(conn, "heavy")
    dog = add_tag(conn, "dog")
    link(conn, add_artwork(conn, a), dog)
    link(conn, add_artwork(conn, a), dog)
    add_tag(conn, "owl")

    assert suggested(suggest(user, q="")) == ["cat"]


def test_a_tag_appears_when_a_second_user_has_it_and_disappears_when_that_artwork_is_deleted(user, conn):
    cat = used_by(conn, "cat", 1)
    second = add_artwork(conn, add_user(conn, "second"))
    assert suggested(suggest(user)) == []

    link(conn, second, cat)
    assert suggested(suggest(user)) == ["cat"]
    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": second})
    assert suggested(suggest(user)) == []


def test_private_artworks_count_for_suggestions(user, conn):
    cat = add_tag(conn, "cat")
    for name in ("a", "b"):
        link(conn, add_artwork(conn, add_user(conn, name), "WATCHLIST"), cat)

    assert suggested(suggest(user)) == ["cat"]


def test_suggestions_have_only_id_and_name(user, conn):
    cat = used_by(conn, "cat", 2)

    assert suggest(user).json() == [{"id": cat, "name": "cat"}]


def test_suggestions_put_most_popular_tags_first(user, conn):
    catalogue = used_by(conn, "catalogue", 1)
    used_by(conn, "cats", 3)
    used_by(conn, "cat", 5)
    heavy = add_user(conn, "heavy")
    for _ in range(10):
        link(conn, add_artwork(conn, heavy), catalogue)

    assert suggested(suggest(user, q="cat")) == ["cat", "cats", "catalogue"]


def test_suggestions_with_equal_popularity_are_in_alphabetical_order(user, conn):
    used_by(conn, "bird", 3)
    used_by(conn, "bear", 3)

    assert suggested(suggest(user)) == ["bear", "bird"]
    assert suggested(suggest(user)) == ["bear", "bird"]


def test_suggestions_return_at_most_ten_tags(user, conn):
    for number in range(12):
        used_by(conn, f"tag {number:02}", 2)
    used_by(conn, "tag 12", 3)

    result = suggested(suggest(user, q="tag"))

    assert len(result) == 10
    assert result == ["tag 12"] + [f"tag {number:02}" for number in range(9)]


@pytest.mark.parametrize("q, name", [("Port", "self-portrait"), ("trait", "self-portrait"), ("ΘΑΛ", "θαλασσα")])
def test_suggestions_match_anywhere_in_the_tag_ignoring_capitals(user, conn, q, name):
    used_by(conn, name, 2)

    assert suggested(suggest(user, q=q)) == [name]


def test_suggestion_text_is_cleaned_like_a_tag(user, conn):
    used_by(conn, "still life", 2)

    assert suggested(suggest(user, q="  Still   LIFE ")) == ["still life"]


def test_suggestions_do_not_ignore_accents(user, conn):
    used_by(conn, "café", 2)

    assert suggested(suggest(user, q="cafe")) == []
    assert suggested(suggest(user, q="cafe\u0301")) == ["café"]


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "   "}])
def test_suggestions_without_text_are_the_most_popular_tags(user, conn, params):
    used_by(conn, "cat", 2)
    used_by(conn, "dog", 3)

    assert suggested(suggest(user, **params)) == ["dog", "cat"]


@pytest.mark.parametrize("q", ["%", "_", "\\"])
def test_percent_in_suggestion_text_is_a_plain_character(user, conn, q):
    used_by(conn, "cat", 2)

    assert suggest(user, q=q).json() == []


@pytest.mark.parametrize("q", ["ca\u0000t", "\u0007", "a" * 51, "a" * 1000, "cat!"])
def test_suggestion_text_no_tag_could_match_gives_an_empty_list(user, conn, q):
    used_by(conn, "cat", 2)

    response = suggest(user, q=q)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("query", ["q=ca%00t", "q=%07", "q=a%ED%A0%80b", "q=%FF"])
def test_broken_suggestion_text_in_the_address_gives_an_empty_list(user, conn, query):
    used_by(conn, "cat", 2)

    response = user.get(f"/api/tags/suggestions?{query}")

    assert response.status_code == 200
    assert response.json() == []


# No other operations


@pytest.mark.parametrize("path", ["/api/tags", "/api/tags/1"])
@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_other_operations_on_tags_are_not_available(user, conn, path, method):
    tag = add_tag(conn, "cat")

    response = user.request(method, path)

    assert response.status_code in (404, 405)
    assert tag_rows(conn) == [(tag, "cat", 0)]
