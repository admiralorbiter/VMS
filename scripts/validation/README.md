# Validation Scripts

This directory contains all validation-related scripts and tools for the Salesforce Data Validation System.

## 📁 **Scripts Overview**

### **Main CLI Interface**
- **`run_validation.py`** - Command-line interface for running validations
  - `fast` - Quick validation checks
  - `slow` - Comprehensive validation
  - `count` - Record count validation
  - `status` - Check validation run status
  - `recent` - Show recent validation runs
  - `results` - Display validation results

### **Testing Scripts**
- **`test_validation_basic.py`** - Basic functionality tests (6/6 tests passing ✅)
- **`test_validation_minimal.py`** - Minimal dependency tests
- **`test_validation_system.py`** - Comprehensive system tests

## 🚀 **Usage Examples**

### **From Project Root Directory**
```bash
# Run fast validation
python scripts/validation/run_validation.py fast

# Run count validation for volunteers
python scripts/validation/run_validation.py count --entity-type volunteer

# Check status of a validation run
python scripts/validation/run_validation.py status --run-id 123

# Show recent validation runs
python scripts/validation/run_validation.py recent --limit 5

# Run basic tests
python scripts/validation/test_validation_basic.py
```

### **From Validation Scripts Directory**
```bash
cd scripts/validation

# Run validation CLI
python run_validation.py --help

# Run tests
python test_validation_basic.py
```

## 🔧 **Prerequisites**

1. **Database Setup**: Run `alembic upgrade head` from project root
2. **Dependencies**: Install requirements with `pip install -r requirements.txt`
3. **Environment**: Set up validation environment variables (optional)

## 📊 **Current Status**

- ✅ **Phase 1 Complete**: Foundation and infrastructure operational
- ✅ **Database**: Validation tables created and migrated
- ✅ **Core System**: Validation engine and models working
- ✅ **Testing**: All basic tests passing (6/6)

## 🎯 **Next Steps**

- 🚀 **Phase 2**: Implement Field Completeness Validation
- 📊 **Phase 3**: Add Data Type Validation
- 📈 **Phase 4**: Build Validation Dashboard

## 📝 **Notes**

- All scripts should be run from the **project root directory** for proper imports
- The validation system creates and uses `vms.db` SQLite database
- Test scripts verify core functionality without requiring external connections
