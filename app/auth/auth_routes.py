from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import create_access_token, verify_token
from app.database import db_connect
from app.utils.password_utils import pwd_context
from fastapi.security import OAuth2PasswordBearer
from mysql.connector import Error

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
blacklist = set()  # In-memory token blacklist

router = APIRouter()

@router.post("/login")
def login(username: str, password: str):
    query = "SELECT id, password FROM users WHERE username = %s"
    result = db_connect.execute_query(query, (username,))
    
    if not result or not pwd_context.verify(password, result[0][1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = result[0][0]
    token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    blacklist.add(token)
    return {"message": "Successfully logged out"}

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token in blacklist:
        raise HTTPException(status_code=401, detail="Token has been invalidated. Please log in again.")

    user_id = verify_token(token)
    
    # Fetch user details from the database using user_id from the token
    try:
        query = "SELECT id,username,usertype FROM users WHERE id = %s"
        user = db_connect.execute_query(query, (user_id,))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"id": user[0][0], "username": user[0][1], "usertype": user[0][2]}  # Return as a dictionary

    except Error as e:
        raise HTTPException(status_code=500, detail="Database error")
