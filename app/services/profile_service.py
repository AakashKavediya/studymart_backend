"""
USER PROFILE APIs

| Method | Endpoint               | Purpose                                | Status |
| ------ | ---------------------- | -------------------------------------- | ------ |
| GET    | `/users/{user_id}`     | View another user's public profile     | 🚧 Pending |
| PUT    | `/users/profile`       | Update own profile                     | Done |
| GET    | `/users/products`      | Get all products listed by the user    | 🚧 Pending |
| GET    | `/users/stats`         | Get user statistics                    | 🚧 Pending |
| PUT    | `/users/password`      | Change account password                | Done |
| DELETE | `/users/account`       | Delete user account                    | 🚧 Pending |

"""
# ==========================
# Standard Library Imports
# ==========================
import asyncio
import os
import logging
from datetime import datetime, timedelta


# ==========================
# Fast API Library Imports
# ==========================
import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Response
from fastapi.concurrency import run_in_threadpool

# ==========================
# Local Imports
# ==========================
from app.mongodb.connect import connectdb
from app.utils.user import get_current_user


# Temporary imports
# (We'll move these later to utils/jwt.py)
from app.main import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
)


# ==========================
# Schema Imports
# ==========================
from app.schemas.profile_schema import ProfileImageUpload, UserProfilePublic, UpdatePassword, UpdateProfile,UserPublicProfile



# ==========================
# Database Connections
# ==========================
db = connectdb()
signup_collection = db["signup"]
refresh_token_collection = db["refresh_tokens"]
profile_collection = db["user-profile"]





# ==========================================================
# Update User Profile Service
# ==========================================================

async def update_user_profile_service(
    profile_data: UpdateProfile,  # Using Schema instead of request
    current_user: dict  # Receives user from route, NOT Depends
):
    """
    Update user profile using validated schema data.
    """
    # Get user_id from current_user
    user_id = current_user["_id"]
    
    # Fetch existing profile
    profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )
    
    # If no profile exists, create one
    if not profile:
        profile_data_dict = {
            "_id": user_id,
            "name": current_user.get("name"),
            "email": current_user.get("email"),
            "phone": current_user.get("phone"),
            "campus": current_user.get("campus"),
            "year": current_user.get("year"),
            "branch": current_user.get("branch"),
            "bio": current_user.get("bio"),
            "skills": [],
            "social_links": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await run_in_threadpool(
            profile_collection.insert_one,
            profile_data_dict
        )
        profile = profile_data_dict
    
    # Get update data from schema (automatically validated)
    update_data = profile_data.dict(exclude_unset=True)
    
    # If no fields to update, return error
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided to update"
        )
    
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update the profile
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": user_id},
        {"$set": update_data}
    )
    
    # Fetch updated profile
    updated_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )
    
    # Convert ObjectId to string
    if updated_profile and "_id" in updated_profile:
        updated_profile["_id"] = str(updated_profile["_id"])
    
    return {
        "status": "ok",
        "user": updated_profile
    }



# ==========================================================
# Update Password Service
# ==========================================================

