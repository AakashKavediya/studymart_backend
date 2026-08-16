# app/routers/lost_and_found.py

"""
LOST & FOUND MODULE API ROADMAP

No. | Method | Endpoint                                  | Purpose                                      | Status
----|--------|-------------------------------------------|----------------------------------------------|---------
 1  | POST   | /lost-and-found                           | Create a new lost item                       | ✅ Done
 2  | GET    | /lost-and-found                           | Get all lost items (with pagination)         | ✅ Done
 3  | GET    | /lost-and-found/search                    | Search lost items                            | ✅ Done
 4  | GET    | /lost-and-found/{item_id}                 | Get a specific lost item by ID               | ✅ Done
 5  | PUT    | /lost-and-found/{item_id}                 | Edit/update a lost item                      | ✅ Done
 6  | DELETE | /lost-and-found/{item_id}                 | Delete a lost item                           | ✅ Done
 7  | PATCH  | /lost-and-found/{item_id}/status          | Update item status                           | ✅ Done
 8  | POST   | /lost-and-found/{item_id}/claim           | Claim a found item                           | ✅ Done
 9  | POST   | /lost-and-found/{item_id}/comment         | Add a comment to a lost item                 | ✅ Done
10  | GET    | /lost-and-found/{item_id}/comments        | Get comments for a lost item                 | ✅ Done
11  | GET    | /lost-and-found/my-items                  | Get current user's lost items                | ✅ Done
12  | GET    | /lost-and-found/user/{user_id}            | Get items by a specific user                 | ✅ Done
13  | GET    | /lost-and-found/categories                | Get all categories with counts               | ✅ Done
14  | GET    | /lost-and-found/stats                     | Get lost & found statistics                  | ✅ Done
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import List, Optional

from app.utils.user import get_current_user
from app.schemas.lost_and_found_schema import (
    LostItemCreate,
    LostItemUpdate,
    LostItemSearchParams,
    LostItemStatus,
    LostItemType,
    CommentCreate,
    ClaimItemCreate,
)

from app.services.lost_and_found_service import (
    create_lost_item_service,
    get_all_lost_items_service,
    search_lost_items_service,
    get_lost_item_by_id_service,
    update_lost_item_service,
    delete_lost_item_service,
    update_item_status_service,
    claim_item_service,
    add_comment_service,
    get_comments_service,
    get_my_lost_items_service,
    get_user_lost_items_service,
    get_lost_item_categories_service,
    get_lost_found_stats_service,
)

router = APIRouter(prefix="/lost-and-found", tags=["Lost & Found"])


# ============================================================
# 1. CREATE LOST ITEM
# ============================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_lost_item(
    item_data: LostItemCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new lost/found item.
    
    - **title**: Item title (3-200 characters)
    - **description**: Item description (optional)
    - **type**: 'lost' or 'complaint'
    - **location**: Where it was lost/found
    - **image**: Optional image URL (Cloudinary)
    """
    return await create_lost_item_service(item_data, current_user)


# ============================================================
# 2. GET ALL LOST ITEMS (with pagination)
# ============================================================

