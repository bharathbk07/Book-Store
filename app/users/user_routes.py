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

@router.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    """
    Get the user's profile information, order history, and books they have added.
    If the user is an admin, return all transactions.
    Requires a valid JWT token in the Authorization header.
    """

    try:
        # Determine if the user is an admin
        if user["usertype"] == "admin":
            # Admin: Fetch all transactions
            orders_query = """
                SELECT o.order_id, o.order_date, o.transaction_id, o.total_amount, 
                       o.status, o.quantity, b.name AS book_name, u.username 
                FROM orders o
                JOIN books b ON o.barcode = b.barcode
                JOIN users u ON o.user_id = u.id
            """
            orders_params = ()
        else:
            # Regular user: Fetch only their own orders
            orders_query = """
                SELECT o.order_id, o.order_date, o.transaction_id, o.total_amount, 
                       o.status, o.quantity, b.name AS book_name 
                FROM orders o
                JOIN books b ON o.barcode = b.barcode
                WHERE o.user_id = %s
            """
            orders_params = (user["id"],)

        # Execute the orders query
        orders = db_connect.execute_query(orders_query, orders_params)

        # Fetch books added by the current user
        books_query = """
            SELECT barcode, name, author, price, quantity 
            FROM books 
            WHERE added_by = %s
        """
        books_params = (user["username"],)
        added_books = db_connect.execute_query(books_query, books_params)

        # Format orders data
        orders_data = [
            {
                "order_id": row[0],
                "order_date": row[1].strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_id": row[2],
                "total_amount": float(row[3]),
                "status": row[4],
                "quantity": row[5],
                "book_name": row[6],
                **({"ordered_by": row[7]} if user["usertype"] == "admin" else {}),
            }
            for row in orders
        ]

        # Format added books data
        books_data = [
            {
                "barcode": row[0],
                "name": row[1],
                "author": row[2],
                "price": float(row[3]),
                "quantity": row[4],
            }
            for row in added_books
        ]

        # Handle case when no data is found
        orders_data = orders_data or "No orders found."
        books_data = books_data or "No books added."

        # Construct the response
        return {
            "username": user["username"],
            "message": "Welcome to your profile!",
            "orders": orders_data,
            "added_books": books_data,
        }

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