async def update_password_service(
    password_data: UpdatePassword,  # Using Schema instead of request
    current_user: dict  # Receives user from route, NOT Depends
):
    """
    Update user password using validated schema data.
    """
    # Get user_id from current_user
    user_id = current_user["_id"]
    
    # Fetch existing user data from signup collection
    user_data = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": user_id}
    )
    
    if not user_data:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Validate current password
    is_password_valid = await run_in_threadpool(
        bcrypt.checkpw,
        password_data.current_password.encode('utf-8'),
        user_data["password"]
    )
    
    if not is_password_valid:
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )
    
    # Check if new password is same as current
    is_same_password = await run_in_threadpool(
        bcrypt.checkpw,
        password_data.new_password.encode('utf-8'),
        user_data["password"]
    )
    
    if is_same_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as current password"
        )
    
    # Hash the new password
    try:
        hashed_new_password = await run_in_threadpool(
            bcrypt.hashpw,
            password_data.new_password.encode('utf-8'),
            bcrypt.gensalt(rounds=10)
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error hashing password"
        )
    
    # Update the user's password in the database
    result = await run_in_threadpool(
        signup_collection.update_one,
        {"_id": user_id},
        {
            "$set": {
                "password": hashed_new_password,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=500,
            detail="Failed to update password"
        )
    
    # Clear refresh tokens to force re-login
    await run_in_threadpool(
        refresh_token_collection.delete_many,
        {"user_id": str(user_id)}
    )
    
    return {
        "status": "ok",
        "message": "Password updated successfully. Please login again."
    }




# ==========================================================
# Delete Account Service
# ==========================================================


async def delete_account_service(
        current_user: dict  # Receives user from route, NOT Depends
):
    """
    Delete user account and associated data.
    """
    # Get user_id from current_user
    user_id = current_user["_id"]

        # Delete user from signup collection
    result_signup = await run_in_threadpool(
        signup_collection.delete_one,
        {"_id": user_id}
    )

    # Delete user profile from profile collection
    result_profile = await run_in_threadpool(
        profile_collection.delete_one,
        {"_id": user_id}
    )

    # Delete refresh tokens for the user
    result_tokens = await run_in_threadpool(
        refresh_token_collection.delete_many,
        {"user_id": str(user_id)}
    )

    if result_signup.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "status": "ok",
        "message": "Account deleted successfully."
    }




# ==========================================================
# Search User Service
# ==========================================================

async def get_user_profile_service(user_id: str):
    """
    Get public profile of a user by their user_id.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    
    # Fetch user from signup collection (for basic info)
    user = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Fetch profile from profile collection
    profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    # Merge data - Start with user data
    merged_data = {
        "_id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "campus": user.get("campus"),
        "year": user.get("year"),
        "created_at": user.get("created_at"),
    }
    
    # If profile exists, override with profile data
    if profile:
        merged_data.update({
            "profile_image": profile.get("profile_image"),
            "bio": profile.get("bio"),
            "campus": profile.get("campus") or merged_data.get("campus"),
            "year": profile.get("year") or merged_data.get("year"),
            "branch": profile.get("branch"),
            "skills": profile.get("skills", []),
            "rating": profile.get("rating", 0),
            "total_reviews": profile.get("total_reviews", 0),
            "products_sold_count": profile.get("products_sold_count", 0),
            "active_listings_count": profile.get("active_listings_count", 0),
            "followers_count": profile.get("followers_count", 0),
            "following_count": profile.get("following_count", 0),
            "is_verified": profile.get("is_verified", False),
        })
    else:
        # If no profile, set defaults
        merged_data.update({
            "profile_image": None,
            "bio": None,
            "branch": None,
            "skills": [],
            "rating": 0,
            "total_reviews": 0,
            "products_sold_count": 0,
            "active_listings_count": 0,
            "followers_count": 0,
            "following_count": 0,
            "is_verified": False,
        })
    
    return merged_data



# ==========================================================
# Upload Profile Image Service
# ==========================================================

async def upload_profile_image_service(
    image_data: ProfileImageUpload,
    current_user: dict
):
    """
    Upload profile image URL from Cloudinary.
    """
    user_id = current_user["_id"]
    image_url = str(image_data.profile_image)
    
    # Fetch existing profile
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
            "phone": current_user.get("phone"),
            "campus": current_user.get("campus"),
            "year": current_user.get("year"),
            "branch": current_user.get("branch"),
            "bio": current_user.get("bio"),
            "profile_image": image_url,
            "skills": [],
            "social_links": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await run_in_threadpool(
            profile_collection.insert_one,
            profile_data
        )
        profile = profile_data
    else:
        # Update existing profile with new image
        await run_in_threadpool(
            profile_collection.update_one,
            {"_id": user_id},
            {
                "$set": {
                    "profile_image": image_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    # Fetch updated profile
    updated_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )
    
    # Convert ObjectId to string
    if updated_profile and "_id" in updated_profile:
        updated_profile["_id"] = str(updated_profile["_id"])
    
    return {
        "status": "ok",
        "message": "Profile image updated successfully",
        "user": updated_profile
    }



