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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.mongodb.connect import connectdb
db = connectdb()
product_collection = db["products_for_sale"]
profile_collection = db["user-profile"]
follow_collection = db["follows"]
signup_collection = db["signup"]

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
    """
    
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Fetch product with proper typing
    product = await run_in_threadpool(
        product_collection.find_one,
        {
            "_id": ObjectId(product_id),
            "is_active": True,
            "status": ProductStatus.ACTIVE.value
        }
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 3. Format response
    response_data = {
        "id": str(product["_id"]),
        "seller_id": str(product["seller_id"]),
        "title": product.get("title"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "thumbnail": product.get("thumbnail"),
        "images": product.get("images", []),
        "tags": product.get("tags", []),
        "is_active": product.get("is_active", True),
        "is_verified": product.get("is_verified", False),
        "is_featured": product.get("is_featured", False),
        "status": product.get("status"),
        "seller_name": product.get("seller_name"),
        "seller_campus": product.get("seller_campus"),
        "views_count": product.get("views_count", 0) + 1,  # Increment for response
        "likes_count": product.get("likes_count", 0),
        "saved_count": product.get("saved_count", 0),
        "report_count": product.get("report_count", 0),
        "created_at": product.get("created_at"),
        "updated_at": product.get("updated_at"),
    }
    
    # 4. Check if current user is the seller
    is_owner = False
    if current_user:
        user_id = current_user.get("_id") or current_user.get("id")
        if user_id and str(user_id) == str(product["_id"]):
            is_owner = True
    
    response_data["is_owner"] = is_owner
    
    # 5. Check follow status (if authenticated and not the seller)
    if current_user and not is_owner:
        user_id = current_user.get("_id") or current_user.get("id")
        if user_id:
            try:
                is_following = await check_follow_status(
                    follower_id=user_id,
                    following_id=str(product["_id"])
                )
                response_data["is_following_seller"] = is_following
            except Exception:
                response_data["is_following_seller"] = False
    
    # 6. Increment view count in database (fire and forget)
    # Don't await - let it run in background to not slow down response
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$inc": {"views_count": 1}}
    )
    
    return {
        "status": "ok",
        "data": response_data
    }
   
# -------------------------
# Edit/update a product
# -------------------------

async def edit_product_service(
    product_id: str,
    update_data: ProductUpdate,
    current_user: dict
):
    """
    Edit/update an existing product.
    
    Args:
        product_id (str): The ID of the product to update
        update_data (ProductUpdate): The data to update
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Updated product details
    """
    
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,  # ✅ Correct usage
            detail="Invalid product ID format"
        )
    
    # 2. Check if product exists and user is the owner
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # ✅ Correct usage
            detail="Product not found"
        )
    
    # 3. Check if current user is the seller/owner
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # ✅ Correct usage
            detail="User not authenticated"
        )
    
    seller_id = product.get("seller_id")
    if str(user_id) != str(seller_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # ✅ Correct usage
            detail="You are not authorized to edit this product"
        )
    
    # 4. Prepare update data (exclude unset fields)
    update_dict = update_data.dict(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,  # ✅ Correct usage
            detail="No fields to update"
        )
    
    # 5. Add updated_at timestamp
    update_dict["updated_at"] = datetime.utcnow()
    
    # 6. Update the product
    result = await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # ✅ Correct usage
            detail="Product not found"
        )
    
    # 7. Fetch updated product
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    # 8. Format response
    if updated_product:
        updated_product["_id"] = str(updated_product["_id"])
        updated_product["seller_id"] = str(updated_product["seller_id"])
    
    return {
        "status": "ok",
        "message": "Product updated successfully",
        "data": updated_product
    }



# -------------------------
# Delete a product
# -------------------------

async def delete_product_service(
    product_id: str,
    current_user: dict,
    permanent: bool = False
):
    """
    Delete a product.
    
    Args:
        product_id (str): The ID of the product to delete
        current_user (dict): Currently authenticated user
        permanent (bool): If True, permanently delete from database. 
                         If False, soft delete (mark as inactive).
    
    Returns:
        dict: Success message
    """
    
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 3. Check if current user is the seller/owner
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    seller_id = product.get("seller_id")
    if str(user_id) != str(seller_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this product"
        )
    
    # 4. Delete the product
    if permanent:
        # Permanent delete - remove from database
        result = await run_in_threadpool(
            product_collection.delete_one,
            {"_id": ObjectId(product_id)}
        )
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return {
            "status": "ok",
            "message": "Product permanently deleted successfully",
            "data": {
                "product_id": product_id,
                "deleted": True
            }
        }
    else:
        # Soft delete - mark as inactive
        result = await run_in_threadpool(
            product_collection.update_one,
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "is_active": False,
                    "status": "inactive",
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return {
            "status": "ok",
            "message": "Product deleted successfully",
            "data": {
                "product_id": product_id,
                "deleted": True,
                "soft_delete": True
            }
        }


# -------------------------
# Bulk delete products
# -------------------------

async def bulk_delete_products_service(
    product_ids: list,
    current_user: dict,
    permanent: bool = False
):
    """
    Delete multiple products at once.
    
    Args:
        product_ids (list): List of product IDs to delete
        current_user (dict): Currently authenticated user
        permanent (bool): If True, permanently delete from database.
    
    Returns:
        dict: Success message with counts
    """
    
    if not product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No product IDs provided"
        )
    
    # 1. Validate all ObjectIds
    valid_ids = []
    for pid in product_ids:
        if ObjectId.is_valid(pid):
            valid_ids.append(ObjectId(pid))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product ID format: {pid}"
            )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if all products belong to the user
    products = await run_in_threadpool(
        lambda: list(
            product_collection.find({
                "_id": {"$in": valid_ids}
            })
        )
    )
    
    # Check if all products exist
    if len(products) != len(valid_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more products not found"
        )
    
    # Check ownership for all products
    for product in products:
        if str(product.get("seller_id")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You are not authorized to delete product: {product.get('_id')}"
            )
    
    # 4. Delete products
    if permanent:
        result = await run_in_threadpool(
            product_collection.delete_many,
            {"_id": {"$in": valid_ids}}
        )
        
        return {
            "status": "ok",
            "message": f"{result.deleted_count} products permanently deleted successfully",
            "data": {
                "deleted_count": result.deleted_count,
                "product_ids": product_ids
            }
        }
    else:
        result = await run_in_threadpool(
            product_collection.update_many,
            {"_id": {"$in": valid_ids}},
            {
                "$set": {
                    "is_active": False,
                    "status": "inactive",
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "status": "ok",
            "message": f"{result.modified_count} products deleted successfully",
            "data": {
                "deleted_count": result.modified_count,
                "product_ids": product_ids,
                "soft_delete": True
            }
        }

# -------------------------
# Update product status
# -------------------------

async def update_product_status_service(
    product_id: str,
    status_value: ProductStatus,
    current_user: dict
):
    """
    Update the status of a product.
    
    Args:
        product_id (str): The ID of the product to update
        status_value (ProductStatus): New status (active, sold, inactive)
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Updated product details
    """
    
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 3. Check if current user is the seller/owner
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    seller_id = product.get("seller_id")
    if str(user_id) != str(seller_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this product"
        )
    
    # 4. Prepare update data
    update_dict = {
        "status": status_value.value,
        "updated_at": datetime.utcnow()
    }
    
    # 5. Update is_active based on status
    if status_value == ProductStatus.ACTIVE:
        update_dict["is_active"] = True
    elif status_value == ProductStatus.SOLD:
        update_dict["is_active"] = False
        # Add sold_at timestamp if needed
        update_dict["sold_at"] = datetime.utcnow()
    elif status_value == ProductStatus.INACTIVE:
        update_dict["is_active"] = False
    
    # 6. Update the product
    result = await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 7. Fetch updated product
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    # 8. Format response
    if updated_product:
        updated_product["_id"] = str(updated_product["_id"])
        updated_product["seller_id"] = str(updated_product["seller_id"])
    
    return {
        "status": "ok",
        "message": f"Product status updated to {status_value.value}",
        "data": updated_product
    }


# -------------------------
# Mark product as sold
# -------------------------

async def mark_product_as_sold_service(
    product_id: str,
    current_user: dict
):
    """
    Mark a product as sold.
    
    Args:
        product_id (str): The ID of the product to mark as sold
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Updated product details
    """
    return await update_product_status_service(
        product_id=product_id,
        status_value=ProductStatus.SOLD,
        current_user=current_user
    )


# -------------------------
# Mark product as active
# -------------------------

async def mark_product_as_active_service(
    product_id: str,
    current_user: dict
):
    """
    Mark a product as active (available for sale).
    
    Args:
        product_id (str): The ID of the product to mark as active
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Updated product details
    """
    return await update_product_status_service(
        product_id=product_id,
        status_value=ProductStatus.ACTIVE,
        current_user=current_user
    )


# -------------------------
# Mark product as inactive
# -------------------------

async def mark_product_as_inactive_service(
    product_id: str,
    current_user: dict
):
    """
    Mark a product as inactive (temporarily unavailable).
    
    Args:
        product_id (str): The ID of the product to mark as inactive
        current_user (dict): Currently authenticated user
    
    Returns:
        dict: Updated product details
    """
    return await update_product_status_service(
        product_id=product_id,
        status_value=ProductStatus.INACTIVE,
        current_user=current_user
    )



# In app/services/product_service.py - Replace the existing search_products_service

async def search_products_service(
    search_params: ProductSearchParams
):
    """
    Search products by keyword with filters.
    Uses $text if index exists, otherwise falls back to regex.
    """
    # 1. Build search query
    query = {}
    
    # 2. Search logic with fallback
    if search_params.query:
        # SAFE FALLBACK: Use regex (no index required)
        # This guarantees it won't crash if the text index is missing
        query["$or"] = [
            {"title": {"$regex": search_params.query, "$options": "i"}},
            {"description": {"$regex": search_params.query, "$options": "i"}}
        ]
    
    # Category filter
    if search_params.category:
        query["category"] = search_params.category.value if hasattr(search_params.category, 'value') else search_params.category
    
    # Price range filter
    price_filter = {}
    if search_params.min_price is not None:
        price_filter["$gte"] = search_params.min_price
    if search_params.max_price is not None:
        price_filter["$lte"] = search_params.max_price
    if price_filter:
        query["price"] = price_filter
    
    # Only active products
    query["is_active"] = True
    query["status"] = ProductStatus.ACTIVE.value
    
    # 2. Calculate pagination
    skip = (search_params.page - 1) * search_params.limit
    
    # 3. Determine sort order
    sort_direction = -1 if search_params.sort_order.lower() == "desc" else 1
    sort_field = search_params.sort_by
    
    # 4. Get total count
    total_count = await run_in_threadpool(
        product_collection.count_documents,
        query
    )
    
    # 5. Fetch products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort(sort_field, sort_direction)
    cursor = cursor.skip(skip).limit(search_params.limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 6. Format products
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    # 7. Pagination metadata
    total_pages = (total_count + search_params.limit - 1) // search_params.limit if total_count > 0 else 1
    
    # 8. Return response
    return {
        "status": "ok",
        "data": {
            "products": formatted_products,
            "pagination": {
                "current_page": search_params.page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": search_params.limit,
                "has_next": search_params.page < total_pages,
                "has_previous": search_params.page > 1
            },
            "search_query": search_params.query,
            "filters": {
                "category": search_params.category,
                "min_price": search_params.min_price,
                "max_price": search_params.max_price
            }
        }
    }




# Add to product_service.py - Filter products

async def filter_products_service(
    category: Optional[ProductCategory] = None,
    product_type: Optional[ProductType] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    campus: Optional[str] = None,
    condition: Optional[ProductCondition] = None,
    is_verified: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    Filter products by multiple criteria.
    """
    # 1. Build filter query
    query = {"is_active": True, "status": ProductStatus.ACTIVE.value}
    
    # Category filter
    if category:
        query["category"] = category.value if hasattr(category, 'value') else category
    
    # Product type filter
    if product_type:
        query["product_type"] = product_type.value if hasattr(product_type, 'value') else product_type
    
    # Campus filter
    if campus:
        query["seller_campus"] = campus
    
    # Condition filter
    if condition:
        query["condition"] = condition.value if hasattr(condition, 'value') else condition
    
    # Verified/Featured filters
    if is_verified is not None:
        query["is_verified"] = is_verified
    if is_featured is not None:
        query["is_featured"] = is_featured
    
    # Price range filter
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter
    
    # 2. Calculate pagination
    skip = (page - 1) * limit
    
    # 3. Sort
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    
    # 4. Get total count
    total_count = await run_in_threadpool(
        product_collection.count_documents,
        query
    )
    
    # 5. Fetch products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort(sort_by, sort_direction)
    cursor = cursor.skip(skip).limit(limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 6. Format
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    # 7. Pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
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
            "filters_applied": {
                "category": category,
                "product_type": product_type,
                "campus": campus,
                "condition": condition,
                "min_price": min_price,
                "max_price": max_price,
                "is_verified": is_verified,
                "is_featured": is_featured
            }
        }
    }






