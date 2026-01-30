
USE library_dw;

-- ============================================================================
-- DIMENSION 1: Date Dimension
-- Purpose: Standardized date hierarchy for time-based analysis
-- ============================================================================
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,           -- Format: YYYYMMDD (e.g., 20240115)
    full_date DATE NOT NULL UNIQUE,
    day_of_week VARCHAR(10),            -- Monday, Tuesday, etc.
    day_of_month INT,
    day_of_year INT,
    week_of_year INT,
    month_number INT,
    month_name VARCHAR(10),
    quarter INT,
    year INT,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE,
    academic_term VARCHAR(20),          -- Fall, Spring, Summer
    INDEX idx_full_date (full_date),
    INDEX idx_year_month (year, month_number),
    INDEX idx_quarter (year, quarter)
) ENGINE=InnoDB;

-- ============================================================================
-- DIMENSION 2: Student Dimension
-- Purpose: Student information and demographics
-- ============================================================================
CREATE TABLE dim_student (
    student_key INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL UNIQUE,
    department VARCHAR(100),
    student_type VARCHAR(50),           -- Undergraduate, Graduate, Faculty, Staff
    enrollment_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    -- SCD Type 2 fields for tracking changes
    effective_date DATE,
    expiry_date DATE DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    INDEX idx_student_id (student_id),
    INDEX idx_department (department),
    INDEX idx_student_type (student_type),
    INDEX idx_current (is_current)
) ENGINE=InnoDB;

-- ============================================================================
-- DIMENSION 3: Resource Dimension
-- Purpose: Library resources (books, e-books, journals)
-- ============================================================================
CREATE TABLE dim_resource (
    resource_key INT AUTO_INCREMENT PRIMARY KEY,
    resource_id VARCHAR(50) NOT NULL,   -- ISBN or unique identifier
    resource_type VARCHAR(50),          -- Physical Book, E-book, Journal, Article
    resource_title VARCHAR(255),
    resource_category VARCHAR(100),     -- Fiction, Reference, Textbook, etc.
    author VARCHAR(255),
    publication_year INT,
    is_available BOOLEAN DEFAULT TRUE,
    INDEX idx_resource_id (resource_id),
    INDEX idx_resource_type (resource_type),
    INDEX idx_category (resource_category)
) ENGINE=InnoDB;

-- ============================================================================
-- DIMENSION 4: Location Dimension
-- Purpose: Physical locations (study rooms)
-- ============================================================================
CREATE TABLE dim_location (
    location_key INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(20) NOT NULL UNIQUE,
    room_type VARCHAR(50),              -- Study Room, Meeting Room, Computer Lab
    capacity INT,
    floor_number INT,
    building VARCHAR(50),
    has_computers BOOLEAN DEFAULT FALSE,
    has_whiteboard BOOLEAN DEFAULT FALSE,
    is_accessible BOOLEAN DEFAULT TRUE,
    INDEX idx_room_number (room_number),
    INDEX idx_room_type (room_type)
) ENGINE=InnoDB;

-- ============================================================================
-- DIMENSION 5: Time Slot Dimension
-- Purpose: Standardized time periods for room bookings
-- ============================================================================
CREATE TABLE dim_time_slot (
    time_slot_key INT AUTO_INCREMENT PRIMARY KEY,
    time_slot_name VARCHAR(50) NOT NULL UNIQUE,  -- Morning, Afternoon, Evening
    start_time TIME,
    end_time TIME,
    slot_duration_hours DECIMAL(4,2),
    is_peak_hour BOOLEAN DEFAULT FALSE,
    INDEX idx_time_slot_name (time_slot_name)
) ENGINE=InnoDB;

-- ============================================================================
-- DIMENSION 6: Purpose Dimension (for room bookings)
-- Purpose: Categorize room booking purposes
-- ============================================================================
CREATE TABLE dim_purpose (
    purpose_key INT AUTO_INCREMENT PRIMARY KEY,
    purpose_name VARCHAR(100) NOT NULL UNIQUE,
    purpose_category VARCHAR(50),        -- Individual Study, Group Work, Meeting
    INDEX idx_purpose_name (purpose_name)
) ENGINE=InnoDB;

-- ============================================================================
-- Insert default values for unknown/missing dimension records
-- ============================================================================

-- Unknown Student (for missing StudentID in room bookings)
INSERT INTO dim_student 
    (student_id, department, student_type, enrollment_date, effective_date) 
VALUES 
    ('UNKNOWN', 'Unknown', 'Unknown', '1900-01-01', '1900-01-01');

-- Unknown Resource
INSERT INTO dim_resource 
    (resource_id, resource_type, resource_title, resource_category) 
VALUES 
    ('UNKNOWN', 'Unknown', 'Unknown Resource', 'Unknown');

-- Unknown Location
INSERT INTO dim_location 
    (room_number, room_type, capacity, floor_number, building) 
VALUES 
    ('UNKNOWN', 'Unknown', 0, 0, 'Unknown');

-- Default Time Slots
INSERT INTO dim_time_slot (time_slot_name, start_time, end_time, slot_duration_hours, is_peak_hour) 
VALUES 
    ('Morning', '08:00:00', '12:00:00', 4.0, TRUE),
    ('Afternoon', '12:00:00', '17:00:00', 5.0, TRUE),
    ('Evening', '17:00:00', '21:00:00', 4.0, FALSE),
    ('Night', '21:00:00', '23:00:00', 2.0, FALSE);

-- Default Purposes
INSERT INTO dim_purpose (purpose_name, purpose_category) 
VALUES 
    ('Study', 'Individual Study'),
    ('Group Project', 'Group Work'),
    ('Meeting', 'Meeting'),
    ('Research', 'Individual Study'),
    ('Unknown', 'Unknown');

SELECT 'Dimension tables created successfully!' AS Status;