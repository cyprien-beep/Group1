
USE library_dw;

-- ============================================================================
-- FACT TABLE: Library Usage Facts
-- Purpose: Central fact table recording all library usage events
-- Grain: One row per library transaction/event
-- ============================================================================
CREATE TABLE fact_library_usage (
    -- Surrogate Primary Key
    usage_key BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Foreign Keys to Dimensions
    date_key INT NOT NULL,
    student_key INT NOT NULL,
    resource_key INT NOT NULL,
    location_key INT,                    -- Nullable (only for room bookings)
    time_slot_key INT,                   -- Nullable (only for room bookings)
    purpose_key INT,                     -- Nullable (only for room bookings)
    
    -- Degenerate Dimensions (attributes that don't warrant their own dimension)
    transaction_id VARCHAR(50),          -- Original transaction ID from source
    usage_type VARCHAR(50) NOT NULL,     -- 'BOOK_CHECKOUT', 'DIGITAL_DOWNLOAD', 'ROOM_BOOKING'
    
    -- Measurable Facts (Metrics)
    checkout_duration_days INT,          -- For book checkouts
    download_count INT DEFAULT 1,        -- For digital resources
    reading_duration_minutes INT,        -- For digital resources
    booking_duration_hours DECIMAL(4,2), -- For room bookings
    
    -- Flags for analytics
    is_returned BOOLEAN DEFAULT FALSE,   -- Book return status
    is_overdue BOOLEAN DEFAULT FALSE,    -- Late return flag
    is_walk_in BOOLEAN DEFAULT FALSE,    -- Room booking walk-in flag
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_date FOREIGN KEY (date_key) 
        REFERENCES dim_date(date_key),
    CONSTRAINT fk_student FOREIGN KEY (student_key) 
        REFERENCES dim_student(student_key),
    CONSTRAINT fk_resource FOREIGN KEY (resource_key) 
        REFERENCES dim_resource(resource_key),
    CONSTRAINT fk_location FOREIGN KEY (location_key) 
        REFERENCES dim_location(location_key),
    CONSTRAINT fk_time_slot FOREIGN KEY (time_slot_key) 
        REFERENCES dim_time_slot(time_slot_key),
    CONSTRAINT fk_purpose FOREIGN KEY (purpose_key) 
        REFERENCES dim_purpose(purpose_key),
    
    -- Indexes for query performance
    INDEX idx_date (date_key),
    INDEX idx_student (student_key),
    INDEX idx_resource (resource_key),
    INDEX idx_usage_type (usage_type),
    INDEX idx_composite_date_student (date_key, student_key),
    INDEX idx_composite_date_usage (date_key, usage_type),
    INDEX idx_transaction (transaction_id)
) ENGINE=InnoDB;

-- ============================================================================
-- Create a view for easy querying (joins dimensions automatically)
-- ============================================================================
CREATE OR REPLACE VIEW vw_library_usage_detailed AS
SELECT 
    -- Fact table metrics
    f.usage_key,
    f.usage_type,
    f.checkout_duration_days,
    f.download_count,
    f.reading_duration_minutes,
    f.booking_duration_hours,
    f.is_returned,
    f.is_overdue,
    
    -- Date dimension attributes
    d.full_date,
    d.day_of_week,
    d.month_name,
    d.quarter,
    d.year,
    d.is_weekend,
    d.academic_term,
    
    -- Student dimension attributes
    s.student_id,
    s.department,
    s.student_type,
    
    -- Resource dimension attributes
    r.resource_id,
    r.resource_type,
    r.resource_title,
    r.resource_category,
    
    -- Location dimension attributes
    l.room_number,
    l.room_type,
    l.capacity,
    
    -- Time slot attributes
    t.time_slot_name,
    t.start_time,
    t.end_time,
    
    -- Purpose attributes
    p.purpose_name,
    p.purpose_category

FROM fact_library_usage f
    INNER JOIN dim_date d ON f.date_key = d.date_key
    INNER JOIN dim_student s ON f.student_key = s.student_key
    INNER JOIN dim_resource r ON f.resource_key = r.resource_key
    LEFT JOIN dim_location l ON f.location_key = l.location_key
    LEFT JOIN dim_time_slot t ON f.time_slot_key = t.time_slot_key
    LEFT JOIN dim_purpose p ON f.purpose_key = p.purpose_key;

SELECT 'Fact table and views created successfully!' AS Status;