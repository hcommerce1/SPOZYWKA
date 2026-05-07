"""MCP endpoints — Claude łączy się tutaj żeby czytać sesje i zapisywać wyniki."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import get_sessions, get_session, get_photos, save_meta

router = APIRouter(tags=["mcp"])


class MetaPayload(BaseModel):
    product_name: str = ""
    ingredients: str = ""
    bbf: str = ""
    production_date: str = ""
    lot_number: str = ""
    serving_ml: int = 15
    nutrition: dict = {}
    origin: str = ""
    importer: str = ""
    storage: str = ""
    net_weight: str = ""
    certs: str = ""
    ean: str = ""
    notes: str = ""


class EanPayload(BaseModel):
    ean: str


@router.get("/sessions")
def mcp_sessions():
    """Lista sesji z URL zdjęć — Claude wybiera którą obrobić."""
    sessions = get_sessions()
    result = []
    for s in sessions:
        photos = get_photos(s["id"])
        result.append({
            "id": s["id"],
            "created_at": s["created_at"],
            "status": s["status"],
            "photo_count": s["photo_count"],
            "photo_urls": [p["url"] for p in photos],
            "has_meta": bool(s.get("meta")),
        })
    return result


@router.get("/session/{sid}/photos")
def mcp_photos(sid: str):
    """Lista publicznych URL zdjęć dla sesji."""
    if not get_session(sid):
        raise HTTPException(404, "Session not found")
    return [p["url"] for p in get_photos(sid)]


@router.post("/session/{sid}/meta")
def mcp_save_meta(sid: str, payload: MetaPayload):
    """Claude zapisuje wyniki analizy — dane do etykiety i BaseLinker."""
    if not get_session(sid):
        raise HTTPException(404, "Session not found")
    save_meta(sid, payload.model_dump())
    return {"ok": True, "session_id": sid}


@router.post("/session/{sid}/assign-ean")
def mcp_assign_ean(sid: str, payload: EanPayload):
    """Przypisuje EAN do sesji (po matchingu w BL przez Claude)."""
    s = get_session(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    meta = json.loads(s["meta"]) if s.get("meta") else {}
    meta["ean"] = payload.ean
    save_meta(sid, meta)
    return {"ok": True, "ean": payload.ean}


@router.get("/session/{sid}/full")
def mcp_full(sid: str):
    """Pełne dane sesji + wyniki AI — dla skilla przed wysyłką do BL."""
    s = get_session(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    photos = get_photos(sid)
    meta = json.loads(s["meta"]) if s.get("meta") else {}
    return {
        "id": s["id"],
        "created_at": s["created_at"],
        "status": s["status"],
        "photo_urls": [p["url"] for p in photos],
        "meta": meta,
    }
