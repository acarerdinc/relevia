-- WARNING: This will DELETE all users and recreate the table
-- Only run this if you're sure you want to reset all user data

-- Drop the users table completely
DROP TABLE IF EXISTS users CASCADE;

-- Recreate the users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert single user with hashed password
-- Email: info@acarerdinc.com
-- Password: zazarov123
-- Note: This hash was generated using bcrypt with passlib
INSERT INTO users (email, username, hashed_password, is_active) VALUES
('info@acarerdinc.com', 'acarerdinc', '$2b$12$KvN3XmHhXiU8h7yYeqLWaOU./H0kKhJVmZfbQj9O3xlx7lAKfKYhq', true);

-- Verify the user was created
SELECT id, email, username, is_active, created_at FROM users;