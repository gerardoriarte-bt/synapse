from sqlalchemy.orm import Session
from database.models import SessionLocal


def get_db():
    """FastAPI dependency to get a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
