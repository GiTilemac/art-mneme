"""Database set-up for the tests.

The tests only ever use the database in TEST_DATABASE_URL. At the start of a
run they empty it completely and build it with the schema command, so every
run starts from the same state. Each test runs inside a transaction that is
rolled back, so it leaves nothing behind.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ArgumentError, OperationalError

BACKEND = Path(__file__).parent.parent


def database_identity(url: str) -> tuple:
    """What the server reports about itself and the database, however its address is written.

    Only reads, in a read-only session, so it is safe on the development database.
    """
    engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT (SELECT system_identifier FROM pg_control_system()), d.oid "
                    "FROM pg_database d WHERE d.datname = current_database()"
                )
            ).one()
    finally:
        engine.dispose()


def empty_database(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        for table in inspect(connection).get_table_names():
            connection.execute(text(f'DROP TABLE "{table}" CASCADE'))
    engine.dispose()


def run_schema_command(url: str) -> subprocess.CompletedProcess:
    """`alembic upgrade head`, run as from the command line, against `url`."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )


def pytest_sessionstart(session):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set. Set it to the test database address, see README.md.", returncode=1)
    try:
        test_identity = database_identity(url)
    except (ArgumentError, ValueError, OperationalError) as error:
        pytest.exit(f"Cannot connect to the test database in TEST_DATABASE_URL: {getattr(error, 'orig', error)}", returncode=1)
    development_url = os.environ.get("DATABASE_URL")
    if development_url:
        try:
            development_identity = database_identity(development_url)
        except (ArgumentError, ValueError, OperationalError) as error:
            pytest.exit(
                "Cannot connect to the database in DATABASE_URL to check that it is not the test database: "
                f"{getattr(error, 'orig', error)}. Fix DATABASE_URL or unset it before running the tests.",
                returncode=1,
            )
        if development_identity == test_identity:
            pytest.exit(
                "TEST_DATABASE_URL and DATABASE_URL point to the same database. "
                "The tests delete everything in their database, so they need a separate one.",
                returncode=1,
            )
    empty_database(url)
    result = run_schema_command(url)
    if result.returncode != 0:
        pytest.exit(f"The schema command failed on the test database:\n{result.stderr}", returncode=1)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def engine(test_database_url):
    engine = create_engine(test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def conn(engine):
    """A connection whose changes are rolled back at the end of the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
