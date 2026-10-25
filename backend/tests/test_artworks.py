"""Creating an artwork (`POST /api/artworks`): parts, state and photo, text, ids, tags, date, and photo and database in step."""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of
from test_tags import add_tag, add_user, count

import photos
from main import app, date_display

JPEG = b"\xff\xd8\xff\xe0" + b"photo bytes" * 100
NO_PHOTO = "Add a photo to put this artwork in your collection."
THIS_YEAR = datetime.now(UTC).year
ARTWORK_FIELDS = {
    "id", "state", "title", "artist", "date", "subject", "movement", "museum", "tags", "notes",
    "has_photo", "photo_version", "detail_photo_ids", "is_discoverable", "are_notes_discoverable", "created_at",
}


@pytest.fixture(autouse=True)
def folder(tmp_path, monkeypatch):
    """Every test saves photos into its own temporary folder; none reaches R2."""
    for name in photos.R2_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path / "photos"))
    return tmp_path / "photos"


@pytest.fixture
def user(client):
    """`client` logged in as a new user."""
    register(client)
    return client


def post(client, artwork=None, state=None, photo=None, as_file=False):
    """The create request, always multipart. `artwork` is sent as JSON text (or as a file part, like a browser's Blob)."""
    parts = {}
    if artwork is not None:
        body = artwork if isinstance(artwork, str) else json.dumps(artwork)
        parts["artwork"] = ("blob", body.encode(), "application/json") if as_file else (None, body)
    if state is not None:
        parts["state"] = (None, state)
    if photo is not None:
        parts["photo"] = ("photo.jpg", photo, "image/jpeg")
    return client.post("/api/artworks", files=parts or {"other": (None, "x")})


def watch(client, artwork=None, **parts):
    return post(client, {} if artwork is None else artwork, state="WATCHLIST", **parts)


def snapshot(conn, folder):
    """Everything a refused request must leave unchanged: artworks, tag links, tag counts and stored files."""
    return (
        conn.execute(text("SELECT count(*) FROM artworks")).scalar(),
        conn.execute(text("SELECT count(*) FROM artwork_tags")).scalar(),
        conn.execute(text("SELECT id, usage_count FROM tags ORDER BY id")).all(),
        sorted(p.name for p in folder.glob("*")) if folder.exists() else [],
    )


def refused(client, conn, folder, detail=None, **request):
    """Sends the request, expects 422 (with `detail` if given) and nothing created or stored."""
    before = snapshot(conn, folder)
    response = post(client, **request)
    assert response.status_code == 422, response.text
    assert list(response.json()) == ["detail"] and isinstance(response.json()["detail"], str)
    if detail:
        assert response.json() == {"detail": detail}
    assert snapshot(conn, folder) == before


def row(conn, id):
    return conn.execute(text("SELECT * FROM artworks WHERE id = :id"), {"id": id}).one()


def add_entry(conn, table, name):
    return conn.execute(text(f"INSERT INTO {table} (name) VALUES (:name) RETURNING id"), {"name": name}).scalar()


# Login required


@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_creating_an_artwork_while_logged_out_is_refused_and_creates_nothing(client, conn, folder, case):
    before = snapshot(conn, folder)

    response = post(device(case(client, conn)), {}, photo=JPEG)

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN
    assert snapshot(conn, folder) == before


def test_a_logged_in_request_sends_the_session_cookie_again_for_30_days(client):
    token = token_of(register(client))

    response = watch(device(token))

    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# State and photo


@pytest.mark.parametrize(
    "state, photo, expected_state",
    [
        ("COLLECTION", JPEG, "COLLECTION"),
        (None, JPEG, "COLLECTION"),
        ("WATCHLIST", None, "WATCHLIST"),
        ("WATCHLIST", JPEG, "WATCHLIST"),
    ],
)
def test_state_and_photo_that_go_together_are_accepted(user, state, photo, expected_state):
    response = post(user, {}, state=state, photo=photo)

    assert response.status_code == 201
    assert response.json()["state"] == expected_state
    assert response.json()["has_photo"] is (photo is not None)


@pytest.mark.parametrize("state", ["COLLECTION", None])
def test_artwork_without_a_photo_is_refused_unless_it_is_on_the_watchlist(user, conn, folder, state):
    refused(user, conn, folder, NO_PHOTO, artwork={}, state=state)


