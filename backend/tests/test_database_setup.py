import os
import subprocess
import sys

from conftest import BACKEND, empty_database, run_schema_command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

import db
from main import app

TABLES = {"users", "artworks", "artists", "movements", "subjects", "tags", "artwork_tags", "detail_photos"}


def run_tests(**env):
    """Run the #1 tests in a separate pytest, with these environment variables changed (None removes one)."""
    environment = {**os.environ, **env}
    environment = {name: value for name, value in environment.items() if value is not None}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_health.py"],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
    )


def movement_names(engine):
    with engine.connect() as connection:
        return connection.execute(text("SELECT name FROM movements")).scalars().all()


def all_rows(engine):
    with engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1, 2")).all() for table in TABLES}


# Connection settings


def test_schema_command_without_database_url_names_the_variable():
    environment = {name: value for name, value in os.environ.items() if name != "DATABASE_URL"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=environment, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "DATABASE_URL is not set" in result.stderr
    assert "Traceback" not in result.stderr


def test_tests_without_test_database_url_stop_and_name_the_variable():
    result = run_tests(TEST_DATABASE_URL=None)
    assert result.returncode != 0
    assert "TEST_DATABASE_URL is not set" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_tests_stop_when_test_database_is_the_development_database(engine, test_database_url):
    result = run_tests(DATABASE_URL=test_database_url)
    assert result.returncode != 0
    assert "point to the same database" in result.stdout + result.stderr
    assert inspect(engine).get_table_names()  # the test database was not emptied


def test_tests_stop_when_development_url_names_the_test_database_with_another_host_spelling(engine, test_database_url):
    url = make_url(test_database_url)
    other_host = "127.0.0.1" if url.host == "localhost" else "localhost"
    result = run_tests(DATABASE_URL=url.set(host=other_host).render_as_string(hide_password=False))
    assert result.returncode != 0
    assert "point to the same database" in result.stdout + result.stderr
    assert inspect(engine).get_table_names()  # the test database was not emptied


def test_tests_stop_when_development_database_cannot_be_reached(engine, test_database_url):
    unreachable = make_url(test_database_url).set(port=1).render_as_string(hide_password=False)
    result = run_tests(DATABASE_URL=unreachable)
    assert result.returncode != 0
    assert "Cannot connect to the database in DATABASE_URL" in result.stdout + result.stderr
    assert inspect(engine).get_table_names()  # the test database was not emptied


def test_tests_fail_with_a_clear_message_when_test_database_url_is_malformed():
    result = run_tests(TEST_DATABASE_URL="notaurl")
    assert result.returncode != 0
    assert "Cannot connect to the test database in TEST_DATABASE_URL" in result.stdout + result.stderr
    assert "INTERNALERROR" not in result.stdout + result.stderr


def test_tests_fail_with_a_clear_message_when_test_database_cannot_be_reached(test_database_url):
    unreachable = make_url(test_database_url).set(port=1).render_as_string(hide_password=False)
    result = run_tests(TEST_DATABASE_URL=unreachable)
    assert result.returncode != 0
    assert "Cannot connect to the test database in TEST_DATABASE_URL" in result.stdout + result.stderr
    assert "skipped" not in result.stdout


def test_backend_starts_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_backend_connection_code_connects_to_the_test_database(monkeypatch, test_database_url):
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    db.get_engine.cache_clear()
    try:
        with db.get_engine().connect() as connection:
            assert connection.execute(text("SELECT current_database()")).scalar() == make_url(test_database_url).database
    finally:
        db.get_engine().dispose()
        db.get_engine.cache_clear()


# The one command


def test_schema_builds_on_an_empty_database(engine, test_database_url):
    empty_database(test_database_url)
    assert inspect(engine).get_table_names() == []

    assert run_schema_command(test_database_url).returncode == 0

    assert set(inspect(engine).get_table_names()) == TABLES | {"alembic_version"}
    assert len(movement_names(engine)) == 16


def test_running_the_schema_command_twice_changes_nothing(engine, test_database_url):
    first = run_schema_command(test_database_url)
    before = all_rows(engine)
    second = run_schema_command(test_database_url)

    assert (first.returncode, second.returncode) == (0, 0)
    assert all_rows(engine) == before
    assert len(movement_names(engine)) == 16


def test_schema_command_leaves_existing_user_data_untouched(engine, test_database_url):
    with engine.begin() as connection:
        user_id = connection.execute(
            text("INSERT INTO users (email, password_hash) VALUES ('ann@example.com', 'hash') RETURNING id")
        ).scalar()
        movement_id = connection.execute(text("INSERT INTO movements (name) VALUES ('Dutch Golden Age') RETURNING id")).scalar()
        tag_id = connection.execute(text("INSERT INTO tags (name, usage_count) VALUES ('battle', 1) RETURNING id")).scalar()
        artwork_id = connection.execute(
            text(
                "INSERT INTO artworks (user_id, movement_id, title, artwork_photo_path) "
                "VALUES (:user_id, :movement_id, 'The Night Watch', 'photos/1.jpg') RETURNING id"
            ),
            {"user_id": user_id, "movement_id": movement_id},
        ).scalar()
        connection.execute(text("INSERT INTO artwork_tags (artwork_id, tag_id) VALUES (:a, :t)"), {"a": artwork_id, "t": tag_id})
        connection.execute(text("INSERT INTO detail_photos (artwork_id, path) VALUES (:a, 'details/1.jpg')"), {"a": artwork_id})
    try:
        before = all_rows(engine)
        assert run_schema_command(test_database_url).returncode == 0
        assert all_rows(engine) == before
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM artworks WHERE id = :id"), {"id": artwork_id})
            connection.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag_id})
            connection.execute(text("DELETE FROM movements WHERE id = :id"), {"id": movement_id})
            connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


def test_backend_does_not_create_tables_when_it_starts(engine, monkeypatch, test_database_url):
    empty_database(test_database_url)
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    try:
        with TestClient(app) as client:
            client.get("/api/health")
        assert inspect(engine).get_table_names() == []
    finally:
        assert run_schema_command(test_database_url).returncode == 0
