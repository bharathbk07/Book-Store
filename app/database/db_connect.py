import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create a connection pool
pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,  # Set the desired pool size
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

def get_column_descriptions(cursor):
    """Retrieve column descriptions from the executed query."""
    if cursor.description:
        return [desc[0] for desc in cursor.description]
    return []

def execute_query(query: str, params=None):
    """Execute a SQL query using a connection from the pool."""
    connection = None
    cursor = None
    try:
        # Get a connection from the pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Execute the query with parameters if provided
        cursor.execute(query, params)

        # Check if the query modifies data (INSERT, UPDATE, DELETE)
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            connection.commit()  # Commit the changes

         # Fetch results for SELECT queries
        if cursor.description:  # Check if the cursor has results
            result = cursor.fetchall()
            column_names = get_column_descriptions(cursor)
            return {
                "data": result,
                "columns": column_names
            }
            return result  # Return both result and column names

        return None  # Return None for non-SELECT queries

    except Error as e:
        print(f"Database error: '{e}' occurred")
        raise  # Reraise the exception for higher-level handling

    finally:
        if cursor:
            cursor.close()  # Close the cursor
        if connection:
            connection.close()  # Return connection to the pool
