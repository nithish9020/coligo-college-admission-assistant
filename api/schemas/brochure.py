from datetime import datetime

from pydantic import BaseModel


class BrochureUpdate(BaseModel):
    title: str | None = None
    category: str | None = None


class BrochureResponse(BaseModel):
    id: int
    college_id: int
    title: str
    category: str | None = None
    file_size_bytes: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}
