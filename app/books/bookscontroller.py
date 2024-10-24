from fastapi import APIRouter, Depends, HTTPException
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.user_schemas import Book
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