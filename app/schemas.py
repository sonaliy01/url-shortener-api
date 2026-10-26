from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

class LinkCreate(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    expires_at: datetime | None = None

class LinkCreated(BaseModel):
    code: str
    short_url: str
    original_url: str
    expires_at: datetime | None

class LinkStats(BaseModel):
    code: str
    original_url: str
    total_clicks: int
    last_clicked_at: datetime | None
