import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import create_document, get_documents, db

app = FastAPI(title="SaaS Landing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Utility helpers
# -----------------------------

def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$")
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == digest


# -----------------------------
# Request/Response Models
# -----------------------------

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user: dict
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BlogCreate(BaseModel):
    title: str
    content: str
    author: str
    tags: Optional[List[str]] = None
    status: str = "published"


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str
    subject: Optional[str] = None


# -----------------------------
# Base routes
# -----------------------------

@app.get("/")
def read_root():
    return {"message": "SaaS Landing API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else ""
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# -----------------------------
# Auth Endpoints (simple demo)
# -----------------------------

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    # check existing
    existing = get_documents("user", {"email": payload.email}, limit=1)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pwd_hash = hash_password(payload.password)
    user_doc = {
        "name": payload.name,
        "email": str(payload.email),
        "password_hash": pwd_hash,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    _id = create_document("user", user_doc)
    token = secrets.token_urlsafe(24)
    # Don't return password hash
    user_doc["_id"] = _id
    user_doc.pop("password_hash", None)
    return {"user": user_doc, "token": token}


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    users = get_documents("user", {"email": payload.email}, limit=1)
    if not users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = users[0]
    if not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(24)
    user_sanitized = {k: v for k, v in user.items() if k != "password_hash"}
    return {"user": user_sanitized, "token": token}


# -----------------------------
# Blog Endpoints
# -----------------------------

@app.get("/api/blog")
def list_posts(limit: int = 10):
    posts = get_documents("blogpost", {"status": "published"}, limit=limit)
    # ensure stable shape
    for p in posts:
        p.pop("password_hash", None)
    return {"items": posts}


@app.get("/api/blog/{slug}")
def get_post(slug: str):
    docs = get_documents("blogpost", {"slug": slug}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Post not found")
    return docs[0]


@app.post("/api/blog")
def create_post(payload: BlogCreate):
    slug = payload.title.lower().strip().replace(" ", "-")
    doc = {
        "title": payload.title,
        "slug": slug,
        "excerpt": (payload.content[:180] + "...") if len(payload.content) > 180 else payload.content,
        "content": payload.content,
        "author": payload.author,
        "tags": payload.tags or [],
        "published_at": datetime.utcnow(),
        "status": payload.status
    }
    _id = create_document("blogpost", doc)
    doc["_id"] = _id
    return doc


# -----------------------------
# Contact Endpoint
# -----------------------------

@app.post("/api/contact")
def submit_contact(payload: ContactRequest):
    doc = {
        "name": payload.name,
        "email": str(payload.email),
        "message": payload.message,
        "subject": payload.subject,
        "handled": False,
        "received_at": datetime.utcnow()
    }
    _id = create_document("contactmessage", doc)
    return {"status": "ok", "id": _id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
