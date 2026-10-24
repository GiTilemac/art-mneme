from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

SEEDED_MOVEMENTS = [
    "Gothic",
    "Renaissance",
    "Mannerism",
    "Baroque",
    "Rococo",
    "Neoclassicism",
    "Romanticism",
    "Realism",
    "Impressionism",
    "Post-Impressionism",
    "Symbolism",
    "Expressionism",
    "Cubism",
    "Surrealism",
    "Abstract Expressionism",
    "Pop Art",
]

COLUMNS = {
    "users": ["id", "email", "password_hash", "created_at", "updated_at"],
    "artworks": [
        "id",
        "user_id",
        "collection_state",
        "title",
        "artist_id",
        "date_display",
        "year_start",
        "year_end",
        "date_is_circa",
        "subject_id",
        "movement_id",
        "museum",
        "notes",
        "is_discoverable",
        "are_notes_discoverable",
        "artwork_photo_path",
        "created_at",
        "updated_at",
    ],
    "artists": ["id", "name", "created_at"],
    "movements": ["id", "name", "created_at"],
    "subjects": ["id", "name", "created_at"],
    "tags": ["id", "name", "usage_count", "created_at"],
    "artwork_tags": ["artwork_id", "tag_id", "source"],
    "detail_photos": ["id", "artwork_id", "path", "created_at"],
}

COMMUNITY_TABLES = ["artists", "movements", "subjects", "tags"]


def insert(conn, table, **values):
    if values:
        sql = f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join(':' + c for c in values)})"
    else:
        sql = f"INSERT INTO {table} DEFAULT VALUES"
    return conn.execute(text(sql + " RETURNING *"), values).one()


@contextmanager
def refused(conn):
    """The statement inside must be refused by the database."""
    with pytest.raises(IntegrityError), conn.begin_nested():
        yield


def user(conn, email="ann@example.com"):
    return insert(conn, "users", email=email, password_hash="hash").id


def artwork(conn, **values):
    values.setdefault("user_id", user(conn))
    values.setdefault("artwork_photo_path", "photos/1.jpg")
    return insert(conn, "artworks", **values).id


def count(conn, table, where="true", **params):
    return conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), params).scalar()


def columns(conn, table):
    return conn.execute(
        text(
            "SELECT column_name, data_type, column_default FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = :table ORDER BY ordinal_position"
        ),
        {"table": table},
    ).all()


def index_definitions(conn, table):
    return conn.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename = :table"), {"table": table}).scalars().all()


# Tables and columns


@pytest.mark.parametrize("table", COLUMNS)
def test_table_has_the_documented_columns(conn, table):
    assert [name for name, _, _ in columns(conn, table)] == COLUMNS[table]


@pytest.mark.parametrize("table", [t for t in COLUMNS if t != "artwork_tags"])
def test_every_id_is_an_auto_numbered_integer(conn, table):
    id_column = next(c for c in columns(conn, table) if c.column_name == "id")
    assert id_column.data_type == "integer"
    assert id_column.column_default.startswith("nextval(")


@pytest.mark.parametrize("missing", ["email", "password_hash"])
def test_user_without_email_or_password_hash_is_refused(conn, missing):
    values = {"email": "ann@example.com", "password_hash": "hash"}
    del values[missing]
    with refused(conn):
        insert(conn, "users", **values)


def test_two_users_with_same_email_in_other_case_are_refused(conn):
    user(conn, "Ann@x.com")
    with refused(conn):
        user(conn, "ann@X.com")


def test_artwork_with_only_user_and_photo_gets_the_defaults(conn):
    row = conn.execute(text("SELECT * FROM artworks WHERE id = :id"), {"id": artwork(conn)}).one()
    assert row.collection_state == "COLLECTION"
    assert row.is_discoverable is False
    assert row.are_notes_discoverable is False
    assert row.date_is_circa is False
    assert (row.title, row.museum, row.notes) == ("", "", "")
    assert (row.artist_id, row.subject_id, row.movement_id) == (None, None, None)
    assert (row.year_start, row.year_end, row.date_display) == (None, None, None)


def test_artwork_without_user_is_refused(conn):
    with refused(conn):
        insert(conn, "artworks", artwork_photo_path="photos/1.jpg")


def test_artwork_with_artist_subject_and_movement_is_accepted(conn):
    artwork(
        conn,
        artist_id=insert(conn, "artists", name="Rembrandt").id,
        subject_id=insert(conn, "subjects", name="Cat").id,
        movement_id=insert(conn, "movements", name="Dutch Golden Age").id,
    )


@pytest.mark.parametrize("table", ["artists", "movements", "subjects"])
def test_community_entity_without_name_is_refused(conn, table):
    with refused(conn):
        insert(conn, table)


def test_tag_usage_count_starts_at_zero(conn):
    assert insert(conn, "tags", name="battle").usage_count == 0


