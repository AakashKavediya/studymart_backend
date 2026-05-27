from pydantic import BaseModel
from typing import List, Optional

class ProductCreate(BaseModel):
    title: str
    description: str
    category: str
    price: float
    condition: str
    negotiable: bool
    images: List[str]
    campus: str
    location: str


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    condition: Optional[str] = None
    negotiable: Optional[bool] = None
    images: Optional[List[str]] = None
    campus: Optional[str] = None
    location: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    price: float
    condition: str
    images: List[str]
    owner_name: str
    views: int
    status: str