# Add to product_service.py - Latest products

async def get_latest_products_service(
    limit: int = 20
):
    """
    Get the latest products added.
    """
    # 1. Query for active products, sorted by creation date (newest first)
    query = {
        "is_active": True,
        "status": ProductStatus.ACTIVE.value
    }
    
    # 2. Fetch products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).limit(limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 3. Format
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    return {
        "status": "ok",
        "data": {
            "products": formatted_products,
            "count": len(formatted_products),
            "limit": limit
        }
    }







# Add to product_service.py - Trending products

async def get_trending_products_service(
    limit: int = 20,
    time_period: str = "week"  # day, week, month
):
    """
    Get trending products based on engagement (views + likes + saves).
    """
    # 1. Calculate time threshold
    now = datetime.utcnow()
    if time_period == "day":
        threshold = now - timedelta(days=1)
    elif time_period == "week":
        threshold = now - timedelta(days=7)
    elif time_period == "month":
        threshold = now - timedelta(days=30)
    else:
        threshold = now - timedelta(days=7)  # default: week
    
    # 2. Query active products with engagement metrics
    query = {
        "is_active": True,
        "status": ProductStatus.ACTIVE.value,
        "created_at": {"$gte": threshold}  # Only recent products
    }
    
    # 3. Calculate trending score: views + (likes * 2) + (saves * 3)
    # We'll sort by engagement in the query
    pipeline = [
        {"$match": query},
        {
            "$addFields": {
                "trending_score": {
                    "$add": [
                        "$views_count",
                        {"$multiply": ["$likes_count", 2]},
                        {"$multiply": ["$saved_count", 3]}
                    ]
                }
            }
        },
        {"$sort": {"trending_score": -1}},
        {"$limit": limit}
    ]
    
    # 4. Execute aggregation
    products_list = await run_in_threadpool(
        lambda: list(product_collection.aggregate(pipeline))
    )
    
    # 5. Format
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    return {
        "status": "ok",
        "data": {
            "products": formatted_products,
            "count": len(formatted_products),
            "time_period": time_period,
            "limit": limit
        }
    }






