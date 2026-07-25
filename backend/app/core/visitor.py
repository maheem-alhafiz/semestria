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

COOKIE SETTINGS, and why they're simpler than they used to be:
- Originally, production (frontend on Vercel, backend on Render --
  different domains) made every API call cross-site as far as the
  browser was concerned, which required SameSite=None (+ the Secure it
  mandates) to have the cookie sent back at all.
- SameSite=None cookies are cross-site cookies, and Safari ITP / Chrome
  Incognito both block third-party cookies outright regardless of
  SameSite/Secure -- that's what caused plans to fail to save in those
  contexts (the create request succeeded, but the follow-up request
  carried no cookie, so it looked like a brand-new anonymous visitor to
  a plan that visitor didn't create).
- The actual fix was upstream of this file: the frontend now proxies
  /api/v1/* through its own Next.js server (see
  frontend/next.config.js), so the browser only ever talks to its own
  origin -- there is no cross-site relationship left, in production or
  local dev. That makes SameSite=Lax correct (and strictly more
  CSRF-resistant than None) in both environments now.
- secure still needs to differ by environment: local dev serves plain
  http://localhost, where browsers silently drop `Secure` cookies
  entirely; production is real HTTPS, where Secure should stay on.
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
        # See module docstring: the Next.js proxy makes every request
        # first-party now, in both environments, so Lax is correct (and
        # more CSRF-resistant than the None this used to need).
        samesite="lax",
        # Still environment-dependent: Secure cookies are silently
        # dropped over local dev's plain http://localhost, but should
        # stay on for real production HTTPS.
        secure=is_production,
    )
    return new_id