# ----------------------------
# GET CURRENT AUTHENTICATED USER
# ----------------------------

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime

from app.core.security import security
from app.schemas.profile_schema import UserProfilePublic
from app.mongodb.connect import connectdb
from app.main import ALGORITHM, SECRET_KEY

# Database connections
db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get the current authenticated user based on the provided JWT token.
    """
    access_token = credentials.credentials

    # -------------------------
    # Decode JWT
    # -------------------------
    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # -------------------------
    # Ensure access token
    # -------------------------
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # -------------------------
    # Get current user ID
    # -------------------------
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # -------------------------
    # Validate ObjectId
    # -------------------------
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id"
        )
    
    # -------------------------
    # Find User in Signup Collection
    # -------------------------
    db_user = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": ObjectId(user_id)}
    )

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return db_user