from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./synapse.db")

# Railway provee URLs con prefijo 'postgres://' pero SQLAlchemy 2.x requiere 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    tenant_id = Column(String, index=True)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    query = Column(Text)
    narrative = Column(Text)
    render_type = Column(String)
    chart_config = Column(JSON, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CortexSession(Base):
    """Estado de hilo Cortex Agent por sesión de chat (conversation_id del cliente)."""

    __tablename__ = "cortex_sessions"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    tenant_id = Column(String, index=True, nullable=True)
    cortex_thread_id = Column(BigInteger, nullable=False)
    last_assistant_message_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


def init_db():
    Base.metadata.create_all(bind=engine)
