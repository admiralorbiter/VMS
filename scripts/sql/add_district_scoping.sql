-- Add district scoping columns to users table
-- This script migrates the hardcoded KCK viewer system to flexible district scoping

-- Add new columns for district scoping
ALTER TABLE users ADD COLUMN allowed_districts TEXT;
ALTER TABLE users ADD COLUMN scope_type VARCHAR(20) DEFAULT 'global' NOT NULL;

-- Migrate existing KCK viewers (security_level = -1) to new system
UPDATE users
SET scope_type = 'district',
    allowed_districts = '["Kansas City Kansas Public Schools"]'
WHERE security_level = -1;

-- Optional: Update security_level from -1 to 0 for migrated users
-- Uncomment the line below if you want to normalize security levels
-- UPDATE users SET security_level = 0 WHERE security_level = -1;

-- Verify migration
SELECT id, username, email, security_level, scope_type, allowed_districts
FROM users
WHERE scope_type = 'district' OR security_level = -1;
