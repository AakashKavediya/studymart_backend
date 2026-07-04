import datetime

from bson import ObjectId
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.concurrency import run_in_threadpool


# -------------------------
# importing required modules
# -------------------------



# -------------------------
# importing schemas
# -------------------------
from app.mongodb.connect import connectdb
db = connectdb()
profile_collection = db["user-profile"]
follow_collection = db["user-follow"]
product_collection = db["products_for_sale"]
signup_collection = db["signup"]


async def check_follow_status(
    follower_id, following_id
):
    """check if the user if following the other user or not

    Args:
        follower_id (str): getting the user id of the follower
        following_id (str): getting the user id of the user to be followed
    """

    follow = await run_in_threadpool(
        profile_collection.find_one,
        
        {"follower_id": ObjectId(follower_id), "following_id": ObjectId(following_id)},
    )
    return follow is not None




# async def get_user_stats(
#         user_id: str,
# ):
#     """Get user stats from various sources.

#     Args:
#         user_id (str): 
#     """
#     # Count followers
#     followers_count = await run_in_threadpool(
#         follow_collection.count_documents,
#         {"following_id": ObjectId(user_id)},
#     )

#     # Count following
#     following_count = await run_in_threadpool(
#         follow_collection.count_documents,
#         {"follower_id": ObjectId(user_id)},
#     )

#     # Count Products
#     count_products = await run_in_threadpool(
#         product_collection.count_documents,
#         {"seller_id": ObjectId(user_id), "status": "active"},
#     )

#     return{
#         "followers": followers_count,
#         "following": following_count,
#         "products": count_products
#     }


# async def get_or_create_user_profile(
#         user_id: str,
# ):
#     profile = await run_in_threadpool(
#         profile_collection.find_one,
#         {"user_id": ObjectId(user_id)},
#     )

#     if not profile:
#         user = await run_in_threadpool(
#             signup_collection.find_one,
#             {"_id": ObjectId(user_id)},
#         )

#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found"
#             )

#         profile_data = {
#             "_id": ObjectId(user_id),
#             "name": user.get("name"),
#             "email": user.get("email"),
#             "campus": user.get("campus"),
#             "year": user.get("year"),
#             "bio": "",
#             "profile_image": "",
#             "skills": [],
#             "social_links": {},
#             "followers_count": 0,
#             "following_count": 0,
#             "products_count": 0,
#             "is_verified": False,
#             "created_at": datetime.datetime.utcnow(),
#             "updated_at": datetime.datetime.utcnow()
#         }
#         await run_in_threadpool(
#             profile_collection.insert_one,
#             profile_data
#         )
        
#         return profile_data
    
#     return profile