# Add to product_service.py - My products

async def get_my_products_service(
    current_user: dict,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[ProductStatus] = None
):
    """
    Get current user's products.
    """
    # 1. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Build query
    query: Dict[str, Any] = {"seller_id": ObjectId(user_id)}
    
    # Status filter
    if status_filter:
        query["status"] = status_filter.value if hasattr(status_filter, 'value') else status_filter
    
    # 3. Pagination
    skip = (page - 1) * limit
    
    # 4. Get total count
    total_count = await run_in_threadpool(
        product_collection.count_documents,
        query
    )
    
    # 5. Fetch products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 6. Format
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    # 7. Pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
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
            "status_filter": status_filter
        }
    }








# Add to product_service.py - User products

async def get_user_products_service(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[ProductStatus] = None
):
    """
    Get products by a specific user.
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
    
    # 3. Build query - only show active products for public view
    query = {
        "seller_id": ObjectId(user_id),
        "is_active": True,
        "status": ProductStatus.ACTIVE.value
    }
    
    # Status filter (overrides default)
    if status_filter:
        query["status"] = status_filter.value if hasattr(status_filter, 'value') else status_filter
    
    # 4. Pagination
    skip = (page - 1) * limit
    
    # 5. Get total count
    total_count = await run_in_threadpool(
        product_collection.count_documents,
        query
    )
    
    # 6. Fetch products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 7. Format
    formatted_products = []
    for product in products_list:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    # 8. Pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "user_id": user_id,
            "user_name": user.get("name"),
            "products": formatted_products,
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






# Add to product_service.py - Categories

async def get_product_categories_service():
    """
    Get all product categories with product counts.
    """
    # 1. Aggregate categories with counts
    pipeline = [
        {"$match": {"is_active": True, "status": ProductStatus.ACTIVE.value}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    categories = await run_in_threadpool(
        lambda: list(product_collection.aggregate(pipeline))
    )
    
    # 2. Format categories
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









# Add to product_service.py - Types

async def get_product_types_service():
    """
    Get all product types with product counts.
    """
    # 1. Aggregate types with counts
    pipeline = [
        {"$match": {"is_active": True, "status": ProductStatus.ACTIVE.value}},
        {"$group": {
            "_id": "$product_type",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    types = await run_in_threadpool(
        lambda: list(product_collection.aggregate(pipeline))
    )
    
    # 2. Format types
    formatted_types = []
    for t in types:
        formatted_types.append({
            "name": t["_id"],
            "count": t["count"]
        })
    
    return {
        "status": "ok",
        "data": {
            "types": formatted_types,
            "total": len(formatted_types)
        }
    }








# Add to product_service.py - Similar products

async def get_similar_products_service(
    product_id: str,
    limit: int = 10
):
    """
    Get similar products based on category and tags.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get the product
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 3. Build similar products query
    # Find products with same category OR overlapping tags
    category = product.get("category")
    tags = product.get("tags", [])
    
    query = {
        "_id": {"$ne": ObjectId(product_id)},  # Exclude current product
        "is_active": True,
        "status": ProductStatus.ACTIVE.value,
        "$or": [
            {"category": category},
            {"tags": {"$in": tags}}
        ]
    }
    
    # 4. Fetch similar products
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.limit(limit)
    
    products_list = await run_in_threadpool(list, cursor)
    
    # 5. Format
    formatted_products = []
    for prod in products_list:
        prod["_id"] = str(prod["_id"])
        prod["seller_id"] = str(prod["seller_id"])
        formatted_products.append(prod)
    
    return {
        "status": "ok",
        "data": {
            "product_id": product_id,
            "similar_products": formatted_products,
            "count": len(formatted_products),
            "limit": limit
        }
    }







