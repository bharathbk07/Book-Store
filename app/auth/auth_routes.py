from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import create_access_token, verify_token
from app.database import db_connect
from app.utils.password_utils import pwd_context
from fastapi.security import OAuth2PasswordBearer, HTTPBasic, HTTPBasicCredentials
from mysql.connector import Error

security = HTTPBasic()  # Initialize HTTP Basic Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
blacklist = set()  # In-memory token blacklist

router = APIRouter()

@router.post("/login")
def login(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Login using Basic Authentication. Requires username and password in the 'Authorization' header.
    """
    try:
        # Extract username and password from Basic Auth credentials
        username = credentials.username
        password = credentials.password

        # Fetch user details from the database
        query = "SELECT id, password FROM users WHERE username = %s"
        query_result = db_connect.execute_query(query, (username,))
        data = query_result["data"]

        # Verify if user exists and password matches
        if not data or not pwd_context.verify(password, data[0][1]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        user_id = data[0][0]
        token = create_access_token(data={"sub": str(user_id)})

        # Return a success message with the token
        return {"message": f"Login successful!","Token": f"Bearer {token}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )

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