def test_tag_link_source_defaults_to_user(conn):
    tag_id = insert(conn, "tags", name="battle").id
    assert insert(conn, "artwork_tags", artwork_id=artwork(conn), tag_id=tag_id).source == "USER"


def test_detail_photo_without_path_is_refused(conn):
    artwork_id = artwork(conn)
    with refused(conn):
        insert(conn, "detail_photos", artwork_id=artwork_id)


def test_created_at_and_updated_at_are_filled_in_with_time_zone(conn):
    for table in COLUMNS:
        for name, data_type, _ in columns(conn, table):
            if name in ("created_at", "updated_at"):
                assert data_type == "timestamp with time zone", (table, name)
    now = conn.execute(text("SELECT now()")).scalar()
    row = conn.execute(text("SELECT * FROM artworks WHERE id = :id"), {"id": artwork(conn)}).one()
    assert row.created_at == now and row.updated_at == now
    assert row.created_at.tzinfo is not None
    for table in ("users", "artists", "movements", "subjects", "tags"):
        values = {"email": "bob@example.com", "password_hash": "hash"} if table == "users" else {"name": "Ship"}
        assert insert(conn, table, **values).created_at == now
    assert insert(conn, "detail_photos", artwork_id=row.id, path="details/1.jpg").created_at == now


# Rules the database enforces


@pytest.mark.parametrize("state", ["collection", "DONE"])
def test_unknown_collection_state_is_refused(conn, state):
    user_id = user(conn)
    with refused(conn):
        artwork(conn, user_id=user_id, collection_state=state)


def test_collection_artwork_without_photo_is_refused(conn):
    user_id = user(conn)
    with refused(conn):
        artwork(conn, user_id=user_id, artwork_photo_path=None)


def test_watchlist_artwork_with_or_without_photo_is_accepted(conn):
    user_id = user(conn)
    artwork(conn, user_id=user_id, collection_state="WATCHLIST", artwork_photo_path=None)
    artwork(conn, user_id=user_id, collection_state="WATCHLIST", artwork_photo_path="photos/2.jpg")


@pytest.mark.parametrize("source", ["user", "OTHER"])
def test_unknown_tag_link_source_is_refused(conn, source):
    artwork_id, tag_id = artwork(conn), insert(conn, "tags", name="battle").id
    with refused(conn):
        insert(conn, "artwork_tags", artwork_id=artwork_id, tag_id=tag_id, source=source)


def test_system_tag_link_source_is_accepted(conn):
    tag_id = insert(conn, "tags", name="battle").id
    insert(conn, "artwork_tags", artwork_id=artwork(conn), tag_id=tag_id, source="SYSTEM")


@pytest.mark.parametrize("table", COMMUNITY_TABLES)
def test_second_name_in_other_case_is_refused(conn, table):
    insert(conn, table, name="Cat")
    for name in ("cat", "CAT", "Cat"):
        with refused(conn):
            insert(conn, table, name=name)


def test_second_artist_with_same_name_in_other_case_is_refused(conn):
    insert(conn, "artists", name="Rembrandt")
    with refused(conn):
        insert(conn, "artists", name="rembrandt")


@pytest.mark.parametrize("table", COMMUNITY_TABLES)
def test_names_that_differ_by_more_than_case_are_accepted(conn, table):
    insert(conn, table, name="Rembrandt")
    insert(conn, table, name="Rembrandt van Rijn")
    assert count(conn, table, "name LIKE 'Rembrandt%'") == 2


def test_same_tag_twice_on_same_artwork_is_refused(conn):
    artwork_id, tag_id = artwork(conn), insert(conn, "tags", name="battle").id
    insert(conn, "artwork_tags", artwork_id=artwork_id, tag_id=tag_id)
    with refused(conn):
        insert(conn, "artwork_tags", artwork_id=artwork_id, tag_id=tag_id, source="SYSTEM")


def test_same_tag_on_two_artworks_is_accepted(conn):
    user_id, tag_id = user(conn), insert(conn, "tags", name="battle").id
    insert(conn, "artwork_tags", artwork_id=artwork(conn, user_id=user_id), tag_id=tag_id)
    insert(conn, "artwork_tags", artwork_id=artwork(conn, user_id=user_id), tag_id=tag_id)


def test_negative_usage_count_is_refused(conn):
    with refused(conn):
        insert(conn, "tags", name="battle", usage_count=-1)


@pytest.mark.parametrize("years", [{"year_start": 0}, {"year_start": -5, "year_end": 0}])
def test_year_zero_is_refused(conn, years):
    user_id = user(conn)
    with refused(conn):
        artwork(conn, user_id=user_id, **years)


@pytest.mark.parametrize("start, end", [(1605, 1600), (-450, -500)])
def test_year_end_earlier_than_year_start_is_refused(conn, start, end):
    user_id = user(conn)
    with refused(conn):
        artwork(conn, user_id=user_id, year_start=start, year_end=end)


