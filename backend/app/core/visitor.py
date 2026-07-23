"""
Anonymous per-visitor identity via an HttpOnly cookie.

No login, no accounts -- this gives private, per-browser data isolation
(each visitor sees only their own Plans/AcademicRecord; a stranger with
the site's URL sees an empty dashboard) without the friction of a real
auth system, appropriate for the app's current single-user-per-browser
stage. Swapping this for real accounts later is meant to be a drop-in
replacement at every call site: every Plan/AcademicRecord row's
`owner_id` column would just start being populated from a logged-in
user's id instead of a cookie-derived one -- nothing about the schema
shape needs to change.

get_current_owner_id is a FastAPI dependency: call it in any route that
needs to know/set who's making the request. It reads the `visitor_id`
cookie if present; if absent (first-ever visit), it generates a new
random id and sets it on the response so every subsequent request from
that browser carries it automatically.
"""

from __future__ import annotations

import secrets

from fastapi import Request, Response

_COOKIE_NAME = "visitor_id"
_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 2  # ~2 years


def get_current_owner_id(request: Request, response: Response) -> str:
    existing = request.cookies.get(_COOKIE_NAME)
    if existing:
        return existing

    new_id = secrets.token_urlsafe(24)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=new_id,
        max_age=_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        # NOTE: flip to secure=True once this is served over HTTPS in
        # production. Left False here because browsers silently drop
        # `Secure` cookies on plain http, which would break this
        # entirely against local http://localhost during development --
        # don't forget to change this before a real deployment.
        secure=False,
    )
    return new_id
