from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer
from app.db.session import Base

class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    file_count = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
