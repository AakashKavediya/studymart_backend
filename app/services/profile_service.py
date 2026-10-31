# app/services/profile_service.py
"""
USER PROFILE SERVICES
- update profile
- update password
- delete account
- get public profile
- view public profile (with is_following)
- upload profile image
- get user stats (followers / following / products / lost_found)
- get-or-create profile
"""

# ==========================
# Standard Library
# ==========================
import logging
from datetime import datetime

# ==========================
# Third Party
# ==========================
import bcrypt
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool

# ==========================
# Local Imports
# ==========================
from app.mongodb.connect import connectdb
from app.schemas.profile_schema import (
    ProfileImageUpload,
    UpdatePassword,
    UpdateProfile,
)

# ==========================
# DB + Collections
# ==========================
db = connectdb()
signup_collection = db["signup"]
refresh_token_collection = db["refresh_tokens"]
profile_collection = db["user-profile"]
product_collection = db["products_for_sale"]
lost_found_collection = db["lost_and_found"]   # ✅ matches your router
# NOTE: also fall back to "lost_items" for older data
_alt_lost_collection = db["lost_items"]

# ------------------------------------------------------------------
# Auto-detect follow collection name
# ------------------------------------------------------------------
def _resolve_follow_collection():
    existing = set(db.list_collection_names())
    for name in ("follows", "user-follow", "user_follow", "follow"):
        if name in existing:
            return db[name]
    return db["follows"]


follow_collection = _resolve_follow_collection()
print(f"ℹ️  profile_service using follow collection: {follow_collection.name}")


# ============================================================================
# UPDATE PROFILE
# ============================================================================
async def update_user_profile_service(
    profile_data: UpdateProfile,
    current_user: dict,
):
    user_id = current_user["_id"]

    profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": user_id}
    )

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
            profile_collection.insert_one, profile_data_dict
        )
        profile = profile_data_dict

    update_data = profile_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="No valid fields provided to update"
        )

    update_data["updated_at"] = datetime.utcnow()

    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": user_id},
        {"$set": update_data},
    )

    updated_profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": user_id}
    )
    if updated_profile and "_id" in updated_profile:
        updated_profile["_id"] = str(updated_profile["_id"])

    return {"status": "ok", "user": updated_profile}


