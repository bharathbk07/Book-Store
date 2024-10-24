from fastapi import APIRouter, Depends, HTTPException, status
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.user_schemas import Book
from app.schemas.user_schemas import BookUpdateRequest
from mysql.connector import Error
from datetime import datetime
import uuid  # For generating unique order IDs
from typing import Dict

router = APIRouter()

@router.get("/view_books")
def view_books():
    try:
        view_all_books_query = """
            SELECT * from books;
        """
        # Execute the query using your database function
        books = db_connect.execute_query(view_all_books_query)

        # Format the result as a list of dictionaries
        books_data = [
                {
                    "barcode": row[0],
                    "name": row[1],
                    "author": row[2],
                    "price": row[3],
                    "quantity": row[4],
                    "added_by":row[5]
                }
            for row in books
        ]

        # Return all users' details in JSON format
        return {"message": "Books details retrieved successfully", "books_data": books_data}
    except HTTPException as http_err:
        # Reraise HTTP exceptions for specific status codes
        raise http_err
    except Error as e:
        # General error handling
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Catch any other exceptions
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/add_books")
def add_books(book_details: Book, current_user: dict = Depends(get_current_user)):
    """
    Add a new book to the database. Only authenticated users can add books.
    """
    query = """
        INSERT INTO books (barcode, name, author, price, quantity, added_by) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        db_connect.execute_query(
            query, 
            (
                book_details.barcode, 
                book_details.name, 
                book_details.author, 
                book_details.price, 
                book_details.quantity, 
                current_user["username"]
            )
        )
        return {
            "message": f"'{book_details.name}' added successfully by {current_user['username']}"
        }

    except Exception as e:
        # Raise 500 error with database error details
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.post("/order_book")
def order_book(order_details: Dict[str, int], current_user: dict = Depends(get_current_user)):
    """
    Place an order for a book. Only authenticated users can order books.
    The request body should contain the 'barcode' and 'quantity' of the book.
    """

    # Extract barcode and quantity from the request body
    barcode = order_details.get("barcode")
    quantity = order_details.get("quantity")

    if not barcode or not quantity:
        raise HTTPException(status_code=400, detail="Barcode and quantity must be provided.")

    # Fetch book details from the database
    book_query = "SELECT price, quantity FROM books WHERE barcode = %s"
    book_details = db_connect.execute_query(book_query, (barcode,))

    if not book_details:
        raise HTTPException(status_code=404, detail="Book not found.")
    
    price, available_quantity = book_details[0]  # Assuming price is the first column and quantity is the second

    if available_quantity < quantity:
        raise HTTPException(status_code=400, detail="Not enough books available to fulfill the order.")

    total_amount = price * quantity  # Calculate total amount for the order

    # Generate transaction ID and order date
    transaction_id = str(uuid.uuid4())  # Generate a unique transaction ID
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current date and time

    # Insert the order into the database (no need to specify order_id)
    insert_order_query = """
        INSERT INTO orders (user_id, barcode, order_date, transaction_id, total_amount, status, quantity) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        db_connect.execute_query(
            insert_order_query,
            (current_user['id'], barcode, order_date, transaction_id, total_amount, "Order Placed", quantity)
        )
        
        # Update the book quantity in the books table
        new_quantity = available_quantity - quantity
        if new_quantity > 0:
            update_book_query = "UPDATE books SET quantity = %s WHERE barcode = %s"
            db_connect.execute_query(update_book_query, (new_quantity, barcode))
        else:
            # If quantity reaches zero, delete the book from the books table
            delete_book_query = "DELETE FROM books WHERE barcode = %s"
            db_connect.execute_query(delete_book_query, (barcode,))
        
        return {"message": "Order placed successfully", "transaction_id": transaction_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.put("/modify_or_delete_book")
def modify_or_delete_book(
    book_update: BookUpdateRequest, 
    delete: bool = False,  # Query parameter to trigger deletion
    user: dict = Depends(get_current_user)
):
    """
    Modify or delete a book. 
    Users can modify/delete only books they added, but admins have full access.
    """

    # Step 1: Check if the book exists and if the user has permissions
    verify_query = """
        SELECT barcode, added_by FROM books WHERE barcode = %s
    """
    book = db_connect.execute_query(verify_query, (book_update.barcode,))

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found."
        )

    book_data = book[0]
    added_by = book_data[1]

    # Check if the user is either the creator or an admin
    if user["username"] != added_by and user["usertype"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify or delete this book."
        )

    # Step 2: Handle deletion request
    if delete:
        try:
            delete_query = "DELETE FROM books WHERE barcode = %s"
            db_connect.execute_query(delete_query, (book_update.barcode,))
            return {"message": f"Book with barcode {book_update.barcode} deleted successfully."}
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Database error while deleting the book: {str(e)}"
            )

    # Step 3: Handle update request if not deleting
    update_fields = []
    update_params = []

    if book_update.quantity is not None:
        update_fields.append("quantity = %s")
        update_params.append(book_update.quantity)

    if book_update.price is not None:
        update_fields.append("price = %s")
        update_params.append(book_update.price)

    if book_update.name is not None:
        update_fields.append("name = %s")
        update_params.append(book_update.name)

    # Ensure there's at least one field to update
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update."
        )

    # Step 4: Execute the update query
    update_query = f"""
        UPDATE books SET {", ".join(update_fields)} WHERE barcode = %s
    """
    update_params.append(book_update.barcode)

    try:
        db_connect.execute_query(update_query, tuple(update_params))
        return {"message": f"Book with barcode {book_update.barcode} updated successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )
