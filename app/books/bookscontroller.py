from fastapi import APIRouter, Depends, HTTPException, status
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.schemas import Book, BookUpdateRequest
from mysql.connector import Error
from datetime import datetime
import uuid
from typing import Dict

router = APIRouter()

# Utility function to raise HTTP exceptions
def raise_db_error(e: Exception, message: str = "Database error"):
    raise HTTPException(status_code=500, detail=f"{message}: {str(e)}")

@router.get("/view_books")
def view_books():
    """
    Retrieve all books from the database.
    """
    try:
        books = db_connect.execute_query("SELECT * FROM books;")
        books_data = [
            {
                "barcode": row[0],
                "name": row[1],
                "author": row[2],
                "price": row[3],
                "quantity": row[4],
                "added_by": row[5]
            }
            for row in books
        ]
        return {"message": "Books retrieved successfully", "books_data": books_data}

    except Error as e:
        raise_db_error(e)


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
        db_connect.execute_query(query, (
            book_details.barcode, book_details.name, book_details.author,
            book_details.price, book_details.quantity, current_user["username"]
        ))
        return {"message": f"'{book_details.name}' added by {current_user['username']}"}
    except Exception as e:
        raise_db_error(e)


@router.post("/order_book")
def order_book(order_details: Dict[str, int], current_user: dict = Depends(get_current_user)):
    """
    Place an order for a book. Provide 'barcode' and 'quantity' in the request.
    """
    barcode = order_details.get("barcode")
    quantity = order_details.get("quantity")

    if not barcode or not quantity:
        raise HTTPException(status_code=400, detail="Barcode and quantity are required.")

    try:
        # Fetch book details
        book = db_connect.execute_query(
            "SELECT price, quantity FROM books WHERE barcode = %s", (barcode,)
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")

        price, available_quantity = book[0]

        if available_quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock.")

        # Calculate total amount and generate transaction details
        total_amount = price * quantity
        transaction_id = str(uuid.uuid4())
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert the order
        db_connect.execute_query("""
            INSERT INTO orders (user_id, barcode, order_date, transaction_id, 
                                total_amount, status, quantity) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (current_user['id'], barcode, order_date, transaction_id, total_amount, 
              "Order Placed", quantity))

        # Update book stock or delete if out of stock
        new_quantity = available_quantity - quantity
        if new_quantity > 0:
            db_connect.execute_query(
                "UPDATE books SET quantity = %s WHERE barcode = %s", (new_quantity, barcode)
            )
        else:
            db_connect.execute_query(
                "DELETE FROM books WHERE barcode = %s", (barcode,)
            )

        return {"message": "Order placed successfully", "transaction_id": transaction_id}

    except Exception as e:
        raise_db_error(e)


@router.put("/modify_or_delete_book")
def modify_or_delete_book(
    book_update: BookUpdateRequest, 
    delete: bool = False, 
    user: dict = Depends(get_current_user)
):
    """
    Modify or delete a book. Only the creator or admin can modify/delete it.
    """
    try:
        # Verify if the book exists and fetch the added_by field
        book = db_connect.execute_query(
            "SELECT barcode, added_by FROM books WHERE barcode = %s", (book_update.barcode,)
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")

        _, added_by = book[0]

        # Check authorization (either creator or admin)
        if user["username"] != added_by and user["usertype"] != "admin":
            raise HTTPException(
                status_code=403, detail="Unauthorized to modify or delete this book."
            )

        # Handle deletion
        if delete:
            db_connect.execute_query(
                "DELETE FROM books WHERE barcode = %s", (book_update.barcode,)
            )
            return {"message": f"Book with barcode {book_update.barcode} deleted successfully."}

        # Handle update
        update_fields, params = [], []
        if book_update.quantity is not None:
            update_fields.append("quantity = %s")
            params.append(book_update.quantity)
        if book_update.price is not None:
            update_fields.append("price = %s")
            params.append(book_update.price)
        if book_update.name is not None:
            update_fields.append("name = %s")
            params.append(book_update.name)

        if not update_fields:
            raise HTTPException(
                status_code=400, detail="No valid fields to update."
            )

        params.append(book_update.barcode)
        db_connect.execute_query(
            f"UPDATE books SET {', '.join(update_fields)} WHERE barcode = %s", tuple(params)
        )
        return {"message": f"Book with barcode {book_update.barcode} updated successfully."}

    except Exception as e:
        raise_db_error(e)