# Add to product_service.py - Product statistics

async def get_product_stats_service(
    current_user: dict
):
    """
    Get product statistics for the current user.
    """
    # 1. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 2. Build pipeline for stats
    pipeline = [
        {"$match": {"seller_id": ObjectId(user_id)}},
        {"$group": {
            "_id": None,
            "total_products": {"$sum": 1},
            "active_products": {
                "$sum": {"$cond": [{"$eq": ["$status", ProductStatus.ACTIVE.value]}, 1, 0]}
            },
            "sold_products": {
                "$sum": {"$cond": [{"$eq": ["$status", ProductStatus.SOLD.value]}, 1, 0]}
            },
            "inactive_products": {
                "$sum": {"$cond": [{"$eq": ["$status", ProductStatus.INACTIVE.value]}, 1, 0]}
            },
            "total_views": {"$sum": "$views_count"},
            "total_likes": {"$sum": "$likes_count"},
            "total_saves": {"$sum": "$saved_count"},
            "total_revenue": {
                "$sum": {"$cond": [{"$eq": ["$status", ProductStatus.SOLD.value]}, "$price", 0]}
            }
        }}
    ]
    
    # 3. Execute aggregation
    stats = await run_in_threadpool(
        lambda: list(product_collection.aggregate(pipeline))
    )
    
    if not stats:
        # No products yet
        return {
            "status": "ok",
            "data": {
                "total_products": 0,
                "active_products": 0,
                "sold_products": 0,
                "inactive_products": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_saves": 0,
                "total_revenue": 0
            }
        }
    
    # 4. Format response
    stats_data = stats[0]
    del stats_data["_id"]  # Remove _id field
    
    return {
        "status": "ok",
        "data": stats_data
    }





