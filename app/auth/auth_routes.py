from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import create_access_token, verify_token
from app.database import db_connect
from app.utils.password_utils import pwd_context
from fastapi.security import OAuth2PasswordBearer
from mysql.connector import Error
from app.schemas.schemas import LoginRequest

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
blacklist = set()  # In-memory token blacklist

router = APIRouter()

@router.post("/login")
def login(user: LoginRequest):
    query = "SELECT id, password FROM users WHERE username = %s"
    
    # Execute query and extract result and column data
    query_result = db_connect.execute_query(query, (user.username,))
    data = query_result["data"]

    if not data or not pwd_context.verify(user.password, data[0][1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = data[0][0]
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

    try:
        query = "SELECT id, username, usertype FROM users WHERE id = %s"
        
        # Execute query and extract result and column data
        query_result = db_connect.execute_query(query, (user_id,))
        data = query_result["data"]

        if not data:
            raise HTTPException(status_code=404, detail="User not found")

        user = data[0]
        return {"id": user[0], "username": user[1], "usertype": user[2]}  # Return as a dictionary

    except Error as e:
        raise HTTPException(status_code=500, detail="Database error")
