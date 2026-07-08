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
    product_data: ProductCreate,  # Use Pydantic schema for validation
    current_user: dict  # Receive user from route, NOT Depends
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
    
    # 2. Check if user has a profile (optional but recommended)
    user_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please complete your profile first."
        )
    
    # 3. Build product payload
    payload = {
        "seller_id": ObjectId(user_id),
        "title": product_data.title,
        "description": product_data.description,
        "short_description": product_data.short_description,
        
        # Category
        "category": product_data.category,
        "sub_category": product_data.sub_category,
        
        # Pricing
        "price": product_data.price,
        "original_price": product_data.original_price,
        "discount_percentage": product_data.discount_percentage,
        "currency": product_data.currency,
        
        # Images
        "thumbnail": product_data.thumbnail,
        "images": product_data.images,
        
        # Product Type
        "product_type": product_data.product_type,
        
        # Tags
        "tags": product_data.tags,
        
        # Status
        "is_active": True,
        "is_verified": False,
        "is_featured": False,
        "status": ProductStatus.ACTIVE,  # ✅ Use enum
        
        # Location
        "campus": product_data.campus or user_profile.get("campus"),
        "location": product_data.location or user_profile.get("location"),
        
        # Negotiable
        "is_negotiable": product_data.is_negotiable,
        
        # Delivery
        "delivery_available": product_data.delivery_available,
        "delivery_fee": product_data.delivery_fee,
        
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
            "category": product_data.category,
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



# -------------------------
# Get a specific product by ID
# -------------------------



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


