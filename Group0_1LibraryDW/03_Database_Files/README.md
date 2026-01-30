# Library Data Warehouse – Database Setup Instructions

## Overview
This document provides step-by-step instructions for setting up the **Library Data Warehouse database** using **MySQL**.  
It includes database creation, schema setup, and verification steps required before running the ETL process and dashboards.

---

## Prerequisites

Before starting, ensure you have the following installed:

- MySQL Server (version 8.0 or higher)
- MySQL Workbench or phpMyAdmin
- Git (optional, for cloning the project)
- Python 3.8+ (for ETL scripts)
- Database user with CREATE and ALTER privileges

---

## Step 1: Clone the Project Repository (Optional)

```bash
git clone https://github.com/your-repo/library-data-warehouse.git
cd library-data-warehouse

tep 2: Start MySQL Server

Ensure the MySQL service is running.

Windows (XAMPP):

Start Apache and MySQL from XAMPP Control Panel

Linux / macOS:

sudo service mysql start

Step 3: Create the Database

Login to MySQL:

mysql -u root -p


Create the database:

CREATE DATABASE library_dw;
USE library_dw;

Step 4: Create Database User (Recommended)
CREATE USER 'dw_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON library_dw.* TO 'dw_user'@'localhost';
FLUSH PRIVILEGES;

Step 5: Create Dimension Tables

Run the SQL scripts located in:

02_Database_Schema/
├── dim_date.sql
├── dim_student.sql
├── dim_department.sql
├── dim_resource.sql
├── dim_location.sql


Example:

SOURCE 02_Database_Schema/dim_date.sql;

Step 6: Create Fact Tables

Run the fact table scripts:

02_Database_Schema/
├── fact_book_loans.sql
├── fact_digital_usage.sql
├── fact_room_bookings.sql

Step 7: Create Staging Tables

Staging tables are used for raw data loading during ETL.

03_Staging_Tables/
├── staging_books.sql
├── staging_digital.sql
├── staging_rooms.sql


Run each script using:

SOURCE 03_Staging_Tables/staging_books.sql;

Step 8: Verify Table Creation

Check that all tables were created successfully:

SHOW TABLES;


You should see:

Dimension tables (dim_*)

Fact tables (fact_*)

Staging tables (staging_*)

Step 9: Configure Database Connection

Update the database connection settings in the ETL script:

04_ETL_Files/
├── etl_script.py


Edit:

DB_HOST = "localhost"
DB_USER = "dw_user"
DB_PASSWORD = "strong_password"
DB_NAME = "library_dw"

Step 10: Test Database Connection

Run the ETL script in test mode:

python etl_script.py --test


If successful, you should see:

Database connection successful

Step 11: Load Initial Data

Run the full ETL process:

python etl_script.py


This will:

Load raw data into staging tables

Apply transformation rules

Populate dimension and fact tables

Step 12: Backup the Database (Recommended)

Create a backup after successful setup:

mysqldump -u dw_user -p library_dw > library_dw_backup.sql

Troubleshooting
Issue	Solution
Access denied error	Check username, password, and privileges
Tables not created	Verify SQL script paths
ETL fails	Check database connection settings
Duplicate data	Truncate staging tables and rerun ETL
Security Notes

Do not commit database passwords to GitHub

Use environment variables for production deployments

Restrict database access using RBAC policies

Support

For issues or questions:

Data Warehouse Team

IT Support Department

License

This project is intended for academic use only.