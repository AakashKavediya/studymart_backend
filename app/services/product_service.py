"""
==========================================================================================================
PRODUCT MODULE API ROADMAP
==========================================================================================================

No. | Method | Endpoint                              | Purpose                                      | Status
----|--------|---------------------------------------|----------------------------------------------|---------
 1  | POST   | /products                             | Create a new product                         | 🚧 Done
 2  | GET    | /products                             | Get all products (with pagination)           | 🚧 Done
 3  | GET    | /products/{product_id}                | Get a specific product by ID                 | 🚧 Done
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

"""
Importing database connection and required modules
"""
from datetime import datetime
from typing import Dict, Any, Optional

from app.mongodb.connect import connectdb
db = connectdb()
product_collection = db["products_for_sale"]
profile_collection = db["user-profile"]
follow_collection = db["follows"]

"""
Importing from FastAPI
"""
from fastapi.concurrency import run_in_threadpool
from fastapi import Depends, HTTPException, status

"""
importing required modules
"""
from bson import ObjectId

"""
importing local modules
"""
from app.utils.validators import check_follow_status
from app.utils.user import get_current_user
from app.schemas.product_schema import (
    CartCreate,
    CartItem,
    CartResponse,
    CartUpdate,
    ProductBase,
    ProductCategory,
    ProductCondition,
    ProductCreate,
    ProductReportCreate,
    ProductReportResponse,
    ProductResponse,
    ProductSearchParams,
    ProductStatsResponse,
    ProductStatus,
    ProductType,
    ProductUpdate,
    ReportReason,
)

# -------------------------
# Create a new product
# -------------------------

async def create_new_product_service(
    product_data: ProductCreate,
    current_user: dict
):
    """
    Create a new product for sale.
    
    Args:
        product_data (ProductCreate): Validated product data from request
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Response with product_id and status
    """
    
    # 1. Extract user_id from current_user
    user_id = current_user.get("_id") or current_user.get("id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Check if user has a profile
    user_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please complete your profile first."
        )
    
    # 3. Build product payload (simplified)
    payload = {
        "seller_id": ObjectId(user_id),
        
        # Basic Info
        "title": product_data.title,
        "description": product_data.description,
        
        # Category
        "category": product_data.category,
        
        # Pricing
        "price": product_data.price,
        
        # Images
        "thumbnail": str(product_data.thumbnail),
        "images": [str(img) for img in product_data.images] if product_data.images else [],
        
        # Tags
        "tags": product_data.tags,
        
        # Status
        "is_active": True,
        "is_verified": False,
        "is_featured": False,
        "status": ProductStatus.ACTIVE.value,
        
        # Seller info (cached for faster display)
        "seller_name": user_profile.get("name"),
        "seller_campus": user_profile.get("campus"),
        
        # Engagement counters
        "views_count": 0,
        "likes_count": 0,
        "saved_count": 0,
        "report_count": 0,
        
        # Timestamps
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # 4. Insert into database
    try:
        result = await run_in_threadpool(
            product_collection.insert_one,
            payload
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )
    
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )
    
    # 5. Return response
    return {
        "status": "ok",
        "message": "Product created successfully",
        "data": {
            "product_id": str(result.inserted_id),
            "title": product_data.title,
            "price": product_data.price,
            "category": product_data.category.value if hasattr(product_data.category, 'value') else product_data.category,
            "created_at": datetime.utcnow().isoformat()
        }
    }


# -------------------------
# Alternative: Manual validation without Pydantic schema
# -------------------------

async def create_new_product_service_manual(
    product_data: Dict[str, Any],
    current_user: dict
):
    """
    Create a new product with manual validation (if you don't want to use Pydantic).
    """
    
    # 1. Extract user_id
    user_id = current_user.get("_id") or current_user.get("id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Validate required fields
    required_fields = ["title", "description", "price", "category", "product_type"]
    for field in required_fields:
        if field not in product_data or not product_data[field]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} is required"
            )
    
    # 3. Validate price
    price = product_data.get("price")
    if not isinstance(price, (int, float)) or price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be a non-negative number"
        )
    
    # 4. Check if user exists
    user_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # 5. Build payload
    payload = {
        "seller_id": ObjectId(user_id),
        "title": product_data["title"],
        "description": product_data["description"],
        "short_description": product_data.get("short_description"),
        "category": product_data["category"],
        "sub_category": product_data.get("sub_category"),
        "price": price,
        "original_price": product_data.get("original_price"),
        "discount_percentage": product_data.get("discount_percentage"),
        "currency": product_data.get("currency", "INR"),
        "thumbnail": product_data.get("thumbnail"),
        "images": product_data.get("images", []),
        "product_type": product_data["product_type"],
        "tags": product_data.get("tags", []),
        "is_active": True,
        "is_verified": False,
        "is_featured": False,
        "status": "active",
        "campus": product_data.get("campus") or user_profile.get("campus"),
        "location": product_data.get("location") or user_profile.get("location"),
        "is_negotiable": product_data.get("is_negotiable", False),
        "delivery_available": product_data.get("delivery_available", False),
        "delivery_fee": product_data.get("delivery_fee"),
        "views_count": 0,
        "likes_count": 0,
        "saved_count": 0,
        "report_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # 6. Insert
    try:
        result = await run_in_threadpool(
            product_collection.insert_one,
            payload
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )
    
    return {
        "status": "ok",
        "message": "Product created successfully",
        "data": {
            "product_id": str(result.inserted_id)
        }
    }    


# -------------------------
# Get all products (with pagination)
# -------------------------

async def get_all_products_service(
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    Get all active products with pagination and sorting.
    
    Args:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 50)
        sort_by (str): Field to sort by (default: "created_at")
        sort_order (str): Sort order "asc" or "desc" (default: "desc")
    
    Returns:
        dict: Paginated products with metadata
    """
    
    # 1. Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 50:
        limit = 20
    
    # 2. Calculate skip
    skip = (page - 1) * limit
    
    # 3. Determine sort order
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    
    # 4. Query filter - only active products
    filter_query = {
        "is_active": True,
        "status": ProductStatus.ACTIVE.value
    }
    
    # 5. Get total count for pagination
    total_count = await run_in_threadpool(
        product_collection.count_documents,
        filter_query
    )
    
    # 6. Fetch products with pagination and sorting
    products_cursor = await run_in_threadpool(
        product_collection.find,
        filter_query
    )
    
    # Apply sorting
    products_cursor = products_cursor.sort(sort_by, sort_direction)
    
    # Apply pagination
    products_cursor = products_cursor.skip(skip).limit(limit)
    
    # 7. Convert cursor to list
    products_list = await run_in_threadpool(
        list,
        products_cursor
    )
    
    # 8. Convert ObjectId to string for each product
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    # 9. Calculate pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    # 10. Return response
    return {
        "status": "ok",
        "data": {
            "products": formatted_products,
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


# -------------------------
# Get a specific product by ID
# -------------------------

async def get_product_by_id_service(
    product_id: str,
    current_user: Optional[dict] = None
):
    """
    Get a specific product by its ID.
    
    Args:
        product_id (str): The ID of the product to retrieve
        current_user (Optional[dict]): Currently authenticated user (if any)
    
    Returns:
        dict: Product details if found, else raises HTTPException
    """
    
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Build query
    query = {"_id": ObjectId(product_id)}
    
    if not current_user:
        query["is_active"] = True
        query["status"] = ProductStatus.ACTIVE.value
    else:
        query["is_active"] = True
        # This requires checking if the current user is the seller
    
    # 3. Fetch product
    product = await run_in_threadpool(
        product_collection.find_one,
        query
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Convert ObjectId to string
    product["_id"] = str(product["_id"])
    product["seller_id"] = str(product["seller_id"])
    
    # 5. Check if current user is the seller
    is_owner = False
    if current_user:
        user_id = current_user.get("_id") or current_user.get("id")
        if user_id and str(user_id) == product["seller_id"]:
            is_owner = True
    
    # 6. Check follow status (if authenticated and not the seller)
    if current_user and not is_owner:
        user_id = current_user.get("_id") or current_user.get("id")
        if user_id:
            is_following = await check_follow_status(
                follower_id=user_id,
                following_id=product["seller_id"]
            )
            product["is_following_seller"] = is_following
    
    # 7. Increment view count (if not the seller viewing their own product)
    if not is_owner:
        await run_in_threadpool(
            product_collection.update_one,
            {"_id": ObjectId(product_id)},
            {"$inc": {"views_count": 1}}
        )
        # Update the view count in the response
        product["views_count"] = product.get("views_count", 0) + 1
    
    # 8. Add is_owner flag to response
    product["is_owner"] = is_owner
    
    return {
        "status": "ok",
        "data": product
    }
    
   
# -------------------------
# Edit/update a product
# -------------------------



# -------------------------
# Delete a product
# -------------------------



# -------------------------
# Update product status
# -------------------------



# -------------------------
# Get product recommendations
# -------------------------



# -------------------------
# Get product statistics
# -------------------------




# -------------------------
# Get product categories
# -------------------------



# -------------------------
# Get product types
# -------------------------



# -------------------------
# Get similar products
# -------------------------


