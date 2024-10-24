from fastapi import APIRouter, Depends, HTTPException
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.user_schemas import UserCreate
from app.utils.password_utils import pwd_context
from mysql.connector import Error

router = APIRouter()

@router.post("/register")
def register(user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    query = """
        INSERT INTO users (username, password, firstname, lastname, address, phone, mailid, usertype) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        db_connect.execute_query(query, (
            user.username, hashed_password, user.firstname, user.lastname,
            user.address, user.phone, user.mailid, user.usertype
        ))
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/user_details")
def user_details(user: dict = Depends(get_current_user)):
    try:
        if user["usertype"] == 'admin':
            user_data_query = """
            SELECT username, firstname, lastname, address, phone, mailid, usertype FROM users;
            """
            # Execute the query using your database function
            users = db_connect.execute_query(user_data_query)

            # Format the result as a list of dictionaries
            user_data = [
                {
                    "username": row[0],
                    "firstname": row[1],
                    "lastname": row[2],
                    "address": row[3],
                    "phone": row[4],
                    "mailid": row[5],
                    "usertype": row[6]
                }
                for row in users
            ]

            # Return all users' details in JSON format
            return {"message": "User details retrieved successfully", "user_data": user_data}
        else:
            user_data_query = """
            SELECT username, firstname, lastname, address, phone, mailid, usertype FROM users WHERE username = %s;
            """
            # Execute the query using your database function
            user_data = db_connect.execute_query(user_data_query, (user['username'],))
            
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")

            # Format the result for a specific user
            user_info = {
                "username": user_data[0][0],
                "firstname": user_data[0][1],
                "lastname": user_data[0][2],
                "address": user_data[0][3],
                "phone": user_data[0][4],
                "mailid": user_data[0][5],
                "usertype": user_data[0][6]
            }

            # Return specific user's details in JSON format
            return {"message": "User details retrieved successfully", "user_data": user_info}

    except HTTPException as http_err:
        # Reraise HTTP exceptions for specific status codes
        raise http_err
    except Error as e:
        # General error handling
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Catch any other exceptions
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
