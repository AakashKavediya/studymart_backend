"""
==========================================================================================================
PRODUCT MODULE API ROADMAP
==========================================================================================================

No. | Method | Endpoint                              | Purpose                                      | Status
----|--------|---------------------------------------|----------------------------------------------|---------
 1  | POST   | /products                             | Create a new product                         | 🚧 Done
 2  | GET    | /products                             | Get all products (with pagination)           | 🚧 Done
 3  | GET    | /products/{product_id}                | Get a specific product by ID                 | 🚧 Done
 4  | PUT    | /products/{product_id}                | Edit/update a product                        | 🚧 Done
 5  | DELETE | /products/{product_id}                | Delete a product                             | 🚧 Done
 6  | PATCH  | /products/{product_id}/status         | Update product status                        | 🚧 Done
 7  | GET    | /products/search                      | Search products by keyword                   | 🚧 Done
 8  | GET    | /products/filter                      | Filter products                              | 🚧 Done
 9  | GET    | /products/latest                      | Get latest products                          | 🚧 Done
10  | GET    | /products/trending                    | Get trending/popular products                | 🚧 Done
11  | GET    | /products/my-products                 | Get current user's products                  | 🚧 Done
12  | GET    | /users/{user_id}/products             | Get products by specific user                | 🚧 Done
13  | GET    | /products/seller/{seller_id}          | Get products by seller                       | 🚧 Done
14  | POST   | /cart/add                             | Add product to cart                          | 🚧 Pending
15  | GET    | /cart                                 | Get user's cart                              | 🚧 Pending
16  | PUT    | /cart/update                          | Update cart item quantity                    | 🚧 Pending
17  | DELETE | /cart/remove/{product_id}             | Remove product from cart                     | 🚧 Pending
18  | DELETE | /cart/clear                           | Clear entire cart                            | 🚧 Pending
19  | POST   | /products/{product_id}/like           | Like a product                               | 🚧 Done
20  | DELETE | /products/{product_id}/like           | Unlike a product                             | 🚧 Done
21  | POST   | /products/{product_id}/save           | Save/Favorite a product                      | 🚧 Done
22  | DELETE | /products/{product_id}/save           | Remove saved product                         | 🚧 Done
23  | POST   | /products/{product_id}/view           | Increment product view count                 | 🚧 Done
24  | GET    | /products/{product_id}/similar        | Get similar products                         | 🚧 Done
25  | GET    | /products/recommendations             | Get personalized recommendations             | 🚧 Done
26  | POST   | /products/report                      | Report a product                             | 🚧 Done
27  | GET    | /products/reports                     | Get reported products (Admin)                | 🚧 Done
28  | GET    | /products/stats                       | Get product statistics                       | 🚧 Done
29  | GET    | /products/categories                  | Get all product categories                   | 🚧 Done
30  | GET    | /products/types                       | Get all product types                        | 🚧 Done

==========================================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from app.schemas.product_schema import ProductCondition, ProductCreate, ProductType
from app.services.product_service import (
    create_new_product_service,
    filter_products_service,
    get_all_products_service,
    get_latest_products_service,
    get_my_products_service,
    get_product_by_id_service,
    edit_product_service,
    delete_product_service,
    bulk_delete_products_service,
    get_product_categories_service,
    get_product_recommendations_service,
    get_product_stats_service,
    get_product_types_service,
    get_reported_products_service,
    get_similar_products_service,
    get_trending_products_service,
    increment_product_view_service,
    like_product_service,
    report_product_service,
    save_product_service,
    search_products_service,
    unlike_product_service,
    unsave_product_service,
    update_product_status_service,
    mark_product_as_sold_service,
    mark_product_as_active_service,
    mark_product_as_inactive_service,
    get_user_products_service,
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
# STATIC/SPECIAL ROUTES (Must be defined BEFORE /{product_id})
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


@router.get("/search", status_code=status.HTTP_200_OK)
async def search_products(
    query: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, gt=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, gt=0, description="Maximum price"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Search products by keyword with filters.
    
    - **query**: Search term (searches title and description)
    - **category**: Filter by product category
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **sort_by**: Field to sort by
    - **sort_order**: Sort order (asc/desc)
    """
    search_params = ProductSearchParams(
        query=query,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )
    return await search_products_service(search_params)


