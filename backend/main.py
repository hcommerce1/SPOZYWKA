import json, os, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models import init_db, new_session, get_sessions, get_session, add_photo, get_photos, save_meta, delete_session
from s3_client import upload_photo
from label_generator import generate_label
from mcp_router import router as mcp_router

app = FastAPI(title="Spożywka App")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(mcp_router, prefix="/mcp")

FRONTEND = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")


@app.on_event("startup")
def startup():
    init_db()


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
        raise HTTPException(400, "No meta yet — Claude must analyze first via /mcp/session/{id}/meta")
    pdf = generate_label(meta)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="label_{sid[:8]}.pdf"'})
