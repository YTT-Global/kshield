from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.db.session import Base

class Configuration(Base):
    __tablename__ = "configurations"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