# Add to product_service.py - Like/Unlike product

async def like_product_service(
    product_id: str,
    current_user: dict
):
    """
    Like a product.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Check if already liked (using likes collection)
    likes_collection = db["product_likes"]
    
    existing_like = await run_in_threadpool(
        likes_collection.find_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    if existing_like:
        # Already liked
        return {
            "status": "ok",
            "message": "Product already liked",
            "data": {
                "product_id": product_id,
                "likes_count": product.get("likes_count", 0),
                "is_liked": True
            }
        }
    
    # 5. Add like
    like_data = {
        "product_id": ObjectId(product_id),
        "user_id": ObjectId(user_id),
        "created_at": datetime.utcnow()
    }
    
    await run_in_threadpool(
        likes_collection.insert_one,
        like_data
    )
    
    # 6. Increment likes count
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$inc": {"likes_count": 1}}
    )
    
    # 7. Get updated likes count
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    return {
        "status": "ok",
        "message": "Product liked successfully",
        "data": {
            "product_id": product_id,
            "likes_count": updated_product.get("likes_count", 0) if updated_product else 0,
            "is_liked": True
        }
    }


async def unlike_product_service(
    product_id: str,
    current_user: dict
):
    """
    Unlike a product.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Check if liked
    likes_collection = db["product_likes"]
    
    existing_like = await run_in_threadpool(
        likes_collection.find_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    if not existing_like:
        # Not liked
        return {
            "status": "ok",
            "message": "Product not liked",
            "data": {
                "product_id": product_id,
                "likes_count": product.get("likes_count", 0),
                "is_liked": False
            }
        }
    
    # 5. Remove like
    await run_in_threadpool(
        likes_collection.delete_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    # 6. Decrement likes count (ensure not below 0)
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id), "likes_count": {"$gt": 0}},
        {"$inc": {"likes_count": -1}}
    )
    
    # 7. Get updated likes count
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    return {
        "status": "ok",
        "message": "Product unliked successfully",
        "data": {
            "product_id": product_id,
            "likes_count": updated_product.get("likes_count", 0) if updated_product else 0,
            "is_liked": False
        }
    }





