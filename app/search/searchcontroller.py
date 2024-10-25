from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from app.database import db_connect
from app.auth.auth_routes import get_current_user
from mysql.connector import Error

router = APIRouter()

# Allowed tables based on user roles
NON_ADMIN_TABLES = ["books", "orders"]
ADMIN_TABLES = NON_ADMIN_TABLES + ["users"]

# Define valid order_by fields for each table
VALID_ORDER_BY = {
    "books": ["title", "author", "price"],
    "orders": ["order_date", "total"],
    "users": ["username", "email"],  # Add more fields as necessary
}

@router.get("/search")
def search(
    table: str = Query(..., description="Table to search in.", enum=NON_ADMIN_TABLES + ["users"]),
    keywords: List[str] = Query(None, description="Search keywords in the format 'field:value'"),
    order_by: Optional[str] = Query(None, description="Field to sort by, e.g., 'price'."),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order: 'asc' or 'desc'."),
    current_user: dict = Depends(get_current_user)
):
    """
    Search API to perform searches across one selected table.
    - Only admin users can search in the 'users' table.
    - Supports multiple input parameters for search.
    - Allows sorting by a specified field in ascending or descending order.
    """

    # Step 1: Check if user is allowed to search in the selected table
    allowed_tables = ADMIN_TABLES if current_user["usertype"] == "admin" else NON_ADMIN_TABLES

    if table not in allowed_tables:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not authorized to search in the '{table}' table."
        )

    try:
        # Step 2: Build the query dynamically
        where_clauses = []
        params = []

        if keywords:
            for keyword in keywords:
                # Split keyword by colon to get field and value
                field_value = keyword.split(":", 1)
                if len(field_value) != 2:
                    raise HTTPException(status_code=400, detail=f"Invalid keyword format: '{keyword}'")
                
                field, value = field_value
                where_clauses.append(f"{field} LIKE %s")
                params.append(f"%{value}%")

        query = f"SELECT * FROM {table}"

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # Step 3: Handle ordering
        if order_by:
            # Check if order_by is a valid field for the selected table
            if order_by not in VALID_ORDER_BY[table]:
                raise HTTPException(status_code=400, detail=f"Invalid order_by field: '{order_by}'")
            query += f" ORDER BY {order_by} {sort_order.upper()}"

        # Execute the query and get the result data and columns
        result = db_connect.execute_query(query, tuple(params))

        # Extract data and column names
        data = result.get("data", [])
        columns = result.get("columns", [])

        # Format the data into a list of dictionaries
        formatted_data = [dict(zip(columns, row)) for row in data]

        # Step 4: Hide passwords if the users table is queried
        if table == "users":
            for item in formatted_data:
                item.pop("password", None)  # Remove password field if it exists

        # Step 5: Return the search result
        return {
            "message": "Search completed successfully",
            "table": table,
            "results": formatted_data or "No matching records found."
        }

    except HTTPException as http_err:
        raise http_err  # Re-raise HTTP exceptions
    except Error as db_err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
