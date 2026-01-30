-- Drop database if exists (for fresh start)
DROP DATABASE IF EXISTS library_dw;
DROP DATABASE IF EXISTS library_staging;

-- Create main data warehouse database
CREATE DATABASE library_dw
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create staging database for ETL
CREATE DATABASE library_staging
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Use the data warehouse database
USE library_dw;

-- Create metadata table for ETL tracking
CREATE TABLE etl_metadata (
    etl_id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL,
    load_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_extracted INT,
    records_loaded INT,
    records_rejected INT,
    status VARCHAR(20),
    error_message TEXT,
    INDEX idx_source_date (source_name, load_date)
) ENGINE=InnoDB;

-- Success message
SELECT 'Database created successfully!' AS Status;