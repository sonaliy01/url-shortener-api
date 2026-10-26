import os
import secrets
import string
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Link
from .schemas import LinkCreate, LinkCreated, LinkStats

Base.metadata.create_all(bind=engine)
app = FastAPI(title="URL Shortener API", version="1.0.0")
ALPHABET = string.ascii_letters + string.digits

def utc_now():
    return datetime.now(timezone.utc)

def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))

def is_valid_public_url(url: str) -> bool:
    """Reject non-HTTP(S) URLs and URLs without a hostname."""
    try:
        parsed = urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/links", response_model=LinkCreated, status_code=status.HTTP_201_CREATED)
def create_link(payload: LinkCreate, request: Request, db: Session = Depends(get_db)):
    original_url = str(payload.url)
    if not is_valid_public_url(original_url):
        raise HTTPException(status_code=422, detail="URL must be a valid http or https URL.")

    now = utc_now()
    expires_at = payload.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            raise HTTPException(status_code=422, detail="expires_at must include a timezone, for example +00:00 or Z.")
        if expires_at <= now:
            raise HTTPException(status_code=422, detail="expires_at must be in the future.")

    code = payload.custom_alias or generate_code()
    if db.query(Link).filter(Link.code == code).first():
        if payload.custom_alias:
            raise HTTPException(status_code=409, detail=f"The alias '{code}' is already in use. Choose another alias.")
        # Extremely unlikely random-code collision: try a few alternatives.
        for _ in range(5):
            code = generate_code()
            if not db.query(Link).filter(Link.code == code).first():
                break
        else:
            raise HTTPException(status_code=503, detail="Could not generate a unique short code. Please retry.")

    link = Link(code=code, original_url=original_url, created_at=now, expires_at=expires_at, clicks=0)
    db.add(link)
    try:
        db.commit()
        db.refresh(link)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"The alias '{code}' is already in use. Choose another alias.")

    short_url = str(request.base_url).rstrip("/") + "/" + link.code
    return LinkCreated(code=link.code, short_url=short_url, original_url=link.original_url, expires_at=link.expires_at)

@app.get("/links/{code}/stats", response_model=LinkStats)
def link_stats(code: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.code == code).first()
    if not link:
        raise HTTPException(status_code=404, detail=f"No short link exists for code '{code}'.")
    return LinkStats(code=link.code, original_url=link.original_url,
                     total_clicks=link.clicks, last_clicked_at=link.last_clicked_at)

@app.get("/{code}", include_in_schema=False)
def redirect_link(code: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.code == code).first()
    if not link:
        raise HTTPException(status_code=404, detail=f"No short link exists for code '{code}'.")
    now = utc_now()
    if link.expires_at is not None:
        expiry = link.expires_at
        # SQLite may return naive datetimes even when timezone=True.
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= now:
            raise HTTPException(status_code=410, detail=f"Short link '{code}' has expired.")
    link.clicks += 1
    link.last_clicked_at = now
    db.commit()
    return RedirectResponse(url=link.original_url, status_code=302)
