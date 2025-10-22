-- Rollback script for district scoping changes
-- Use this if you need to revert the district scoping implementation

-- Restore KCK viewers to original state
UPDATE users
SET security_level = -1,
    scope_type = 'global',
    allowed_districts = NULL
WHERE scope_type = 'district'
  AND allowed_districts LIKE '%Kansas City Kansas%';

-- Remove the new columns
ALTER TABLE users DROP COLUMN allowed_districts;
ALTER TABLE users DROP COLUMN scope_type;

-- Verify rollback
SELECT id, username, email, security_level
FROM users
WHERE security_level = -1;
