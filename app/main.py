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
from app.routers import lost_and_found

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
        "https://studybazar.vercel.app",
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
from app.routers import auth, profile, follower, products

# Include the router
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(follower.router)
app.include_router(products.router)
app.include_router(lost_and_found.router)









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


# @app.post("/products", status_code=201)
# async def post_product(
#     product: ProductCreate,
#     current_user = Depends(get_current_user)
# ):

#     seller_id = current_user["_id"]

#     product_info = {
#         "title": product.title,
#         "description": product.description,
#         "category": product.category,
#         "price": product.price,
#         "condition": product.condition,
#         "negotiable": product.negotiable,
#         "images": product.images,
#         "campus": product.campus,
#         "location": product.location,

#         "seller_id": seller_id,

#         "status": "active",
#         "created_at": datetime.now()
#     }

#     result = await run_in_threadpool(
#         product_collection.insert_one,
#         product_info
#     )

#     return {
#         "status": "ok",
#         "product_id": str(result.inserted_id)
#     }







#----------------------------
# API FOR DELETE PRODUCT
#----------------------------


# @app.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
# async def delete_product(
#     product_id: str,
#     current_user=Depends(get_current_user)
# ):

#     seller_id = current_user["_id"]

#     try:
#         object_id = ObjectId(product_id)
#     except:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid product id"
#         )

#     result = await run_in_threadpool(
#         product_collection.delete_one,
#         {
#             "_id": object_id,
#             "seller_id": seller_id
#         }
#     )

#     if result.deleted_count == 0:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Product not found or you are not the owner"
#         )

#     return {
#         "status": "ok",
#         "message": "Product deleted successfully"
#     }






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


# @app.get("/products/{product_id}", status_code=status.HTTP_200_OK)
# async def get_single_product(product_id: str):

#     # Validate ObjectId
#     try:
#         obj_id = ObjectId(product_id)
#     except InvalidId:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid product id"
#         )

#     # Fetch product
#     product = await run_in_threadpool(
#         product_collection.find_one,
#         {"_id": obj_id}
#     )

#     if not product:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Product not found"
#         )

#     # Convert ObjectIds to string
#     product["_id"] = str(product["_id"])
#     product["seller_id"] = str(product["seller_id"])

#     return {
#         "status": "ok",
#         "product": product
#     }




#----------------------------
# API FOR EDIT THE PRODUCT
#----------------------------



# @app.put("/products/{product_id}", status_code=status.HTTP_200_OK)
# async def update_product(
#     product_id: str,
#     product: ProductUpdate,
#     current_user = Depends(get_current_user)
# ):

#     # Validate ID
#     try:
#         obj_id = ObjectId(product_id)
#     except InvalidId:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid product id"
#         )

#     seller_id = current_user["_id"]

#     update_data = product.dict(exclude_unset=True)

#     if not update_data:
#         raise HTTPException(
#             status_code=400,
#             detail="No fields provided to update"
#         )

#     update_data["updated_at"] = datetime.utcnow()

#     result = await run_in_threadpool(
#         product_collection.update_one,
#         {
#             "_id": obj_id,
#             "seller_id": seller_id
#         },
#         {"$set": update_data}
#     )

#     if result.matched_count == 0:
#         raise HTTPException(
#             status_code=404,
#             detail="Product not found or you are not the owner"
#         )

#     return {
#         "status": "ok",
#         "message": "Product updated successfully"
#     }

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


# @app.post("/lost", status_code=201)
# async def create_lost_post(
#     post: LostCreate,
#     current_user=Depends(get_current_user)
# ):

#     lost_post = {
#         "title": post.title,
#         "description": post.description,
#         "category": post.category,
#         "location": post.location,
#         "campus": post.campus,
#         "contact_info": post.contact_info,

#         "user_id": current_user["_id"],

#         "status": "active",
#         "created_at": datetime.utcnow(),
#         "updated_at": datetime.utcnow()
#     }

#     result = await run_in_threadpool(
#         lost_and_found_collection.insert_one,
#         lost_post
#     )

#     return {
#         "status": "ok",
#         "lost_id": str(result.inserted_id)
#     }





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


# @app.put("/lost/{lost_id}")
# async def update_lost_post(
#     lost_id: str,
#     data: LostUpdate,
#     current_user=Depends(get_current_user)
# ):

#     update_data = data.dict(exclude_unset=True)

#     if not update_data:
#         raise HTTPException(400, "No fields to update")

#     update_data["updated_at"] = datetime.utcnow()

#     result = await run_in_threadpool(
#         lost_and_found_collection.update_one,
#         {
#             "_id": ObjectId(lost_id),
#             "user_id": current_user["_id"]
#         },
#         {"$set": update_data}
#     )

#     if result.matched_count == 0:
#         raise HTTPException(
#             403,
#             "You are not allowed to edit this post"
#         )

#     return {"status": "ok"}



#----------------------------
# API FOR DELETE LOST PRODUCTS
#----------------------------

# @app.delete("/lost/{lost_id}")
# async def delete_lost_post(
#     lost_id: str,
#     current_user=Depends(get_current_user)
# ):

#     result = await run_in_threadpool(
#         lost_and_found_collection.delete_one,
#         {
#             "_id": ObjectId(lost_id),
#             "user_id": current_user["_id"]
#         }
#     )

#     if result.deleted_count == 0:
#         raise HTTPException(
#             403,
#             "You are not allowed to delete this post"
#         )

#     return {"status": "ok", "message": "Post deleted"}



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