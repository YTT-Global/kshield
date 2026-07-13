from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from app.db.session import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    commit_sha = Column(String, nullable=True)
    is_safe = Column(Boolean, default=True, nullable=False)
    issues_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
