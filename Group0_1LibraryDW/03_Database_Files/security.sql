-- Set up users and permissions
CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY 'Admin@2024';
CREATE USER IF NOT EXISTS 'etl'@'localhost' IDENTIFIED BY 'Etl@2024';
CREATE USER IF NOT EXISTS 'analyst'@'localhost' IDENTIFIED BY 'Analyst@2024';
CREATE USER IF NOT EXISTS 'department'@'localhost' IDENTIFIED BY 'Dept@2024';

-- Grant permissions
GRANT ALL PRIVILEGES ON library_dw.* TO 'admin'@'localhost';
GRANT SELECT ON library_dw.fact_library_usage TO 'analyst'@'localhost';
GRANT ALL PRIVILEGES ON library_dw_staging.* TO 'etl'@'localhost';
GRANT RELOAD ON *.* TO 'backup_user'@'localhost';
GRANT SELECT, LOCK TABLES ON library_dw.* TO 'backup_user'@'localhost';

-- Create backup user
CREATE USER IF NOT EXISTS 'backup_user'@'localhost' IDENTIFIED BY 'Backup@2024';
GRANT SELECT, RELOAD, LOCK TABLES ON library_dw.* TO 'backup_user'@'localhost';

-- Set session variables for better performance
SET GLOBAL innodb_buffer_pool_size = 268435456;
SET GLOBAL max_connections = 200;
SET GLOBAL query_cache_size = 67108864;
