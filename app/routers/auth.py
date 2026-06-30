
"""
All the APIS for AUTHENTICATION
--
| Method | Endpoint             | Purpose                    |
| ------ | -------------------- | -------------------------- |
| POST   | `/auth/signup`       | Create new student account | done
| POST   | `/auth/login`        | Login and generate JWT     | done
| POST   | `/auth/logout`       | Logout user                | done
| GET    | `/auth/me`           | Get current logged-in user | done
| POST   | `/auth/refresh`      | Refresh access token       |  
| POST   | `/auth/verify-email` | Verify college email       |

"""


from fastapi import APIRouter, Request, Response, status
from app.schemas.user_schema import CreateUser, LoginSchema
from app.services.auth_service import login_user, sign_up, refresh_token_service, debug_cookies_service, logout

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# ==========================================================
# Login Service
# ==========================================================

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    user: LoginSchema,
    response: Response,
):
    return await login_user(user, response)



# ==========================================================
# Signup Service
# ==========================================================


@router.post(
    "/signup",
    status_code=status.HTTP_200_OK,
)
async def signup(
    user: CreateUser,
    response: Response,
):
    return await sign_up(user)


# ==========================================================
# Refresh Token Service
# ==========================================================

@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
async def refresh(
    request: Request,
    response: Response,
):
    return await refresh_token_service(request, response)   




# ==========================================================
# Debug Cookies Service
# ==========================================================

@router.get(
    "/debug-cookies",
    status_code=status.HTTP_200_OK,
)
async def debug_cookies(
    request: Request,
):
    return await debug_cookies_service(request)




# ==========================================================
# Logout Service
# ==========================================================

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout_user(
    request: Request,
    response: Response,
):
    return await logout(request, response)