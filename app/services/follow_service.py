from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError  # ✅ Add this import

from app.mongodb.connect import connectdb
from app.utils.validators import check_follow_status

db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]
follows_collection = db["follows"]


async def follow_user_service(
    target_user_id: str,
    current_user: dict
):
    """
    Follow a user.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(target_user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    
    target_id = ObjectId(target_user_id)
    current_user_id = current_user["_id"]
    
    # 2. Check if trying to follow yourself
    if current_user_id == target_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot follow yourself"
        )
    
    # 3. Check if target user exists
    target_user = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": target_id}
    )
    
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 4. Check if already following
    is_following = await check_follow_status(current_user_id, target_id)
    
    if is_following:
        # Already following - return success
        return {
            "status": "ok",
            "message": "Already following this user",
            "data": {
                "following": True,
                "followers_count": 0  # We'll get this from profile
            }
        }
    
    # 5. Create follow document
    follow_data = {
        "follower_id": current_user_id,
        "following_id": target_id,
        "created_at": datetime.utcnow()
    }
    
    try:
        await run_in_threadpool(
            follows_collection.insert_one,
            follow_data
        )
    except DuplicateKeyError:
        # Already following (race condition)
        return {
            "status": "ok",
            "message": "Already following this user",
            "data": {
                "following": True,
                "followers_count": 0
            }
        }
    
    # 6. Update counts
    # Increment target user's followers_count
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": target_id},
        {"$inc": {"followers_count": 1}}
    )
    
    # Increment current user's following_count
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": current_user_id},
        {"$inc": {"following_count": 1}}
    )
    
    # 7. Get updated counts from profile collection
    updated_target = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": target_id}
    )
    
    return {
        "status": "ok",
        "message": "User followed successfully",
        "data": {
            "following": True,
            "followers_count": updated_target.get("followers_count", 0) if updated_target else 0
        }
    }


async def unfollow_user_service(
    target_user_id: str,
    current_user: dict
):
    """
    Unfollow a user.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(target_user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    
    target_id = ObjectId(target_user_id)
    current_user_id = current_user["_id"]
    
    # 2. Check if trying to unfollow yourself
    if current_user_id == target_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot unfollow yourself"
        )
    
    # 3. Check if target user exists
    target_user = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": target_id}
    )
    
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # 4. Check if currently following
    is_following = await check_follow_status(current_user_id, target_id)
    
    if not is_following:
        # Not following - return success
        return {
            "status": "ok",
            "message": "Not following this user",
            "data": {
                "following": False,
                "followers_count": 0
            }
        }
    
    # 5. Delete follow document
    result = await run_in_threadpool(
        follows_collection.delete_one,
        {
            "follower_id": current_user_id,
            "following_id": target_id
        }
    )
    
    if result.deleted_count == 0:
        # Not following (race condition)
        return {
            "status": "ok",
            "message": "Not following this user",
            "data": {
                "following": False,
                "followers_count": 0
            }
        }
    
    # 6. Update counts (ensure they don't go below 0)
    # Decrement target user's followers_count
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": target_id, "followers_count": {"$gt": 0}},
        {"$inc": {"followers_count": -1}}
    )
    
    # Decrement current user's following_count
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": current_user_id, "following_count": {"$gt": 0}},
        {"$inc": {"following_count": -1}}
    )
    
    # 7. Get updated counts from profile collection
    updated_target = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": target_id}
    )
    
    return {
        "status": "ok",
        "message": "User unfollowed successfully",
        "data": {
            "following": False,
            "followers_count": updated_target.get("followers_count", 0) if updated_target else 0
        }
    }