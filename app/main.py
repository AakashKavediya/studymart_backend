# importing dependencies
from fastapi import FastAPI, Depends, status, Query, APIRouter, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import Response, Request
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from bson.errors import InvalidId
from pydantic import BaseModel, EmailStr, field_validator
from jose import jwt, JWTError
from fastapi.concurrency import run_in_threadpool
import logging
import secrets
import bcrypt
import asyncio
import email
import re
import os

# --------------------
# Importing environment variables
# --------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# --------------------
# JWT Functions
# --------------------
def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    # Opaque random string — NOT a JWT, harder to forge
    return secrets.token_urlsafe(32)

# --------------------
# Importing Schemas
# --------------------
from app.schemas.user_schema import CreateUser, LoginSchema, LogoutSchema, RefreshTokenSchema
from app.schemas.profile_schema import UserProfilePublic, UpdateProfile
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse

# Import Socket Manager
from app.socket_manager import socket_app 

# --------------------
# Importing Database
# --------------------
from app.mongodb.connect import connectdb

# --------------------
# Database Connections
# --------------------
db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]
product_collection = db["products"]
lost_and_found_collection = db["lost_and_found"]
lost_and_found_comment_collection = db["lost_and_found_comment"]
refresh_token_collection = db["refresh_tokens"]

"""
App Created
"""
app = FastAPI()

"""
Logging Configuration
"""
logging.basicConfig(level=logging.INFO)

"""
SECURITY CODES
"""
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://studybazar.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"],
)

# SECURITY
security = HTTPBearer()

"""
Server Started Message
"""
@app.on_event("startup")
async def startup_event():
    # Fast lookup + prevent duplicate active tokens
    await run_in_threadpool(
        refresh_token_collection.create_index, "token", unique=True
    )
    # TTL index — MongoDB auto-deletes expired tokens after 0 seconds past expires_at
    await run_in_threadpool(
        refresh_token_collection.create_index,
        "expires_at",
        expireAfterSeconds=0
    )
    print("Server started successfully")

@app.get("/")
def StartServer():
    return {"message": "Server is running successfully"}

# --------------------
# Importing routers
# --------------------
from app.routers import auth, profile, follower, products, lost_and_found, chat

# Include the router
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(follower.router)
app.include_router(products.router)
app.include_router(lost_and_found.router)
app.include_router(chat.router)

# --------------------
# Mount Socket.IO (CRITICAL FIX)
# --------------------
# Mount the WebSocket app at /socket.io (Direct connection)
app.mount("/socket.io", socket_app)

# Mount the WebSocket app at /api/socket.io (Through Next.js Proxy)
app.mount("/api/socket.io", socket_app)
