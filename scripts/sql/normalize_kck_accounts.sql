-- Migrate remaining KCK viewers to district-scoped with USER security level
-- This script completes the migration from legacy KCK_VIEWER to district scoping

-- Migrate remaining KCK viewers to district-scoped with USER security level
UPDATE users
SET security_level = 0,  -- Change from -1 to USER (0)
    scope_type = 'district',
    allowed_districts = '["Kansas City Kansas Public Schools"]'
WHERE security_level = -1;

-- Verify no -1 security levels remain
SELECT COUNT(*) as remaining_kck_viewers
FROM users
WHERE security_level = -1;

-- Show migrated users
SELECT id, username, email, security_level, scope_type, allowed_districts
FROM users
WHERE scope_type = 'district' AND allowed_districts LIKE '%Kansas City Kansas%';
