from mysql.connector import Error, pooling
from dotenv import load_dotenv
import os
import time  # For implementing the retry mechanism
import logging  # Optional for logging errors

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

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
                port=int(os.getenv("DB_PORT")),  # Accepting port number from the environment
            )
            logging.info("Database connection pool created successfully.")
            return pool  # Return the connection pool
        except Error as e:
            attempt += 1
            wait_time = min(16, 2 ** attempt)  # Exponential backoff with a cap
            logging.error(f"Attempt {attempt}/{max_retries} failed: '{e}'. Retrying in {wait_time} seconds...")
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
            return {"status": "success"}  # Indicate success for non-SELECT queries

        # Fetch results for SELECT queries
        if cursor.description:  # Check if the cursor has results
            result = cursor.fetchall()
            column_names = get_column_descriptions(cursor)
            return {
                "data": result,
                "columns": column_names
            }  # Return both result and column names

        return None  # Return None if no results are found

    except Error as e:
        logging.error(f"Database error: '{e}' occurred")
        raise  # Reraise the exception for higher-level handling

    finally:
        if cursor:
            cursor.close()  # Close the cursor
        if connection:
            connection.close()  # Return connection to the pool
