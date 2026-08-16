from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from app.schemas.chat_schema import ChatRoomCreate, ChatRoomResponse, ChatMessageResponse
from app.services.chat_service import (
    get_or_create_room_service,
    get_user_rooms_service,
    get_room_messages_service,
    delete_message_service
)
from app.utils.user import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])

# ----------------------------
# 1. Create or Get Chat Room
# ----------------------------
@router.post("/room", response_model=ChatRoomResponse)
async def create_or_get_room(
    room_data: ChatRoomCreate,
    current_user = Depends(get_current_user)
):
    """
    Creates a new chat room or returns an existing one between the current user and the participant.
    """
    user_id = str(current_user["_id"])
    
    room = await get_or_create_room_service(
        current_user_id=user_id,
        participant_id=room_data.participant_id,
        product_id=room_data.product_id
    )
    
    return room

# ----------------------------
# 2. Get User's Inbox
# ----------------------------
@router.get("/rooms", response_model=List[ChatRoomResponse])
async def get_user_rooms(current_user = Depends(get_current_user)):
    """
    Get all chat rooms the current user is participating in.
    """
    user_id = str(current_user["_id"])
    rooms = await get_user_rooms_service(user_id)
    return rooms

# ----------------------------
# 3. Get Room Messages (Chat History)
# ----------------------------
@router.get("/room/{room_id}/messages", response_model=List[ChatMessageResponse])
async def get_room_messages(
    room_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    Get message history for a specific room.
    """
    user_id = str(current_user["_id"])
    messages = await get_room_messages_service(
        room_id=room_id,
        current_user_id=user_id,
        page=page,
        limit=limit
    )
    return messages

# ----------------------------
# 4. Delete Message (30-Minute Rule)
# ----------------------------
@router.delete("/message/{message_id}")
async def delete_message(
    message_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete a message (only if sent within the last 30 minutes).
    """
    user_id = str(current_user["_id"])
    result = await delete_message_service(message_id, user_id)
    return result