from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

# ----------------------------
# Room Schemas
# ----------------------------
class ChatRoomCreate(BaseModel):
    participant_id: str  # The ID of the user you want to chat with
    product_id: Optional[str] = None  # Optional context (product or lost item)

class ChatRoomResponse(BaseModel):
    id: str = Field(..., alias="_id")
    participants: List[str]
    product_id: Optional[str] = None  # ✅ Changed to Optional[str]
    last_message_text: Optional[str]
    last_message_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# ----------------------------
# Message Schemas
# ----------------------------
class ChatMessageCreate(BaseModel):
    room_id: str
    content: str

class ChatMessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    room_id: str
    sender_id: str
    content: str
    created_at: datetime
    is_deleted: bool = False
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# ----------------------------
# WebSocket Payload Schemas
# ----------------------------
class WSMessagePayload(BaseModel):
    room_id: str
    content: str

class WSDeletePayload(BaseModel):
    message_id: str