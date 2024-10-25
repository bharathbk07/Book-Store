from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

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

class CartItem(BaseModel):
    barcode: str
    quantity: int


# Schema for placing an order request
class OrderRequest(BaseModel):
    barcode: int = Field(..., description="The barcode of the book.")
    quantity: int = Field(..., gt=0, description="Quantity of the book to order.")

# Schema for updating order status
class OrderStatusUpdate(BaseModel):
    status: str = Field(..., description="New status for the order (In Transit / Order Delivered)")

# Response schema for a single order
class OrderResponse(BaseModel):
    order_id: int
    user_id: int
    barcode: int
    order_date: datetime
    transaction_id: str
    total_amount: float
    status: str
    quantity: int

# Response schema for viewing orders
class OrdersResponse(BaseModel):
    orders: list[OrderResponse] = Field(..., description="List of orders.")

# Response schema for order placement
class OrderPlacementResponse(BaseModel):
    message: str
    transaction_id: str

# Response schema for order cancellation or status update
class OrderActionResponse(BaseModel):
    message: str