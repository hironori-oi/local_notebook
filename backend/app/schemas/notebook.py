from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class NotebookBase(BaseModel):
    title: str
    description: Optional[str] = None


class NotebookCreate(NotebookBase):
    pass


class NotebookOut(NotebookBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
