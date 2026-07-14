"""
==========================================================================================================
PRODUCT MODULE API ROADMAP
==========================================================================================================

No. | Method | Endpoint                              | Purpose                                      | Status
----|--------|---------------------------------------|----------------------------------------------|---------
 1  | POST   | /products                             | Create a new product                         | 🚧 Pending
 2  | GET    | /products                             | Get all products (with pagination)           | 🚧 Pending
 3  | GET    | /products/{product_id}                | Get a specific product by ID                 | 🚧 Pending
 4  | PUT    | /products/{product_id}                | Edit/update a product                        | 🚧 Pending
 5  | DELETE | /products/{product_id}                | Delete a product                             | 🚧 Pending
 6  | PATCH  | /products/{product_id}/status         | Update product status                        | 🚧 Pending
 7  | GET    | /products/search                      | Search products by keyword                   | 🚧 Pending
 8  | GET    | /products/filter                      | Filter products                              | 🚧 Pending
 9  | GET    | /products/latest                      | Get latest products                          | 🚧 Pending
10  | GET    | /products/trending                    | Get trending/popular products                | 🚧 Pending
11  | GET    | /products/my-products                 | Get current user's products                  | 🚧 Pending
12  | GET    | /users/{user_id}/products             | Get products by specific user                | 🚧 Pending
13  | GET    | /products/seller/{seller_id}          | Get products by seller                       | 🚧 Pending
14  | POST   | /cart/add                             | Add product to cart                          | 🚧 Pending
15  | GET    | /cart                                 | Get user's cart                              | 🚧 Pending
16  | PUT    | /cart/update                          | Update cart item quantity                    | 🚧 Pending
17  | DELETE | /cart/remove/{product_id}             | Remove product from cart                     | 🚧 Pending
18  | DELETE | /cart/clear                           | Clear entire cart                            | 🚧 Pending
19  | POST   | /products/{product_id}/like           | Like a product                               | 🚧 Pending
20  | DELETE | /products/{product_id}/like           | Unlike a product                             | 🚧 Pending
21  | POST   | /products/{product_id}/save           | Save/Favorite a product                      | 🚧 Pending
22  | DELETE | /products/{product_id}/save           | Remove saved product                         | 🚧 Pending
23  | POST   | /products/{product_id}/view           | Increment product view count                 | 🚧 Pending
24  | GET    | /products/{product_id}/similar        | Get similar products                         | 🚧 Pending
25  | GET    | /products/recommendations             | Get personalized recommendations             | 🚧 Pending
26  | POST   | /products/report                      | Report a product                             | 🚧 Pending
27  | GET    | /products/reports                     | Get reported products (Admin)                | 🚧 Pending
28  | GET    | /products/stats                       | Get product statistics                       | 🚧 Pending
29  | GET    | /products/categories                  | Get all product categories                   | 🚧 Pending
30  | GET    | /products/types                       | Get all product types                        | 🚧 Pending

==========================================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from app.schemas.product_schema import ProductCreate
from app.services.product_service import (
    create_new_product_service,
    get_all_products_service,
    get_product_by_id_service,
    edit_product_service,
    delete_product_service,
    bulk_delete_products_service,
    update_product_status_service,
    mark_product_as_sold_service,
    mark_product_as_active_service,
    mark_product_as_inactive_service,
)

# ====================
# Importing Schemas
# ====================

from app.schemas.product_schema import (
    ProductCreate,
    ProductUpdate,      
    ProductStatus,      
    ProductCategory,
    ProductSearchParams,
    ProductReportCreate,
)

# ====================
# Import local modules
# ====================
from app.utils.user import get_current_user


# ====================
# Import modules and dependencies
# ====================

from typing import List, Optional
from bson import ObjectId


router = APIRouter(prefix="/products", tags=["Products"])

# ============================================================
# 1. CREATE PRODUCT
# ============================================================

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new product listing.
    
    - **title**: Product title (3-200 characters)
    - **description**: Product description (min 10 characters)
    - **category**: Product category (notes, books, lab, etc.)
    - **price**: Product price (must be > 0)
    - **thumbnail**: Product thumbnail image URL (required)
    - **images**: Additional product images (max 4)
    - **tags**: Product tags for better searchability
    """
    return await create_new_product_service(product_data, current_user)


# ============================================================
# 2. GET ALL PRODUCTS (with pagination)
# ============================================================

@router.get("/get_all_products", status_code=status.HTTP_200_OK)
async def get_all_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get all active products with pagination and sorting.
    """
    return await get_all_products_service(page, limit, sort_by, sort_order)


# ============================================================
# 3. GET PRODUCT BY ID
# ============================================================

@router.get("/{product_id}", status_code=status.HTTP_200_OK)
async def get_product_by_id(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Get a specific product by its ID.
    """
    return await get_product_by_id_service(product_id, current_user)


