"""
USER PROFILE APIs

| Method | Endpoint               | Purpose                                | Status |
| ------ | ---------------------- | -------------------------------------- | ------ |
| GET    | `/users/{user_id}`     | View another user's public profile     | Done |
| PUT    | `/users/profile`       | Update own profile                     | Done |
| GET    | `/users/products`      | Get all products listed by the user    | 🚧 Pending |
| POST   | `/users/profile_image` | Upload profile image                   | 🚧 Pending |
| GET    | `/users/stats`         | Get user statistics                    | 🚧 Pending |
| PUT    | `/users/password`      | Change account password                | Done |
| DELETE | `/users/account`       | Delete user account                    | Done |

"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from app.utils.user import get_current_user
from app.schemas.profile_schema import UpdatePassword, UpdateProfile, ProfileImageUpload
from app.schemas.user_schema import CreateUser, LoginSchema
from app.services.auth_service import get_current_user_profile
from app.services.profile_service import update_user_profile_service, update_password_service, delete_account_service, get_user_profile_service, upload_profile_image_service

from app.mongodb.connect import connectdb
db = connectdb()
profile_collection = db["user-profile"]

router = APIRouter(
    prefix="/users",
    tags=["User Profile"],
)

# ==========================================================
# Update User Profile Router
# ==========================================================
@router.put("/profile", status_code=status.HTTP_200_OK)
async def update_user_profile(
    profile_data: UpdateProfile,
    current_user = Depends(get_current_user)
):
    return await update_user_profile_service(profile_data, current_user)

# ==========================================================
# Update Password Router
# ==========================================================

@router.put("/password", status_code=status.HTTP_200_OK)
async def update_password(
    password_data: UpdatePassword,
    current_user = Depends(get_current_user)
):
    return await update_password_service(password_data, current_user)
# ==========================================================
# Delete Account Router
# ==========================================================

@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user = Depends(get_current_user)
):
    return await delete_account_service(current_user)


# ==========================================================
# Search User by Name Router
# ==========================================================


# 1. Search route (specific, no path params)
@router.get("/search", status_code=status.HTTP_200_OK)
async def search_users(
    query: str = Query(..., min_length=2, description="Search query for username"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return")
):
    """
    Search users by name (Instagram-style search).
    """
    # Search in profile collection
    profiles = await run_in_threadpool(
        lambda: list(
            profile_collection.find(
                {"name": {"$regex": query, "$options": "i"}},
                {"name": 1, "profile_image": 1, "email": 1, "campus": 1}
            ).limit(limit)
        )
    )
    
    results = []
    for p in profiles:
        results.append({
            "id": str(p["_id"]),
            "name": p.get("name"),
            "email": p.get("email"),
            "profile_image": p.get("profile_image"),
            "campus": p.get("campus"),
        })
    
    return {
        "status": "ok",
        "results": results,
        "count": len(results)
    }

# ==========================================================
# Search User by ID Router
# ==========================================================


# 2. Get user by ID route (parameterized)
@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def get_user_profile(user_id: str):
    """
    Get public profile of a user by their ID.
    """
    # Validate ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    
    user_profile = await get_user_profile_service(user_id)
    
    return {
        "status": "ok",
        "user": user_profile
    }

# ==========================================================
# Upload Profile Image Router
# ==========================================================


@router.post("/profile_image", status_code=status.HTTP_200_OK)
async def upload_profile_image(
    image_data: ProfileImageUpload,
    current_user = Depends(get_current_user)
):
    """
    Upload profile image URL from Cloudinary.
    
    Request body:
    {
        "profile_image": "https://res.cloudinary.com/..."
    }
    
    Returns updated user profile with new image URL.
    """
    return await upload_profile_image_service(image_data, current_user)