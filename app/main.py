#importing dependencies
from fastapi import FastAPI, Depends, status, Query
from fastapi.security import HTTPBearer,  HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import Response, Request
from fastapi import APIRouter, HTTPException, status
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
import re
import os



#--------------------
# Importing evironment variables
#--------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


#--------------------
# Importing Schema's
#--------------------
def create_access_token(user_id: str, email:str) -> str:
    expire = datetime.utcnow() + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
    payLoad = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(payLoad, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    # Opaque random string — NOT a JWT, harder to forge
    return secrets.token_urlsafe(32)

#--------------------
# Importing Schema's
#--------------------

from app.schemas.user_schema import CreateUser, LoginSchema, LogoutSchema, RefreshTokenSchema
from app.schemas.profile_schema import UserProfilePublic, UpdateProfile
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.lost_and_found_schema import LostCreate, LostUpdate

#--------------------
# Importing Database
#--------------------
from app.mongodb.connect import connectdb


#------------------------
# Database Connections
#------------------------

#DB Connections
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
        "https://studybazar.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#SECURITY
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


"""
All the APIS for AUTHENTICATION
--
| Method | Endpoint             | Purpose                    |
| ------ | -------------------- | -------------------------- |
| POST   | `/auth/signup`       | Create new student account | done
| POST   | `/auth/login`        | Login and generate JWT     | done
| POST   | `/auth/logout`       | Logout user                | done
| GET    | `/auth/me`           | Get current logged-in user | done
| POST   | `/auth/refresh`      | Refresh access token       |  
| POST   | `/auth/verify-email` | Verify college email       |

"""

#----------------------------
# Create new student account
#----------------------------

@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
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



# ----------------------------
# POST /auth/login
# ----------------------------
@app.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(user: LoginSchema, response: Response):

    # --------------------------------------------------
    # Normalize email
    # --------------------------------------------------
    email = user.email.strip().lower()

    # --------------------------------------------------
    # Fetch user
    # --------------------------------------------------
    db_user = await run_in_threadpool(
        signup_collection.find_one,
        {"email": email}
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # --------------------------------------------------
    # Verify password
    # --------------------------------------------------
    password_valid = await run_in_threadpool(
        bcrypt.checkpw,
        user.password.encode("utf-8"),
        db_user["password"]
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # --------------------------------------------------
    # Prepare token data
    # --------------------------------------------------
    now = datetime.utcnow()

    user_id = str(db_user["_id"])
    email = db_user["email"]

    access_token = create_access_token(
        user_id=user_id,
        email=email
    )

    refresh_token = create_refresh_token()

    refresh_expiry = now + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    # --------------------------------------------------
    # Save refresh token & update last login
    # --------------------------------------------------
    await asyncio.gather(

        run_in_threadpool(
            refresh_token_collection.insert_one,
            {
                "token": refresh_token,
                "user_id": user_id,
                "email": email,
                "created_at": now,
                "expires_at": refresh_expiry,
                "is_revoked": False,
            }
        ),

        run_in_threadpool(
            signup_collection.update_one,
            {"_id": db_user["_id"]},
            {
                "$set": {
                    "last_login": now
                }
            }
        )
    )

    # --------------------------------------------------
    # Store refresh token in HttpOnly cookie
    # --------------------------------------------------
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Must be True in production (HTTPS)
        samesite="none",  # Required for cross-site requests
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        domain=".railway.app",  # Add this if backend is on railway
    )

    # --------------------------------------------------
    # Return access token
    # --------------------------------------------------
    return {
        "status": "ok",
        "access_token": access_token,
    }


# ----------------------------
# POST /auth/refresh
# ----------------------------
@app.post("/auth/refresh", status_code=status.HTTP_200_OK)
async def refresh(request: Request, response: Response):
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
        domain=".railway.app",  # ADD THIS - matches login endpoint
    )

    # --------------------------------------------------
    # Return new access token
    # --------------------------------------------------
    logging.info(f"Refresh successful for user: {email}")
    return {
        "status": "ok",
        "access_token": access_token,
    }


# ----------------------------
# POST /auth/logout
# ----------------------------
@app.post("/auth/logout", status_code=status.HTTP_200_OK)
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

#----------------------------
# API FOR GET MY INFORMATION
#----------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Reject refresh tokens being used as access tokens
        if payload.get("type") != "access":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    db_user = await run_in_threadpool(
        signup_collection.find_one, {"_id": ObjectId(user_id)}
    )
    if not db_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return db_user



@app.get("/auth/me", status_code=status.HTTP_200_OK)
async def get_me(current_user=Depends(get_current_user)):

    user_info = {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "year": current_user["year"],
        "phone": current_user["phone"],
        "campus": current_user["campus"],
        "is_verified": current_user.get("is_verified", False),
        "created_at": current_user.get("created_at"),
    }

    return {
        "status": "ok",
        "user": user_info
    }


"""
USER PROFILE APIs

| Method | Endpoint                 | Purpose               |
| ------ | ------------------------ | --------------------- |
| GET    | `/users/{user_id}`       | View public profile   | Done
| PUT    | `/users/profile`         | Update own profile    | Done
| POST   | `/users/profile/image`   | Upload profile image  | #Done
| GET    | `/users/my-products`     | Get my listings       |
| GET    | `/users/my-lost-posts`   | My lost & found posts |
| POST   | `/users/block/{user_id}` | Block user            |
| GET    | `/users/search`          | Search users          | Done

"""


#----------------------------
# API FOR SEARCH USER
#----------------------------

@app.get("/users/search")
async def search_user(name: str):
    profiles = await run_in_threadpool(
        lambda: list(
            profile_collection.find(
                {"name": {"$regex": name, "$options": "i"}}
            ).limit(20)
        )
    )

    for p in profiles:
        p["_id"] = str(p["_id"])

    return {
        "status": "ok",
        "results": profiles
    }




#----------------------------
# API FOR VIEW PUBIC PROFILE
#----------------------------

@app.get("/users/{user_id}")
async def get_public_profile(user_id: str):

    user = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["_id"] = str(user["_id"])

    return user




#----------------------------
# API FOR COMPLETE PROFILE LIST
#----------------------------
"""
NOT WORKING PROPERLY
INTERNAL SERVER ERROR

"""

@app.get("/users/profile_list")
async def get_profile_list():

    profiles = await run_in_threadpool(
        lambda: list(
            profile_collection.find({}, {"name": 1})
        )
    )

    result = []

    for p in profiles:
        result.append({
            "id": str(p["_id"]),
            "name": p.get("name")
        })

    return {"status": "ok", "profiles": result}



#----------------------------
# API FOR UPDATE OWN PROFILE
#----------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user

@app.put("/users/profile", status_code=status.HTTP_200_OK)
async def update_my_profile(
    profile: UpdateProfile,
    current_user=Depends(get_current_user)
):

    user_id = current_user["_id"]

    update_data = profile.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )

    update_data["updated_at"] = datetime.utcnow()

    result = await run_in_threadpool(
        profile_collection.update_one,
        {"_id": user_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updated_user = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": user_id}
    )

    updated_user["_id"] = str(updated_user["_id"])

    return {
        "status": "ok",
        "user": updated_user
    }



#----------------------------
# API FOR UPLOAD PROFILE IMAGE
#----------------------------

#DONE







"""
PRODUCT (MARKETPLACE) APIs

Core Product Management

| Method | Endpoint                           | Purpose                            |
| ------ | ---------------------------------- | ---------------------------------- |
| POST   | `/products`                        | Create product                     | Done
| GET    | `/products`                        | Get all products (with pagination) | Done
| GET    | `/products/{product_id}`           | Get single product                 | Done
| PUT    | `/products/{product_id}`           | Edit product                       | Done
| DELETE | `/products/{product_id}`           | Delete product                     | Done
| PATCH  | `/products/{product_id}/mark-sold` | Mark product sold                  |

"""




#----------------------------
# API FOR CREATE PRODUCT
#----------------------------


@app.post("/products", status_code=201)
async def post_product(
    product: ProductCreate,
    current_user = Depends(get_current_user)
):

    seller_id = current_user["_id"]

    product_info = {
        "title": product.title,
        "description": product.description,
        "category": product.category,
        "price": product.price,
        "condition": product.condition,
        "negotiable": product.negotiable,
        "images": product.images,
        "campus": product.campus,
        "location": product.location,

        "seller_id": seller_id,

        "status": "active",
        "created_at": datetime.now()
    }

    result = await run_in_threadpool(
        product_collection.insert_one,
        product_info
    )

    return {
        "status": "ok",
        "product_id": str(result.inserted_id)
    }







#----------------------------
# API FOR DELETE PRODUCT
#----------------------------


@app.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: str,
    current_user=Depends(get_current_user)
):

    seller_id = current_user["_id"]

    try:
        object_id = ObjectId(product_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )

    result = await run_in_threadpool(
        product_collection.delete_one,
        {
            "_id": object_id,
            "seller_id": seller_id
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you are not the owner"
        )

    return {
        "status": "ok",
        "message": "Product deleted successfully"
    }






#----------------------------
# API FOR GET ALL PRODUCT
#----------------------------



@app.get("/products", status_code=200)
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):

    skip = (page - 1) * limit

    products = await run_in_threadpool(
        lambda: list(
            product_collection
            .find({"status": "active"})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
    )

    for p in products:
        p["_id"] = str(p["_id"])
        p["seller_id"] = str(p["seller_id"])

    return {
        "status": "ok",
        "page": page,
        "limit": limit,
        "count": len(products),
        "products": products
    }




#----------------------------
# API FOR GET ALL SINGLE PRODUCT
#----------------------------


@app.get("/products/{product_id}", status_code=status.HTTP_200_OK)
async def get_single_product(product_id: str):

    # Validate ObjectId
    try:
        obj_id = ObjectId(product_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )

    # Fetch product
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": obj_id}
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Convert ObjectIds to string
    product["_id"] = str(product["_id"])
    product["seller_id"] = str(product["seller_id"])

    return {
        "status": "ok",
        "product": product
    }




#----------------------------
# API FOR EDIT THE PRODUCT
#----------------------------



@app.put("/products/{product_id}", status_code=status.HTTP_200_OK)
async def update_product(
    product_id: str,
    product: ProductUpdate,
    current_user = Depends(get_current_user)
):

    # Validate ID
    try:
        obj_id = ObjectId(product_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid product id"
        )

    seller_id = current_user["_id"]

    update_data = product.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update"
        )

    update_data["updated_at"] = datetime.utcnow()

    result = await run_in_threadpool(
        product_collection.update_one,
        {
            "_id": obj_id,
            "seller_id": seller_id
        },
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Product not found or you are not the owner"
        )

    return {
        "status": "ok",
        "message": "Product updated successfully"
    }

