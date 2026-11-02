from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from bson import ObjectId
from app.mongodb.connect import connectdb
from fastapi import BackgroundTasks
from app.services.email_service import send_email

# Connect to both databases
db = connectdb()
rooms_collection = db["chat_rooms"]
messages_collection = db["chat_messages"]
messages_archive_collection = db["chat_messages_archive"]  # Immutable backup
signup_collection = db["signup"]

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
async def save_message_service(room_id: str, sender_id: str, content: str) -> dict:
    if not ObjectId.is_valid(room_id):
        raise HTTPException(status_code=400, detail="Invalid room ID format")

    now = datetime.utcnow()
    message_doc = {
        "room_id": ObjectId(room_id),
        "sender_id": ObjectId(sender_id),
        "content": content,
        "created_at": now,
        "is_deleted": False,
    }

    # 1. Save to Primary DB
    result = await run_in_threadpool(messages_collection.insert_one, message_doc)
    message_doc["_id"] = result.inserted_id

    # 2. Save to Archive DB
    archive_doc = message_doc.copy()
    archive_doc["_id"] = result.inserted_id
    await run_in_threadpool(messages_archive_collection.insert_one, archive_doc)

    # 3. Update room last message
    await run_in_threadpool(
        rooms_collection.update_one,
        {"_id": ObjectId(room_id)},
        {"$set": {"last_message_text": content, "last_message_at": now}},
    )

    # ✅ 4. Debounced Offline Email
    try:
        room = await run_in_threadpool(rooms_collection.find_one, {"_id": ObjectId(room_id)})
        recipient_id = [p for p in room["participants"] if p != sender_id][0]
        last_notified = room.get("last_notified_at")

        # Skip if notified recently (< 5 mins)
        if not last_notified or (now - last_notified) > timedelta(minutes=5):
            recipient = await run_in_threadpool(
                signup_collection.find_one, {"_id": ObjectId(recipient_id)}
            )
            if not recipient or not recipient.get("email"):
                return {
                    "_id": str(result.inserted_id),
                    "room_id": str(room_id),
                    "sender_id": str(sender_id),
                    "content": content,
                    "created_at": now.isoformat(),
                    "is_deleted": False,
                }

            # Get ALL unread messages in the last 5 mins
            query_time = last_notified or (now - timedelta(minutes=5))
            unread_msgs = await run_in_threadpool(
                lambda: list(messages_collection.find({
                    "room_id": ObjectId(room_id),
                    "created_at": {"$gt": query_time},
                    "sender_id": {"$ne": ObjectId(recipient_id)},
                }))
            )

            if unread_msgs:
                sender = await run_in_threadpool(
                    signup_collection.find_one, {"_id": ObjectId(sender_id)}
                )
                sender_name = sender.get("name", "Someone") if sender else "Someone"

                msg_html = "".join(
                    [f"<li><b>{sender_name}:</b> {m['content']}</li>" for m in unread_msgs]
                )
                body = f"""
                <div style="font-family: sans-serif; padding: 20px;">
                    <h3>You have {len(unread_msgs)} new messages from {sender_name}!</h3>
                    <ul>{msg_html}</ul>
                    <a href="https://studybazar.vercel.app/chat/{room_id}"
                       style="background:#F5A623; padding:10px 20px; text-decoration:none; color:black; border-radius:5px;">
                       Reply here
                    </a>
                </div>
                """
                await send_email(f"New messages from {sender_name}", [recipient["email"]], body)

                # Mark as notified
                await run_in_threadpool(
                    rooms_collection.update_one,
                    {"_id": ObjectId(room_id)},
                    {"$set": {"last_notified_at": now}},
                )
                print(f"📧 Sent aggregated email to {recipient['email']}")
    except Exception as e:
        print(f"❌ Email notification error: {e}")

    return {
        "_id": str(result.inserted_id),
        "room_id": str(room_id),
        "sender_id": str(sender_id),
        "content": content,
        "created_at": now.isoformat(),
        "is_deleted": False,
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