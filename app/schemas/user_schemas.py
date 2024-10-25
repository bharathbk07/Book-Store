from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    firstname: str = Field(..., max_length=100)
    lastname: str = Field(..., max_length=100)
    address: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=15)
    mailid: EmailStr
    usertype: str = Field(default="user")

class LoginRequest(BaseModel):
    username: str
    password: str

class Book(BaseModel):
    barcode: str
    name: str
    author: str
    price: float
    quantity: int

class BookUpdateRequest(BaseModel):
    barcode: str
    quantity: int = Field(None, ge=0)  # Optional, but must be >= 0
    price: float = Field(None, gt=0)   # Optional, must be > 0
    name: str = None  

class UserUpdateRequest(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mailid: Optional[EmailStr] = None
    usertype: Optional[str] = None  # 'admin', 'seller', 'user'