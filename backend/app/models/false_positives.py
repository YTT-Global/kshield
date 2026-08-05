from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.db.session import Base

class FalsePositive(Base):
    __tablename__ = "false_positives"

    id = Column(String, primary_key=True, index=True)
    file_signature = Column(String, nullable=False, index=True)  # MD5/SHA256 file calculation
    rule_id = Column(String, nullable=False, index=True)
    justification = Column(Text, nullable=True)
    # Normalized template of the dismissed finding's description (quoted
    # identifiers and file paths stripped) — see quiet_office.py. Deliberately
    # not an embedding: findings are template-generated text, not free-form
    # prose, so matching the structural shell is both simpler and more
    # reliable than cosine similarity on a hash-seeded vector would be.
    signature = Column(Text, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
