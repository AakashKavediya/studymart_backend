# app/services/lost_and_found_service.py

"""
LOST & FOUND MODULE API ROADMAP

No. | Method | Endpoint                                  | Purpose                                      | Status
----|--------|-------------------------------------------|----------------------------------------------|---------
 1  | POST   | /lost-and-found                           | Create a new lost item                       | 🚧 Done
 2  | GET    | /lost-and-found                           | Get all lost items (with pagination)         | 🚧 Done
 3  | GET    | /lost-and-found/search                    | Search lost items                            | 🚧 Done
 4  | GET    | /lost-and-found/{item_id}                 | Get a specific lost item by ID               | 🚧 Done
 5  | PUT    | /lost-and-found/{item_id}                 | Edit/update a lost item                      | 🚧 Done
 6  | DELETE | /lost-and-found/{item_id}                 | Delete a lost item                           | 🚧 Done
 7  | PATCH  | /lost-and-found/{item_id}/status          | Update item status                           | 🚧 Done
 8  | POST   | /lost-and-found/{item_id}/claim           | Claim a found item                           | 🚧 Done
 9  | POST   | /lost-and-found/{item_id}/comment         | Add a comment to a lost item                 | 🚧 Done
10  | GET    | /lost-and-found/{item_id}/comments        | Get comments for a lost item                 | 🚧 Done
11  | GET    | /lost-and-found/my-items                  | Get current user's lost items                | 🚧 Done
12  | GET    | /lost-and-found/user/{user_id}            | Get items by a specific user                 | 🚧 Done
13  | GET    | /lost-and-found/categories                | Get all categories with counts               | 🚧 Done
14  | GET    | /lost-and-found/stats                     | Get lost & found statistics                  | 🚧 Done
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.mongodb.connect import connectdb
db = connectdb()
lost_items_collection = db["lost_items"]
profile_collection = db["user-profile"]
signup_collection = db["signup"]
comments_collection = db["lost_item_comments"]
claims_collection = db["lost_item_claims"]

from fastapi.concurrency import run_in_threadpool
from fastapi import Depends, HTTPException, status
from bson import ObjectId

from app.utils.user import get_current_user
from app.schemas.lost_and_found_schema import (
    LostItemCreate,
    LostItemUpdate,
    LostItemSearchParams,
    LostItemStatus,
    CommentCreate,
    ClaimItemCreate,
)

# ============================================================
# 1. CREATE LOST ITEM
# ============================================================

async def create_lost_item_service(
    item_data: LostItemCreate,
    current_user: dict
):
    """
    Create a new lost/found item.
    """
    # 1. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Get user profile for caching
    user_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    # 3. Build payload
    payload = {
        "user_id": ObjectId(user_id),
        "title": item_data.title,
        "description": item_data.description,
        "category": item_data.category,
        "location": item_data.location,
        "campus": item_data.campus,
        "contact_info": item_data.contact_info,
        "condition": item_data.condition,
        "images": [str(img) for img in item_data.images] if item_data.images else [],
        "status": LostItemStatus.LOST.value,
        "is_resolved": False,
        "user_name": user_profile.get("name") if user_profile else current_user.get("name"),
        "user_email": current_user.get("email"),
        "user_avatar": user_profile.get("profile_image") if user_profile else None,
        "views_count": 0,
        "comments_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # 4. Insert into database
    result = await run_in_threadpool(
        lost_items_collection.insert_one,
        payload
    )
    
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )
    
    return {
        "status": "ok",
        "message": "Lost item created successfully",
        "data": {
            "item_id": str(result.inserted_id),
            "title": item_data.title,
            "category": item_data.category.value if hasattr(item_data.category, 'value') else item_data.category,
            "created_at": datetime.utcnow().isoformat()
        }
    }


# ============================================================
# 2. GET ALL LOST ITEMS (with pagination)
# ============================================================

async def get_all_lost_items_service(
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    Get all lost items with pagination and sorting.
    """
    # 1. Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 50:
        limit = 20
    
    skip = (page - 1) * limit
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    
    # 2. Query filter - show all except closed
    filter_query = {
        "status": {"$ne": LostItemStatus.CLOSED.value}
    }
    
    # 3. Get total count
    total_count = await run_in_threadpool(
        lost_items_collection.count_documents,
        filter_query
    )
    
    # 4. Fetch items
    cursor = await run_in_threadpool(
        lost_items_collection.find,
        filter_query
    )
    cursor = cursor.sort(sort_by, sort_direction).skip(skip).limit(limit)
    
    items_list = await run_in_threadpool(list, cursor)
    
    # 5. Format
    formatted_items = []
    for item in items_list:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        formatted_items.append(item)
    
    # 6. Pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "items": formatted_items,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "sort": {
                "by": sort_by,
                "order": sort_order
            }
        }
    }


