# app/utils/auth.py

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from datetime import datetime
from app.mongodb.connect import connectdb
from app.main import SECRET_KEY, ALGORITHM

db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get the current authenticated user based on the provided JWT token.
    """
    access_token = credentials.credentials

    # Decode JWT
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
    
    # Ensure access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get current user ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id"
        )
    
    # Find User
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


async def get_current_user_profile(
    current_user = Depends(get_current_user)
):
    """
    Get complete profile data by merging signup and profile collections.
    """
    user_id = current_user["_id"]
    
    # Fetch Profile from Profile Collection
    profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )
    
    # If no profile exists, create one
    if not profile:
        profile_data = {
            "_id": user_id,
            "name": current_user.get("name"),
            "email": current_user.get("email"),
            "campus": current_user.get("campus"),
            "phone": current_user.get("phone"),
            "year": current_user.get("year"),
            "created_at": current_user.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
        }
        
        await run_in_threadpool(
            profile_collection.insert_one,
            profile_data
        )
        
        profile = profile_data
    
    # Merge Data (Profile overrides Signup)
    merged_data = {
        "_id": str(current_user["_id"]),
        "name": profile.get("name") or current_user.get("name"),
        "email": current_user.get("email"),
        "phone": profile.get("phone") or current_user.get("phone"),
        "campus": profile.get("campus") or current_user.get("campus"),
        "year": profile.get("year") or current_user.get("year"),
        "branch": profile.get("branch"),
        "profile_image": profile.get("profile_image"),
        "bio": profile.get("bio"),
        "skills": profile.get("skills", []),
        "social_links": profile.get("social_links"),
        "rating": profile.get("rating", 0),
        "total_reviews": profile.get("total_reviews", 0),
        "products_sold_count": profile.get("products_sold_count", 0),
        "active_listings_count": profile.get("active_listings_count", 0),
        "followers_count": profile.get("followers_count", 0),
        "following_count": profile.get("following_count", 0),
        "is_verified": profile.get("is_verified", False),
        "is_blocked": profile.get("is_blocked", False),
        "created_at": profile.get("created_at") or current_user.get("created_at"),
        "updated_at": profile.get("updated_at") or current_user.get("updated_at"),
        "last_active": profile.get("last_active") or current_user.get("last_login"),
    }
    
    return merged_data