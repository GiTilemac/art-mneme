"""The database work of a request is committed before its answer is sent.

Otherwise a fast next request (e.g. `GET /api/auth/me` right after login) can arrive before
the new session row is committed, and the user is wrongly told to sign in again.
"""

from fastapi.routing import APIRoute

from main import app, get_connection


def dependencies(dependant):
    for dependency in dependant.dependencies:
        yield dependency
        yield from dependencies(dependency)


def test_every_database_connection_closes_before_the_answer_is_sent():
    scopes = {
        (route.path, dependency.scope)
        for route in app.routes
        if isinstance(route, APIRoute)
        for dependency in dependencies(route.dependant)
        if dependency.call is get_connection
    }

    assert scopes and {scope for _, scope in scopes} == {"function"}
