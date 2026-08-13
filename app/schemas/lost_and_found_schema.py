# app/schemas/lost_and_found_schema.py

from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

# Enums
class LostItemStatus(str, Enum):
    LOST = "lost"
    FOUND = "found"
    RESOLVED = "resolved"
    CLOSED = "closed"

class LostItemCategory(str, Enum):
    ELECTRONICS = "electronics"
    BOOKS = "books"
    CLOTHING = "clothing"
    ID_CARD = "id_card"
    BAG = "bag"
    WATER_BOTTLE = "water_bottle"
    UMBRELLA = "umbrella"
    KEYS = "keys"
    JEWELRY = "jewelry"
    OTHER = "other"

class LostItemCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

# ============================================================
# Base Lost Item Schema
# ============================================================

class LostItemBase(BaseModel):
    """Base schema with common lost item fields."""
    
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    category: LostItemCategory
    location: str = Field(..., min_length=3)
    campus: str = Field(..., min_length=2)
    contact_info: Optional[str] = None
    condition: Optional[LostItemCondition] = LostItemCondition.GOOD
    images: List[HttpUrl] = Field(default_factory=list)

    @field_validator("images")
    @classmethod
    def validate_images(cls, v: List[HttpUrl]) -> List[HttpUrl]:
        if len(v) > 4:
            raise ValueError("Maximum 4 images allowed")
        return v

# ============================================================
# Create Lost Item Schema
# ============================================================

class LostItemCreate(LostItemBase):
    """Schema for creating a new lost item."""
    pass

# ============================================================
# Update Lost Item Schema
# ============================================================

class LostItemUpdate(BaseModel):
    """Schema for updating a lost item."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[LostItemCategory] = None
    location: Optional[str] = Field(None, min_length=3)
    campus: Optional[str] = Field(None, min_length=2)
    contact_info: Optional[str] = None
    condition: Optional[LostItemCondition] = None
    status: Optional[LostItemStatus] = None
    images: Optional[List[HttpUrl]] = None
    is_resolved: Optional[bool] = None

# ============================================================
# Lost Item Response Schema
# ============================================================

class LostItemResponse(LostItemBase):
    """Schema for lost item responses."""
    
    id: str = Field(..., alias="_id")
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_avatar: Optional[HttpUrl] = None
    status: LostItemStatus = LostItemStatus.LOST
    is_resolved: bool = False
    views_count: int = 0
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        populate_by_name = True

# ============================================================
# Lost Item Search Schema
# ============================================================

class LostItemSearchParams(BaseModel):
    """Schema for lost item search/filter parameters."""
    query: Optional[str] = None
    category: Optional[LostItemCategory] = None
    campus: Optional[str] = None
    status: Optional[LostItemStatus] = None
    location: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    
    class Config:
        use_enum_values = True

# ============================================================
# Claim Item Schema
# ============================================================

class ClaimItemCreate(BaseModel):
    """Schema for claiming a found item."""
    item_id: str
    proof_description: str = Field(..., min_length=10)
    contact_info: Optional[str] = None

# ============================================================
# Comment Schema
# ============================================================

class CommentCreate(BaseModel):
    """Schema for adding a comment to a lost item."""
    content: str = Field(..., min_length=1, max_length=500)

class CommentResponse(BaseModel):
    """Schema for comment responses."""
    id: str = Field(..., alias="_id")
    item_id: str
    user_id: str
    user_name: Optional[str] = None
    user_avatar: Optional[HttpUrl] = None
    content: str
    created_at: datetime
    
    class Config:
        populate_by_name = True