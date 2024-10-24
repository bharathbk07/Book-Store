# Book-Store

# Online Bookstore Database Setup

This document provides instructions for setting up the database for the Online Bookstore application.

## Creating the Database

To create the database, run the following SQL command:

```sql
CREATE DATABASE IF NOT EXISTS onlinebookstore;
```

# Creating Tables

After creating the database, you can create the necessary tables by executing the following SQL commands:

## Create Books Table
```sql
CREATE TABLE IF NOT EXISTS books (
    barcode VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100),
    author VARCHAR(100),
    price INT,
    quantity INT,
    added_by VARCHAR(100)
);
```

## Create Users Table
```sql
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    address VARCHAR(255),
    phone VARCHAR(20),
    mailid VARCHAR(100) UNIQUE,
    usertype VARCHAR(50)
);
```

## Create Orders table

```sql
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    barcode VARCHAR(100),
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    transaction_id VARCHAR(100) UNIQUE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (barcode) REFERENCES books(barcode)
);
```
