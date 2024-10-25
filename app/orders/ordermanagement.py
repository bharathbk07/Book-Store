from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.schemas import (
    OrderRequest, OrderStatusUpdate, OrdersResponse, OrderPlacementResponse, OrderActionResponse
)
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/order_book", response_model=OrderPlacementResponse)
def order_book(
    order_details: OrderRequest, 
    current_user: dict = Depends(get_current_user)
):
    """
    Place an order for a book.
    """
    try:
        query_result = db_connect.execute_query(
            "SELECT price, quantity FROM books WHERE barcode = %s", (order_details.barcode,)
        )
        book = query_result["data"]

        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")

        price, available_quantity = book[0]
        if available_quantity < order_details.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock.")

        total_amount = price * order_details.quantity
        transaction_id = str(uuid.uuid4())
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db_connect.execute_query(
            """
            INSERT INTO orders (user_id, barcode, order_date, transaction_id, 
                                total_amount, status, quantity) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                current_user['id'], order_details.barcode, order_date, 
                transaction_id, total_amount, "Order Placed", order_details.quantity
            )
        )

        new_quantity = available_quantity - order_details.quantity
        if new_quantity > 0:
            db_connect.execute_query(
                "UPDATE books SET quantity = %s WHERE barcode = %s", 
                (new_quantity, order_details.barcode)
            )
        else:
            db_connect.execute_query("DELETE FROM books WHERE barcode = %s", (order_details.barcode,))

        return {"message": "Order placed successfully", "transaction_id": transaction_id}

    except Exception as e:
        raise_db_error(e)


@router.get("/view_orders", response_model=OrdersResponse)
def view_orders(
    current_user: dict = Depends(get_current_user),
    username_param: str = Query(None, description="Username to filter orders (admin only).")
):
    """
    View orders. Admins can view all orders or filter by username.
    """
    try:
        user_id = current_user["id"]
        is_admin = current_user["usertype"] == "admin"

        if is_admin and username_param:
            # Fetch the user ID using the provided username
            user_id_query = "SELECT id FROM users WHERE username = %s"
            user_id_result = db_connect.execute_query(user_id_query, (username_param,))
            user_data = user_id_result["data"]

            if not user_data:
                raise HTTPException(status_code=404, detail="User not found.")

            user_id = user_data[0][0]  # Extract user ID from the result
            query = "SELECT * FROM orders WHERE user_id = %s"
            params = (user_id,)

        elif is_admin:
            # If no username provided by admin, return all orders
            query = "SELECT * FROM orders"
            params = ()

        else:
            # For regular users, return only their own orders
            query = "SELECT * FROM orders WHERE user_id = %s"
            params = (user_id,)

        orders_result = db_connect.execute_query(query, params)
        orders = orders_result["data"]

        # Prepare the response data
        orders_data = [
            {
                "order_id": row[0],
                "user_id": row[1],
                "barcode": row[2],
                "order_date": row[3],
                "transaction_id": row[4],
                "total_amount": row[5],
                "status": row[6],
                "quantity": row[7],
            }
            for row in orders
        ]

        return {"orders": orders_data}

    except Exception as e:
        raise_db_error(e)

@router.put("/cancel_order/{transaction_id}", response_model=OrderActionResponse)
def cancel_order(
    transaction_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an order if it belongs to the current user.
    """
    try:
        order_query = "SELECT status FROM orders WHERE transaction_id = %s AND user_id = %s"
        order_result = db_connect.execute_query(order_query, (transaction_id, current_user["id"]))
        order = order_result["data"]

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        if order[0][0] != "Order Placed":
            raise HTTPException(status_code=400, detail="Order cannot be canceled.")

        db_connect.execute_query("UPDATE orders SET status = 'Order Canceled' WHERE transaction_id = %s", (transaction_id,))

        return {"message": "Order canceled successfully"}

    except Exception as e:
        raise_db_error(e)

@router.put("/update_order_status/{transaction_id}", response_model=OrderActionResponse)
def update_order_status(
    transaction_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of an order (admin only).
    """
    allowed_statuses = ["In Transit", "Order Delivered"]

    if status_update.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_update.status}")

    if current_user["usertype"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update order status.")

    try:
        db_connect.execute_query(
            "UPDATE orders SET status = %s WHERE transaction_id = %s", 
            (status_update.status, transaction_id)
        )
        return {"message": f"Order status updated to '{status_update.status}'"}

    except Exception as e:
        raise_db_error(e)

def raise_db_error(e: Exception):
    """Raise a 500 error with the database exception message."""
    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
