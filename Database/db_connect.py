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
def execute_query(query, params=None):
    """Execute a SQL query using a connection from the pool."""
    connection = None
    cursor = None
    try:
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Execute the query with parameters if provided
        cursor.execute(query, params)
        
        # Fetch all results; you can change this to fetchone() if you expect only one result
        result = cursor.fetchall()  # Fetches all rows for the query

        # Commit changes if it's an INSERT/UPDATE/DELETE query
        if result is not None:
            #print("Query executed successfully")
            return result
        else:
            connection.commit()  # Commit if there is no result to fetch (e.g., INSERT/UPDATE/DELETE)

    except Error as e:
        print(f"Error: '{e}' occurred")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
