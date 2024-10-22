from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Database import db_connect

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
    login_verify_query = "SELECT username, password FROM users WHERE username = %s;"
    login_query_result = db_connect.execute_query(login_verify_query, (user.username,))

    if login_query_result[0][1] == user.password:
        return {"username": user.username, "message": "Logged in successfully."}
    else:
        return {"username": user.username, "message": "Invalid Username or Password."}