@pytest.mark.parametrize("state", ["collection", "DONE", ""])
def test_a_state_that_is_not_exactly_collection_or_watchlist_is_refused(user, conn, folder, state):
    refused(user, conn, folder, artwork={}, state=state, photo=JPEG)


@pytest.mark.parametrize(
    "photo, detail",
    [
        (b"\x89PNG\r\n\x1a\n" + b"x" * 50, "This file type is not supported."),
        (b"just text", "This file type is not supported."),
        (b"", "This file type is not supported."),
        (JPEG + b"x" * photos.MAX_PHOTO_BYTES, "This photo is too large."),
    ],
)
def test_a_photo_that_is_not_an_accepted_jpeg_is_refused(user, conn, folder, photo, detail):
    refused(user, conn, folder, detail, artwork={}, photo=photo)


def test_a_photo_of_exactly_10_mb_is_accepted(user):
    photo = JPEG + b"x" * (photos.MAX_PHOTO_BYTES - len(JPEG))

    assert post(user, {}, photo=photo).status_code == 201


def test_a_photo_sent_as_a_text_field_is_refused(user, conn, folder):
    before = snapshot(conn, folder)

    response = user.post(
        "/api/artworks", files={"artwork": (None, "{}"), "state": (None, "WATCHLIST"), "photo": (None, "not a file")}
    )

    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert snapshot(conn, folder) == before


# The artwork part


def test_an_empty_artwork_on_the_watchlist_has_empty_details(user):
    response = watch(user)

    assert response.status_code == 201
    body = response.json()
    assert (body["title"], body["museum"], body["notes"]) == ("", "", "")
    assert (body["artist"], body["subject"], body["movement"], body["date"]) == (None, None, None, None)
    assert body["tags"] == []


@pytest.mark.parametrize("as_file", [False, True])
def test_artwork_is_accepted_as_a_text_field_and_as_a_json_file_part(user, as_file):
    response = post(user, {"title": "Guernica"}, state="WATCHLIST", as_file=as_file)

    assert response.json()["title"] == "Guernica"


@pytest.mark.parametrize("artwork", [None, "not json", "{", "[]", '"x"', "5", "null"])
def test_a_missing_or_unreadable_artwork_part_is_refused(user, conn, folder, artwork):
    refused(user, conn, folder, artwork=artwork, state="WATCHLIST")


def test_a_request_that_is_not_multipart_is_refused(user, conn, folder):
    before = snapshot(conn, folder)

    response = user.post("/api/artworks", json={"title": "x"})

    assert response.status_code == 422
    assert list(response.json()) == ["detail"]
    assert snapshot(conn, folder) == before


@pytest.mark.parametrize(
    "artwork",
    [{"title": 5}, {"title": None}, {"museum": None}, {"notes": None}, {"tag_ids": "3"}, {"tag_ids": None},
     {"tag_ids": ["3"]}, {"artist_id": "abc"}, {"artist_id": "3"}, {"subject_id": True}, {"date": "1642"},
     {"date": {"to_year": 5}}, {"date": {"from_year": "5"}}, {"date": {"from_year": 5, "circa": "yes"}}],
)
def test_fields_of_the_wrong_type_are_refused(user, conn, folder, artwork):
    refused(user, conn, folder, artwork=artwork, state="WATCHLIST")


def test_extra_fields_are_ignored(user, conn):
    other = add_user(conn, "other")
    extra = {"is_discoverable": True, "are_notes_discoverable": True, "state": "COLLECTION", "user_id": other, "id": 5,
             "date": {"from_year": 5, "bc": True}}

    response = watch(user, extra)

    body = response.json()
    assert (body["state"], body["is_discoverable"], body["are_notes_discoverable"]) == ("WATCHLIST", False, False)
    assert body["id"] != 5 and body["date"]["from_bc"] is False
    assert row(conn, body["id"]).user_id != other


# Text fields


@pytest.mark.parametrize("field", ["title", "museum"])
def test_title_and_museum_are_cleaned_like_names(user, field):
    body = watch(user, {field: "  The \t Night  Watch\n "}).json()

    assert body[field] == "The Night Watch"
    assert watch(user, {field: " \t "}).json()[field] == ""
    assert watch(user, {field: "Café"}).json()[field] == "Café"


