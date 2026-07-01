# app/schemas/profile_schema.py

from pydantic import BaseModel, EmailStr, field_validator, Field, HttpUrl
from datetime import datetime
from typing import List, Optional, Dict
import re


class UserProfilePublic(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    phone: Optional[str] = None
    campus: Optional[str] = None
    year: Optional[int] = None
    branch: Optional[str] = None
    profile_image: Optional[HttpUrl] = None
    bio: Optional[str] = None
    skills: List[str] = []
    social_links: Optional[Dict[str, str]] = None
    rating: Optional[float] = 0
    total_reviews: Optional[int] = 0
    products_sold_count: Optional[int] = 0
    active_listings_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    is_verified: Optional[bool] = False
    is_blocked: Optional[bool] = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_active: Optional[datetime] = None

    class Config:
        populate_by_name = True



class UpdateProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    campus: Optional[str] = None
    year: Optional[int] = None
    branch: Optional[str] = None
    profile_image: Optional[HttpUrl] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    social_links: Optional[Dict[str, str]] = None
    


class UpdatePassword(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v
    


class UserPublicProfile(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    profile_image: Optional[HttpUrl] = None
    bio: Optional[str] = None
    campus: Optional[str] = None
    year: Optional[int] = None
    branch: Optional[str] = None
    skills: List[str] = []
    rating: Optional[float] = 0
    total_reviews: Optional[int] = 0
    products_sold_count: Optional[int] = 0
    active_listings_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    is_verified: Optional[bool] = False
    created_at: datetime
    
    class Config:
        populate_by_name = True



# New Schema for Profile Image Upload
class ProfileImageUpload(BaseModel):
    profile_image: HttpUrl  # Cloudinary URL
    
    class Config:
        populate_by_name = True