"""
PRODUCT (MARKETPLACE) APIs

Product Filtering & Search

| Method | Endpoint                        | Purpose            |
| ------ | ------------------------------- | ------------------ |
| GET    | `/products/search`              | Search products    | Done
| GET    | `/products/category/{category}` | Filter by category |
| GET    | `/products/user/{user_id}`      | Products by seller |

"""



#----------------------------
# API FOR SEARCH ALL PRODUCTS
#----------------------------

@app.get("/products/search", status_code=status.HTTP_200_OK)
async def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):

    skip = (page - 1) * limit

    products = await run_in_threadpool(
        lambda: list(
            product_collection.find(
                {
                    "status": "active",
                    "title": {"$regex": q, "$options": "i"}
                }
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
    )

    for p in products:
        p["_id"] = str(p["_id"])
        p["seller_id"] = str(p["seller_id"])

    return {
        "status": "ok",
        "query": q,
        "page": page,
        "limit": limit,
        "count": len(products),
        "products": products
    }




"""
PRODUCT (MARKETPLACE) APIs

Engagement

| Method | Endpoint                      | Purpose             |
| ------ | ----------------------------- | ------------------- |
| POST   | `/products/{product_id}/view` | Increase view count |
| POST   | `/products/{product_id}/like` | Like product        |
| DELETE | `/products/{product_id}/like` | Remove like         |

"""







"""
IMAGE UPLOAD APIs

| Method | Endpoint                | Purpose                |
| ------ | ----------------------- | ---------------------- |
| POST   | `/upload/product-image` | Upload product images  |# not requied rn
| POST   | `/upload/profile-image` | Upload profile image   |# not requied rn
| POST   | `/upload/lost-image`    | Upload lost item image |# not requied rn
| POST   | `/upload/event-image`   | Upload event image     |# not requied rn

"""







"""
CHAT APIs (Real-Time System)

REST Endpoints

| Method | Endpoint                   | Purpose       |
| ------ | -------------------------- | ------------- |
| POST   | `/chat/start/{product_id}` | Start chat    |
| GET    | `/chat/my-chats`           | Get all chats |
| GET    | `/chat/{chat_id}`          | Get messages  |
| DELETE | `/chat/{chat_id}`          | Delete chat   |


WebSocket Endpoint

| Method | Endpoint             | Purpose             |
| ------ | -------------------- | ------------------- |
| WS     | `/ws/chat/{chat_id}` | Real-time messaging |

"""







"""
NOTIFICATION APIs

| Method | Endpoint                   | Purpose             |
| ------ | -------------------------- | ------------------- |
| GET    | `/notifications`           | Get notifications   |
| PATCH  | `/notifications/{id}/read` | Mark as read        |
| DELETE | `/notifications/{id}`      | Delete notification |

"""







"""
LOST & FOUND APIs

Lost Items

| Method | Endpoint          | Purpose                |
| ------ | ----------------- | ---------------------- |
| POST   | `/lost`           | Create lost/found post | Done
| GET    | `/lost`           | Get all lost posts     | Done
| GET    | `/lost/{lost_id}` | Get single post        | Done
| PUT    | `/lost/{lost_id}` | Update lost post       | Done
| DELETE | `/lost/{lost_id}` | Delete post            | Done

"""





#----------------------------
# API FOR POST LOST PRODUCT
#----------------------------


@app.post("/lost", status_code=201)
async def create_lost_post(
    post: LostCreate,
    current_user=Depends(get_current_user)
):

    lost_post = {
        "title": post.title,
        "description": post.description,
        "category": post.category,
        "location": post.location,
        "campus": post.campus,
        "contact_info": post.contact_info,

        "user_id": current_user["_id"],

        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await run_in_threadpool(
        lost_and_found_collection.insert_one,
        lost_post
    )

    return {
        "status": "ok",
        "lost_id": str(result.inserted_id)
    }





#----------------------------
# API FOR LIST OF ALL LOST PRODUCT
#----------------------------


@app.get("/lost")
async def get_lost_posts(
    page: int = 1,
    limit: int = 10
):

    skip = (page - 1) * limit

    posts = await run_in_threadpool(
        lambda: list(
            lost_and_found_collection
            .find({"status": "active"})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
    )

    for p in posts:
        p["_id"] = str(p["_id"])
        p["user_id"] = str(p["user_id"])

    return {
        "status": "ok",
        "posts": posts
    }



#----------------------------
# API FOR SEARCH FOR SINGLE PRODUCTS
#----------------------------


@app.get("/lost/{lost_id}")
async def get_single_lost_post(lost_id: str):

    try:
        obj_id = ObjectId(lost_id)
    except:
        raise HTTPException(400, "Invalid lost id")

    post = await run_in_threadpool(
        lost_and_found_collection.find_one,
        {"_id": obj_id}
    )

    if not post:
        raise HTTPException(404, "Post not found")

    post["_id"] = str(post["_id"])
    post["user_id"] = str(post["user_id"])

    return post





#----------------------------
# API FOR UPDATE THE LOST PRODUCT   
#----------------------------


@app.put("/lost/{lost_id}")
async def update_lost_post(
    lost_id: str,
    data: LostUpdate,
    current_user=Depends(get_current_user)
):

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(400, "No fields to update")

    update_data["updated_at"] = datetime.utcnow()

    result = await run_in_threadpool(
        lost_and_found_collection.update_one,
        {
            "_id": ObjectId(lost_id),
            "user_id": current_user["_id"]
        },
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            403,
            "You are not allowed to edit this post"
        )

    return {"status": "ok"}



#----------------------------
# API FOR DELETE LOST PRODUCTS
#----------------------------

@app.delete("/lost/{lost_id}")
async def delete_lost_post(
    lost_id: str,
    current_user=Depends(get_current_user)
):

    result = await run_in_threadpool(
        lost_and_found_collection.delete_one,
        {
            "_id": ObjectId(lost_id),
            "user_id": current_user["_id"]
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            403,
            "You are not allowed to delete this post"
        )

    return {"status": "ok", "message": "Post deleted"}



"""
LOST & FOUND APIs

Lost Item Comments

| Method | Endpoint                     | Purpose        |
| ------ | ---------------------------- | -------------- |
| POST   | `/lost/{lost_id}/comment`    | Add comment    |
| GET    | `/lost/{lost_id}/comments`   | Get comments   |
| DELETE | `/lost/comment/{comment_id}` | Delete comment |

"""







"""
LOST & FOUND APIs

Claim System

| Method | Endpoint                  | Purpose       |
| ------ | ------------------------- | ------------- |
| POST   | `/lost/{lost_id}/claim`   | Claim item    |
| PATCH  | `/lost/{lost_id}/resolve` | Mark resolved |

"""







"""
ADMIN APIs

| Method | Endpoint                  | Purpose             |
| ------ | ------------------------- | ------------------- |
| GET    | `/admin/users`            | View all users      |
| PATCH  | `/admin/users/{id}/block` | Block user          |
| GET    | `/admin/products`         | View all products   |
| DELETE | `/admin/products/{id}`    | Remove product      |
| GET    | `/admin/lost`             | Moderate lost posts |
| DELETE | `/admin/events/{id}`      | Remove event        |
| GET    | `/admin/reports`          | View abuse reports  |

"""