def test_notes_keep_their_layout_and_only_get_unicode_nfc(user, conn):
    notes = "  line one\n\tline  two\r\n Café "

    body = watch(user, {"notes": notes}).json()

    assert body["notes"] == notes.replace("é", "é")


@pytest.mark.parametrize(
    "field, limit, label", [("title", 300, "Title"), ("museum", 200, "Museum"), ("notes", 10000, "Notes")]
)
def test_text_up_to_the_limit_is_accepted_and_one_more_character_is_refused(user, conn, folder, field, limit, label):
    padded = f" {'é' * limit} " if field != "notes" else "é" * limit
    assert watch(user, {field: padded}).status_code == 201

    detail = f"{label} must be at most {limit:,} characters."
    refused(user, conn, folder, detail, artwork={field: "é" * (limit + 1)}, state="WATCHLIST")


@pytest.mark.parametrize("field", ["title", "museum", "notes"])
def test_text_with_a_control_character_is_refused(user, conn, folder, field):
    refused(user, conn, folder, f"{field.capitalize()} contains characters that are not allowed.",
            artwork={field: "a\x01b"}, state="WATCHLIST")


@pytest.mark.parametrize("content", ['"a\\ud800b"', '"a\\u0000b"'])
def test_a_lone_surrogate_or_nul_is_refused_by_the_shared_check_not_with_a_server_error(user, conn, folder, content):
    refused(user, conn, folder, artwork=f'{{"notes": {content}}}', state="WATCHLIST")


def test_in_notes_only_tab_line_feed_and_carriage_return_are_allowed(user, conn, folder):
    assert watch(user, {"notes": "a\tb\nc\rd"}).status_code == 201
    for control in ("\x0b", "\x85", "\x1f", "\x7f"):
        refused(user, conn, folder, artwork={"notes": f"a{control}b"}, state="WATCHLIST")


# Artist, subject, movement and tags


def test_entries_of_any_user_are_stored_and_shown_with_their_names(user, conn):
    ids = {table: add_entry(conn, table, f"{table} entry") for table in ("artists", "subjects", "movements")}

    body = watch(user, {"artist_id": ids["artists"], "subject_id": ids["subjects"], "movement_id": ids["movements"]}).json()

    assert body["artist"] == {"id": ids["artists"], "name": "artists entry"}
    assert body["subject"] == {"id": ids["subjects"], "name": "subjects entry"}
    assert body["movement"] == {"id": ids["movements"], "name": "movements entry"}
    stored = row(conn, body["id"])
    assert (stored.artist_id, stored.subject_id, stored.movement_id) == tuple(ids.values())


@pytest.mark.parametrize("field, label", [("artist_id", "artist"), ("subject_id", "subject"), ("movement_id", "movement")])
@pytest.mark.parametrize("id", [999999, 0, -1, 99999999999])
def test_an_id_that_does_not_exist_or_does_not_fit_is_refused(user, conn, folder, field, label, id):
    refused(user, conn, folder, f"This {label} does not exist.", artwork={field: id}, state="WATCHLIST", photo=JPEG)


def test_a_movement_id_is_checked_against_movements(user, conn, folder):
    artist_id = conn.execute(text("INSERT INTO artists (id, name) VALUES (900000, 'Only an artist') RETURNING id")).scalar()
    assert conn.execute(text("SELECT 1 FROM movements WHERE id = :id"), {"id": artist_id}).first() is None

    refused(user, conn, folder, "This movement does not exist.", artwork={"movement_id": artist_id}, state="WATCHLIST")


def test_tags_are_linked_and_listed_sorted_by_name(user, conn):
    zebra, apple = add_tag(conn, "zebra"), add_tag(conn, "apple")

    body = watch(user, {"tag_ids": [zebra, apple, zebra]}).json()

    assert body["tags"] == [{"id": apple, "name": "apple"}, {"id": zebra, "name": "zebra"}]
    assert conn.execute(text("SELECT count(*) FROM artwork_tags WHERE artwork_id = :id"), {"id": body["id"]}).scalar() == 2
    assert watch(user, {"tag_ids": []}).json()["tags"] == watch(user).json()["tags"] == []


def test_the_tag_count_follows_the_number_of_different_users(user, conn):
    cat = add_tag(conn, "cat")
    watch(user, {"tag_ids": [cat, cat]})
    assert count(conn, cat) == 1
    watch(user, {"tag_ids": [cat]})
    assert count(conn, cat) == 1
    watch(device(token_of(register(device(), "bo@example.com"))), {"tag_ids": [cat]})
    assert count(conn, cat) == 2


