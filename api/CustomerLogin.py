from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str

router = APIRouter()

@router.post("/users")
def create_user(user: User):
    # Logic to create a user
    return {"message": "User created", "user": user}

@router.get("/users/{user_id}")
def read_user(user_id: int):  # Corrected type
    # Logic to read a user
    return {"user_id": user_id, "name": "Sample User"}

@router.post("/login")  # Changed to POST for login
def user_login(user: User):  # Corrected to accept User model
    # Logic to verify user
    return {"username": user.username, "message": "Logged in successfully."}
