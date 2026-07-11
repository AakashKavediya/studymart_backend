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

from fastapi import APIRouter, Depends, status, Query
from app.utils.user import get_current_user
from app.schemas.product_schema import ProductCreate
from app.services.product_service import create_new_product_service,get_all_products_service

router = APIRouter(prefix="/products", tags=["Products"])

# -------------------------
# Create a new product
# -------------------------

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new product listing.
    """
    return await create_new_product_service(product_data, current_user)

# -------------------------
# Get all products (with pagination)
# -------------------------

@router.get("/get", status_code=status.HTTP_200_OK)
async def get_all_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get all active products with pagination.
    """
    return await get_all_products_service(page, limit, sort_by, sort_order)


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


