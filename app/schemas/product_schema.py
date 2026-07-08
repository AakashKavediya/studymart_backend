# app/schemas/product_schema.py

from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# Enums for better type safety
class ProductType(str, Enum):
    NOTES = "notes"
    BOOK = "book"
    COURSE = "course"
    ASSIGNMENT = "assignment"
    PPT = "ppt"
    QUESTION_BANK = "question_bank"
    HANDWRITTEN_NOTES = "handwritten_notes"
    LAB_REPORT = "lab_report"
    CHEAT_SHEET = "cheat_sheet"
    OTHER = "other"

class ProductCategory(str, Enum):
    ENGINEERING = "engineering"
    MEDICAL = "medical"
    COMMERCE = "commerce"
    ARTS = "arts"
    SCIENCE = "science"
    LAW = "law"
    MANAGEMENT = "management"
    OTHER = "other"

class ProductCondition(str, Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    DIGITAL = "digital"

class ProductStatus(str, Enum):
    ACTIVE = "active"
    SOLD = "sold"
    INACTIVE = "inactive"
    PENDING = "pending"
    REJECTED = "rejected"

# ============================================================
# Base Product Schema
# ============================================================

class ProductBase(BaseModel):
    """Base schema with common product fields."""
    
    # Basic Info
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    short_description: Optional[str] = Field(None, max_length=100)
    
    # Category
    category: ProductCategory
    sub_category: Optional[str] = None
    
    # Pricing
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    currency: str = "INR"
    
    # Images
    thumbnail: Optional[HttpUrl] = None
    images: List[HttpUrl] = Field(default_factory=list)
    
    # Product Type
    product_type: ProductType
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    is_featured: bool = False
    
    # Location
    campus: Optional[str] = None
    location: Optional[str] = None
    
    # Negotiable
    is_negotiable: bool = False
    
    # Delivery
    delivery_available: bool = False
    delivery_fee: Optional[float] = None
    
    @field_validator("images")
    @classmethod
    def validate_images(cls, v: List[HttpUrl]) -> List[HttpUrl]:
        if len(v) > 4:
            raise ValueError("Maximum 4 images allowed")
        return v

    @field_validator("discount_percentage")
    @classmethod
    def validate_discount(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and (v > 100 or v < 0):
            raise ValueError("Discount must be between 0 and 100")
        return v


# ============================================================
# Product Create Schema
# ============================================================

class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    
    @field_validator("images")
    @classmethod
    def validate_images_required(cls, v: List[HttpUrl]) -> List[HttpUrl]:
        if not v:
            raise ValueError("At least one image is required")
        return v


# ============================================================
# Product Update Schema
# ============================================================

class ProductUpdate(BaseModel):
    """Schema for updating an existing product."""
    
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    short_description: Optional[str] = Field(None, max_length=100)
    category: Optional[ProductCategory] = None
    sub_category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    currency: Optional[str] = None
    thumbnail: Optional[HttpUrl] = None
    images: Optional[List[HttpUrl]] = Field(None)
    product_type: Optional[ProductType] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_featured: Optional[bool] = None
    campus: Optional[str] = None
    location: Optional[str] = None
    is_negotiable: Optional[bool] = None
    delivery_available: Optional[bool] = None
    delivery_fee: Optional[float] = None


# ============================================================
# Product Response Schema
# ============================================================

class ProductResponse(ProductBase):
    """Schema for product responses."""
    
    id: str = Field(..., alias="_id")
    seller_id: str
    seller_name: Optional[str] = None
    seller_avatar: Optional[HttpUrl] = None
    seller_campus: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    views_count: int = 0
    likes_count: int = 0
    saved_count: int = 0
    report_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        use_enum_values = True
        populate_by_name = True


# ============================================================
# Product Search Schema
# ============================================================

class ProductSearchParams(BaseModel):
    """Schema for product search/filter parameters."""
    
    query: Optional[str] = None
    category: Optional[ProductCategory] = None
    product_type: Optional[ProductType] = None
    min_price: Optional[float] = Field(None, gt=0)
    max_price: Optional[float] = Field(None, gt=0)
    campus: Optional[str] = None
    condition: Optional[ProductCondition] = None
    is_negotiable: Optional[bool] = None
    tags: Optional[List[str]] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


# ============================================================
# Cart Schema
# ============================================================

class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)
    added_at: datetime = Field(default_factory=datetime.utcnow)

class CartCreate(BaseModel):
    product_id: str
    quantity: int = 1

class CartUpdate(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)

class CartResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    items: List[CartItem]
    total_items: int
    total_price: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


# ============================================================
# Product Stats Schema
# ============================================================

class ProductStatsResponse(BaseModel):
    total_products: int
    active_products: int
    sold_products: int
    pending_products: int
    total_views: int
    total_likes: int
    total_saves: int
    total_revenue: float


# ============================================================
# Product Report Schema
# ============================================================

class ReportReason(str, Enum):
    SPAM = "spam"
    SCAM = "scam"
    FAKE = "fake"
    COPYRIGHT = "copyright"
    WRONG_CATEGORY = "wrong_category"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"

class ProductReportCreate(BaseModel):
    product_id: str
    reason: ReportReason
    description: Optional[str] = None

class ProductReportResponse(BaseModel):
    id: str = Field(..., alias="_id")
    product_id: str
    reporter_id: str
    reason: ReportReason
    description: Optional[str]
    created_at: datetime
    
    class Config:
        populate_by_name = True