# ============================================================
# 3. SEARCH LOST ITEMS
# ============================================================

async def search_lost_items_service(
    search_params: LostItemSearchParams
):
    """
    Search lost items by keyword with filters.
    """
    # 1. Build query
    query: Dict[str, Any] = {
        "status": {"$ne": LostItemStatus.CLOSED.value}
    }
    
    # Text search (regex fallback)
    if search_params.query:
        query["$or"] = [
            {"title": {"$regex": search_params.query, "$options": "i"}},
            {"description": {"$regex": search_params.query, "$options": "i"}}
        ]
    
    # Category filter
    if search_params.category:
        query["category"] = search_params.category.value if hasattr(search_params.category, 'value') else search_params.category
    
    # Campus filter
    if search_params.campus:
        query["campus"] = search_params.campus
    
    # Status filter
    if search_params.status:
        query["status"] = search_params.status.value if hasattr(search_params.status, 'value') else search_params.status
    
    # Location filter
    if search_params.location:
        query["location"] = {"$regex": search_params.location, "$options": "i"}
    
    # 2. Pagination
    skip = (search_params.page - 1) * search_params.limit
    sort_direction = -1 if search_params.sort_order.lower() == "desc" else 1
    
    # 3. Count
    total_count = await run_in_threadpool(
        lost_items_collection.count_documents,
        query
    )
    
    # 4. Fetch
    cursor = await run_in_threadpool(
        lost_items_collection.find,
        query
    )
    cursor = cursor.sort(search_params.sort_by, sort_direction).skip(skip).limit(search_params.limit)
    
    items_list = await run_in_threadpool(list, cursor)
    
    # 5. Format
    formatted_items = []
    for item in items_list:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        formatted_items.append(item)
    
    total_pages = (total_count + search_params.limit - 1) // search_params.limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "items": formatted_items,
            "pagination": {
                "current_page": search_params.page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": search_params.limit,
                "has_next": search_params.page < total_pages,
                "has_previous": search_params.page > 1
            },
            "filters": {
                "query": search_params.query,
                "category": search_params.category,
                "campus": search_params.campus,
                "status": search_params.status,
                "location": search_params.location
            }
        }
    }


# ============================================================
# 4. GET LOST ITEM BY ID
# ============================================================