@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_lost_items(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get all lost items with pagination and sorting.
    """
    return await get_all_lost_items_service(page, limit, sort_by, sort_order)


# ============================================================
# 3. SEARCH LOST ITEMS
# ============================================================

@router.get("/search", status_code=status.HTTP_200_OK)
async def search_lost_items(
    query: Optional[str] = Query(None, description="Search keyword"),
    type: Optional[LostItemType] = Query(None, description="Filter by type (lost/complaint)"),
    status: Optional[LostItemStatus] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Search lost items by keyword with filters.
    
    - **query**: Search term
    - **type**: 'lost' or 'complaint'
    - **status**: active, resolved, closed
    - **location**: Location filter
    """
    search_params = LostItemSearchParams(
        query=query,
        type=type,
        status=status,
        location=location,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )
    return await search_lost_items_service(search_params)


# ============================================================
# 4. GET LOST ITEM BY ID
# ============================================================

@router.get("/{item_id}", status_code=status.HTTP_200_OK)
async def get_lost_item_by_id(
    item_id: str = Path(..., description="Item ID"),
    current_user = Depends(get_current_user)
):
    """
    Get a specific lost item by its ID.
    """
    return await get_lost_item_by_id_service(item_id, current_user)


# ============================================================
# 5. UPDATE LOST ITEM
# ============================================================

@router.put("/{item_id}", status_code=status.HTTP_200_OK)
async def update_lost_item(
    item_id: str = Path(..., description="Item ID"),
    update_data: LostItemUpdate = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Update an existing lost item.
    
    Only the owner can update their own item.
    """
    return await update_lost_item_service(item_id, update_data, current_user)


# ============================================================
# 6. DELETE LOST ITEM
# ============================================================

@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
async def delete_lost_item(
    item_id: str = Path(..., description="Item ID"),
    current_user = Depends(get_current_user)
):
    """
    Delete a lost item.
    
    Only the owner can delete their own item.
    """
    return await delete_lost_item_service(item_id, current_user)


# ============================================================
# 7. UPDATE ITEM STATUS
# ============================================================

@router.patch("/{item_id}/status", status_code=status.HTTP_200_OK)
async def update_item_status(
    item_id: str = Path(..., description="Item ID"),
    status_value: LostItemStatus = Query(..., description="New status"),
    current_user = Depends(get_current_user)
):
    """
    Update item status.
    
    Available statuses:
    - **active**: Item is active
    - **resolved**: Item is resolved
    - **closed**: Item is closed
    """
    return await update_item_status_service(item_id, status_value, current_user)


# ============================================================
# 8. CLAIM ITEM
# ============================================================

@router.post("/{item_id}/claim", status_code=status.HTTP_200_OK)
async def claim_item(
    item_id: str = Path(..., description="Item ID"),
    claim_data: ClaimItemCreate = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Claim a found item.
    
    - **proof_description**: Description proving ownership
    - **contact_info**: Contact information (optional)
    """
    return await claim_item_service(claim_data, current_user)


# ============================================================
# 9. ADD COMMENT (✅ This is the missing piece!)
# ============================================================

@router.post("/{item_id}/comment", status_code=status.HTTP_200_OK)
async def add_comment(
    item_id: str = Path(..., description="Item ID"),
    comment_data: CommentCreate = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Add a comment to a lost item.
    """
    return await add_comment_service(item_id, comment_data, current_user)


# ============================================================
# 10. GET COMMENTS
# ============================================================

@router.get("/{item_id}/comments", status_code=status.HTTP_200_OK)
async def get_comments(
    item_id: str = Path(..., description="Item ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Comments per page")
):
    """
    Get comments for a lost item.
    """
    return await get_comments_service(item_id, page, limit)


# ============================================================
# 11. GET MY LOST ITEMS
# ============================================================

@router.get("/my-items", status_code=status.HTTP_200_OK)
async def get_my_lost_items(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[LostItemStatus] = Query(None, description="Filter by status"),
    current_user = Depends(get_current_user)
):
    """
    Get current user's lost items.
    """
    return await get_my_lost_items_service(current_user, page, limit, status_filter)


# ============================================================
# 12. GET ITEMS BY USER
# ============================================================

@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_lost_items(
    user_id: str = Path(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[LostItemStatus] = Query(None, description="Filter by status")
):
    """
    Get lost items by a specific user.
    """
    return await get_user_lost_items_service(user_id, page, limit, status_filter)


# ============================================================
# 13. GET CATEGORIES
# ============================================================

@router.get("/categories", status_code=status.HTTP_200_OK)
async def get_lost_item_categories():
    """
    Get all lost item categories with counts.
    """
    return await get_lost_item_categories_service()


# ============================================================
# 14. GET STATISTICS
# ============================================================

@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_lost_found_stats():
    """
    Get lost & found statistics.
    """
    return await get_lost_found_stats_service()