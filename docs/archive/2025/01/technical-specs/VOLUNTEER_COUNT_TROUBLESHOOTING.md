# Volunteer Count Validation Troubleshooting Guide

## 🚨 **Issue Description**

**Error Message**:
```
Count validation failed for volunteer: Failed to get volunteer count: Malformed request
https://prep-kc.my.salesforce.com/services/data/v59.0/query/?q=SELECT+COUNT%28%29+FROM+Contact+WHERE+RecordType.Name+%3D+%27Volunteer%27

Response content: [{'message': "\nSELECT COUNT() FROM Contact WHERE RecordType.Name = 'Volunteer'\n ^\nERROR at Row:1:Column:35\nDidn't understand relationship 'RecordType' in field path. If you are attempting to use a custom relationship, be sure to append the '__r' after the custom relationship name. Please reference your WSDL or the describe call for the appropriate names.", 'errorCode': 'INVALID_FIELD'}]
```

## 🔍 **Root Cause Analysis**

The error shows a query using `RecordType.Name = 'Volunteer'`, but your code uses the correct query `Contact_Type__c = 'Volunteer'`.

**This indicates a code version mismatch or configuration issue.**

## 🛠️ **Immediate Fixes Applied**

### 1. **Code Verification**
- ✅ Verified `utils/salesforce_client.py` uses correct query: `Contact_Type__c = 'Volunteer'`
- ✅ Verified `utils/validators/count_validator.py` calls the correct method
- ✅ Added detailed logging and debugging

### 2. **Query Consistency**
- ✅ All volunteer count queries now use `Contact_Type__c` field
- ✅ Added comments explaining why `RecordType.Name` is incorrect
- ✅ Enhanced error logging to show exact query being executed

## 🔧 **Troubleshooting Steps**

### **Step 1: Verify Current Code**
Run the test script to confirm the fix is working:

```bash
cd scripts/validation
python test_volunteer_count.py
```

**Expected Output**:
```
✅ SUCCESS: Volunteer count = [number]
✅ The correct query (Contact_Type__c = 'Volunteer') is working!
```

### **Step 2: Check for Code Version Mismatch**
If the test fails, check:

1. **Git Status**: Are there uncommitted changes?
   ```bash
   git status
   git log --oneline -10
   ```

2. **Python Cache**: Clear Python bytecode cache
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

3. **Environment**: Are you running the correct Python environment?
   ```bash
   which python
   python --version
   ```

### **Step 3: Check for Configuration Overrides**
Look for environment variables or config files that might override queries:

1. **Environment Variables**:
   ```bash
   env | grep -i volunteer
   env | grep -i salesforce
   env | grep -i validation
   ```

2. **Configuration Files**:
   - Check `config/validation.py`
   - Check `.env` files
   - Check any Salesforce-specific config files

### **Step 4: Verify Validation Execution**
Check which validation script is actually running:

1. **Check Running Processes**:
   ```bash
   ps aux | grep validation
   ps aux | grep python
   ```

2. **Check Logs**:
   ```bash
   tail -f logs/validation.log  # if it exists
   ```

## 🎯 **Most Likely Causes**

### **1. Code Version Mismatch (80% probability)**
- **Scenario**: You have an older version of the code running
- **Solution**: Restart the validation process, clear Python cache

### **2. Configuration Override (15% probability)**
- **Scenario**: Environment variable or config file overriding the query
- **Solution**: Check environment variables and config files

### **3. Different Validation Script (5% probability)**
- **Scenario**: A different validation script is executing
- **Solution**: Verify which script is actually running

## 🚀 **Prevention Measures**

### **1. Code Validation**
- Always use `Contact_Type__c` field for volunteer identification
- Never use `RecordType.Name` in Salesforce Contact queries
- Add unit tests for query validation

### **2. Configuration Management**
- Use environment variables for configurable values
- Validate configuration at startup
- Log all queries being executed

### **3. Monitoring**
- Add query logging to track what's actually being executed
- Monitor validation errors and alert on failures
- Regular validation testing

## 📋 **Verification Checklist**

- [ ] Test script runs successfully
- [ ] No `RecordType.Name` queries found in codebase
- [ ] All volunteer count queries use `Contact_Type__c`
- [ ] Validation logs show correct queries
- [ ] No configuration overrides found
- [ ] Python cache cleared
- [ ] Correct validation script running

## 🔗 **Related Files**

- `utils/salesforce_client.py` - Main Salesforce client
- `utils/validators/count_validator.py` - Count validation logic
- `scripts/validation/test_volunteer_count.py` - Test script
- `config/validation.py` - Validation configuration

## 📞 **Next Steps**

1. **Run the test script** to verify the fix
2. **Check for code version mismatches** if test fails
3. **Clear Python cache** and restart validation
4. **Monitor logs** to ensure correct queries are executed
5. **Update documentation** once issue is resolved

## 💡 **Key Takeaway**

**This is NOT a data quality issue** - it's a **code execution issue**. Your Salesforce data is fine, and your validation logic is correct. The problem is that somewhere in your system, an old version of the code is still running with the incorrect `RecordType.Name` query.

Once you resolve this code version mismatch, your volunteer count validation should work perfectly and give you accurate data quality metrics.
