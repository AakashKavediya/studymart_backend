from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, EmailStr, field_validator, Field
import bcrypt
import re


"""
Information required:
1. name
2. email
3. password
4. confirm_password
5. phone_no
6. campus
7. year

"""

#----------------------------
# SIGN UP SCHEMA
#----------------------------


class CreateUser(BaseModel):
    name: str
    email: EmailStr                  # validated email format
    password: str
    confirm_password: str
    campus: str
    phone: str
    year: int

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not re.fullmatch(r"\+?\d{7,15}", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name too short")
        return v

# ── Startup: ensure indexes exist once (call this at app startup) ──────────────

def ensure_indexes(collection):
    """Call once at startup — not on every request."""
    collection.create_index("email", unique=True)
    collection.create_index("phone", unique=True)




#----------------------------
# LOG IN SCHEMA
#----------------------------

class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)



#----------------------------
# LOG OUT SCHEMA
#----------------------------

class LogoutSchema(BaseModel):
    refresh_token: str

