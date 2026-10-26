from sqlalchemy import Column, DateTime, Integer, String
from .database import Base

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True, nullable=False)
    original_url = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    clicks = Column(Integer, nullable=False, default=0)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
