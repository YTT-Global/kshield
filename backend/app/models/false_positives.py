from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.db.session import Base

class FalsePositive(Base):
    __tablename__ = "false_positives"

    id = Column(String, primary_key=True, index=True)
    file_signature = Column(String, nullable=False, index=True)  # MD5/SHA256 file calculation
    rule_id = Column(String, nullable=False, index=True)
    justification = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
