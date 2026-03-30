"""Auth-related schemas."""

from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel): # Registration payload.
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel): # Login payload.
    email: EmailStr
    password: str

class Token(BaseModel): # JWT token response.
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel): # Decoded JWT payload (for dependency).
    sub: int  # user_id
    role: str
    exp: int