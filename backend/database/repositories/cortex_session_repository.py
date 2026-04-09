"""Persistencia de sesiones Cortex Agent (thread_id Snowflake por conversation_id)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from database.models import CortexSession


class CortexSessionRepository:
    def __init__(self, db: Session):
        self._db = db

    def get(self, session_id: str) -> Optional[CortexSession]:
        return (
            self._db.query(CortexSession).filter(CortexSession.id == session_id).first()
        )

    def create(
        self,
        *,
        session_id: str,
        user_id: str,
        tenant_id: str,
        cortex_thread_id: int,
    ) -> CortexSession:
        row = CortexSession(
            id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            cortex_thread_id=cortex_thread_id,
            last_assistant_message_id=None,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def update_last_assistant(self, session_id: str, message_id: int) -> None:
        row = self.get(session_id)
        if row:
            row.last_assistant_message_id = message_id
