from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.schemas import UserCreate, UserUpdateRequest
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
    try:
        if user["usertype"] == "admin":
            orders_query = """
                SELECT o.order_id, o.order_date, o.transaction_id, o.total_amount, 
                       o.status, o.quantity, b.name AS book_name, u.username 
                FROM orders o
                JOIN books b ON o.barcode = b.barcode
                JOIN users u ON o.user_id = u.id
            """
            orders_params = ()
        else:
            orders_query = """
                SELECT o.order_id, o.order_date, o.transaction_id, o.total_amount, 
                       o.status, o.quantity, b.name AS book_name 
                FROM orders o
                JOIN books b ON o.barcode = b.barcode
                WHERE o.user_id = %s
            """
            orders_params = (user["id"],)

        orders_result = db_connect.execute_query(orders_query, orders_params)
        orders = orders_result["data"]

        books_query = """
            SELECT barcode, name, author, price, quantity 
            FROM books 
            WHERE added_by = %s
        """
        books_result = db_connect.execute_query(books_query, (user["username"],))
        added_books = books_result["data"]

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

        return {
            "username": user["username"],
            "message": "Welcome to your profile!",
            "orders": orders_data or "No orders found.",
            "added_books": books_data or "No books added.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/user_details")
def user_details(user: dict = Depends(get_current_user)):
    try:
        if user["usertype"] == 'admin':
            user_data_query = "SELECT username, firstname, lastname, address, phone, mailid, usertype FROM users;"
            users_result = db_connect.execute_query(user_data_query)
            users = users_result["data"]

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
            return {"message": "User details retrieved successfully", "user_data": user_data}

        else:
            user_data_query = "SELECT username, firstname, lastname, address, phone, mailid, usertype FROM users WHERE username = %s;"
            user_result = db_connect.execute_query(user_data_query, (user['username'],))
            user_info = user_result["data"][0] if user_result["data"] else None

            if not user_info:
                raise HTTPException(status_code=404, detail="User not found")

            user_data = {
                "username": user_info[0],
                "firstname": user_info[1],
                "lastname": user_info[2],
                "address": user_info[3],
                "phone": user_info[4],
                "mailid": user_info[5],
                "usertype": user_info[6]
            }

            return {"message": "User details retrieved successfully", "user_data": user_data}

    except HTTPException as http_err:
        raise http_err
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.put("/update_user")
def update_user(
    user_update: UserUpdateRequest,
    username: str = Query(None, description="Username to update (only for admins)", example="john_doe"), 
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user["usertype"] == "admin":
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username is required for admin updates."
                )
        else:
            username = current_user["username"]

        user_query = "SELECT id, usertype FROM users WHERE username = %s"
        user_result = db_connect.execute_query(user_query, (username,))
        user_data = user_result["data"]

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found."
            )

        user_id, existing_role = user_data[0]

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

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update."
            )

        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = %s"
        update_params.append(username)

        db_connect.execute_query(update_query, tuple(update_params))

        return {"message": f"User '{username}' updated successfully."}

    except HTTPException as http_err:
        raise http_err
    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
