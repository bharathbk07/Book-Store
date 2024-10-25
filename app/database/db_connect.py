import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv
import os
import time  # For implementing the retry mechanism

# Load environment variables from .env file
load_dotenv()

# Create a connection pool with retries for failures
def create_connection_pool():
    max_retries = 5  # Max attempts to establish connection pool
    attempt = 0
    while attempt < max_retries:
        try:
            pool = pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=5,  # Set the desired pool size
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
            )
            print("Database connection pool created successfully.")
            return pool  # Return the connection pool
        except Error as e:
            attempt += 1
            wait_time = 2 ** attempt  # Exponential backoff (2, 4, 8, 16 seconds)
            print(f"Attempt {attempt}/{max_retries} failed: '{e}'. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    raise RuntimeError("Failed to establish connection pool after multiple attempts.")

# Initialize the pool at module load
pool = create_connection_pool()

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
            }  # Return both result and column names

        return None  # Return None for non-SELECT queries

    except Error as e:
        print(f"Database error: '{e}' occurred")
        raise  # Reraise the exception for higher-level handling

    finally:
        if cursor:
            cursor.close()  # Close the cursor
        if connection:
            connection.close()  # Return connection to the pool
