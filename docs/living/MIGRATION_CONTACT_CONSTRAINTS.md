# Contact Model Constraints Migration

## Overview
Migration `e5801d458e9f` adds database constraints and indexes to the Contact model and related tables (Phone, Email, Address) to improve data integrity and query performance.

## Changes Applied

### 1. Database Constraints
- **Phone.number**: Changed from `nullable=True` to `nullable=False` (required)
- **Email.email**: Changed from `nullable=True` to `nullable=False` (required)

### 2. Indexes Added

#### Phone Table
- `ix_phone_contact_id` - Index on foreign key for faster contact lookups
- `ix_phone_primary` - Index on primary flag for primary phone queries
- `idx_phone_contact_primary` - Composite index (contact_id, primary) for optimized primary phone lookups

#### Email Table
- `ix_email_contact_id` - Index on foreign key for faster contact lookups
- `ix_email_primary` - Index on primary flag for primary email queries
- `idx_email_contact_primary` - Composite index (contact_id, primary) for optimized primary email lookups

#### Address Table
- `ix_address_contact_id` - Index on foreign key for faster contact lookups
- `ix_address_zip_code` - Index on zip_code for local status calculations
- `ix_address_primary` - Index on primary flag for primary address queries
- `idx_address_contact_primary` - Composite index (contact_id, primary) for optimized primary address lookups

## Data Migration

### Pre-Migration Data Cleanup
The migration automatically removes invalid records before applying constraints:
- Deletes phone records with NULL or empty `number` values
- Deletes email records with NULL or empty `email` values

### Data Validation
Before applying the migration, run:
```bash
python scripts/maintenance/check_contact_data_before_migration.py
```

This script checks for invalid records and reports:
- Number of phone records with NULL/empty numbers
- Number of email records with NULL/empty addresses
- Detailed list of affected records (first 10 shown)

## Migration Details

- **Revision ID**: `e5801d458e9f`
- **Parent Revision**: `65611e539650`
- **Migration File**: `alembic/versions/e5801d458e9f_add_contact_model_constraints_and_indexes.py`

## Application

The migration was applied on:
- Date: 2025-11-01 (estimated based on migration creation date)
- Status: ✅ Applied successfully
- Invalid Records Found: 0 (all data was clean)

## Rollback

If needed, the migration can be rolled back using:
```bash
alembic downgrade 65611e539650
```

The downgrade will:
1. Remove NOT NULL constraints (make fields nullable again)
2. Remove all added indexes

**Warning**: Rolling back will remove data integrity constraints. Only rollback if absolutely necessary.

## Impact

### Positive Impacts
- ✅ Improved data integrity - prevents NULL values in critical fields
- ✅ Better query performance - indexes speed up common lookups
- ✅ Automatic validation - SQLAlchemy event listeners ensure data consistency

### Breaking Changes
- ⚠️ Phone.number is now required when creating Phone records
- ⚠️ Email.email is now required when creating Email records
- ⚠️ Any code that creates Phone/Email records without these fields will fail

### Code Updates Required
All code creating Phone or Email records must ensure:
```python
# Phone must have number
phone = Phone(
    contact_id=contact.id,
    number="555-123-4567",  # Required!
    primary=True
)

# Email must have email
email = Email(
    contact_id=contact.id,
    email="user@example.com",  # Required!
    primary=True
)
```

## Testing

After migration, run tests to verify:
```bash
pytest tests/unit/models/test_contact.py -v
```

Key test cases:
- `test_phone_number_required_constraint` - Verifies Phone.number is required
- `test_email_address_required_constraint` - Verifies Email.email is required
- `test_automatic_primary_phone_validation` - Tests automatic primary validation
- `test_automatic_primary_email_validation` - Tests automatic primary validation

## Related Changes

This migration complements the model improvements in `models/contact.py`:
- Added automatic primary status validation via SQLAlchemy event listeners
- Enhanced documentation and error handling
- Added `to_dict()` methods to Phone and Address models
- Added `__repr__()` and `__str__()` methods to all models

## References

- Model File: `models/contact.py`
- Migration File: `alembic/versions/e5801d458e9f_add_contact_model_constraints_and_indexes.py`
- Data Check Script: `scripts/maintenance/check_contact_data_before_migration.py`
- Test File: `tests/unit/models/test_contact.py`