# ============================================================================
# UPDATE PASSWORD
# ============================================================================
async def update_password_service(
    password_data: UpdatePassword,
    current_user: dict,
):
    user_id = current_user["_id"]

    user_data = await run_in_threadpool(
        signup_collection.find_one, {"_id": user_id}
    )
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if not user_data.get("password"):
        raise HTTPException(
            status_code=400,
            detail="This account was created with Google. "
                   "Set a password via the forgot-password flow.",
        )

    is_password_valid = await run_in_threadpool(
        bcrypt.checkpw,
        password_data.current_password.encode("utf-8"),
        user_data["password"],
    )
    if not is_password_valid:
        raise HTTPException(
            status_code=401, detail="Current password is incorrect"
        )

    is_same_password = await run_in_threadpool(
        bcrypt.checkpw,
        password_data.new_password.encode("utf-8"),
        user_data["password"],
    )
    if is_same_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as current password",
        )

    try:
        hashed_new_password = await run_in_threadpool(
            bcrypt.hashpw,
            password_data.new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=10),
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error hashing password")

    result = await run_in_threadpool(
        signup_collection.update_one,
        {"_id": user_id},
        {
            "$set": {
                "password": hashed_new_password,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update password")

    await run_in_threadpool(
        refresh_token_collection.delete_many, {"user_id": str(user_id)}
    )

    return {
        "status": "ok",
        "message": "Password updated successfully. Please login again.",
    }


# ============================================================================
# DELETE ACCOUNT
# ============================================================================
async def delete_account_service(current_user: dict):
    user_id = current_user["_id"]

    result_signup = await run_in_threadpool(
        signup_collection.delete_one, {"_id": user_id}
    )
    await run_in_threadpool(
        profile_collection.delete_one, {"_id": user_id}
    )
    await run_in_threadpool(
        refresh_token_collection.delete_many, {"user_id": str(user_id)}
    )
    # Best-effort cleanup of follow relations
    try:
        await run_in_threadpool(
            follow_collection.delete_many,
            {
                "$or": [
                    {"follower_id": user_id},
                    {"following_id": user_id},
                    {"follower": user_id},
                    {"following": user_id},
                ]
            },
        )
    except Exception as e:
        logging.warning(f"Follow cleanup failed: {e}")

    if result_signup.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ok", "message": "Account deleted successfully."}


# ============================================================================
# GET USER PROFILE (simple)
# ============================================================================
async def get_user_profile_service(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await run_in_threadpool(
        signup_collection.find_one, {"_id": ObjectId(user_id)}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": ObjectId(user_id)}
    )

    merged = {
        "_id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "campus": user.get("campus"),
        "year": user.get("year"),
        "created_at": user.get("created_at"),
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
    }

    if profile:
        merged.update(
            {
                k: profile.get(k, merged.get(k))
                for k in (
                    "profile_image",
                    "bio",
                    "branch",
                    "skills",
                    "rating",
                    "total_reviews",
                    "products_sold_count",
                    "active_listings_count",
                    "followers_count",
                    "following_count",
                    "is_verified",
                )
            }
        )
        merged["campus"] = profile.get("campus") or merged["campus"]
        merged["year"] = profile.get("year") or merged["year"]

    return merged


# ============================================================================
# VIEW PUBLIC PROFILE (with is_following)
# ============================================================================
async def view_public_profile_service(user_id: str, current_user: dict):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await run_in_threadpool(
        signup_collection.find_one, {"_id": ObjectId(user_id)}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": ObjectId(user_id)}
    )

    if not user_profile:
        default_profile = {
            "_id": ObjectId(user_id),
            "name": user.get("name"),
            "email": user.get("email"),
            "campus": user.get("campus"),
            "year": user.get("year"),
            "bio": "",
            "profile_image": "",
            "skills": [],
            "social_links": {},
            "followers_count": 0,
            "following_count": 0,
            "products_count": 0,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await run_in_threadpool(
            profile_collection.insert_one, default_profile
        )
        user_profile = default_profile

    # is_following check
    is_following = False
    if current_user:
        follower_id = current_user["_id"]
        following_id = ObjectId(user_id)
        try:
            doc = await run_in_threadpool(
                follow_collection.find_one,
                {
                    "$or": [
                        {"follower_id": follower_id, "following_id": following_id},
                        {"follower": follower_id, "following": following_id},
                    ]
                },
            )
            is_following = doc is not None
        except Exception as e:
            logging.warning(f"is_following check failed: {e}")

    profile_data = {
        "id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "campus": user_profile.get("campus") or user.get("campus"),
        "year": user_profile.get("year") or user.get("year"),
        "branch": user_profile.get("branch"),
        "bio": user_profile.get("bio"),
        "profile_image": user_profile.get("profile_image"),
        "skills": user_profile.get("skills", []),
        "social_links": user_profile.get("social_links", {}),
        "followers_count": user_profile.get("followers_count", 0),
        "following_count": user_profile.get("following_count", 0),
        "products_count": user_profile.get("products_count", 0),
        "is_verified": user_profile.get("is_verified", False),
        "created_at": user.get("created_at"),
        "is_following": is_following if current_user else None,
    }

    return {"status": "ok", "user": profile_data}


# ============================================================================
# UPLOAD PROFILE IMAGE
# ============================================================================
async def upload_profile_image_service(
    image_data: ProfileImageUpload,
    current_user: dict,
):
    user_id = current_user["_id"]
    image_url = str(image_data.profile_image)

    profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": user_id}
    )

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
            profile_collection.insert_one, profile_data
        )
    else:
        await run_in_threadpool(
            profile_collection.update_one,
            {"_id": user_id},
            {
                "$set": {
                    "profile_image": image_url,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    updated_profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": user_id}
    )
    if updated_profile and "_id" in updated_profile:
        updated_profile["_id"] = str(updated_profile["_id"])

    return {
        "status": "ok",
        "message": "Profile image updated successfully",
        "user": updated_profile,
    }


# ============================================================================
# GET USER STATS  ← Fixed: accepts current_user dict, not user_id string
# ============================================================================
async def get_user_stats_service(current_user: dict):
    """
    Real-time counts from DB. Does NOT rely on cached counters.
    Returns: { status, data: { followers, following, products, lost_found } }
    """
    # Accept dict OR string for maximum compatibility
    if isinstance(current_user, dict):
        user_id = current_user.get("_id") or current_user.get("id")
    else:
        user_id = current_user

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )

    if not ObjectId.is_valid(str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    uid = ObjectId(str(user_id))

    # Followers — handle both possible field name variants
    followers_count = await run_in_threadpool(
        follow_collection.count_documents,
        {
            "$or": [
                {"following_id": uid},
                {"following": uid},
            ]
        },
    )

    # Following
    following_count = await run_in_threadpool(
        follow_collection.count_documents,
        {
            "$or": [
                {"follower_id": uid},
                {"follower": uid},
            ]
        },
    )

    # Active products
    products_count = await run_in_threadpool(
        product_collection.count_documents,
        {"seller_id": uid, "is_active": True},
    )

    # Lost & found posts (count from both possible collections)
    lost_found_count = await run_in_threadpool(
        lost_found_collection.count_documents, {"user_id": uid}
    )
    try:
        lost_found_count += await run_in_threadpool(
            _alt_lost_collection.count_documents, {"user_id": uid}
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "data": {
            "followers": followers_count,
            "following": following_count,
            "products": products_count,
            "lost_found": lost_found_count,
        },
    }


# ============================================================================
# GET OR CREATE PROFILE  ← Fixed: query by `_id`, not `user_id`
# ============================================================================
async def get_or_create_user_profile_service(current_user: dict):
    # Accept dict OR string
    if isinstance(current_user, dict):
        user_id = current_user.get("_id") or current_user.get("id")
    else:
        user_id = current_user

    if not user_id or not ObjectId.is_valid(str(user_id)):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    uid = ObjectId(str(user_id))

    profile = await run_in_threadpool(
        profile_collection.find_one, {"_id": uid}
    )

    if profile:
        profile["_id"] = str(profile["_id"])
        return {"status": "ok", "user": profile}

    user = await run_in_threadpool(
        signup_collection.find_one, {"_id": uid}
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    profile_data = {
        "_id": uid,
        "name": user.get("name"),
        "email": user.get("email"),
        "campus": user.get("campus"),
        "year": user.get("year"),
        "bio": "",
        "profile_image": "",
        "skills": [],
        "social_links": {},
        "followers_count": 0,
        "following_count": 0,
        "products_count": 0,
        "is_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await run_in_threadpool(
        profile_collection.insert_one, profile_data
    )

    profile_data["_id"] = str(profile_data["_id"])
    return {"status": "ok", "user": profile_data}