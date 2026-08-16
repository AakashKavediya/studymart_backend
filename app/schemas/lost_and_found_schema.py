# app/schemas/lost_and_found_schema.py

from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

# ============================================================
# Enums
# ============================================================

class LostItemType(str, Enum):
    LOST = "lost"
    COMPLAINT = "complaint"

class LostItemStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CLOSED = "closed"

# ⚠️ DEPRECATED: Kept only to prevent Router crashes. Not used by frontend.
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

# ⚠️ DEPRECATED: Kept only to prevent Router crashes. Not used by frontend.
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
    
    # Required
    title: str = Field(..., min_length=3, max_length=200)
    location: str = Field(..., min_length=3)
    type: LostItemType  # 'lost' or 'complaint'
    
    # Optional
    description: Optional[str] = Field(None, min_length=10)
    image: Optional[HttpUrl] = None  # Single optional image
    
    # ⚠️ DEPRECATED FIELDS (Kept to prevent Router crashes)
    category: Optional[LostItemCategory] = None
    condition: Optional[LostItemCondition] = None
    campus: Optional[str] = None
    contact_info: Optional[str] = None

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        return v

# ============================================================
# Create Lost Item Schema (Used by frontend Modal)
# ============================================================

class LostItemCreate(BaseModel):
    """Schema for creating a new lost item."""
    title: str = Field(..., min_length=3, max_length=200)
    location: str = Field(..., min_length=3)
    type: LostItemType
    description: Optional[str] = Field(None, min_length=10)
    image: Optional[HttpUrl] = None

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        return v

# ============================================================
# Update Lost Item Schema
# ============================================================

class LostItemUpdate(BaseModel):
    """Schema for updating an existing lost item."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    location: Optional[str] = Field(None, min_length=3)
    type: Optional[LostItemType] = None
    description: Optional[str] = Field(None, min_length=10)
    image: Optional[HttpUrl] = None
    status: Optional[LostItemStatus] = None
    is_resolved: Optional[bool] = None

# ============================================================
# Lost Item Response Schema (Used by frontend Card)
# ============================================================

class LostItemResponse(BaseModel):
    """Schema for lost item responses."""
    
    id: str = Field(..., alias="_id")
    user_id: str
    user_name: Optional[str] = None  # Populated via lookup
    user_avatar: Optional[HttpUrl] = None
    
    title: str
    location: str
    type: LostItemType  # Matches frontend 'post.type'
    description: Optional[str] = None
    image: Optional[HttpUrl] = None  # Frontend checks if null
    
    status: LostItemStatus = LostItemStatus.ACTIVE
    is_resolved: bool = False
    comments_count: int = 0
    views_count: int = 0
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        use_enum_values = True
        populate_by_name = True

# ============================================================
# Lost Item Search Schema
# ============================================================

class LostItemSearchParams(BaseModel):
    """Schema for lost item search/filter parameters."""
    query: Optional[str] = None
    type: Optional[LostItemType] = None  # Filter by 'lost' or 'complaint'
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    
    class Config:
        use_enum_values = True

# ============================================================
# Claim Item Schema (Required by your Router)
# ============================================================

class ClaimItemCreate(BaseModel):
    """Schema for claiming a found item."""
    item_id: str
    proof_description: str = Field(..., min_length=10)
    contact_info: Optional[str] = None

# ============================================================
# Comment Schemas (Required by your frontend)
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