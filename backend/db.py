"""The backend's connection to the database named in DATABASE_URL."""

import os
from functools import cache

from sqlalchemy import Engine, create_engine


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set. Set it to the database address, see README.md.")
    return url


@cache
def get_engine() -> Engine:
    """Created on first use, so the backend starts without a database."""
    return create_engine(database_url())