@router.get("/filter", status_code=status.HTTP_200_OK)
async def filter_products(
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    product_type: Optional[ProductType] = Query(None, description="Filter by product type"),
    min_price: Optional[float] = Query(None, gt=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, gt=0, description="Maximum price"),
    campus: Optional[str] = Query(None, description="Filter by seller campus"),
    condition: Optional[ProductCondition] = Query(None, description="Product condition"),
    is_verified: Optional[bool] = Query(None, description="Only verified products"),
    is_featured: Optional[bool] = Query(None, description="Only featured products"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Filter products by multiple criteria.
    """
    return await filter_products_service(
        category=category,
        product_type=product_type,
        min_price=min_price,
        max_price=max_price,
        campus=campus,
        condition=condition,
        is_verified=is_verified,
        is_featured=is_featured,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/latest", status_code=status.HTTP_200_OK)
async def get_latest_products(
    limit: int = Query(20, ge=1, le=50, description="Number of products to return")
):
    """
    Get the latest products added to the platform.
    """
    return await get_latest_products_service(limit)


@router.get("/trending", status_code=status.HTTP_200_OK)
async def get_trending_products(
    limit: int = Query(20, ge=1, le=50, description="Number of products to return"),
    time_period: str = Query("week", pattern="^(day|week|month)$", description="Time period for trending calculation")
):
    """
    Get trending products based on engagement (views, likes, saves).
    
    - **time_period**: day, week, or month
    """
    return await get_trending_products_service(limit, time_period)


@router.get("/my-products", status_code=status.HTTP_200_OK)
async def get_my_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[ProductStatus] = Query(None, description="Filter by status"),
    current_user = Depends(get_current_user)
):
    """
    Get current user's products.
    
    - **status_filter**: Filter by product status (active, sold, inactive)
    """
    return await get_my_products_service(current_user, page, limit, status_filter)


@router.get("/categories", status_code=status.HTTP_200_OK)
async def get_product_categories():
    """
    Get all product categories with product counts.
    """
    return await get_product_categories_service()


@router.get("/types", status_code=status.HTTP_200_OK)
async def get_product_types():
    """
    Get all product types with product counts.
    """
    return await get_product_types_service()


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_product_stats(
    current_user = Depends(get_current_user)
):
    """
    Get product statistics for the current user.
    """
    return await get_product_stats_service(current_user)


@router.get("/recommendations", status_code=status.HTTP_200_OK)
async def get_product_recommendations(
    limit: int = Query(20, ge=1, le=50, description="Number of recommendations"),
    current_user = Depends(get_current_user)
):
    """
    Get personalized product recommendations based on user activity.
    """
    return await get_product_recommendations_service(current_user, limit)


@router.get("/reports", status_code=status.HTTP_200_OK)
async def get_reported_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, resolved, rejected)"),
    current_user = Depends(get_current_user)
):
    """
    Get all reported products (Admin only).
    """
    return await get_reported_products_service(current_user, page, limit, status_filter)


@router.post("/report", status_code=status.HTTP_200_OK)
async def report_product(
    report_data: ProductReportCreate,
    current_user = Depends(get_current_user)
):
    """
    Report a product for violation.
    
    Reasons: spam, scam, fake, copyright, wrong_category, inappropriate, other
    """
    return await report_product_service(report_data, current_user)

# ============================================================
# DYNAMIC ROUTES (Must be defined AFTER static routes)
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


@router.patch("/{product_id}/active", status_code=status.HTTP_200_OK)
async def mark_as_active(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Mark a product as active (available for sale).
    """
    return await mark_product_as_active_service(product_id, current_user)


@router.patch("/{product_id}/inactive", status_code=status.HTTP_200_OK)
async def mark_as_inactive(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Mark a product as inactive (temporarily unavailable).
    """
    return await mark_product_as_inactive_service(product_id, current_user)


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


@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_products(
    user_id: str = Path(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[ProductStatus] = Query(None, description="Filter by status")
):
    """
    Get products by a specific user.
    
    Only active products are shown by default.
    """
    return await get_user_products_service(user_id, page, limit, status_filter)


@router.get("/seller/{seller_id}", status_code=status.HTTP_200_OK)
async def get_seller_products(
    seller_id: str = Path(..., description="Seller ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    status_filter: Optional[ProductStatus] = Query(None, description="Filter by status")
):
    """
    Get products by a specific seller (alias for /user/{user_id}).
    """
    return await get_user_products_service(seller_id, page, limit, status_filter)


@router.get("/{product_id}/similar", status_code=status.HTTP_200_OK)
async def get_similar_products(
    product_id: str = Path(..., description="Product ID"),
    limit: int = Query(10, ge=1, le=20, description="Number of similar products to return")
):
    """
    Get similar products based on category and tags.
    """
    return await get_similar_products_service(product_id, limit)


@router.post("/{product_id}/like", status_code=status.HTTP_200_OK)
async def like_product(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Like a product.
    """
    return await like_product_service(product_id, current_user)


@router.delete("/{product_id}/like", status_code=status.HTTP_200_OK)
async def unlike_product(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Unlike a product.
    """
    return await unlike_product_service(product_id, current_user)


@router.post("/{product_id}/save", status_code=status.HTTP_200_OK)
async def save_product(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Save/favorite a product.
    """
    return await save_product_service(product_id, current_user)


@router.delete("/{product_id}/save", status_code=status.HTTP_200_OK)
async def unsave_product(
    product_id: str = Path(..., description="Product ID"),
    current_user = Depends(get_current_user)
):
    """
    Remove a saved/favorited product.
    """
    return await unsave_product_service(product_id, current_user)


@router.post("/{product_id}/view", status_code=status.HTTP_200_OK)
async def increment_product_view(
    product_id: str = Path(..., description="Product ID")
):
    """
    Increment product view count.
    """
    return await increment_product_view_service(product_id)