# Add to product_service.py - Save/Unsave product

async def save_product_service(
    product_id: str,
    current_user: dict
):
    """
    Save/favorite a product.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Check if already saved
    saves_collection = db["product_saves"]
    
    existing_save = await run_in_threadpool(
        saves_collection.find_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    if existing_save:
        # Already saved
        return {
            "status": "ok",
            "message": "Product already saved",
            "data": {
                "product_id": product_id,
                "saved_count": product.get("saved_count", 0),
                "is_saved": True
            }
        }
    
    # 5. Add save
    save_data = {
        "product_id": ObjectId(product_id),
        "user_id": ObjectId(user_id),
        "created_at": datetime.utcnow()
    }
    
    await run_in_threadpool(
        saves_collection.insert_one,
        save_data
    )
    
    # 6. Increment saved count
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$inc": {"saved_count": 1}}
    )
    
    # 7. Get updated saved count
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    return {
        "status": "ok",
        "message": "Product saved successfully",
        "data": {
            "product_id": product_id,
            "saved_count": updated_product.get("saved_count", 0) if updated_product else 0,
            "is_saved": True
        }
    }


async def unsave_product_service(
    product_id: str,
    current_user: dict
):
    """
    Remove a saved/favorited product.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Check if saved
    saves_collection = db["product_saves"]
    
    existing_save = await run_in_threadpool(
        saves_collection.find_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    if not existing_save:
        # Not saved
        return {
            "status": "ok",
            "message": "Product not saved",
            "data": {
                "product_id": product_id,
                "saved_count": product.get("saved_count", 0),
                "is_saved": False
            }
        }
    
    # 5. Remove save
    await run_in_threadpool(
        saves_collection.delete_one,
        {"product_id": ObjectId(product_id), "user_id": ObjectId(user_id)}
    )
    
    # 6. Decrement saved count (ensure not below 0)
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id), "saved_count": {"$gt": 0}},
        {"$inc": {"saved_count": -1}}
    )
    
    # 7. Get updated saved count
    updated_product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(product_id)}
    )
    
    return {
        "status": "ok",
        "message": "Product unsaved successfully",
        "data": {
            "product_id": product_id,
            "saved_count": updated_product.get("saved_count", 0) if updated_product else 0,
            "is_saved": False
        }
    }






