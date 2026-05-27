from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LostCreate(BaseModel):
    title: str
    description: str
    category: str
    location: str
    campus: str
    contact_info: Optional[str] = None

class LostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    campus: Optional[str] = None
    contact_info: Optional[str] = None