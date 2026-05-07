import json, os, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from models import init_db, new_session, get_sessions, get_session, add_photo, get_photos, save_meta, delete_session
from s3_client import upload_photo
from label_generator import generate_label
from mcp_router import router as mcp_router
from auth import is_authenticated, set_auth_cookie, clear_auth_cookie, APP_PASSWORD

app = FastAPI(title="Spożywka App", docs_url=None, redoc_url=None)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(mcp_router, prefix="/mcp")

FRONTEND = Path(__file__).parent.parent / "frontend"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/login", "/logout") or path.startswith("/static"):
            return await call_next(request)
        if not is_authenticated(request):
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)


app.add_middleware(AuthMiddleware)

if (FRONTEND / "static").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")


@app.on_event("startup")
def startup():
    init_db()
    if not APP_PASSWORD:
        print("\n⚠️  APP_PASSWORD nie ustawione w .env — ustaw hasło przed deployem!\n")


# ── Auth ─────────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>Spożywka — Logowanie</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f0f0f;
      color: #f0f0f0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .card {{
      background: #1a1a1a;
      border: 1px solid #333;
      border-radius: 16px;
      padding: 40px 32px;
      width: 100%;
      max-width: 360px;
      margin: 16px;
    }}
    h1 {{
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #c9a84c;
      margin-bottom: 8px;
    }}
    p {{ font-size: 13px; color: #888; margin-bottom: 28px; }}
    input {{
      display: block;
      width: 100%;
      background: #252525;
      border: 1px solid #444;
      border-radius: 10px;
      color: #f0f0f0;
      font-size: 16px;
      padding: 14px 16px;
      margin-bottom: 14px;
      outline: none;
    }}
    input:focus {{ border-color: #c9a84c; }}
    button {{
      display: block;
      width: 100%;
      background: #c9a84c;
      color: #000;
      border: none;
      border-radius: 10px;
      font-size: 16px;
      font-weight: 700;
      padding: 16px;
      cursor: pointer;
      margin-top: 4px;
    }}
    button:active {{ background: #8a7035; }}
    .error {{
      background: #2a0a0a;
      border: 1px solid #c0392b55;
      color: #e74c3c;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      margin-bottom: 16px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Spożywka</h1>
    <p>Zaloguj się żeby kontynuować</p>
    {error}
    <form method="post" action="/login">
      <input type="password" name="password" placeholder="Hasło" autofocus autocomplete="current-password">
      <button type="submit">Zaloguj</button>
    </form>
  </div>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_HTML.format(error="")


@app.post("/login")
def login(password: str = Form(...)):
    if not APP_PASSWORD:
        raise HTTPException(500, "APP_PASSWORD not configured")
    if password != APP_PASSWORD:
        html = LOGIN_HTML.format(error='<div class="error">Nieprawidłowe hasło</div>')
        return HTMLResponse(html, status_code=401)
    resp = RedirectResponse(url="/", status_code=303)
    return set_auth_cookie(resp)


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    return clear_auth_cookie(resp)


# ── UI ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")


# ── Sessions ─────────────────────────────────────────────────────────────────

@app.post("/sessions")
def create_session():
    return new_session()


@app.get("/sessions")
def list_sessions():
    return get_sessions()


@app.delete("/sessions/{sid}")
def remove_session(sid: str):
    s = get_session(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    delete_session(sid)
    return {"ok": True}


# ── Photos ────────────────────────────────────────────────────────────────────

@app.post("/sessions/{sid}/photos")
async def upload_photos(sid: str, files: list[UploadFile] = File(...)):
    if not get_session(sid):
        raise HTTPException(404, "Session not found")
    uploaded = []
    for f in files:
        data = await f.read()
        ext = Path(f.filename or "photo.jpg").suffix or ".jpg"
        fname = f"{uuid.uuid4().hex}{ext}"
        url = upload_photo(sid, fname, data, f.content_type or "image/jpeg")
        add_photo(sid, url, fname)
        uploaded.append({"filename": fname, "url": url})
    return {"uploaded": uploaded}


@app.get("/sessions/{sid}/photos")
def list_photos(sid: str):
    if not get_session(sid):
        raise HTTPException(404, "Session not found")
    return get_photos(sid)


# ── Label PDF ─────────────────────────────────────────────────────────────────

@app.get("/sessions/{sid}/label.pdf")
def get_label(sid: str):
    s = get_session(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    meta = json.loads(s["meta"]) if s.get("meta") else {}
    if not meta:
        raise HTTPException(400, "No meta yet — Claude must save via /mcp/session/{id}/meta first")
    pdf = generate_label(meta)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="label_{sid[:8]}.pdf"'})