# ============================================================
# 4. EDIT/UPDATE PRODUCT
# ============================================================

@router.put("/{product_id}", status_code=status.HTTP_200_OK)
async def edit_product(
    product_id: str = Path(..., description="Product ID"),
    update_data: ProductUpdate = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Edit/update a product.
    
    Only the seller can edit their own product.
    """
    return await edit_product_service(product_id, update_data, current_user)


# ============================================================
# 5. DELETE PRODUCT
# ============================================================

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: str = Path(..., description="Product ID"),
    permanent: bool = Query(False, description="Permanently delete from database"),
    current_user = Depends(get_current_user)
):
    """
    Delete a product.
    
    - **Soft delete** (default): Marks product as inactive
    - **Permanent delete**: Removes from database (use with caution)
    """
    return await delete_product_service(product_id, current_user, permanent)


# ============================================================
# 6. UPDATE PRODUCT STATUS
# ============================================================

@router.patch("/{product_id}/status", status_code=status.HTTP_200_OK)
async def update_product_status(
    product_id: str = Path(..., description="Product ID"),
    status_value: ProductStatus = Query(..., description="New status"),
    current_user = Depends(get_current_user)
):
    """
    Update product status.
    
    Available statuses:
    - **active**: Product is available for sale
    - **sold**: Product has been sold
    - **inactive**: Product is temporarily unavailable
    """
    return await update_product_status_service(product_id, status_value, current_user)


# ============================================================
# 7. MARK PRODUCT AS SOLD
# ============================================================

@router.patch("/{product_id}/sold", status_code=status.HTTP_200_OK)
async def mark_as_sold(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Mark a product as sold.
    
    This is a convenience endpoint for `status=sold`.
    """
    return await mark_product_as_sold_service(product_id, current_user)


# ============================================================
# 8. MARK PRODUCT AS ACTIVE
# ============================================================

@router.patch("/{product_id}/active", status_code=status.HTTP_200_OK)
async def mark_as_active(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Mark a product as active (available for sale).
    """
    return await mark_product_as_active_service(product_id, current_user)


# ============================================================
# 9. MARK PRODUCT AS INACTIVE
# ============================================================

@router.patch("/{product_id}/inactive", status_code=status.HTTP_200_OK)
async def mark_as_inactive(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Mark a product as inactive (temporarily unavailable).
    """
    return await mark_product_as_inactive_service(product_id, current_user)


# ============================================================
# 10. BULK DELETE PRODUCTS
# ============================================================

@router.delete("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_products(
    product_ids: List[str] = Query(..., description="List of product IDs to delete"),
    permanent: bool = Query(False, description="Permanently delete from database"),
    current_user = Depends(get_current_user)
):
    """
    Delete multiple products at once.
    
    Only the seller can delete their own products.
    """
    return await bulk_delete_products_service(product_ids, current_user, permanent)


# ============================================================
# 11. GET MY PRODUCTS (Current User's Products)
# ============================================================

# @router.get("/my-products", status_code=status.HTTP_200_OK)
# async def get_my_products(
#     page: int = Query(1, ge=1, description="Page number"),
#     limit: int = Query(20, ge=1, le=50, description="Items per page"),
#     status_filter: Optional[ProductStatus] = Query(None, description="Filter by status"),
#     current_user = Depends(get_current_user)
# ):
#     """
#     Get current user's products.
    
#     - **page**: Page number
#     - **limit**: Items per page
#     - **status_filter**: Filter by product status (active, sold, inactive)
#     """
#     return await get_user_products_service(
#         user_id=current_user.get("_id"),
#         page=page,
#         limit=limit,
#         status_filter=status_filter,
#         current_user=current_user
#     )


# ============================================================
# 12. GET PRODUCTS BY USER ID
# ============================================================




# ============================================================
# 13. SEARCH PRODUCTS
# ============================================================




# ============================================================
# 14. FILTER PRODUCTS
# ============================================================



# ============================================================
# 15. GET LATEST PRODUCTS
# ============================================================



# ============================================================
# 16. GET TRENDING PRODUCTS
# ============================================================



# ============================================================
# 17. GET PRODUCT CATEGORIES
# ============================================================


# ============================================================
# 18. GET PRODUCT TYPES
# ============================================================



# ============================================================
# 19. GET SIMILAR PRODUCTS
# ============================================================



# ============================================================
# 20. LIKE PRODUCT
# ============================================================



# ============================================================
# 21. UNLIKE PRODUCT
# ============================================================




# ============================================================
# 22. SAVE PRODUCT
# ============================================================


# ============================================================
# 23. UNSAVE PRODUCT
# ============================================================


# ============================================================
# 24. INCREMENT VIEW COUNT
# ============================================================




# ============================================================
# 25. REPORT PRODUCT
# ============================================================


# ============================================================
# 26. GET PRODUCT STATISTICS
# ============================================================

