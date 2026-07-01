# ----------------------------
# HTTP BEARER SECURITY
# ----------------------------

from fastapi.security import HTTPBearer

# Used in protected routes
security = HTTPBearer(auto_error=True)