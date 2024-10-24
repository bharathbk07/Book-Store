from fastapi import APIRouter, Depends, HTTPException
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from app.schemas.user_schemas import Book
from app.utils.password_utils import pwd_context
from mysql.connector import Error

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
    