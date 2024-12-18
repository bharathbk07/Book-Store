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
        query_result = db_connect.execute_query("SELECT * FROM books;")
        books = query_result["data"]

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
        query_result = db_connect.execute_query(
            "SELECT barcode, added_by FROM books WHERE barcode = %s", (book_update.barcode,)
        )
        book = query_result["data"]

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