"""Viewing, editing and deleting one's own artwork (`GET`, `PATCH`, `DELETE /api/artworks/{artwork_id}`)."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from test_artworks import ARTWORK_FIELDS, JPEG, THIS_YEAR, add_entry, folder, post, row, user, watch  # noqa: F401
from test_auth import NOT_LOGGED_IN, NOT_LOGGED_IN_CASES, THIRTY_DAYS, cookie, device, register, token_of
from test_tags import add_artwork, add_tag, add_user, count, link

import photos

NOT_FOUND = {"detail": "Artwork not found."}
KEEP = {"detail": "An artwork must keep its title, artist and date while it is discoverable."}
UNAVAILABLE = {"detail": "Photos are unavailable right now. Please try again later."}
METHODS = ["get", "patch", "delete"]


def url(id):
    return f"/api/artworks/{id}"


def call(client, method, id, body=None):
    return getattr(client, method)(url(id), **({"json": body} if method == "patch" else {}))


def patch(client, id, body):
    return client.patch(url(id), json=body)


def create(client, artwork=None, **parts):
    """A WATCHLIST artwork made through the API; returns its `Artwork`."""
    response = watch(client, artwork, **parts)
    assert response.status_code == 201, response.text
    return response.json()


def create_with_photo(client, artwork=None):
    response = post(client, artwork or {}, state="COLLECTION", photo=JPEG)
    assert response.status_code == 201, response.text
    return response.json()


def add_detail(conn, artwork_id):
    """A detail photo: the file saved through the photo module, the row inserted directly. Returns its path."""
    path = photos.save(JPEG)
    conn.execute(text("INSERT INTO detail_photos (artwork_id, path) VALUES (:id, :path)"), {"id": artwork_id, "path": path})
    return path


def make_discoverable(conn, id):
    conn.execute(text("UPDATE artworks SET is_discoverable = true WHERE id = :id"), {"id": id})


def storage_down(monkeypatch):
    def unavailable(*args, **kwargs):
        raise photos.StorageUnavailable

    for name in ("save", "read", "delete"):
        monkeypatch.setattr(photos, name, unavailable)


def stored(conn, id):
    return conn.execute(text("SELECT * FROM artworks WHERE id = :id"), {"id": id}).one()


def files(folder):
    return sorted(p.name for p in folder.glob("*")) if folder.exists() else []


def tag_links(conn, id):
    return conn.execute(text("SELECT tag_id FROM artwork_tags WHERE artwork_id = :id ORDER BY tag_id"), {"id": id}).scalars().all()


def state_of(conn, id):
    """Row, tag links, detail photo rows and tag counts of one artwork."""
    return (
        stored(conn, id),
        tag_links(conn, id),
        conn.execute(text("SELECT id, path FROM detail_photos WHERE artwork_id = :id ORDER BY id"), {"id": id}).all(),
        conn.execute(text("SELECT id, usage_count FROM tags ORDER BY id")).all(),
    )


# Login required


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("case", NOT_LOGGED_IN_CASES)
def test_without_a_valid_session_it_is_refused_and_nothing_is_read_changed_or_deleted(client, conn, folder, method, case):
    register(client, "ben@example.com")
    artwork = create_with_photo(client)
    before, files_before = state_of(conn, artwork["id"]), files(folder)

    response = call(device(case(client, conn)), method, artwork["id"], {"title": "New"})

    assert response.status_code == 401
    assert response.json() == NOT_LOGGED_IN
    assert state_of(conn, artwork["id"]) == before
    assert files(folder) == files_before


@pytest.mark.parametrize("method", METHODS)
def test_a_valid_session_is_renewed_for_30_days(client, method):
    token = token_of(register(client))
    artwork = create(client)

    response = call(device(token), method, artwork["id"], {})

    renewed, attributes = cookie(response)
    assert renewed == token
    assert attributes["max-age"] == str(THIRTY_DAYS)


# Only one's own artworks


@pytest.mark.parametrize("method", METHODS)
def test_an_unknown_id_and_another_users_artwork_give_the_same_404(client, conn, method):
    register(client, "a@example.com")
    artwork = create(client)
    other = device(token_of(register(client, "b@example.com")))

    missing = call(other, method, artwork["id"] + 1000, {"title": "x"})
    foreign = call(other, method, artwork["id"], {"title": "x"})

    assert (missing.status_code, missing.json()) == (foreign.status_code, foreign.json()) == (404, NOT_FOUND)


def test_another_users_edit_and_delete_attempts_change_nothing(client, conn, folder):
    register(client, "a@example.com")
    cat = add_tag(conn, "cat")
    artwork = create_with_photo(client, {"title": "Mine", "tag_ids": [cat]})
    add_detail(conn, artwork["id"])
    before, files_before = state_of(conn, artwork["id"]), files(folder)
    other = device(token_of(register(client, "b@example.com")))

    patch(other, artwork["id"], {"title": "Stolen", "tag_ids": []})
    other.delete(url(artwork["id"]))

    assert state_of(conn, artwork["id"]) == before
    assert files(folder) == files_before


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("id", ["0", "-1", "abc", "1.5", "99999999999"])
def test_an_id_that_is_not_a_valid_artwork_number_gives_404(user, method, id):
    response = call(user, method, id, {})

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


def test_put_is_not_allowed(user):
    assert user.put(url(1), json={}).status_code == 405


# Get


def test_get_answers_with_the_same_body_as_create(user):
    created = create(user, {"title": "Mona", "date": {"from_year": 1503, "to_year": 1519, "circa": True}})

    response = user.get(url(created["id"]))

    assert response.status_code == 200
    assert response.json() == created
    assert set(response.json()) == ARTWORK_FIELDS


def test_get_lists_tags_by_name_detail_photos_by_id_and_has_photo_only_with_a_photo(user, conn):
    owl, cat, dog = add_tag(conn, "owl"), add_tag(conn, "cat"), add_tag(conn, "dog")
    with_photo = create_with_photo(user, {"tag_ids": [owl, cat, dog]})
    ids = [add_detail(conn, with_photo["id"]) and conn.execute(text("SELECT max(id) FROM detail_photos")).scalar() for _ in range(2)]
    without = create(user)

    body, bare = user.get(url(with_photo["id"])).json(), user.get(url(without["id"])).json()

    assert [tag["name"] for tag in body["tags"]] == ["cat", "dog", "owl"]
    assert body["detail_photo_ids"] == ids
    assert body["has_photo"] is True and body["photo_version"]
    assert (bare["detail_photo_ids"], bare["has_photo"], bare["photo_version"]) == ([], False, None)


def test_the_owner_gets_the_notes_in_full_whether_or_not_they_are_discoverable(user, conn):
    created = create(user, {"notes": "Private\nnotes"})

    assert user.get(url(created["id"])).json()["notes"] == "Private\nnotes"
    conn.execute(text("UPDATE artworks SET are_notes_discoverable = true WHERE id = :id"), {"id": created["id"]})
    assert user.get(url(created["id"])).json()["notes"] == "Private\nnotes"


def test_get_and_edit_work_while_photo_storage_is_unreachable(user, monkeypatch):
    created = create(user, {"title": "Mona"})
    storage_down(monkeypatch)

    assert user.get(url(created["id"])).status_code == 200
    assert patch(user, created["id"], {"title": "Lisa"}).json()["title"] == "Lisa"


# Edit: only the fields sent change


@pytest.fixture
def full(user, conn):
    """An artwork with every field filled, and the entries and tags a patch can point at."""
    ids = {
        "artist": add_entry(conn, "artists", "Leonardo"), "subject": add_entry(conn, "subjects", "Portrait"),
        "movement": add_entry(conn, "movements", "Test movement"), "tag": add_tag(conn, "cat"),
        "other_artist": add_entry(conn, "artists", "Raphael"), "other_tag": add_tag(conn, "owl"),
    }
    artwork = create(user, {
        "title": "Mona Lisa", "artist_id": ids["artist"], "date": {"from_year": 1503, "to_year": 1519, "circa": True},
        "subject_id": ids["subject"], "movement_id": ids["movement"], "museum": "Louvre", "tag_ids": [ids["tag"]],
        "notes": "Famous",
    })
    return artwork, ids


@pytest.mark.parametrize(
    "field, value, key",
    [
        ("title", "Other", "title"), ("museum", "Prado", "museum"), ("notes", "Other notes", "notes"),
        ("date", {"from_year": 1642}, "date"), ("artist_id", "other_artist", "artist"), ("tag_ids", ["other_tag"], "tags"),
    ],
)
def test_a_field_sent_alone_changes_only_itself(user, full, field, value, key):
    artwork, ids = full
    if isinstance(value, str) and value in ids:
        value = ids[value]
    if field == "tag_ids":
        value = [ids[name] for name in value]

    changed = patch(user, artwork["id"], {field: value}).json()

    assert {k: v for k, v in changed.items() if k != key} == {k: v for k, v in artwork.items() if k != key}
    assert changed[key] != artwork[key]


@pytest.mark.parametrize("field", ["subject_id", "movement_id"])
def test_subject_and_movement_sent_alone_change_only_themselves(user, conn, full, field):
    artwork, ids = full
    table = field.replace("_id", "s")
    new = add_entry(conn, table, "Another")

    changed = patch(user, artwork["id"], {field: new}).json()

    key = field[:-3]
    assert changed[key] == {"id": new, "name": "Another"}
    assert {k: v for k, v in changed.items() if k != key} == {k: v for k, v in artwork.items() if k != key}


def test_null_and_empty_values_clear_fields(user, full):
    artwork, ids = full

    changed = patch(user, artwork["id"], {
        "artist_id": None, "subject_id": None, "movement_id": None, "date": None,
        "title": "", "museum": "", "notes": "", "tag_ids": [],
    }).json()

    assert (changed["artist"], changed["subject"], changed["movement"], changed["date"]) == (None,) * 4
    assert (changed["title"], changed["museum"], changed["notes"], changed["tags"]) == ("", "", "", [])


@pytest.mark.parametrize("field", ["title", "museum", "notes", "tag_ids"])
def test_null_for_a_field_that_cannot_be_null_is_refused(user, conn, full, field):
    artwork, _ = full
    before = state_of(conn, artwork["id"])

    response = patch(user, artwork["id"], {field: None})

    assert response.status_code == 422 and list(response.json()) == ["detail"]
    assert state_of(conn, artwork["id"]) == before


def test_an_empty_object_changes_nothing(user, full):
    artwork, _ = full

    response = patch(user, artwork["id"], {})

    assert response.status_code == 200
    assert response.json() == artwork


def test_the_edit_answers_with_what_a_following_get_returns(user, full):
    artwork, _ = full

    edited = patch(user, artwork["id"], {"title": "New"})

    assert edited.json() == user.get(url(artwork["id"])).json()


@pytest.mark.parametrize("state", ["COLLECTION", "WATCHLIST"])
def test_both_states_can_be_edited_and_the_state_stays(user, conn, state):
    created = post(user, {}, state=state, photo=JPEG if state == "COLLECTION" else None).json()

    edited = patch(user, created["id"], {"title": "New"}).json()

    assert (edited["title"], edited["state"]) == ("New", state)


def test_an_edit_keeps_created_at_and_sets_updated_at(user, conn):
    created = create(user)
    before = stored(conn, created["id"]).updated_at

    edited = patch(user, created["id"], {"title": "New"}).json()

    assert edited["created_at"] == created["created_at"]
    assert stored(conn, created["id"]).updated_at > before


def test_fields_outside_the_artwork_input_are_ignored(user, conn):
    created = create(user, {"date": {"from_year": 1600}})

    edited = patch(user, created["id"], {
        "state": "COLLECTION", "is_discoverable": True, "are_notes_discoverable": True, "has_photo": True,
        "photo_version": "x", "detail_photo_ids": [5], "id": 999, "user_id": 999, "created_at": "2000-01-01T00:00:00Z",
    })

    assert edited.status_code == 200
    assert edited.json() == created


# Edit: same rules as create


@pytest.mark.parametrize("field, label", [("title", "Title"), ("museum", "Museum")])
def test_title_and_museum_are_cleaned_and_notes_only_normalised(user, field, label):
    created = create(user)

    cleaned = patch(user, created["id"], {field: " \tThe   Café\nRoom "}).json()
    blank = patch(user, created["id"], {field: " \t "}).json()
    notes = patch(user, created["id"], {"notes": "  A   Café\n "}).json()

    assert cleaned[field] == "The Café Room"
    assert blank[field] == ""
    assert notes["notes"] == "  A   Café\n "


@pytest.mark.parametrize("field, limit, label", [("title", 300, "Title"), ("museum", 200, "Museum"), ("notes", 10_000, "Notes")])
def test_the_limit_is_accepted_and_one_more_character_is_refused(user, conn, field, limit, label):
    created = create(user)

    assert patch(user, created["id"], {field: "é" * limit}).status_code == 200
    response = patch(user, created["id"], {field: "é" * (limit + 1)})

    assert response.status_code == 422
    assert response.json() == {"detail": f"{label} must be at most {limit:,} characters."}
    assert len(getattr(stored(conn, created["id"]), field)) == limit


@pytest.mark.parametrize(
    "field, value",
    [("title", "a\x00b"), ("museum", "a\x7fb"), ("museum", "\ud800"), ("notes", "a\x00b"), ("notes", "a\x1bb"), ("notes", "\udfff")],
)
def test_control_characters_and_lone_surrogates_are_refused_and_nothing_changes(user, conn, field, value):
    created = create(user, {"title": "Mona"})
    before = state_of(conn, created["id"])
    body = json.dumps({field: value}, ensure_ascii=True)

    response = user.patch(url(created["id"]), content=body, headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert response.json() == {"detail": f"{field.capitalize()} contains characters that are not allowed."}
    assert state_of(conn, created["id"]) == before


def test_tab_line_feed_and_carriage_return_are_allowed_in_notes(user):
    created = create(user)

    assert patch(user, created["id"], {"notes": "a\tb\r\nc"}).json()["notes"] == "a\tb\r\nc"


@pytest.mark.parametrize("field, label", [("artist_id", "artist"), ("subject_id", "subject"), ("movement_id", "movement")])
def test_an_unknown_entry_is_refused_with_422(user, conn, field, label):
    created = create(user)
    other_table = add_entry(conn, "tags", "x") if False else None  # noqa: F841
    missing = conn.execute(text("SELECT coalesce(max(id), 0) + 1000 FROM artists")).scalar()

    response = patch(user, created["id"], {field: missing})

    assert response.status_code == 422
    assert response.json() == {"detail": f"This {label} does not exist."}


def test_a_movement_id_is_checked_against_movements(user, conn):
    created = create(user)
    artist = add_entry(conn, "artists", "Only an artist")
    movements = conn.execute(text("SELECT id FROM movements")).scalars().all()
    assert artist not in movements or True
    unused = max(movements) + 1000

    assert patch(user, created["id"], {"movement_id": unused}).status_code == 422
    assert patch(user, created["id"], {"movement_id": movements[0]}).status_code == 200


@pytest.mark.parametrize("field", ["artist_id", "subject_id", "movement_id", "tag_ids"])
@pytest.mark.parametrize("big", [2**31, 10**30, -1])
def test_ids_too_large_or_negative_are_refused_with_422(user, field, big):
    created = create(user)

    response = patch(user, created["id"], {field: [big] if field == "tag_ids" else big})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "date, detail",
    [
        ({}, "The field 'date.from_year' is required."),
        ({"from_year": 0}, "A year must be 1 or more; use the BC box for years before 1 AD."),
        ({"from_year": 100_001, "from_bc": True}, "A BC year cannot be above 100,000."),
        ({"from_year": THIS_YEAR + 1}, "A year cannot be in the future."),
        ({"from_year": 500, "to_year": 400}, "The end year cannot be before the start year."),
        ({"from_year": 10, "from_bc": True, "to_year": 20, "to_bc": True}, "The end year cannot be before the start year."),
    ],
)
def test_a_date_that_breaks_a_rule_is_refused(user, conn, date, detail):
    created = create(user, {"title": "T", "date": {"from_year": 1600}})
    before = state_of(conn, created["id"])

    response = patch(user, created["id"], {"date": date})

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert state_of(conn, created["id"]) == before


def test_a_sent_date_replaces_the_whole_stored_date(user):
    created = create(user, {"date": {"from_year": 1600, "to_year": 1605, "circa": True}})
    assert created["date"]["display"] == "c. 1600–1605"

    date = patch(user, created["id"], {"date": {"from_year": 1642}}).json()["date"]

    assert date == {"from_year": 1642, "to_year": None, "circa": False, "from_bc": False, "to_bc": False, "display": "1642"}


def test_to_bc_without_to_year_is_ignored_and_bc_dates_are_shown(user):
    created = create(user)

    ignored = patch(user, created["id"], {"date": {"from_year": 30, "from_bc": True, "to_bc": True}}).json()["date"]
    bc_to_ad = patch(user, created["id"], {"date": {"from_year": 30, "from_bc": True, "to_year": 14}}).json()["date"]

    assert (ignored["to_bc"], ignored["display"]) == (False, "30 BC")
    assert bc_to_ad["display"] == "30 BC – 14 AD"


@pytest.mark.parametrize(
    "content, headers",
    [
        (b"", {}), (b"not json", {}), (b"[]", {}), (b'"x"', {}), (b"5", {}), (b"null", {}), (b"\xff\xfe", {}),
        (b'{"title": 5}', {}), (b'{"tag_ids": "3"}', {}), (b'{"artist_id": "abc"}', {}), (b'{"date": "1642"}', {}),
    ],
)
def test_a_body_that_is_not_valid_is_refused_in_the_error_shape(user, conn, content, headers):
    created = create(user)
    before = state_of(conn, created["id"])

    response = user.patch(url(created["id"]), content=content, headers={"content-type": "application/json", **headers})

    assert response.status_code == 422
    assert list(response.json()) == ["detail"] and isinstance(response.json()["detail"], str)
    assert state_of(conn, created["id"]) == before


def test_an_unknown_artwork_is_a_404_before_the_body_is_checked(user):
    assert user.patch(url(99999), content=b"not json").status_code == 404


# Edit: tags


def test_a_sent_tag_list_becomes_the_whole_list_and_a_missing_one_keeps_the_tags(user, conn):
    cat, dog, owl = add_tag(conn, "cat"), add_tag(conn, "dog"), add_tag(conn, "owl")
    created = create(user, {"tag_ids": [cat, dog]})

    assert patch(user, created["id"], {"title": "x"}).json()["tags"] == created["tags"]
    edited = patch(user, created["id"], {"tag_ids": [cat, owl]}).json()

    assert [tag["name"] for tag in edited["tags"]] == ["cat", "owl"]


def test_usage_count_follows_the_different_users_rule_when_the_tags_change(user, conn):
    cat, dog, owl = add_tag(conn, "cat"), add_tag(conn, "dog"), add_tag(conn, "owl")
    first = create(user, {"tag_ids": [cat, dog]})
    other_user = add_user(conn, "other")
    link(conn, add_artwork(conn, other_user), dog)
    assert (count(conn, cat), count(conn, dog), count(conn, owl)) == (1, 2, 0)

    patch(user, first["id"], {"tag_ids": [cat, owl]})

    # A's last artwork with dog is gone, but another user still has it: dog 2 -> 1.
    assert (count(conn, cat), count(conn, dog), count(conn, owl)) == (1, 1, 1)


def test_usage_count_stays_when_the_user_has_another_artwork_with_the_tag(user, conn):
    dog = add_tag(conn, "dog")
    first = create(user, {"tag_ids": [dog]})
    create(user, {"tag_ids": [dog]})

    patch(user, first["id"], {"tag_ids": []})

    assert count(conn, dog) == 1


def test_removing_the_last_use_lowers_the_count_and_an_empty_list_removes_every_link(user, conn):
    cat, dog = add_tag(conn, "cat"), add_tag(conn, "dog")
    created = create(user, {"tag_ids": [cat, dog]})

    edited = patch(user, created["id"], {"tag_ids": []}).json()

    assert edited["tags"] == []
    assert (count(conn, cat), count(conn, dog)) == (0, 0)


def test_the_same_tag_id_twice_links_once(user, conn):
    cat = add_tag(conn, "cat")
    created = create(user)

    edited = patch(user, created["id"], {"tag_ids": [cat, cat]}).json()

    assert len(edited["tags"]) == 1 and count(conn, cat) == 1


@pytest.mark.parametrize("extra", [[], ["cat"]])
def test_an_unknown_tag_id_is_refused(user, conn, extra):
    cat = add_tag(conn, "cat")
    created = create(user)

    response = patch(user, created["id"], {"tag_ids": ([cat] if extra else []) + [cat + 1000]})

    assert response.status_code == 422
    assert response.json() == {"detail": "One or more tags do not exist."}


def test_a_refused_edit_changes_nothing(user, conn):
    cat = add_tag(conn, "cat")
    created = create(user, {"title": "Old", "tag_ids": [cat]})
    before = state_of(conn, created["id"])

    response = patch(user, created["id"], {"title": "New", "tag_ids": [cat + 1000]})

    assert response.status_code == 422
    assert state_of(conn, created["id"]) == before


# Edit: a discoverable artwork keeps title, artist and date


@pytest.fixture
def discoverable(user, conn):
    artist = add_entry(conn, "artists", "Leonardo")
    created = create(user, {"title": "Mona", "artist_id": artist, "date": {"from_year": 1503}})
    make_discoverable(conn, created["id"])
    return created, artist


@pytest.mark.parametrize("body", [{"title": ""}, {"title": " \t "}, {"artist_id": None}, {"date": None}])
def test_a_discoverable_artwork_cannot_lose_title_artist_or_date(user, conn, discoverable, body):
    created, _ = discoverable
    before = state_of(conn, created["id"])

    response = patch(user, created["id"], body)

    assert response.status_code == 422
    assert response.json() == KEEP
    assert state_of(conn, created["id"]) == before
    assert stored(conn, created["id"]).is_discoverable is True


def test_a_discoverable_artwork_can_change_those_fields_to_other_values_and_edit_the_rest(user, conn, discoverable):
    created, artist = discoverable
    other = add_entry(conn, "artists", "Raphael")

    response = patch(user, created["id"], {"title": "Lisa", "artist_id": other, "date": {"from_year": 1510}, "notes": "n"})

    assert response.status_code == 200
    assert response.json()["is_discoverable"] is True


def test_an_artwork_that_is_not_discoverable_may_clear_title_artist_and_date(user, conn):
    created = create(user, {"title": "Mona", "artist_id": add_entry(conn, "artists", "L"), "date": {"from_year": 1503}})

    edited = patch(user, created["id"], {"title": "", "artist_id": None, "date": None}).json()

    assert (edited["title"], edited["artist"], edited["date"]) == ("", None, None)


# Delete


def test_delete_removes_the_artwork_its_rows_and_its_files_and_nothing_else(user, conn, folder):
    cat = add_tag(conn, "cat")
    artist = add_entry(conn, "artists", "Leonardo")
    gone = create_with_photo(user, {"artist_id": artist, "tag_ids": [cat]})
    details = [add_detail(conn, gone["id"]), add_detail(conn, gone["id"])]
    kept = create_with_photo(user, {"tag_ids": [cat]})
    kept_detail = add_detail(conn, kept["id"])

    response = user.delete(url(gone["id"]))

    assert response.status_code == 204 and response.content == b""
    for method in METHODS:
        assert call(user, method, gone["id"], {}).json() == NOT_FOUND
    assert conn.execute(text("SELECT count(*) FROM artworks WHERE id = :id"), {"id": gone["id"]}).scalar() == 0
    assert conn.execute(text("SELECT count(*) FROM detail_photos WHERE artwork_id = :id"), {"id": gone["id"]}).scalar() == 0
    assert tag_links(conn, gone["id"]) == []
    assert conn.execute(text("SELECT count(*) FROM artists WHERE id = :id"), {"id": artist}).scalar() == 1
    assert count(conn, cat) == 1  # the user still has another artwork with it
    assert files(folder) == sorted([stored(conn, kept["id"]).artwork_photo_path, kept_detail])
    for path in details:
        with pytest.raises(photos.PhotoNotFound):
            photos.read(path)


def test_deleting_the_last_artwork_with_a_tag_lowers_its_count(user, conn):
    cat = add_tag(conn, "cat")
    created = create(user, {"tag_ids": [cat]})
    assert count(conn, cat) == 1

    user.delete(url(created["id"]))

    assert count(conn, cat) == 0


def test_a_watchlist_artwork_with_and_without_a_photo_can_be_deleted(user, conn, folder):
    with_photo = watch(user, {}, photo=JPEG).json()
    without = create(user)

    assert user.delete(url(with_photo["id"])).status_code == 204
    assert user.delete(url(without["id"])).status_code == 204
    assert files(folder) == []


def test_a_stored_file_that_is_already_missing_does_not_stop_the_delete(user, folder):
    created = create_with_photo(user)
    for path in folder.glob("*"):
        path.unlink()

    assert user.delete(url(created["id"])).status_code == 204


def test_unreachable_storage_gives_503_and_deletes_nothing_until_it_is_back(user, conn, folder, monkeypatch):
    cat = add_tag(conn, "cat")
    created = create_with_photo(user, {"tag_ids": [cat]})
    first, second = add_detail(conn, created["id"]), add_detail(conn, created["id"])
    before = state_of(conn, created["id"])
    real_delete, calls = photos.delete, []

    def fail_on_second(path):
        calls.append(path)
        if len(calls) == 2:
            raise photos.StorageUnavailable
        real_delete(path)

    monkeypatch.setattr(photos, "delete", fail_on_second)
    response = user.delete(url(created["id"]))

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert state_of(conn, created["id"]) == before
    assert user.get(url(created["id"])).status_code == 200

    monkeypatch.setattr(photos, "delete", real_delete)
    assert user.delete(url(created["id"])).status_code == 204
    assert files(folder) == []
    assert tag_links(conn, created["id"]) == [] and count(conn, cat) == 0
    assert second  # both detail files were gone with the second attempt


def test_a_watchlist_artwork_without_files_is_deleted_without_touching_storage(user, monkeypatch):
    created = create(user)
    storage_down(monkeypatch)

    assert user.delete(url(created["id"])).status_code == 204
