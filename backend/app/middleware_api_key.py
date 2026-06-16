# backend/app/middleware_api_key.py
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import DeveloperApiKey
from datetime import datetime

async def verify_api_key(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if api_key and request.url.path.startswith("/api/v1/"):  # внешнее API
        db = SessionLocal()
        try:
            key_record = db.query(DeveloperApiKey).filter(DeveloperApiKey.key == api_key, DeveloperApiKey.is_active == True).first()
            if not key_record:
                raise HTTPException(401, "Invalid API key")
            if key_record.expires_at and key_record.expires_at < datetime.utcnow():
                raise HTTPException(401, "API key expired")
            # rate limiting
            now = datetime.utcnow()
            if (now - key_record.last_reset).seconds > 60:
                key_record.requests_count = 0
                key_record.last_reset = now
            if key_record.requests_count >= key_record.rate_limit:
                raise HTTPException(429, "Rate limit exceeded")
            key_record.requests_count += 1
            db.commit()
            request.state.api_key_user_id = key_record.user_id
        finally:
            db.close()
    return await call_next(request)