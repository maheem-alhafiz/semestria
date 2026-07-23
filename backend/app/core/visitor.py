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

COOKIE SETTINGS ARE ENVIRONMENT-DEPENDENT, on purpose:
- In production, frontend (Vercel) and backend (Render) live on
  DIFFERENT domains -- that makes every API call cross-site as far as
  the browser is concerned. A cross-site cookie is only ever sent if
  it's marked `SameSite=None`, and browsers refuse `SameSite=None`
  unless the cookie is also `Secure` (HTTPS-only). So production needs
  secure=True, samesite="none".
- In local dev, frontend and backend are both on http://localhost --
  `Secure` cookies are silently dropped by browsers over plain HTTP, so
  a hardcoded secure=True would break local development entirely. Local
  dev needs secure=False, samesite="lax".
Hardcoding either combination breaks the other environment; this reads
settings.app_env to pick the right pair automatically.
"""

from __future__ import annotations

import secrets

from fastapi import Request, Response

from app.core.config import get_settings

_COOKIE_NAME = "visitor_id"
_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 2  # ~2 years


def get_current_owner_id(request: Request, response: Response) -> str:
    existing = request.cookies.get(_COOKIE_NAME)
    if existing:
        return existing

    new_id = secrets.token_urlsafe(24)
    settings = get_settings()
    is_production = settings.app_env == "production"

    response.set_cookie(
        key=_COOKIE_NAME,
        value=new_id,
        max_age=_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        # See module docstring: production is cross-site (Vercel <->
        # Render), which requires SameSite=None + Secure together, but
        # Secure cookies are dropped entirely over local dev's plain
        # http://localhost, so this must differ by environment rather
        # than being one fixed value.
        samesite="none" if is_production else "lax",
        secure=is_production,
    )
    return new_id
