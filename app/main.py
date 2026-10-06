import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from jose import jwt

# --------------------
# Environment
# --------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment/.env")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# --------------------
# Database
# --------------------
from app.mongodb.connect import connectdb  # noqa: E402

db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]
product_collection = db["products_for_sale"]
lost_and_found_collection = db["lost_and_found"]
lost_and_found_comment_collection = db["lost_and_found_comment"]
refresh_token_collection = db["refresh_tokens"]

# --------------------
# JWT
# --------------------
def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)

# --------------------
# Lifespan
# --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(refresh_token_collection.create_index, "token", unique=True)
    await run_in_threadpool(
        refresh_token_collection.create_index,
        "expires_at",
        expireAfterSeconds=0,
    )
    print("Server started successfully")
    yield



# --------------------
# App
# --------------------
app = FastAPI(lifespan=lifespan)

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://studybazar.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"],
)

security = HTTPBearer()

@app.get("/")
def start_server():
    return {"message": "Server is running successfully"}

# --------------------
# Routers
# --------------------
from app.routers import auth, profile, follower, products, lost_and_found, chat  # noqa: E402
from app.socket_manager import socket_app  # noqa: E402

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(follower.router)
app.include_router(products.router)
app.include_router(lost_and_found.router)
app.include_router(chat.router)

# Pick ONE mount point, matching your frontend
app.mount("/socket.io", socket_app)

# --------------------
# Test endpoint
# --------------------
@app.get("/products-test")
async def test_get_products():
    products = await run_in_threadpool(
        lambda: list(
            product_collection.find({"is_active": True})
            .sort("created_at", -1)
            .limit(20)
        )
    )
    for p in products:
        p["_id"] = str(p["_id"])
        if "seller_id" in p:
            p["seller_id"] = str(p["seller_id"])
    return {
        "status": "ok",
        "data": {
            "products": products,
            "pagination": {
                "current_page": 1,
                "total_pages": 1,
                "total_items": len(products),
                "items_per_page": 20,
                "has_next": False,
                "has_previous": False,
            },
        },
    }