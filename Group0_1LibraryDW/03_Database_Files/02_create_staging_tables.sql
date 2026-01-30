
USE library_staging;

-- ============================================================================
-- STAGING TABLE 1: Book Transactions (from MySQL)
-- ============================================================================
CREATE TABLE staging_book_transactions (
    staging_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT,
    student_id VARCHAR(50),
    book_isbn VARCHAR(50),
    checkout_date VARCHAR(50),  -- Keep as VARCHAR for initial load
    return_date VARCHAR(50),     -- Keep as VARCHAR for initial load
    department VARCHAR(100),     -- Extra space for inconsistent values
    book_category VARCHAR(100),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_quality_flag VARCHAR(20) DEFAULT 'RAW',
    INDEX idx_student (student_id),
    INDEX idx_transaction (transaction_id)
) ENGINE=InnoDB;

-- ============================================================================
-- STAGING TABLE 2: Digital Downloads (from Excel)
-- ============================================================================
CREATE TABLE staging_digital_usage (
    staging_id INT AUTO_INCREMENT PRIMARY KEY,
    download_date VARCHAR(50),   -- Various formats need cleaning
    user_type VARCHAR(50),
    resource_type VARCHAR(50),
    faculty VARCHAR(100),        -- Inconsistent naming
    download_count INT,
    duration_minutes INT,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_quality_flag VARCHAR(20) DEFAULT 'RAW',
    INDEX idx_date (download_date),
    INDEX idx_faculty (faculty)
) ENGINE=InnoDB;

-- ============================================================================
-- STAGING TABLE 3: Room Bookings (from CSV)
-- ============================================================================
CREATE TABLE staging_room_bookings (
    staging_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    room_number VARCHAR(50),     -- Various formats
    booking_date VARCHAR(50),    -- Need date standardization
    time_slot VARCHAR(50),       -- Need standardization
    student_id VARCHAR(50),      -- Can be NULL
    duration_hours DECIMAL(4,2),
    purpose VARCHAR(100),
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_quality_flag VARCHAR(20) DEFAULT 'RAW',
    INDEX idx_booking (booking_id),
    INDEX idx_room (room_number)
) ENGINE=InnoDB;

-- ============================================================================
-- DATA QUALITY LOG TABLE
-- ============================================================================
CREATE TABLE data_quality_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(100),
    staging_id INT,
    issue_type VARCHAR(100),
    issue_description TEXT,
    original_value VARCHAR(255),
    corrected_value VARCHAR(255),
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source_table),
    INDEX idx_issue (issue_type)
) ENGINE=InnoDB;

SELECT 'Staging tables created successfully!' AS Status;