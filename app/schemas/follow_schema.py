from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from bson import ObjectId

class FollowBase(BaseModel):
    follower_id: str
    following_id: str

class FollowCreate(FollowBase):
    pass

class FollowResponse(BaseModel):
    id: str
    follower_id: str
    following_id: str
    created_at: datetime
    
    class Config:
        populate_by_name = True