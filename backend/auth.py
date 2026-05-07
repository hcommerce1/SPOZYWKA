"""Prosta autoryzacja cookie — login/password z env, token HMAC-SHA256."""
import os, hmac, hashlib, time, secrets
from fastapi import Request, Response
from fastapi.responses import RedirectResponse

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY   = os.environ.get("APP_SECRET", secrets.token_hex(32))
COOKIE_NAME  = "spz_auth"
COOKIE_TTL   = 60 * 60 * 24 * 30  # 30 dni

PUBLIC_PATHS = {"/login", "/static"}


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    ts = str(int(time.time()))
    sig = _sign(ts)
    return f"{ts}.{sig}"


def verify_token(token: str) -> bool:
    try:
        ts, sig = token.split(".", 1)
        if not hmac.compare_digest(_sign(ts), sig):
            return False
        if int(time.time()) - int(ts) > COOKIE_TTL:
            return False
        return True
    except Exception:
        return False


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME, "")
    return verify_token(token)


def require_auth(request: Request):
    path = request.url.path
    if path == "/login" or path.startswith("/static"):
        return None
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def set_auth_cookie(response: Response) -> Response:
    response.set_cookie(
        COOKIE_NAME,
        make_token(),
        max_age=COOKIE_TTL,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return response


def clear_auth_cookie(response: Response) -> Response:
    response.delete_cookie(COOKIE_NAME)
    return response