@pytest.mark.parametrize("start, end", [(1600, 1605), (1600, 1600), (-500, -450), (-1, 1)])
def test_year_end_equal_to_or_later_than_year_start_is_accepted(conn, start, end):
    artwork(conn, year_start=start, year_end=end)


def test_year_end_without_year_start_is_refused(conn):
    user_id = user(conn)
    with refused(conn):
        artwork(conn, user_id=user_id, year_end=1600)


def test_bc_year_is_stored_as_negative_number(conn):
    artwork_id = artwork(conn, year_start=-450, date_is_circa=True)
    row = conn.execute(text("SELECT year_start, date_is_circa FROM artworks WHERE id = :id"), {"id": artwork_id}).one()
    assert (row.year_start, row.date_is_circa) == (-450, True)


@pytest.mark.parametrize("column", ["user_id", "artist_id", "subject_id", "movement_id"])
def test_artwork_pointing_to_missing_row_is_refused(conn, column):
    values = {"user_id": user(conn), column: 999999}
    with refused(conn):
        artwork(conn, **values)


@pytest.mark.parametrize("missing", ["artwork", "tag"])
def test_tag_link_pointing_to_missing_row_is_refused(conn, missing):
    artwork_id = 999999 if missing == "artwork" else artwork(conn)
    tag_id = 999999 if missing == "tag" else insert(conn, "tags", name="battle").id
    with refused(conn):
        insert(conn, "artwork_tags", artwork_id=artwork_id, tag_id=tag_id)


def test_detail_photo_pointing_to_missing_artwork_is_refused(conn):
    with refused(conn):
        insert(conn, "detail_photos", artwork_id=999999, path="details/1.jpg")


# Deleting


def test_deleting_artwork_deletes_its_detail_photos_and_tag_links_only(conn):
    user_id = user(conn)
    used = {
        "artist_id": insert(conn, "artists", name="Rembrandt").id,
        "subject_id": insert(conn, "subjects", name="Cat").id,
        "movement_id": insert(conn, "movements", name="Dutch Golden Age").id,
    }
    tag_id = insert(conn, "tags", name="battle").id
    deleted, kept = artwork(conn, user_id=user_id, **used), artwork(conn, user_id=user_id, **used)
    for artwork_id in (deleted, kept):
        insert(conn, "artwork_tags", artwork_id=artwork_id, tag_id=tag_id)
        insert(conn, "detail_photos", artwork_id=artwork_id, path=f"details/{artwork_id}.jpg")

    conn.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": deleted})

    assert count(conn, "artwork_tags", "artwork_id = :id", id=deleted) == 0
    assert count(conn, "detail_photos", "artwork_id = :id", id=deleted) == 0
    assert count(conn, "artwork_tags", "artwork_id = :id", id=kept) == 1
    assert count(conn, "detail_photos", "artwork_id = :id", id=kept) == 1
    assert count(conn, "tags", "id = :id", id=tag_id) == 1
    assert count(conn, "users", "id = :id", id=user_id) == 1
    for column, entity_id in used.items():
        assert count(conn, column.removesuffix("_id") + "s", "id = :id", id=entity_id) == 1


@pytest.mark.parametrize("table", COMMUNITY_TABLES)
def test_deleting_community_entity_used_by_artwork_is_refused(conn, table):
    entity_id = insert(conn, table, name="Cat").id
    if table == "tags":
        insert(conn, "artwork_tags", artwork_id=artwork(conn), tag_id=entity_id)
    else:
        artwork(conn, **{table.removesuffix("s") + "_id": entity_id})
    with refused(conn):
        conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": entity_id})


def test_deleting_user_with_artworks_is_refused(conn):
    user_id = user(conn)
    artwork(conn, user_id=user_id)
    with refused(conn):
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


# Indexes


@pytest.mark.parametrize(
    "column", ["user_id", "collection_state", "artist_id", "subject_id", "movement_id", "is_discoverable"]
)
def test_artworks_has_an_index_on(conn, column):
    assert any(d.endswith(f"USING btree ({column})") for d in index_definitions(conn, "artworks"))


@pytest.mark.parametrize("table", COMMUNITY_TABLES)
def test_community_table_has_a_unique_index_on_name_ignoring_case(conn, table):
    assert any(
        d.startswith("CREATE UNIQUE INDEX") and d.endswith("USING btree (lower(name))")
        for d in index_definitions(conn, table)
    )


@pytest.mark.parametrize("column", ["artwork_id", "tag_id"])
def test_artwork_tags_has_an_index_on(conn, column):
    assert any(d.endswith(f"USING btree ({column})") for d in index_definitions(conn, "artwork_tags"))


# Seed data


def test_movements_are_the_16_seeded_names(conn):
    assert conn.execute(text("SELECT name FROM movements ORDER BY id")).scalars().all() == SEEDED_MOVEMENTS


@pytest.mark.parametrize("table", [t for t in COLUMNS if t != "movements"])
def test_no_other_table_has_seed_rows(conn, table):
    assert count(conn, table) == 0