@pytest.mark.parametrize("unknown", [[999999], [-1], [99999999999], "with_known"])
def test_an_unknown_tag_creates_nothing(user, conn, folder, unknown):
    tag_ids = [add_tag(conn, "cat"), 999999] if unknown == "with_known" else unknown

    refused(user, conn, folder, "One or more tags do not exist.", artwork={"tag_ids": tag_ids}, state="COLLECTION", photo=JPEG)


# Date


def test_a_missing_or_null_date_stores_no_date(user, conn):
    for artwork in ({}, {"date": None}):
        body = watch(user, artwork).json()
        assert body["date"] is None
        stored = row(conn, body["id"])
        assert (stored.date_display, stored.year_start, stored.year_end) == (None, None, None)


@pytest.mark.parametrize("date", [{}, {"from_year": 0}, {"from_year": -450}, {"from_year": 5, "to_year": 0}, {"from_year": 5, "to_year": -3}])
def test_a_date_without_a_from_year_or_with_a_year_below_1_is_refused(user, conn, folder, date):
    refused(user, conn, folder, artwork={"date": date}, state="WATCHLIST")


def test_circa_and_bc_choices_default_to_false_and_to_bc_without_a_to_year_is_ignored(user):
    assert watch(user, {"date": {"from_year": 1642}}).json()["date"] == {
        "from_year": 1642, "to_year": None, "circa": False, "from_bc": False, "to_bc": False, "display": "1642"}
    date = watch(user, {"date": {"from_year": 450, "from_bc": True, "to_bc": True}}).json()["date"]
    assert (date["to_bc"], date["display"]) == (False, "450 BC")


@pytest.mark.parametrize(
    "date, start, end, circa",
    [
        ({"from_year": 450, "from_bc": True, "circa": True}, -450, None, True),
        ({"from_year": 30, "from_bc": True, "to_year": 14}, -30, 14, False),
        ({"from_year": 1600, "to_year": 1605}, 1600, 1605, False),
        ({"from_year": 500, "from_bc": True, "to_year": 450, "to_bc": True}, -500, -450, False),
        ({"from_year": 1, "from_bc": True, "to_year": 1}, -1, 1, False),
        ({"from_year": 1642, "to_year": 1642}, 1642, 1642, False),
    ],
)
def test_a_date_is_stored_with_bc_years_negative_and_comes_back_as_sent(user, conn, date, start, end, circa):
    body = watch(user, {"date": date}).json()

    stored = row(conn, body["id"])
    assert (stored.year_start, stored.year_end, stored.date_is_circa) == (start, end, circa)
    assert stored.date_display == body["date"]["display"]
    assert {key: body["date"][key] for key in date} == date


@pytest.mark.parametrize(
    "date",
    [
        {"from_year": 1605, "to_year": 1600},
        {"from_year": 450, "from_bc": True, "to_year": 500, "to_bc": True},
        {"from_year": 14, "to_year": 30, "to_bc": True},
    ],
)
def test_an_end_year_before_the_start_year_is_refused(user, conn, folder, date):
    refused(user, conn, folder, "The end year cannot be before the start year.", artwork={"date": date}, state="WATCHLIST")


@pytest.mark.parametrize(
    "date, detail",
    [
        ({"from_year": THIS_YEAR + 1}, "A year cannot be in the future."),
        ({"from_year": 1, "to_year": THIS_YEAR + 1}, "A year cannot be in the future."),
        ({"from_year": 10**30}, "A year cannot be in the future."),
        ({"from_year": 100001, "from_bc": True}, "A BC year cannot be above 100,000."),
        ({"from_year": 10**30, "from_bc": True}, "A BC year cannot be above 100,000."),
    ],
)
def test_a_year_beyond_the_limits_is_refused(user, conn, folder, date, detail):
    refused(user, conn, folder, detail, artwork={"date": date}, state="WATCHLIST")


@pytest.mark.parametrize("date", [{"from_year": THIS_YEAR}, {"from_year": 100000, "from_bc": True}])
def test_the_current_year_and_100000_bc_are_accepted(user, date):
    assert watch(user, {"date": date}).status_code == 201


