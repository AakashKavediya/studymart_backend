
"""
All the APIS for AUTHENTICATION
--
| Method | Endpoint             | Purpose                    |
| ------ | -------------------- | -------------------------- |
| POST   | `/auth/signup`       | Create new student account | done
| POST   | `/auth/login`        | Login and generate JWT     | done
| POST   | `/auth/logout`       | Logout user                | done
| GET    | `/auth/me`           | Get current logged-in user | done
| POST   | `/auth/refresh`      | Refresh access token       | done
| POST   | `/auth/verify-email` | Verify college email       |

"""



# ==========================
# Standard Library Imports
# ==========================
import asyncio
import logging
from datetime import datetime, timedelta

# ==========================
# Third Party Imports
# ==========================
import bcrypt
from fastapi import Depends, HTTPException, Response, status, Request
from fastapi.concurrency import run_in_threadpool

# ==========================
# Local Imports
# ==========================
from app.mongodb.connect import connectdb
from app.schemas.user_schema import LoginSchema, CreateUser
from pymongo.errors import DuplicateKeyError
from app.utils.user import get_current_user



# Temporary imports
# (We'll move these later to utils/jwt.py)
from app.main import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
)

# ==========================================================
# Database Collections
# ==========================================================

db = connectdb()

signup_collection = db["signup"]
refresh_token_collection = db["refresh_tokens"]
profile_collection = db["user-profile"]




# ==========================================================
# Login Service
# ==========================================================

