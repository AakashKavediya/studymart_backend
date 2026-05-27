from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, EmailStr, field_validator, Field, HttpUrl
from datetime import datetime
from typing import List,Optional

"""
Information required:
1.  "_id": ObjectId,
2.  "name": "Aakash",
3.  "email": "aakash@college.edu",
4.  "year": "2nd",
5.  "phone": "9619688218",
6.  "password_hash": "hashed",
7.  "profile_image": "url",
8.  "bio": "Frontend developer & AI enthusiast",
9.  "skills": ["React", "Python", "ML"],
10. "rating": 4.7,
11. "total_reviews": 12,
12. "products_sold_count": 8,
13. "active_listings_count": 3,
14. "is_verified": true,
15. "is_blocked": false,
16. "created_at": datetime,
17. "updated_at": datetime,
18. "last_active": datetime

"""
#----------------------------
# USER PROFILE SCHEMA
#----------------------------


class UserProfilePublic(BaseModel):
    id: str = Field(..., alias="_id")

    name: str
    email: EmailStr

    profile_image: Optional[HttpUrl] = None
    bio: Optional[str] = None

    skills: List[str] = []

    rating: Optional[float] = 0
    total_reviews: Optional[int] = 0

    products_sold_count: Optional[int] = 0
    active_listings_count: Optional[int] = 0

    is_verified: Optional[bool] = False

    created_at: datetime
    last_active: Optional[datetime] = None

    class Config:
        populate_by_name = True

class UpdateProfile(BaseModel):
    name: Optional[str] = None
    profile_image: Optional[HttpUrl] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None