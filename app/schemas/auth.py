from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str 

    @field_validator("full_name")
    @classmethod
    def name_length(cls, v: str) -> str:
        v = v.strip()
        # Meroe requires 8-64 chars for fullName
        if len(v) < 8:
            raise ValueError("Full name must be at least 8 characters")
        if len(v) > 64:
            raise ValueError("Full name must be at most 64 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str | None
    meroe_customer_id: str | None
    kyc_tier: int
    bvn_verified: bool
    id_verified: bool

    model_config = {"from_attributes": True}


AuthResponse.model_rebuild()