# Use the official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Set environment variables
ENV DB_HOST=localhost
ENV DB_USER=your_db_user
ENV DB_PASSWORD=your_db_password
ENV DB_NAME=your_db_name
ENV SECRET_KEY=your_secret_key
ENV DB_PORT=3307

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application into the container
COPY . .

# Run MySQL commands to set up the database
RUN apt-get update && apt-get install -y default-mysql-client

# Copy the SQL script to create the database and tables
COPY setup_db.sql .

# Run the SQL script to create the database and tables
CMD mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD < setup_db.sql && \
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
