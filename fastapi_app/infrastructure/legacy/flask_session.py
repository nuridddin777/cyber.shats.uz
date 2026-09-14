"""
Reads the existing Flask session cookie so new FastAPI routes can identify
the logged-in user without touching login/session/CSRF at all — those stay
entirely Flask-owned. Replicates Flask's own SecureCookieSessionInterface
(salt, serializer, HMAC-SHA1 signing) exactly, using Flask's own
TaggedJSONSerializer, so a cookie minted by the Flask side decodes here
byte-for-byte the same way Flask itself would decode it.
"""
import hashlib

from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask.sessions import TaggedJSONSerializer

from config import Config

_SIGNER_KWARGS = dict(key_derivation="hmac", digest_method=hashlib.sha1)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        Config.SECRET_KEY,
        salt="cookie-session",
        serializer=TaggedJSONSerializer(),
        signer_kwargs=_SIGNER_KWARGS,
    )


def read_session_cookie(cookie_value: str) -> dict:
    """Returns the decoded session dict, or {} if missing/invalid/expired."""
    if not cookie_value:
        return {}
    try:
        return _serializer().loads(cookie_value)
    except BadSignature:
        return {}
    except Exception:
        return {}
