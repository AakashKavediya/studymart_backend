# app/socket_manager.py
import socketio
import traceback
from bson import ObjectId
from datetime import datetime
from app.services.chat_service import save_message_service

# ✅ Allow your actual frontend origin
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://studybazar.vercel.app",
        "*",  # keep wildcard for dev
    ],
    ping_interval=25,
    ping_timeout=60,
)

socket_app = socketio.ASGIApp(sio, socketio_path="socket.io")

# Track connected users
connected_clients = {}

def _json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


@sio.event
async def connect(sid, environ, auth):
    print(f"✅ Client connected: {sid}")
    connected_clients[sid] = auth


@sio.event
async def disconnect(sid):
    print(f"🔴 Client disconnected: {sid}")
    connected_clients.pop(sid, None)


@sio.event
async def join_room(sid, data):
    try:
        if not data:
            print(f"⚠️ Join room failed: Missing data from {sid}")
            return

        room_id = data.get("room_id")
        if room_id is not None:
            room_id = str(room_id)
            await sio.enter_room(sid, room_id)
            print(f"📍 User {sid} joined room: {room_id}")
            # ✅ Notify the client that join succeeded
            await sio.emit("joined_room", {"room_id": room_id, "sid": sid}, to=sid)
        else:
            print(f"⚠️ Join room failed: Missing room_id from {sid}")
    except Exception as e:
        print(f"❌ Error in join_room: {e}")
        traceback.print_exc()


@sio.event
async def send_message(sid, data):
    try:
        print(f"📩 Message received from {sid}:", data)

        room_id = data.get("room_id")
        content = data.get("content")
        sender_id = data.get("sender_id")

        if room_id is None or not content:
            print("❌ Missing required fields (room_id or content)")
            return

        room_id = str(room_id)
        sender_id = str(sender_id) if sender_id is not None else None

        if not sender_id or not ObjectId.is_valid(sender_id):
            print(f"❌ Invalid sender_id: {sender_id}. Message ignored.")
            return

        saved_message = await save_message_service(room_id, sender_id, content)
        print(f"✅ Saved to DB: {saved_message}")

        message_to_send = _json_safe(saved_message)
        await sio.emit("receive_message", message_to_send, room=room_id)
        print(f"📤 Emitted message to room {room_id}")

    except Exception as e:
        print(f"❌ Error in send_message: {e}")
        traceback.print_exc()