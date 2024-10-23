import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from Database import db_connect
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from dotenv import load_dotenv
from mysql.connector import Error

# Load environment variables from .env file
load_dotenv()
# In-memory blacklist for invalidated tokens
blacklist = set()

class User(BaseModel):
    username: str
    password: str

class UserCreate(User):
    firstname: str = Field(..., max_length=100)
    lastname: str = Field(..., max_length=100)
    address: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=15)
    mailid: EmailStr
    usertype: int = Field(..., ge=1)  # Assuming usertype must be at least 1

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

router = APIRouter()

# Password hashing using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function to create a JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Function to verify a token and extract user information
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError as e:
        print(f"JWTError: {str(e)}")  # Print JWT error details
        raise HTTPException(status_code=401, detail="Invalid token or expired token")
    except Exception as e:
        print(f"Exception: {str(e)}")  # Print any other exception details
        raise HTTPException(status_code=500, detail="An error occurred while verifying the token")

# Verify user credentials using a database function
def verify_user_login(username: str, password: str):
    """Verify user credentials."""
    try:
        # SQL query to verify user credentials
        login_verify_query = "SELECT username, password FROM users WHERE username = %s;"
        
        # Execute the query using your database function
        login_query_result = db_connect.execute_query(login_verify_query, (username,))
        
        # If user is found, compare the password
        if login_query_result and pwd_context.verify(password, login_query_result[0][1]):
            return username  # Successful login, return username

        # Return None if the password doesn't match or user not found
        return None

    except Error as e:
        # Catch MySQL database errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Catch any other general exceptions
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Dependency to get the current user from the token
def get_current_user(token: str = Depends(oauth2_scheme)):
    if token in blacklist:
        raise HTTPException(status_code=401, detail="Token has been invalidated. Please log in again.")

    user_id = verify_token(token)
    
    # Fetch user details from the database using user_id from the token
    try:
        query = "SELECT id, username FROM users WHERE id = %s"
        user = db_connect.execute_query(query, (user_id,))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"id": user[0][0], "username": user[0][1]}  # Return as a dictionary

    except Error as e:
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/login", operation_id="user_login_api")  # Changed to POST for login
def user_login(user: User):  # Accept User model
    # Logic to verify user
    username = verify_user_login(user.username, user.password)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Retrieve user ID for the JWT token
    get_user_id = "SELECT id FROM users WHERE username = %s;"
    result = db_connect.execute_query(get_user_id, (user.username,))  # Pass username
    user_id = result[0][0]  # Get the first row's first column (the user ID)

    # Create a JWT token with user ID as the subject (sub)
    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")  # Endpoint for user registration
def create_user(user: UserCreate):
    # Hash the password
    hashed_password = pwd_context.hash(user.password)

    # SQL query to insert the new user into the database
    create_user_query = """
    INSERT INTO users (username, password, firstname, lastname, address, phone, mailid, usertype)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);commit;
    """

    try:
        # Execute the query using your database function
        db_connect.execute_query(create_user_query, (
            user.username,
            hashed_password,
            user.firstname,
            user.lastname,
            user.address,
            user.phone,
            user.mailid,
            user.usertype,
        ))

        return {"message": "User created successfully"}

    except Error as e:
        # Handle database errors
        if e.errno == 1062:  # Duplicate entry error for unique fields
            raise HTTPException(status_code=400, detail="Username already exists")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Handle any other exceptions
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    """
    Get the user's profile information.
    Requires a valid JWT token in the Authorization header.
    """
    return {"username": user["username"], "message": "Welcome to your profile!"}

# Logout endpoint
@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    """
    Logout the user by invalidating the token on the server side.
    The token is provided in the Authorization header.
    """
    # Add the token to the blacklist
    blacklist.add(token)

    return {"message": "Successfully logged out."}