async def login_user(
    user: LoginSchema,
    response: Response,
):
    """
    Authenticate a user and generate access & refresh tokens.
    """

    email = user.email.strip().lower()

    db_user = await run_in_threadpool(
        signup_collection.find_one,
        {"email": email},
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    password_valid = await run_in_threadpool(
        bcrypt.checkpw,
        user.password.encode("utf-8"),
        db_user["password"],
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    now = datetime.utcnow()

    user_id = str(db_user["_id"])

    access_token = create_access_token(
        user_id=user_id,
        email=db_user["email"],
    )

    refresh_token = create_refresh_token()

    refresh_expiry = now + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    await asyncio.gather(

        run_in_threadpool(
            refresh_token_collection.insert_one,
            {
                "token": refresh_token,
                "user_id": user_id,
                "email": db_user["email"],
                "created_at": now,
                "expires_at": refresh_expiry,
                "is_revoked": False,
            },
        ),

        run_in_threadpool(
            signup_collection.update_one,
            {"_id": db_user["_id"]},
            {
                "$set": {
                    "last_login": now,
                }
            },
        ),

    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    logging.info(
        f"Login successful for {db_user['email']}"
    )

    return {
        "status": "ok",
        "access_token": access_token,
    }





# ==========================================================
# Signup Service
# =========================================================

async def sign_up(user: CreateUser):

    from fastapi.concurrency import run_in_threadpool
    from datetime import datetime

    email = user.email.lower()

    if user.password != user.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    existing_user = await run_in_threadpool(
        signup_collection.find_one,
        {"$or": [{"email": email}, {"phone": user.phone}]}
    )

    if existing_user:
        if existing_user["email"] == email:
            raise HTTPException(409, "Email already registered")
        else:
            raise HTTPException(409, "Phone already registered")

    hashed_pw = await run_in_threadpool(
        bcrypt.hashpw, user.password.encode(), bcrypt.gensalt(rounds=10)
    )

    new_user = {
        "name": user.name,
        "email": email,
        "password": hashed_pw,
        "campus": user.campus,
        "phone": user.phone,
        "year": user.year,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    try:
        result = await run_in_threadpool(signup_collection.insert_one, new_user)

        profile = {
            "_id": result.inserted_id,
            "name": user.name,
            "email": email,
            "campus": user.campus,
            "phone": user.phone,
            "year": user.year,
            "created_at": datetime.utcnow(),
        }

        profile_result = await run_in_threadpool(
            profile_collection.insert_one,
            profile
        )

        return {
            "status": "ok",
            "user_id": str(result.inserted_id),
            "profile_id": str(profile_result.inserted_id)
        }

    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Email or phone already registered"
        )
    




# ==========================================================
# Refresh Token Service
# =========================================================

async def refresh_token_service(request: Request, response: Response):
    # Log request details for debugging - with null safety
    client_host = request.client.host if request.client else "unknown"
    logging.info(f"Refresh request from: {client_host}")
    logging.info(f"Cookies: {request.cookies}")
    
    # --------------------------------------------------
    # Get refresh token from HttpOnly cookie
    # --------------------------------------------------
    refresh_token = request.cookies.get("refresh_token")
    logging.info(f"Refresh token present: {bool(refresh_token)}")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    # --------------------------------------------------
    # Fetch refresh token from database
    # --------------------------------------------------
    token_doc = await run_in_threadpool(
        refresh_token_collection.find_one,
        {"token": refresh_token}
    )

    if token_doc is None:
        logging.warning(f"Invalid refresh token used from: {client_host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # --------------------------------------------------
    # Validate refresh token
    # --------------------------------------------------
    if token_doc["is_revoked"]:
        logging.warning(f"Revoked refresh token used from: {client_host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked"
        )

    if token_doc["expires_at"] < datetime.utcnow():
        logging.warning(f"Expired refresh token used from: {client_host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    # --------------------------------------------------
    # Revoke current refresh token
    # --------------------------------------------------
    await run_in_threadpool(
        refresh_token_collection.update_one,
        {"_id": token_doc["_id"]},
        {"$set": {"is_revoked": True}}
    )

    # --------------------------------------------------
    # Generate new token pair
    # --------------------------------------------------
    now = datetime.utcnow()

    user_id = str(token_doc["user_id"])
    email = token_doc["email"]

    access_token = create_access_token(
        user_id=user_id,
        email=email
    )

    new_refresh_token = create_refresh_token()

    refresh_expiry = now + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    # --------------------------------------------------
    # Store new refresh token
    # --------------------------------------------------
    await run_in_threadpool(
        refresh_token_collection.insert_one,
        {
            "token": new_refresh_token,
            "user_id": user_id,
            "email": email,
            "created_at": now,
            "expires_at": refresh_expiry,
            "is_revoked": False,
        }
    )

    # --------------------------------------------------
    # Replace refresh token cookie
    # --------------------------------------------------
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        # domain=".railway.app",  # ADD THIS - matches login endpoint
    )

    # --------------------------------------------------
    # Return new access token
    # --------------------------------------------------
    logging.info(f"Refresh successful for user: {email}")
    return {
        "status": "ok",
        "access_token": access_token,
    }




# ==========================================================
# Debug Cookies Service
# =========================================================

async def debug_cookies_service(request: Request):
    """
    Debug endpoint to check cookies.
    """
    cookies = request.cookies
    
    # Also check if there's any refresh token in the database
    refresh_token = cookies.get("refresh_token")
    token_info = None
    
    if refresh_token:
        token_doc = await run_in_threadpool(
            refresh_token_collection.find_one,
            {"token": refresh_token}
        )
        if token_doc:
            token_info = {
                "user_id": str(token_doc["user_id"]),
                "email": token_doc["email"],
                "created_at": token_doc["created_at"].isoformat() if token_doc["created_at"] else None,
                "expires_at": token_doc["expires_at"].isoformat() if token_doc["expires_at"] else None,
                "is_revoked": token_doc["is_revoked"],
            }
    
    return {
        "cookies": dict(cookies),
        "has_refresh_token": "refresh_token" in cookies,
        "refresh_token_value": cookies.get("refresh_token", "Not found"),
        "all_cookie_names": list(cookies.keys()),
        "token_info_in_db": token_info,
        "headers": {
            "user_agent": request.headers.get("user-agent", "Not provided"),
            "origin": request.headers.get("origin", "Not provided"),
            "referer": request.headers.get("referer", "Not provided"),
        }
    }






# ==========================================================
# Logout Service
# =========================================================


async def logout(request: Request, response: Response):

    # --------------------------------------------------
    # Get refresh token from HttpOnly cookie
    # --------------------------------------------------
    refresh_token = request.cookies.get("refresh_token")

    # --------------------------------------------------
    # Revoke refresh token (if present)
    # --------------------------------------------------
    if refresh_token:

        await run_in_threadpool(
            refresh_token_collection.update_one,
            {"token": refresh_token},
            {
                "$set": {
                    "is_revoked": True
                }
            }
        )

    # --------------------------------------------------
    # Remove refresh token cookie
    # --------------------------------------------------
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=True,          # True in production (HTTPS)
        samesite="none",
    )

    # --------------------------------------------------
    # Return response
    # --------------------------------------------------
    return {
        "status": "ok",
        "message": "Logged out successfully"
    }





# ==========================================================
# Get Me Service
# =========================================================


async def get_current_user_profile(
    current_user = Depends(get_current_user)
):
    """
    Get complete profile data by merging signup and profile collections.
    """
    user_id = current_user["_id"]
    
    # -------------------------
    # Fetch Profile from Profile Collection
    # -------------------------
    profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )
    
    # If no profile exists, create one
    if not profile:
        # Create a basic profile from signup data
        profile_data = {
            "_id": user_id,
            "name": current_user["name"],
            "email": current_user["email"],
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
    
    # -------------------------
    # Merge Data (Profile overrides Signup)
    # -------------------------
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
        "location": profile.get("location"),
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