async def get_lost_item_by_id_service(
    item_id: str,
    current_user: Optional[dict] = None
):
    """
    Get a specific lost item by its ID.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Fetch item
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 3. Format response
    response_data = {
        "id": str(item["_id"]),
        "user_id": str(item["user_id"]),
        "title": item.get("title"),
        "description": item.get("description"),
        "category": item.get("category"),
        "location": item.get("location"),
        "campus": item.get("campus"),
        "contact_info": item.get("contact_info"),
        "condition": item.get("condition"),
        "images": item.get("images", []),
        "status": item.get("status"),
        "is_resolved": item.get("is_resolved", False),
        "user_name": item.get("user_name"),
        "user_email": item.get("user_email"),
        "user_avatar": item.get("user_avatar"),
        "views_count": item.get("views_count", 0) + 1,
        "comments_count": item.get("comments_count", 0),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "resolved_at": item.get("resolved_at"),
    }
    
    # 4. Check if current user is the owner
    is_owner = False
    if current_user:
        user_id = current_user.get("_id") or current_user.get("id")
        if user_id and str(user_id) == str(item["user_id"]):
            is_owner = True
    
    response_data["is_owner"] = is_owner
    
    # 5. Increment view count
    await run_in_threadpool(
        lost_items_collection.update_one,
        {"_id": ObjectId(item_id)},
        {"$inc": {"views_count": 1}}
    )
    
    return {
        "status": "ok",
        "data": response_data
    }


# ============================================================
# 5. UPDATE LOST ITEM
# ============================================================

async def update_lost_item_service(
    item_id: str,
    update_data: LostItemUpdate,
    current_user: dict
):
    """
    Update an existing lost item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 3. Check ownership
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    if str(user_id) != str(item["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this item"
        )
    
    # 4. Prepare update data
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_dict["updated_at"] = datetime.utcnow()
    
    # 5. Update
    result = await run_in_threadpool(
        lost_items_collection.update_one,
        {"_id": ObjectId(item_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 6. Fetch updated
    updated_item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if updated_item:
        updated_item["_id"] = str(updated_item["_id"])
        updated_item["user_id"] = str(updated_item["user_id"])
    
    return {
        "status": "ok",
        "message": "Item updated successfully",
        "data": updated_item
    }


# ============================================================
# 6. DELETE LOST ITEM
# ============================================================

async def delete_lost_item_service(
    item_id: str,
    current_user: dict
):
    """
    Delete a lost item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 3. Check ownership
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    if str(user_id) != str(item["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this item"
        )
    
    # 4. Delete
    result = await run_in_threadpool(
        lost_items_collection.delete_one,
        {"_id": ObjectId(item_id)}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "status": "ok",
        "message": "Item deleted successfully",
        "data": {
            "item_id": item_id,
            "deleted": True
        }
    }


# ============================================================
# 7. UPDATE ITEM STATUS
# ============================================================

async def update_item_status_service(
    item_id: str,
    status_value: LostItemStatus,
    current_user: dict
):
    """
    Update the status of a lost item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 3. Check ownership
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    if str(user_id) != str(item["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this item"
        )
    
    # 4. Prepare update
    update_dict = {
        "status": status_value.value if hasattr(status_value, 'value') else status_value,
        "updated_at": datetime.utcnow()
    }
    
    # Auto-resolve if status is RESOLVED
    if status_value == LostItemStatus.RESOLVED:
        update_dict["is_resolved"] = True
        update_dict["resolved_at"] = datetime.utcnow()
    elif status_value == LostItemStatus.LOST or status_value == LostItemStatus.FOUND:
        update_dict["is_resolved"] = False
    
    # 5. Update
    result = await run_in_threadpool(
        lost_items_collection.update_one,
        {"_id": ObjectId(item_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 6. Fetch updated
    updated_item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if updated_item:
        updated_item["_id"] = str(updated_item["_id"])
        updated_item["user_id"] = str(updated_item["user_id"])
    
    return {
        "status": "ok",
        "message": f"Item status updated to {status_value}",
        "data": updated_item
    }


# ============================================================
# 8. CLAIM ITEM
# ============================================================

async def claim_item_service(
    claim_data: ClaimItemCreate,
    current_user: dict
):
    """
    Claim a found item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(claim_data.item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(claim_data.item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 4. Check if already claimed by this user
    existing_claim = await run_in_threadpool(
        claims_collection.find_one,
        {
            "item_id": ObjectId(claim_data.item_id),
            "claimant_id": ObjectId(user_id)
        }
    )
    
    if existing_claim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already claimed this item"
        )
    
    # 5. Create claim
    claim = {
        "item_id": ObjectId(claim_data.item_id),
        "claimant_id": ObjectId(user_id),
        "claimant_name": current_user.get("name"),
        "claimant_email": current_user.get("email"),
        "proof_description": claim_data.proof_description,
        "contact_info": claim_data.contact_info or current_user.get("email"),
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    result = await run_in_threadpool(
        claims_collection.insert_one,
        claim
    )
    
    return {
        "status": "ok",
        "message": "Claim submitted successfully",
        "data": {
            "claim_id": str(result.inserted_id),
            "item_id": claim_data.item_id,
            "status": "pending"
        }
    }


# ============================================================
# 9. ADD COMMENT
# ============================================================

async def add_comment_service(
    item_id: str,
    comment_data: CommentCreate,
    current_user: dict
):
    """
    Add a comment to a lost item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 4. Create comment
    comment = {
        "item_id": ObjectId(item_id),
        "user_id": ObjectId(user_id),
        "user_name": current_user.get("name"),
        "user_avatar": None,  # Could fetch from profile
        "content": comment_data.content,
        "created_at": datetime.utcnow()
    }
    
    result = await run_in_threadpool(
        comments_collection.insert_one,
        comment
    )
    
    # 5. Increment comments count
    await run_in_threadpool(
        lost_items_collection.update_one,
        {"_id": ObjectId(item_id)},
        {"$inc": {"comments_count": 1}}
    )
    
    return {
        "status": "ok",
        "message": "Comment added successfully",
        "data": {
            "comment_id": str(result.inserted_id),
            "content": comment_data.content,
            "created_at": datetime.utcnow().isoformat()
        }
    }


# ============================================================
# 10. GET COMMENTS
# ============================================================

async def get_comments_service(
    item_id: str,
    page: int = 1,
    limit: int = 20
):
    """
    Get comments for a lost item.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # 2. Check if item exists
    item = await run_in_threadpool(
        lost_items_collection.find_one,
        {"_id": ObjectId(item_id)}
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 3. Pagination
    skip = (page - 1) * limit
    
    # 4. Fetch comments
    cursor = await run_in_threadpool(
        comments_collection.find,
        {"item_id": ObjectId(item_id)}
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    comments_list = await run_in_threadpool(list, cursor)
    
    # 5. Format
    formatted_comments = []
    for comment in comments_list:
        formatted_comments.append({
            "id": str(comment["_id"]),
            "item_id": str(comment["item_id"]),
            "user_id": str(comment["user_id"]),
            "user_name": comment.get("user_name"),
            "user_avatar": comment.get("user_avatar"),
            "content": comment["content"],
            "created_at": comment["created_at"]
        })
    
    # 6. Count
    total_count = await run_in_threadpool(
        comments_collection.count_documents,
        {"item_id": ObjectId(item_id)}
    )
    
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "comments": formatted_comments,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
    }


# ============================================================
# 11. GET MY LOST ITEMS
# ============================================================

async def get_my_lost_items_service(
    current_user: dict,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[LostItemStatus] = None
):
    """
    Get current user's lost items.
    """
    # 1. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Build query
    query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
    
    if status_filter:
        query["status"] = status_filter.value if hasattr(status_filter, 'value') else status_filter
    
    # 3. Pagination
    skip = (page - 1) * limit
    
    # 4. Count
    total_count = await run_in_threadpool(
        lost_items_collection.count_documents,
        query
    )
    
    # 5. Fetch
    cursor = await run_in_threadpool(
        lost_items_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    items_list = await run_in_threadpool(list, cursor)
    
    # 6. Format
    formatted_items = []
    for item in items_list:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        formatted_items.append(item)
    
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "items": formatted_items,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "status_filter": status_filter
        }
    }


# ============================================================
# 12. GET ITEMS BY USER
# ============================================================

async def get_user_lost_items_service(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[LostItemStatus] = None
):
    """
    Get lost items by a specific user.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # 2. Check if user exists
    user = await run_in_threadpool(
        signup_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 3. Build query - show active items for public view
    query = {
        "user_id": ObjectId(user_id),
        "status": {"$ne": LostItemStatus.CLOSED.value}
    }
    
    if status_filter:
        query["status"] = status_filter.value if hasattr(status_filter, 'value') else status_filter
    
    # 4. Pagination
    skip = (page - 1) * limit
    
    # 5. Count
    total_count = await run_in_threadpool(
        lost_items_collection.count_documents,
        query
    )
    
    # 6. Fetch
    cursor = await run_in_threadpool(
        lost_items_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    items_list = await run_in_threadpool(list, cursor)
    
    # 7. Format
    formatted_items = []
    for item in items_list:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        formatted_items.append(item)
    
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "user_id": user_id,
            "user_name": user.get("name"),
            "items": formatted_items,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
    }


# ============================================================
# 13. GET CATEGORIES
# ============================================================

async def get_lost_item_categories_service():
    """
    Get all lost item categories with counts.
    """
    pipeline = [
        {"$match": {"status": {"$ne": LostItemStatus.CLOSED.value}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    categories = await run_in_threadpool(
        lambda: list(lost_items_collection.aggregate(pipeline))
    )
    
    formatted_categories = []
    for cat in categories:
        formatted_categories.append({
            "name": cat["_id"],
            "count": cat["count"]
        })
    
    return {
        "status": "ok",
        "data": {
            "categories": formatted_categories,
            "total": len(formatted_categories)
        }
    }


# ============================================================
# 14. GET STATISTICS
# ============================================================

async def get_lost_found_stats_service():
    """
    Get lost & found statistics.
    """
    # Total items
    total = await run_in_threadpool(
        lost_items_collection.count_documents,
        {}
    )
    
    # Active lost items
    lost = await run_in_threadpool(
        lost_items_collection.count_documents,
        {"status": LostItemStatus.LOST.value}
    )
    
    # Found items
    found = await run_in_threadpool(
        lost_items_collection.count_documents,
        {"status": LostItemStatus.FOUND.value}
    )
    
    # Resolved items
    resolved = await run_in_threadpool(
        lost_items_collection.count_documents,
        {"status": LostItemStatus.RESOLVED.value}
    )
    
    # Closed items
    closed = await run_in_threadpool(
        lost_items_collection.count_documents,
        {"status": LostItemStatus.CLOSED.value}
    )
    
    # Total views
    pipeline = [
        {"$group": {
            "_id": None,
            "total_views": {"$sum": "$views_count"}
        }}
    ]
    
    views_result = await run_in_threadpool(
        lambda: list(lost_items_collection.aggregate(pipeline))
    )
    total_views = views_result[0]["total_views"] if views_result else 0
    
    return {
        "status": "ok",
        "data": {
            "total_items": total,
            "lost": lost,
            "found": found,
            "resolved": resolved,
            "closed": closed,
            "total_views": total_views
        }
    }