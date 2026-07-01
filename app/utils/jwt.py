# # ----------------------------
# # JWT UTILITIES
# # ----------------------------

# from datetime import datetime, timedelta

# from jose import jwt

# # from app.config.settings import (
# #     SECRET_KEY,
# #     ALGORITHM,
# #     ACCESS_TOKEN_EXPIRE_MINUTES,
# # )


# # ----------------------------
# # CREATE ACCESS TOKEN
# # ----------------------------
# def create_access_token(user_id: str, email: str) -> str:

#     expire = datetime.utcnow() + timedelta(
#         minutes=ACCESS_TOKEN_EXPIRE_MINUTES
#     )

#     payload = {
#         "sub": user_id,
#         "email": email,
#         "exp": expire,
#         "type": "access",
#     }

#     return jwt.encode(
#         payload,
#         SECRET_KEY,
#         algorithm=ALGORITHM,
#     )


# # ----------------------------
# # DECODE JWT
# # ----------------------------
# def decode_token(token: str):

#     return jwt.decode(
#         token,
#         SECRET_KEY,
#         algorithms=[ALGORITHM],
#     )