# Add to product_service.py - View count

async def increment_product_view_service(
    product_id: str
):
    """
    Increment product view count.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Increment view count
    result = await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(product_id)},
        {"$inc": {"views_count": 1}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return {
        "status": "ok",
        "message": "View count incremented",
        "data": {
            "product_id": product_id
        }
    }








# Add to product_service.py - Report product

async def report_product_service(
    report_data: ProductReportCreate,
    current_user: dict
):
    """
    Report a product.
    """
    # 1. Validate ObjectId
    if not ObjectId.is_valid(report_data.product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    # 2. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # 3. Check if product exists
    product = await run_in_threadpool(
        product_collection.find_one,
        {"_id": ObjectId(report_data.product_id)}
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 4. Check if already reported by this user
    reports_collection = db["product_reports"]
    
    existing_report = await run_in_threadpool(
        reports_collection.find_one,
        {
            "product_id": ObjectId(report_data.product_id),
            "reporter_id": ObjectId(user_id)
        }
    )
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this product"
        )
    
    # 5. Create report
    report = {
        "product_id": ObjectId(report_data.product_id),
        "reporter_id": ObjectId(user_id),
        "reason": report_data.reason.value if hasattr(report_data.reason, 'value') else report_data.reason,
        "description": report_data.description,
        "created_at": datetime.utcnow(),
        "status": "pending"
    }
    
    result = await run_in_threadpool(
        reports_collection.insert_one,
        report
    )
    
    # 6. Increment report count on product
    await run_in_threadpool(
        product_collection.update_one,
        {"_id": ObjectId(report_data.product_id)},
        {"$inc": {"report_count": 1}}
    )
    
    return {
        "status": "ok",
        "message": "Product reported successfully",
        "data": {
            "report_id": str(result.inserted_id),
            "product_id": report_data.product_id,
            "reason": report_data.reason,
            "status": "pending"
        }
    }







# Add to product_service.py - Get reported products (Admin)

async def get_reported_products_service(
    current_user: dict,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None
):
    """
    Get all reported products (Admin only).
    """
    # 1. Check if user is admin
    user_id = current_user.get("_id") or current_user.get("id")
    
    # Check if user has admin role (you'll need to implement this)
    # For now, let's assume there's an is_admin field
    user_profile = await run_in_threadpool(
        profile_collection.find_one,
        {"_id": ObjectId(user_id)}
    )
    
    if not user_profile or not user_profile.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # 2. Build query
    reports_collection = db["product_reports"]
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    # 3. Pagination
    skip = (page - 1) * limit
    
    # 4. Get total count
    total_count = await run_in_threadpool(
        reports_collection.count_documents,
        query
    )
    
    # 5. Fetch reports with product details
    cursor = await run_in_threadpool(
        reports_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
    
    reports_list = await run_in_threadpool(list, cursor)
    
    # 6. Fetch product details for each report
    formatted_reports = []
    for report in reports_list:
        product_id = report["product_id"]
        product = await run_in_threadpool(
            product_collection.find_one,
            {"_id": product_id}
        )
        
        formatted_reports.append({
            "report_id": str(report["_id"]),
            "product_id": str(product_id),
            "product_title": product.get("title") if product else "Product not found",
            "reporter_id": str(report["reporter_id"]),
            "reason": report["reason"],
            "description": report.get("description"),
            "status": report["status"],
            "created_at": report["created_at"]
        })
    
    # 7. Pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    
    return {
        "status": "ok",
        "data": {
            "reports": formatted_reports,
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






# Add to product_service.py - Recommendations

async def get_product_recommendations_service(
    current_user: dict,
    limit: int = 20
):
    """
    Get personalized product recommendations based on user activity.
    """
    # 1. Get user ID
    user_id = current_user.get("_id") or current_user.get("id")
    if not user_id:
        # For non-authenticated users, return trending products
        return await get_trending_products_service(limit)
    
    # 2. Get user's liked/saved products to understand preferences
    likes_collection = db["product_likes"]
    saves_collection = db["product_saves"]
    
    # Get liked products
    liked_cursor = await run_in_threadpool(
        likes_collection.find,
        {"user_id": ObjectId(user_id)}
    )
    liked_products = await run_in_threadpool(list, liked_cursor)
    
    # Get saved products
    saved_cursor = await run_in_threadpool(
        saves_collection.find,
        {"user_id": ObjectId(user_id)}
    )
    saved_products = await run_in_threadpool(list, saved_cursor)
    
    # 3. Extract categories and tags from liked/saved products
    product_ids = []
    for like in liked_products:
        product_ids.append(like["product_id"])
    for save in saved_products:
        product_ids.append(save["product_id"])
    
    if not product_ids:
        # If no activity, return trending products
        return await get_trending_products_service(limit)
    
    # 4. Get product details to extract preferences
    products = await run_in_threadpool(
        lambda: list(
            product_collection.find({"_id": {"$in": product_ids}})
        )
    )
    
    categories = set()
    tags = set()
    for prod in products:
        if prod.get("category"):
            categories.add(prod["category"])
        if prod.get("tags"):
            tags.update(prod["tags"])
    
    # 5. Build recommendation query
    query = {
        "_id": {"$nin": product_ids},  # Exclude already interacted products
        "is_active": True,
        "status": ProductStatus.ACTIVE.value,
        "$or": [
            {"category": {"$in": list(categories)}} if categories else {},
            {"tags": {"$in": list(tags)}} if tags else {}
        ]
    }
    
    # Remove empty conditions
    if not categories:
        del query["$or"][0]
    if not tags:
        del query["$or"][1]
    
    # If no categories or tags, return trending
    if not query.get("$or"):
        return await get_trending_products_service(limit)
    
    # 6. Fetch recommendations
    cursor = await run_in_threadpool(
        product_collection.find,
        query
    )
    cursor = cursor.sort("created_at", -1).limit(limit)
    
    recommendations = await run_in_threadpool(list, cursor)
    
    # 7. Format
    formatted_products = []
    for product in recommendations:
        product["_id"] = str(product["_id"])
        product["seller_id"] = str(product["seller_id"])
        formatted_products.append(product)
    
    return {
        "status": "ok",
        "data": {
            "recommendations": formatted_products,
            "count": len(formatted_products),
            "limit": limit,
            "based_on": {
                "categories": list(categories),
                "tags": list(tags)
            }
        }
    }