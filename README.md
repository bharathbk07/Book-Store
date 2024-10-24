# Book-Store

# Online Bookstore Database Setup

This document provides instructions for setting up the database for the Online Bookstore application.

## Creating the Database

To create the database, run the following SQL command:

```sql
CREATE DATABASE IF NOT EXISTS onlinebookstore;

```sql
CREATE TABLE IF NOT EXISTS books (
    barcode VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100),
    author VARCHAR(100),
    price INT,
    quantity INT,
    added_by VARCHAR(100)
);


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
