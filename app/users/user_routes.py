from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.user_schemas import UserCreate, UserUpdateRequest
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

@router.put("/update_user")
def update_user(
    user_update: UserUpdateRequest,
    username: str = Query(None, description="Username to update (only for admins)", example="john_doe"), 
    current_user: dict = Depends(get_current_user)
):
    """
    Update user details.
    - Non-admins can update only their own details.
    - Admins can update any user's details by specifying the username.
    - Available roles: 'admin', 'seller', 'user'.
    """

    try:
        # Step 1: Determine which user's details to update
        if current_user["usertype"] == "admin":
            # Admin can update any user's profile; username must be provided
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username is required for admin updates."
                )
        else:
            # Non-admin user can only update their own profile
            username = current_user["username"]

        # Step 2: Check if the user exists
        user_query = "SELECT id, usertype FROM users WHERE username = %s"
        user_data = db_connect.execute_query(user_query, (username,))

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found."
            )

        user_id, existing_role = user_data[0]

        # Step 3: Build the update query dynamically based on provided fields
        update_fields = []
        update_params = []

        if user_update.firstname:
            update_fields.append("firstname = %s")
            update_params.append(user_update.firstname)

        if user_update.lastname:
            update_fields.append("lastname = %s")
            update_params.append(user_update.lastname)

        if user_update.address:
            update_fields.append("address = %s")
            update_params.append(user_update.address)

        if user_update.phone:
            update_fields.append("phone = %s")
            update_params.append(user_update.phone)

        if user_update.mailid:
            update_fields.append("mailid = %s")
            update_params.append(user_update.mailid)

        if user_update.usertype:
            # Only admins can change the user type
            if current_user["usertype"] != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can change the user role."
                )
            if user_update.usertype not in ["admin", "seller", "user"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role. Available roles: 'admin', 'seller', 'user'."
                )
            update_fields.append("usertype = %s")
            update_params.append(user_update.usertype)

        # Ensure at least one field is being updated
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update."
            )

        # Step 4: Execute the update query
        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = %s"
        update_params.append(username)

        db_connect.execute_query(update_query, tuple(update_params))

        return {"message": f"User '{username}' updated successfully."}

    except HTTPException as http_err:
        raise http_err  # Re-raise HTTP exceptions
    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")