"""Auth feature models — stub. The ``feat/auth`` subagent replaces this file."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # plaintext (future: hash)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