@pytest.mark.parametrize(
    "start, end, circa, shown",
    [
        (1642, None, False, "1642"),
        (-450, None, False, "450 BC"),
        (1600, 1605, False, "1600–1605"),
        (-500, -450, False, "500–450 BC"),
        (-30, 14, False, "30 BC – 14 AD"),
        (1642, 1642, False, "1642"),
        (-5, -5, False, "5 BC"),
        (1600, None, True, "c. 1600"),
        (-450, None, True, "c. 450 BC"),
        (1600, 1605, True, "c. 1600–1605"),
        (-30, 14, True, "c. 30 BC – 14 AD"),
    ],
)
def test_the_date_is_displayed_as_one_readable_text(start, end, circa, shown):
    assert date_display(start, end, circa) == shown


# Response


def test_a_full_artwork_is_created_and_every_value_matches_the_request(user, conn, folder):
    artist, subject, movement = (add_entry(conn, t, n) for t, n in (("artists", "Rembrandt"), ("subjects", "Portrait"), ("movements", "Tenebrism")))
    tags = [add_tag(conn, "night"), add_tag(conn, "guard")]
    request = {
        "title": "  The   Night Watch ", "artist_id": artist, "subject_id": subject, "movement_id": movement,
        "date": {"from_year": 1642, "circa": True}, "museum": "Rijksmuseum", "tag_ids": tags, "notes": "Big.\nVery big.",
    }

    response = post(user, request, state="COLLECTION", photo=JPEG)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == ARTWORK_FIELDS
    assert body | {"id": 0, "created_at": "", "photo_version": ""} == {
        "id": 0, "state": "COLLECTION", "title": "The Night Watch", "artist": {"id": artist, "name": "Rembrandt"},
        "date": {"from_year": 1642, "to_year": None, "circa": True, "from_bc": False, "to_bc": False, "display": "c. 1642"},
        "subject": {"id": subject, "name": "Portrait"}, "movement": {"id": movement, "name": "Tenebrism"},
        "museum": "Rijksmuseum", "tags": [{"id": tags[1], "name": "guard"}, {"id": tags[0], "name": "night"}],
        "notes": "Big.\nVery big.", "has_photo": True, "photo_version": "", "detail_photo_ids": [],
        "is_discoverable": False, "are_notes_discoverable": False, "created_at": "",
    }
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    assert len(body["photo_version"]) == 16
    assert watch(user).json()["photo_version"] is None


def test_the_row_has_the_callers_id_and_the_stored_photo_has_the_exact_bytes(user, conn, folder):
    me = user.get("/api/auth/me").json()["id"]
    with_photo, without = post(user, {}, photo=JPEG).json(), watch(user).json()

    assert row(conn, with_photo["id"]).user_id == me == row(conn, without["id"]).user_id
    assert b"".join(photos.read(row(conn, with_photo["id"]).artwork_photo_path)) == JPEG
    assert row(conn, without["id"]).artwork_photo_path is None
    assert len(list(folder.glob("*.jpg"))) == 1


def test_two_users_each_own_their_artwork(user, conn):
    other = device(token_of(register(device(), "bo@example.com")))

    first, second = watch(user).json(), watch(other).json()

    assert row(conn, first["id"]).user_id != row(conn, second["id"]).user_id


# Photo and database stay in step


def test_saved_photo_is_removed_when_the_database_step_fails(user, conn, folder, monkeypatch):
    def fail(connection, artwork_id):
        raise RuntimeError("database step failed")

    monkeypatch.setattr("main.artwork_response", fail)
    before = snapshot(conn, folder)

    response = TestClient(app, base_url="https://testserver", cookies=user.cookies, raise_server_exceptions=False).post(
        "/api/artworks", files={"artwork": (None, "{}"), "photo": ("p.jpg", JPEG, "image/jpeg")}
    )

    assert response.status_code == 500
    assert snapshot(conn, folder) == before
    assert list(folder.glob("*")) == []


def test_unreachable_photo_storage_gives_503_and_creates_nothing_but_the_watchlist_still_works(user, conn, folder, monkeypatch):
    def unreachable(data):
        raise photos.StorageUnavailable

    monkeypatch.setattr(photos, "save", unreachable)
    before = snapshot(conn, folder)

    response = post(user, {}, photo=JPEG)

    assert response.status_code == 503
    assert response.json() == {"detail": "Photos are unavailable right now. Please try again later."}
    assert snapshot(conn, folder) == before
    assert watch(user).status_code == 201
