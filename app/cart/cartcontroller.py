from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from mysql.connector import Error
from app.schemas.schemas import CartItem  # Importing the CartItem schema

router = APIRouter()

@router.post("/add")
def add_to_cart(
    item: CartItem,
    current_user: dict = Depends(get_current_user)
):
    """
    Add an item to the user's cart.
    """
    user_id = current_user["id"]

    query = "INSERT INTO cart (user_id, barcode, quantity) VALUES (%s, %s, %s)"
    params = (user_id, item.barcode, item.quantity)

    try:
        db_connect.execute_query(query, params)
        return {"message": "Item added to cart successfully."}
    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")

@router.post("/modify")
def modify_cart(cart_item: CartItem, current_user: dict = Depends(get_current_user)):
    """
    Modify the quantity of a cart item.
    """
    user_id = current_user["id"]

    # Step 1: Update the cart with the new quantity
    try:
        # Check if the item exists in the cart
        check_query = """
        SELECT quantity FROM cart
        WHERE user_id = %s AND barcode = %s
        """
        check_params = (user_id, cart_item.barcode)
        result = db_connect.execute_query(check_query, check_params)
        existing_item = result.get("data", [])

        if not existing_item:
            raise HTTPException(status_code=404, detail="Item not found in the cart.")

        # Step 2: Update the cart quantity
        update_query = """
        UPDATE cart
        SET quantity = %s
        WHERE user_id = %s AND barcode = %s
        """
        update_params = (cart_item.quantity, user_id, cart_item.barcode)
        db_connect.execute_query(update_query, update_params)

        # Step 3: Fetch the updated cart to return
        return view_cart(current_user)  # Reuse the view_cart function to get the updated cart

    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.delete("/delete")
def delete_cart_item(cart_item: CartItem, current_user: dict = Depends(get_current_user)):
    """
    Delete an item from the cart.
    """
    user_id = current_user["id"]

    try:
        # Step 1: Check if the item exists in the cart
        check_query = """
        SELECT * FROM cart
        WHERE user_id = %s AND barcode = %s
        """
        check_params = (user_id, cart_item.barcode)
        result = db_connect.execute_query(check_query, check_params)
        existing_item = result.get("data", [])

        if not existing_item:
            raise HTTPException(status_code=404, detail="Item not found in the cart.")

        # Step 2: Delete the item from the cart
        delete_query = """
        DELETE FROM cart
        WHERE user_id = %s AND barcode = %s
        """
        delete_params = (user_id, cart_item.barcode)
        db_connect.execute_query(delete_query, delete_params)

        return {"message": "Item deleted successfully from the cart."}

    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.get("/view")
def view_cart(
    current_user: dict = Depends(get_current_user)
):
    """
    View items in the user's cart. Admins can view any user's cart.
    """
    user_id = current_user["id"]
    is_admin = current_user["usertype"] == "admin"

    # If admin, allow specifying a different user ID
    user_id_param = user_id if not is_admin else Query(None, description="User ID to view cart for. Required for admin.")

    # Query to get cart items along with corresponding book details
    query = """
    SELECT c.barcode, c.quantity, b.name AS title, b.price 
    FROM cart c
    JOIN books b ON c.barcode = b.barcode
    WHERE c.user_id = %s
    """
    params = (user_id_param,)

    try:
        result = db_connect.execute_query(query, params)
        cart_items = result.get("data", [])
        columns = result.get("columns", [])

        # Prepare formatted data with book details and calculate final prices
        formatted_cart_items = []
        for row in cart_items:
            item_data = dict(zip(columns, row))
            total_price = item_data['price'] * item_data['quantity']
            formatted_cart_items.append({
                "barcode": item_data['barcode'],
                "title": item_data['title'],  # Corrected field name
                "quantity": item_data['quantity'],
                "price": item_data['price'],
                "total_price": total_price
            })

        return {
            "message": "Cart retrieved successfully.",
            "cart_items": formatted_cart_items
        }
    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
