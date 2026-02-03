#!/usr/bin/env python3
"""
============================================================================
Library Data Warehouse - ETL Script (ENHANCED NULL HANDLING)
Team Member 2: ETL Specialist
Purpose: Extract, Transform, and Load with Advanced NULL Handling
Features: Imputation strategies + NULL flagging + Quality tracking
============================================================================
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error
import numpy as np
from datetime import datetime, timedelta
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_process.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class LibraryETL:
    """ETL Pipeline with Advanced NULL Handling"""
    
    def __init__(self, db_config):
        """Initialize ETL with database configuration"""
        self.db_config = db_config
        self.conn_staging = None
        self.conn_dw = None
        self.data_quality_issues = []
        self.null_handling_stats = {
            'flagged': 0,
            'imputed': 0,
            'kept_null': 0
        }
        
    def connect_databases(self):
        """Establish connections to staging and DW databases"""
        try:
            self.conn_staging = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database='library_staging',
                buffered=True
            )
            
            self.conn_dw = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database='library_dw',
                buffered=True
            )
            
            logging.info("Database connections established successfully")
            return True
            
        except Error as e:
            logging.error(f"Error connecting to databases: {e}")
            return False
    
    # ========================================================================
    # NULL HANDLING STRATEGIES
    # ========================================================================
    
    def handle_missing_return_date(self, return_date, checkout_date):
        """
        Strategy: FLAG as not returned (business logic)
        NULL return_date means book is still checked out
        """
        if return_date is None or pd.isna(return_date):
            self.null_handling_stats['flagged'] += 1
            self.log_data_quality_issue(
                'NULL Handling - Flagging',
                'Book not yet returned',
                'NULL ReturnDate',
                'Flagged as NOT_RETURNED'
            )
            return None, True  # (value, is_flagged)
        return return_date, False
    
    def handle_missing_duration_minutes(self, duration_minutes, resource_type):
        """
        Strategy: IMPUTE with average based on resource type
        Imputation: Use typical reading times by resource type
        """
        if duration_minutes is None or pd.isna(duration_minutes):
            # Imputation logic: Average reading times by resource type
            imputation_map = {
                'E-book': 45,
                'e-Book': 45,
                'Journal': 30,
                'Article': 20,
                'default': 35
            }
            
            imputed_value = imputation_map.get(resource_type, imputation_map['default'])
            
            self.null_handling_stats['imputed'] += 1
            self.log_data_quality_issue(
                'NULL Handling - Imputation',
                f'Missing duration_minutes for {resource_type}',
                'NULL',
                f'Imputed with {imputed_value} minutes (average for {resource_type})'
            )
            
            return imputed_value, True  # (imputed_value, is_imputed)
        
        return duration_minutes, False
    
    def handle_missing_student_id(self, student_id, context='general'):
        """
        Strategy: FLAG for walk-ins, IMPUTE for data errors
        Walk-ins are legitimate NULLs (flagged)
        Data errors should be investigated (flagged differently)
        """
        if student_id is None or pd.isna(student_id):
            if context == 'room_booking':
                # This is expected - walk-in bookings
                self.null_handling_stats['flagged'] += 1
                self.log_data_quality_issue(
                    'NULL Handling - Flagging',
                    'Walk-in room booking (no student ID)',
                    'NULL StudentID',
                    'Flagged as WALK_IN'
                )
                return 'UNKNOWN', True, 'WALK_IN'  # (value, is_flagged, flag_type)
            else:
                # Unexpected NULL - data quality issue
                self.null_handling_stats['flagged'] += 1
                self.log_data_quality_issue(
                    'NULL Handling - Flagging',
                    'Missing student ID (data error)',
                    'NULL StudentID',
                    'Flagged as DATA_ERROR'
                )
                return 'UNKNOWN', True, 'DATA_ERROR'
        
        return student_id, False, None
    
    def handle_missing_department(self, department, student_id):
        """
        Strategy: IMPUTE from lookup or FLAG as Unknown
        Try to lookup department from other records, otherwise flag
        """
        if department is None or pd.isna(department) or department == '':
            # Try to find department from other records for same student
            if student_id and student_id != 'UNKNOWN':
                imputed_dept = self.lookup_student_department(student_id)
                
                if imputed_dept:
                    self.null_handling_stats['imputed'] += 1
                    self.log_data_quality_issue(
                        'NULL Handling - Imputation',
                        f'Missing department for {student_id}',
                        'NULL',
                        f'Imputed from other records: {imputed_dept}'
                    )
                    return imputed_dept, True
            
            # Cannot impute - flag as Unknown
            self.null_handling_stats['flagged'] += 1
            self.log_data_quality_issue(
                'NULL Handling - Flagging',
                'Unknown department',
                'NULL Department',
                'Flagged as Unknown'
            )
            return 'Unknown', True
        
        return department, False
    
    def lookup_student_department(self, student_id):
        """Helper: Lookup department from staging data"""
        try:
            cursor = self.conn_staging.cursor(dictionary=True)
            cursor.execute("""
                SELECT department 
                FROM staging_book_transactions 
                WHERE student_id = %s 
                  AND department IS NOT NULL 
                  AND department != ''
                LIMIT 1
            """, (student_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result and result['department']:
                return result['department']
            
            return None
        except:
            return None
    
    def handle_missing_checkout_duration(self, checkout_date, return_date):
        """
        Strategy: CALCULATE if possible, FLAG if book not returned
        """
        if return_date is None:
            # Book not returned yet - cannot calculate duration
            return None, True  # Flagged as not returned
        
        try:
            checkout = datetime.strptime(checkout_date, '%Y-%m-%d')
            returned = datetime.strptime(return_date, '%Y-%m-%d')
            duration = (returned - checkout).days
            
            return duration, False
        except:
            self.null_handling_stats['flagged'] += 1
            return None, True
    
    # ========================================================================
    # EXTRACTION PHASE (with NULL tracking)
    # ========================================================================
    
    def extract_book_transactions(self, file_path):
        """Extract book checkout data from CSV"""
        logging.info("Extracting book transactions...")
        try:
            df = pd.read_csv(file_path)
            
            # Track NULL counts BEFORE processing
            null_counts = df.isnull().sum()
            logging.info(f"NULL values in source data: {null_counts.to_dict()}")
            
            # Replace NaN with None for proper NULL handling
            df = df.replace({np.nan: None})
            
            cursor = self.conn_staging.cursor()
            for _, row in df.iterrows():
                query = """
                    INSERT INTO staging_book_transactions 
                    (transaction_id, student_id, book_isbn, checkout_date, 
                     return_date, department, book_category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    row.get('TransactionID'),
                    row.get('StudentID'),
                    row.get('BookISBN'),
                    row.get('CheckoutDate'),
                    row.get('ReturnDate'),
                    row.get('Department'),
                    row.get('BookCategory')
                )
                cursor.execute(query, values)
            
            cursor.close()
            self.conn_staging.commit()
            logging.info(f"Extracted {len(df)} book transactions")
            return len(df)
            
        except Exception as e:
            logging.error(f"Error extracting book transactions: {e}")
            return 0
    
    def extract_digital_downloads(self, file_path):
        """Extract digital resource downloads from Excel"""
        logging.info("Extracting digital downloads...")
        try:
            df_dict = pd.read_excel(file_path, sheet_name=None)
            all_data = pd.concat(df_dict.values(), ignore_index=True)
            
            # Track NULL counts
            null_counts = all_data.isnull().sum()
            logging.info(f"NULL values in digital downloads: {null_counts.to_dict()}")
            
            all_data = all_data.replace({np.nan: None})
            
            cursor = self.conn_staging.cursor()
            for _, row in all_data.iterrows():
                query = """
                    INSERT INTO staging_digital_downloads 
                    (download_date, user_type, resource_type, faculty, 
                     download_count, duration_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    str(row.get('Date', '')) if row.get('Date') is not None else None,
                    row.get('UserType'),
                    row.get('ResourceType'),
                    row.get('Faculty'),
                    row.get('DownloadCount', 1),
                    row.get('Duration_Minutes')
                )
                cursor.execute(query, values)
            
            cursor.close()
            self.conn_staging.commit()
            logging.info(f"Extracted {len(all_data)} digital downloads")
            return len(all_data)
            
        except Exception as e:
            logging.error(f"Error extracting digital downloads: {e}")
            return 0
    
    def extract_room_bookings(self, file_path):
        """Extract room booking data from CSV"""
        logging.info("Extracting room bookings...")
        try:
            df = pd.read_csv(file_path)
            
            # Track NULL counts
            null_counts = df.isnull().sum()
            logging.info(f"NULL values in room bookings: {null_counts.to_dict()}")
            
            df = df.replace({np.nan: None})
            
            cursor = self.conn_staging.cursor()
            for _, row in df.iterrows():
                query = """
                    INSERT INTO staging_room_bookings 
                    (booking_id, room_number, booking_date, time_slot, 
                     student_id, duration_hours, purpose)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    row.get('BookingID'),
                    row.get('RoomNumber'),
                    row.get('BookingDate'),
                    row.get('TimeSlot'),
                    row.get('StudentID'),
                    row.get('DurationHours'),
                    row.get('Purpose')
                )
                cursor.execute(query, values)
            
            cursor.close()
            self.conn_staging.commit()
            logging.info(f"Extracted {len(df)} room bookings")
            return len(df)
            
        except Exception as e:
            logging.error(f"Error extracting room bookings: {e}")
            return 0
    
    # ========================================================================
    # TRANSFORMATION PHASE (with enhanced NULL handling)
    # ========================================================================
    
    def standardize_dates(self, date_str):
        """Standardize various date formats to YYYY-MM-DD"""
        if pd.isna(date_str) or date_str == '' or date_str == 'NULL' or date_str is None:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y-%d-%m',
            '%b %d, %Y',
            '%d-%b-%Y',
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(str(date_str).strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except:
                continue
        
        self.log_data_quality_issue('Date Standardization', 'Invalid date format', date_str, None)
        return None
    
    def standardize_department(self, dept_str):
        """Standardize department names"""
        if pd.isna(dept_str) or dept_str is None:
            return 'Unknown'
        
        dept_mapping = {
            'CS': 'Computer Science',
            'CompSci': 'Computer Science',
            'Computer Science': 'Computer Science',
            'ENG': 'Engineering',
            'Engineering': 'Engineering',
            'Engr': 'Engineering',
            'BUS': 'Business',
            'Business': 'Business',
            'MED': 'Medicine',
            'Medicine': 'Medicine',
            'LAW': 'Law',
            'Law': 'Law',
            'ARTS': 'Arts',
            'Arts': 'Arts',
        }
        
        dept_clean = str(dept_str).strip()
        
        if dept_clean in dept_mapping:
            if dept_clean != dept_mapping[dept_clean]:
                self.log_data_quality_issue('Department Standardization', 'Inconsistent naming', dept_str, dept_mapping[dept_clean])
            return dept_mapping[dept_clean]
        
        return dept_clean
    
    def standardize_room_number(self, room_str):
        """Standardize room number formats"""
        if pd.isna(room_str) or room_str is None:
            return 'UNKNOWN'
        
        room_clean = str(room_str).upper().replace(' ', '').replace('-', '').replace('ROOM', 'R')
        
        match = re.search(r'(\d+)', room_clean)
        if match:
            room_num = match.group(1)
            standardized = f'R{room_num}'
            
            if room_str != standardized:
                self.log_data_quality_issue('Room Number Standardization', 'Inconsistent format', room_str, standardized)
            return standardized
        
        return room_clean
    
    def standardize_time_slot(self, time_str):
        """Standardize time slot descriptions"""
        if pd.isna(time_str) or time_str is None:
            return 'Morning'
        
        time_clean = str(time_str).strip().upper()
        
        if any(x in time_clean for x in ['MORNING', 'AM', '8', '9', '10', '11']):
            return 'Morning'
        elif any(x in time_clean for x in ['AFTERNOON', 'PM', '12', '13', '14', '15', '16']):
            return 'Afternoon'
        elif any(x in time_clean for x in ['EVENING', '17', '18', '19', '20']):
            return 'Evening'
        elif any(x in time_clean for x in ['NIGHT', '21', '22', '23']):
            return 'Night'
        
        return 'Morning'
    
    def remove_duplicates(self, table_name, id_column):
        """Remove duplicate records from staging table"""
        logging.info(f"Removing duplicates from {table_name}...")
        
        try:
            cursor = self.conn_staging.cursor()
            
            query = f"""
                DELETE t1 FROM {table_name} t1
                INNER JOIN {table_name} t2 
                WHERE t1.staging_id > t2.staging_id 
                AND t1.{id_column} = t2.{id_column}
            """
            cursor.execute(query)
            deleted_count = cursor.rowcount
            
            cursor.close()
            self.conn_staging.commit()
            
            if deleted_count > 0:
                logging.info(f"Removed {deleted_count} duplicate records from {table_name}")
            
            return deleted_count
        except Exception as e:
            logging.error(f"Error removing duplicates from {table_name}: {e}")
            return 0
    
    def transform_staging_data(self):
        """Apply all transformations with enhanced NULL handling"""
        logging.info("Starting data transformation with NULL handling...")
        
        # Transform book transactions
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_staging.cursor()
        
        cursor_read.execute("SELECT * FROM staging_book_transactions")
        book_records = cursor_read.fetchall()
        
        for record in book_records:
            clean_checkout = self.standardize_dates(record['checkout_date'])
            
            # Handle missing return date (flagging strategy)
            clean_return, is_not_returned = self.handle_missing_return_date(
                record['return_date'], 
                clean_checkout
            )
            
            # Handle missing department (imputation + flagging)
            clean_dept, was_imputed = self.handle_missing_department(
                record['department'],
                record['student_id']
            )
            clean_dept = self.standardize_department(clean_dept)
            
            cursor_write.execute("""
                UPDATE staging_book_transactions
                SET checkout_date = %s, 
                    return_date = %s, 
                    department = %s, 
                    data_quality_flag = 'CLEANED'
                WHERE staging_id = %s
            """, (clean_checkout, clean_return, clean_dept, record['staging_id']))
        
        cursor_read.close()
        cursor_write.close()
        
        # Transform digital downloads
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_staging.cursor()
        
        cursor_read.execute("SELECT * FROM staging_digital_downloads")
        digital_records = cursor_read.fetchall()
        
        for record in digital_records:
            clean_date = self.standardize_dates(record['download_date'])
            clean_faculty = self.standardize_department(record['faculty'])
            
            # Handle missing duration (imputation strategy)
            clean_duration, was_imputed = self.handle_missing_duration_minutes(
                record['duration_minutes'],
                record['resource_type']
            )
            
            cursor_write.execute("""
                UPDATE staging_digital_downloads
                SET download_date = %s, 
                    faculty = %s, 
                    duration_minutes = %s,
                    resource_type = TRIM(resource_type), 
                    data_quality_flag = 'CLEANED'
                WHERE staging_id = %s
            """, (clean_date, clean_faculty, clean_duration, record['staging_id']))
        
        cursor_read.close()
        cursor_write.close()
        
        # Transform room bookings
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_staging.cursor()
        
        cursor_read.execute("SELECT * FROM staging_room_bookings")
        room_records = cursor_read.fetchall()
        
        for record in room_records:
            clean_date = self.standardize_dates(record['booking_date'])
            clean_room = self.standardize_room_number(record['room_number'])
            clean_timeslot = self.standardize_time_slot(record['time_slot'])
            
            # Handle missing student ID (flagging for walk-ins)
            clean_student, was_flagged, flag_type = self.handle_missing_student_id(
                record['student_id'],
                context='room_booking'
            )
            
            cursor_write.execute("""
                UPDATE staging_room_bookings
                SET booking_date = %s, 
                    room_number = %s, 
                    time_slot = %s,
                    student_id = %s,
                    data_quality_flag = 'CLEANED'
                WHERE staging_id = %s
            """, (clean_date, clean_room, clean_timeslot, clean_student, record['staging_id']))
        
        cursor_read.close()
        cursor_write.close()
        
        self.conn_staging.commit()
        logging.info("Data transformation completed")
        
        # Log NULL handling statistics
        logging.info(f"NULL Handling Summary:")
        logging.info(f"  - Flagged: {self.null_handling_stats['flagged']}")
        logging.info(f"  - Imputed: {self.null_handling_stats['imputed']}")
        logging.info(f"  - Kept NULL: {self.null_handling_stats['kept_null']}")
    
    def log_data_quality_issue(self, issue_type, description, original, corrected):
        """Log data quality issues for reporting"""
        self.data_quality_issues.append({
            'issue_type': issue_type,
            'description': description,
            'original_value': str(original) if original is not None else 'NULL',
            'corrected_value': str(corrected) if corrected is not None else 'NULL',
            'timestamp': datetime.now()
        })
    
    # ========================================================================
    # LOADING PHASE (same as before)
    # ========================================================================
    
    def populate_date_dimension(self, start_year=2023, end_year=2027):
        """Populate date dimension with calendar data"""
        logging.info("Populating date dimension...")
        
        cursor = self.conn_dw.cursor()
        
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        
        current_date = start_date
        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))
            
            month = current_date.month
            if month in [9, 10, 11, 12]:
                term = 'Fall'
            elif month in [1, 2, 3, 4, 5]:
                term = 'Spring'
            else:
                term = 'Summer'
            
            query = """
                INSERT IGNORE INTO dim_date 
                (date_key, full_date, day_of_week, day_of_month, day_of_year,
                 week_of_year, month_number, month_name, quarter, year,
                 is_weekend, academic_term)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                date_key,
                current_date.date(),
                current_date.strftime('%A'),
                current_date.day,
                current_date.timetuple().tm_yday,
                current_date.isocalendar()[1],
                current_date.month,
                current_date.strftime('%B'),
                (current_date.month - 1) // 3 + 1,
                current_date.year,
                current_date.weekday() >= 5,
                term
            )
            
            cursor.execute(query, values)
            current_date += timedelta(days=1)
        
        cursor.close()
        self.conn_dw.commit()
        logging.info("Date dimension populated")
    
    def load_student_dimension(self):
        """Load student dimension from staging data"""
        logging.info("Loading student dimension...")
        
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_dw.cursor()
        
        cursor_read.execute("""
            SELECT DISTINCT student_id, department
            FROM staging_book_transactions
            WHERE student_id IS NOT NULL AND data_quality_flag = 'CLEANED'
        """)
        
        students = cursor_read.fetchall()
        count = 0
        
        for row in students:
            cursor_write.execute("""
                INSERT IGNORE INTO dim_student 
                (student_id, department, student_type, enrollment_date, effective_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['student_id'], row['department'], 'Student', 
                  datetime.now().date(), datetime.now().date()))
            count += cursor_write.rowcount
        
        cursor_read.execute("""
            SELECT DISTINCT student_id
            FROM staging_room_bookings
            WHERE student_id IS NOT NULL 
              AND student_id != 'UNKNOWN'
              AND data_quality_flag = 'CLEANED'
        """)
        
        students = cursor_read.fetchall()
        
        for row in students:
            cursor_write.execute("""
                INSERT IGNORE INTO dim_student 
                (student_id, department, student_type, enrollment_date, effective_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['student_id'], 'Unknown', 'Student', 
                  datetime.now().date(), datetime.now().date()))
            count += cursor_write.rowcount
        
        cursor_read.close()
        cursor_write.close()
        self.conn_dw.commit()
        logging.info(f"Loaded {count} students into dimension table")
    
    def load_resource_dimension(self):
        """Load resource dimension from staging data"""
        logging.info("Loading resource dimension...")
        
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_dw.cursor()
        
        cursor_read.execute("""
            SELECT DISTINCT book_isbn, book_category
            FROM staging_book_transactions
            WHERE book_isbn IS NOT NULL AND data_quality_flag = 'CLEANED'
        """)
        
        resources = cursor_read.fetchall()
        count = 0
        
        for row in resources:
            cursor_write.execute("""
                INSERT IGNORE INTO dim_resource 
                (resource_id, resource_type, resource_title, resource_category)
                VALUES (%s, %s, %s, %s)
            """, (row['book_isbn'], 'Physical Book', 
                  f'Book {row["book_isbn"]}', row['book_category']))
            count += cursor_write.rowcount
        
        cursor_read.execute("""
            SELECT DISTINCT resource_type, faculty
            FROM staging_digital_downloads
            WHERE resource_type IS NOT NULL AND data_quality_flag = 'CLEANED'
        """)
        
        resources = cursor_read.fetchall()
        
        for row in resources:
            resource_id = f"DIGITAL_{row['resource_type']}_{row['faculty']}"
            cursor_write.execute("""
                INSERT IGNORE INTO dim_resource 
                (resource_id, resource_type, resource_title, resource_category)
                VALUES (%s, %s, %s, %s)
            """, (resource_id, row['resource_type'], 
                  f"{row['resource_type']} - {row['faculty']}", 'Digital'))
            count += cursor_write.rowcount
        
        cursor_read.close()
        cursor_write.close()
        self.conn_dw.commit()
        logging.info(f"Loaded {count} resources into dimension table")
    
    def load_location_dimension(self):
        """Load location dimension from staging data"""
        logging.info("Loading location dimension...")
        
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        cursor_write = self.conn_dw.cursor()
        
        cursor_read.execute("""
            SELECT DISTINCT room_number
            FROM staging_room_bookings
            WHERE room_number IS NOT NULL AND data_quality_flag = 'CLEANED'
        """)
        
        locations = cursor_read.fetchall()
        count = 0
        
        for row in locations:
            room_num = row['room_number']
            floor = int(room_num[1]) if len(room_num) > 1 and room_num[1].isdigit() else 1
            
            cursor_write.execute("""
                INSERT IGNORE INTO dim_location 
                (room_number, room_type, capacity, floor_number, building)
                VALUES (%s, %s, %s, %s, %s)
            """, (room_num, 'Study Room', 4, floor, 'Main Library'))
            count += cursor_write.rowcount
        
        cursor_read.close()
        cursor_write.close()
        self.conn_dw.commit()
        logging.info(f"Loaded {count} locations into dimension table")
    
    def load_fact_table(self):
        """Load fact table from staging data"""
        logging.info("Loading fact table...")
        
        # Load book checkouts
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        
        cursor_read.execute("""
            SELECT * FROM staging_book_transactions
            WHERE data_quality_flag = 'CLEANED' AND checkout_date IS NOT NULL
        """)
        
        book_records = cursor_read.fetchall()
        count = 0
        
        for row in book_records:
            cursor_write = self.conn_dw.cursor(buffered=True)
            
            date_key = int(datetime.strptime(row['checkout_date'], '%Y-%m-%d').strftime('%Y%m%d'))
            
            cursor_write.execute("SELECT student_key FROM dim_student WHERE student_id = %s AND is_current = TRUE", (row['student_id'],))
            result = cursor_write.fetchone()
            student_key = result[0] if result else 1
            
            cursor_write.execute("SELECT resource_key FROM dim_resource WHERE resource_id = %s", (row['book_isbn'],))
            result = cursor_write.fetchone()
            resource_key = result[0] if result else 1
            
            checkout_duration, is_flagged = self.handle_missing_checkout_duration(
                row['checkout_date'],
                row['return_date']
            )
            
            cursor_write.execute("""
                INSERT INTO fact_library_usage 
                (date_key, student_key, resource_key, transaction_id, usage_type, 
                 checkout_duration_days, is_returned)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (date_key, student_key, resource_key, row['transaction_id'], 
                  'BOOK_CHECKOUT', checkout_duration, row['return_date'] is not None))
            
            cursor_write.close()
            count += 1
        
        cursor_read.close()
        self.conn_dw.commit()
        logging.info(f"Loaded {count} book checkout facts")
        
        # Load room bookings
        cursor_read = self.conn_staging.cursor(dictionary=True, buffered=True)
        
        cursor_read.execute("""
            SELECT * FROM staging_room_bookings
            WHERE data_quality_flag = 'CLEANED' AND booking_date IS NOT NULL
        """)
        
        room_records = cursor_read.fetchall()
        count = 0
        
        for row in room_records:
            cursor_write = self.conn_dw.cursor(buffered=True)
            
            date_key = int(datetime.strptime(row['booking_date'], '%Y-%m-%d').strftime('%Y%m%d'))
            
            student_key = 1
            is_walk_in = False
            
            if row['student_id'] and row['student_id'] != 'UNKNOWN':
                cursor_write.execute("SELECT student_key FROM dim_student WHERE student_id = %s AND is_current = TRUE", (row['student_id'],))
                result = cursor_write.fetchone()
                if result:
                    student_key = result[0]
            else:
                is_walk_in = True
            
            cursor_write.execute("SELECT location_key FROM dim_location WHERE room_number = %s", (row['room_number'],))
            result = cursor_write.fetchone()
            location_key = result[0] if result else 1
            
            cursor_write.execute("SELECT time_slot_key FROM dim_time_slot WHERE time_slot_name = %s", (row['time_slot'],))
            result = cursor_write.fetchone()
            time_slot_key = result[0] if result else 1
            
            cursor_write.execute("SELECT purpose_key FROM dim_purpose WHERE purpose_name = %s", (row['purpose'],))
            result = cursor_write.fetchone()
            purpose_key = result[0] if result else 5
            
            cursor_write.execute("""
                INSERT INTO fact_library_usage 
                (date_key, student_key, resource_key, location_key, time_slot_key, purpose_key, 
                 transaction_id, usage_type, booking_duration_hours, is_walk_in)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (date_key, student_key, 1, location_key, time_slot_key, purpose_key, 
                  row['booking_id'], 'ROOM_BOOKING', row['duration_hours'], is_walk_in))
            
            cursor_write.close()
            count += 1
        
        cursor_read.close()
        self.conn_dw.commit()
        logging.info(f"Loaded {count} room booking facts")
    
    def generate_data_quality_report(self):
        """Generate comprehensive data quality report with NULL handling stats"""
        report = {
            'total_issues': len(self.data_quality_issues),
            'issues_by_type': {},
            'null_handling': self.null_handling_stats,
            'timestamp': datetime.now()
        }
        
        for issue in self.data_quality_issues:
            issue_type = issue['issue_type']
            if issue_type not in report['issues_by_type']:
                report['issues_by_type'][issue_type] = 0
            report['issues_by_type'][issue_type] += 1
        
        logging.info(f"Data Quality Report: {report}")
        
        # FIX: Added encoding='utf-8' to support Unicode characters
        with open('data_quality_report.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DATA QUALITY REPORT (with NULL Handling)\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Report Generated: {report['timestamp']}\n")
            f.write(f"Total Issues Found: {report['total_issues']}\n\n")
            
            f.write("NULL HANDLING STATISTICS:\n")
            f.write(f"  - Values Flagged: {report['null_handling']['flagged']}\n")
            f.write(f"  - Values Imputed: {report['null_handling']['imputed']}\n")
            f.write(f"  - Values Kept NULL: {report['null_handling']['kept_null']}\n\n")
            
            f.write("Issues by Type:\n")
            for issue_type, count in sorted(report['issues_by_type'].items()):
                f.write(f"  - {issue_type}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("NULL HANDLING STRATEGIES APPLIED:\n")
            f.write("=" * 80 + "\n")
            f.write("1. ReturnDate = NULL → FLAGGED as 'Book not returned'\n")
            f.write("2. Duration_Minutes = NULL → IMPUTED with average by resource type\n")
            f.write("3. StudentID = NULL (room bookings) → FLAGGED as 'Walk-in'\n")
            f.write("4. Department = NULL → IMPUTED from other records OR flagged as 'Unknown'\n")
            f.write("5. CheckoutDuration = NULL → CALCULATED if return date exists\n")
        
        return report
    
    def run_full_etl(self, book_file, digital_file, room_file):
        """Execute complete ETL pipeline with NULL handling"""
        logging.info("=" * 80)
        logging.info("Starting Full ETL Process (with NULL Handling)")
        logging.info("=" * 80)
        
        if not self.connect_databases():
            return False
        
        try:
            logging.info("\n--- EXTRACTION PHASE ---")
            self.extract_book_transactions(book_file)
            self.extract_digital_downloads(digital_file)
            self.extract_room_bookings(room_file)
            
            logging.info("\n--- TRANSFORMATION PHASE (with NULL Handling) ---")
            self.remove_duplicates('staging_book_transactions', 'transaction_id')
            self.remove_duplicates('staging_room_bookings', 'booking_id')
            self.transform_staging_data()
            
            logging.info("\n--- LOADING PHASE ---")
            self.populate_date_dimension()
            self.load_student_dimension()
            self.load_resource_dimension()
            self.load_location_dimension()
            self.load_fact_table()
            
            logging.info("\n--- GENERATING REPORT ---")
            self.generate_data_quality_report()
            
            logging.info("=" * 80)
            logging.info("ETL Process Completed Successfully!")
            logging.info("=" * 80)
            
            return True
            
        except Exception as e:
            logging.error(f"ETL Process Failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
        finally:
            if self.conn_staging:
                self.conn_staging.close()
            if self.conn_dw:
                self.conn_dw.close()


if __name__ == "__main__":
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',  
        'port': 3306
    }
    
    etl = LibraryETL(db_config)
    
    success = etl.run_full_etl(
        book_file='../09_Source_Data/book_transactions.csv',
        digital_file='../09_Source_Data/digital_usage.xlsx',
        room_file='../09_Source_Data/room_bookings.csv'
    )
    
    if success:
        print("\n" + "=" * 80)
        print(" ETL COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNULL Handling Applied:")
        print("  ✓ Flagged missing values with business meaning")
        print("  ✓ Imputed missing values where appropriate")
        print("  ✓ Tracked all NULL handling decisions")
        print("\nCheck data_quality_report.txt for detailed NULL handling statistics")
    else:
        print("\n" + "=" * 80)
        print(" ETL FAILED")
        print("=" * 80)
        print("Check etl_process.log for details")