from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from bson import ObjectId
from app.mongodb.connect import connectdb

# Connect to both databases
db = connectdb()
rooms_collection = db["chat_rooms"]
messages_collection = db["chat_messages"]
messages_archive_collection = db["chat_messages_archive"]  # Immutable backup

# ----------------------------
# 1. Create or Get Chat Room
# ----------------------------
async def get_or_create_room_service(
    current_user_id: str,
    participant_id: str,
    product_id: Optional[str] = None
) -> dict:
    """
    Check if a room exists between two users. If not, create one.
    """
    # Validate participant exists (optional, but good practice)
    # You can add a check here to see if participant_id is a valid user
    
    # Sort IDs to ensure consistent lookup
    user_ids = sorted([current_user_id, participant_id])
    
    # Check if room already exists
    existing_room = await run_in_threadpool(
        rooms_collection.find_one,
        {"participants": user_ids}
    )
    
    if existing_room:
        # Convert ObjectIds to strings for response
        existing_room["_id"] = str(existing_room["_id"])
        if existing_room.get("product_id"):
            existing_room["product_id"] = str(existing_room["product_id"])
        return existing_room
    
    # Create new room
    new_room = {
        "participants": user_ids,
        "product_id": ObjectId(product_id) if product_id and ObjectId.is_valid(product_id) else None,
        "last_message_text": None,
        "last_message_at": None,
        "created_at": datetime.utcnow()
    }
    
    result = await run_in_threadpool(rooms_collection.insert_one, new_room)
    new_room["_id"] = str(result.inserted_id)
    
    # ✅ FIX: Convert product_id to string if it exists
    if new_room.get("product_id"):
        new_room["product_id"] = str(new_room["product_id"])
    
    return new_room


# ----------------------------
# 2. Get User's Inbox (List of rooms)
# ----------------------------
async def get_user_rooms_service(user_id: str) -> List[dict]:
    """
    Fetch all rooms the user is a participant in, sorted by latest message.
    """
    cursor = await run_in_threadpool(
        rooms_collection.find,
        {"participants": user_id}
    )
    rooms = await run_in_threadpool(list, cursor.sort("last_message_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    for room in rooms:
        room["_id"] = str(room["_id"])
        if room.get("product_id"):
            room["product_id"] = str(room["product_id"])
    
    return rooms


# ----------------------------
# 3. Get Chat History (Permanent storage)
# ----------------------------
async def get_room_messages_service(
    room_id: str,
    current_user_id: str,
    page: int = 1,
    limit: int = 50
) -> List[dict]:
    """
    Fetch messages from the primary collection (DB 1).
    """
    if not ObjectId.is_valid(room_id):
        raise HTTPException(status_code=400, detail="Invalid room ID format")
    
    # Verify user is in the room
    room = await run_in_threadpool(
        rooms_collection.find_one,
        {"_id": ObjectId(room_id), "participants": current_user_id}
    )
    if not room:
        raise HTTPException(status_code=403, detail="You are not a participant in this chat")
    
    # Fetch messages
    skip = (page - 1) * limit
    cursor = await run_in_threadpool(
        messages_collection.find,
        {"room_id": ObjectId(room_id), "is_deleted": False}
    )
    messages = await run_in_threadpool(
        list, 
        cursor.sort("created_at", -1).skip(skip).limit(limit)
    )
    
    # Convert to JSON-friendly format
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        msg["room_id"] = str(msg["room_id"])
        msg["sender_id"] = str(msg["sender_id"])
        # ✅ FIX: Convert datetime to ISO string for JSON serialization
        if "created_at" in msg and isinstance(msg["created_at"], datetime):
            msg["created_at"] = msg["created_at"].isoformat()
    
    return messages[::-1]  # Return in chronological order


# ----------------------------
# 4. Save Message (Guaranteed Dual Database Write)
# ----------------------------
async def save_message_service(
    room_id: str,
    sender_id: str,
    content: str
) -> dict:
    """
    Guarantees writes to BOTH Primary and Archive DBs before returning.
    """
    if not ObjectId.is_valid(room_id):
        raise HTTPException(status_code=400, detail="Invalid room ID format")
    
    now = datetime.utcnow()
    message_doc = {
        "room_id": ObjectId(room_id),
        "sender_id": ObjectId(sender_id),
        "content": content,
        "created_at": now,
        "is_deleted": False
    }
    
    # 1. Write to Primary DB (Must succeed)
    result = await run_in_threadpool(messages_collection.insert_one, message_doc)
    message_doc["_id"] = result.inserted_id
    
    # 2. Write to Immutable Archive DB (GUARANTEED)
    archive_doc = message_doc.copy()
    archive_doc["_id"] = result.inserted_id
    
    # ✅ AWAIT THIS WRITE - CRITICAL FIX
    await run_in_threadpool(messages_archive_collection.insert_one, archive_doc)
    
    # 3. Update room's last message info
    await run_in_threadpool(
        rooms_collection.update_one,
        {"_id": ObjectId(room_id)},
        {"$set": {"last_message_text": content, "last_message_at": now}}
    )
    
    # 4. Return the message (Stringified IDs for JSON)
    # ✅ CRITICAL FIX: Convert datetime to ISO string before returning
    return {
        "_id": str(result.inserted_id),
        "room_id": str(room_id),
        "sender_id": str(sender_id),
        "content": content,
        "created_at": now.isoformat(),  # ✅ Convert to ISO string here!
        "is_deleted": False
    }


# ----------------------------
# 5. Delete Message (30-Minute Rule)
# ----------------------------
async def delete_message_service(
    message_id: str,
    user_id: str
) -> dict:
    """
    Deletes message from DB 1 only if:
    1. The user owns the message.
    2. The message is less than 30 minutes old.
    """
    if not ObjectId.is_valid(message_id):
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    # Fetch the message from DB 1
    message = await run_in_threadpool(
        messages_collection.find_one,
        {"_id": ObjectId(message_id)}
    )
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check ownership
    if str(message["sender_id"]) != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    
    # Check 30-minute rule
    now = datetime.utcnow()
    message_age = now - message["created_at"]
    if message_age > timedelta(minutes=30):
        raise HTTPException(
            status_code=403, 
            detail="Message is older than 30 minutes and cannot be deleted"
        )
    
    # Soft delete from DB 1 only (Archive DB 2 stays untouched)
    await run_in_threadpool(
        messages_collection.update_one,
        {"_id": ObjectId(message_id)},
        {"$set": {"is_deleted": True}}
    )
    
    # Also get the room_id to return for WebSocket broadcast
    updated_message = await run_in_threadpool(
        messages_collection.find_one,
        {"_id": ObjectId(message_id)}
    )
    
    return {
        "status": "ok", 
        "message_id": message_id,
        "room_id": str(updated_message["room_id"]) if updated_message else None
    }