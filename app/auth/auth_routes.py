from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBasic, HTTPBasicCredentials
from app.auth.jwt_handler import create_access_token, verify_token
from app.database import db_connect
from app.utils.password_utils import pwd_context
from mysql.connector import Error

# Initialize HTTP Basic Auth and OAuth2 schemes
security = HTTPBasic()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# In-memory blacklist for token management
blacklist = set()

router = APIRouter()

@router.post("/login")
def login(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Login using HTTP Basic Authentication. 
    Requires 'username' and 'password' in the 'Authorization' header.
    """
    try:
        # Extract username and password from Basic Auth credentials
        username = credentials.username
        password = credentials.password

        # Fetch user details from the database
        query = "SELECT id, password FROM users WHERE username = %s"
        query_result = db_connect.execute_query(query, (username,))
        data = query_result["data"]

        # Verify user existence and password match
        if not data or not pwd_context.verify(password, data[0][1]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        # Create access token for the user
        user_id = data[0][0]
        token = create_access_token(data={"sub": str(user_id)})

        return {
            "message": "Login successful!",
            "Token": f"Bearer {token}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    """
    Invalidate the JWT token by adding it to the blacklist.
    """
    blacklist.add(token)
    return {"message": "Successfully logged out"}

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Retrieve the current user from the token. 
    Verify that the token is valid and not blacklisted.
    """
    if token in blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please log in again."
        )

    # Verify the token and extract user_id
    user_id = verify_token(token)

    try:
        # Fetch user details from the database using user_id
        query = "SELECT id, username, usertype FROM users WHERE id = %s"
        query_result = db_connect.execute_query(query, (user_id,))
        data = query_result["data"]

        if not data:
            raise HTTPException(status_code=404, detail="User not found")

        # Extract and return user details as a dictionary
        user = data[0]
        return {"id": user[0], "username": user[1], "usertype": user[2]}

    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
