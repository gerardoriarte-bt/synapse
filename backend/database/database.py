from sqlalchemy.orm import Session
from database.models import Conversation, SessionLocal, init_db

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
