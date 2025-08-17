---
title: "VMS Development Onboarding"
status: active
doc_type: overview
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["onboarding", "development", "setup", "vms"]
summary: "90-minute path to first PR for VMS development. Complete environment setup, testing, and contribution workflow for new developers."
canonical: "/docs/living/Onboarding.md"
---

# VMS Development Onboarding

## 🎯 **Goal: First PR in 90 Minutes**

This guide will get you from zero to contributing to the VMS project in under 90 minutes.

You'll set up your development environment, run tests, and make your first contribution.

## 🚀 **Quick Start Checklist**

- [ ] **Environment Setup** (30 minutes)
- [ ] **Code Review** (15 minutes)
- [ ] **Test Run** (15 minutes)
- [ ] **First Change** (20 minutes)
- [ ] **Submit PR** (10 minutes)

## 🔧 **Environment Setup (30 minutes)**

### **Prerequisites**
- **Python**: 3.9+ (check with `python --version`)
- **Git**: 2.30+ (check with `git --version`)
- **Code Editor**: VS Code, PyCharm, or your preference

### **1. Clone Repository**
```bash
git clone https://github.com/your-username/VMS.git
cd VMS
```

### **2. Create Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### **4. Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# (Database paths, API keys, etc.)
```

**Essential Environment Variables:**
```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///instance/your_database.db

# Salesforce Integration
SF_USERNAME=your-salesforce-username
SF_PASSWORD=your-salesforce-password
SF_SECURITY_TOKEN=your-salesforce-security-token
SYNC_AUTH_TOKEN=your-sync-auth-token

# Google Sheets Integration
CLIENT_PROJECTS_SHEET_ID=your-google-sheet-id
SCHOOL_MAPPING_GOOGLE_SHEET=your-school-mapping-sheet
ENCRYPTION_KEY=your-encryption-key
```

### **5. Database Setup**
```bash
# Initialize database
flask db upgrade

# Create admin user (optional)
python scripts/create_admin.py
```

**Database Notes:**
- The app auto-creates missing tables at startup
- New models like `AuditLog` are created automatically in development
- All timestamp columns use UTC with `DateTime(timezone=True)`
- Database-side defaults ensure consistency across environments

### **6. Start Development Server**
```bash
# Run Flask app
python app.py

# Or use Flask CLI
flask run --port 5050
```

**Verify**: Open http://localhost:5050 in your browser

## 🔍 **Code Review (15 minutes)**

### **Project Structure**
```
VMS/
├── app.py                 # Main application entry point
├── models/               # Database models and ORM
├── routes/               # Flask route handlers
├── static/               # CSS, JS, and static assets
├── templates/            # HTML templates
├── utils/                # Utility functions and services
├── tests/                # Test suite
└── docs/                 # Documentation
```

### **Key Files to Understand**
- **`app.py`**: Application configuration and initialization
- **`models/__init__.py`**: Database setup and model registration
- **`routes/__init__.py`**: Route registration and blueprint setup
- **`config/__init__.py`**: Configuration management

### **Development Workflow**
1. **Feature Branch**: Create branch for each feature/fix
2. **Local Development**: Test changes locally
3. **Code Quality**: Run linting and tests
4. **Pull Request**: Submit for review

## 🧪 **Test Run (15 minutes)**

### **Run All Tests**
```bash
# Run entire test suite
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/unit/test_models.py

# Run with verbose output
python -m pytest -v
```

### **Code Quality Checks**
```bash
# Format code
black .

# Lint code
flake8 .

# Security checks
bandit -r .

# Type checking (if using mypy)
mypy .
```

### **Expected Results**
- **Tests**: All tests should pass
- **Coverage**: Aim for 80%+ coverage
- **Linting**: No critical issues
- **Security**: No high-risk vulnerabilities

## ✏️ **First Change (20 minutes)**

### **Choose a Simple Task**
1. **Documentation**: Fix a typo or add a comment
2. **Test**: Add a missing test case
3. **UI**: Small CSS or HTML improvement
4. **Bug**: Fix a minor issue from Bugs.md

### **Example: Add a Test**
```python
# tests/unit/test_models.py
def test_volunteer_creation():
    """Test volunteer model creation with valid data."""
    volunteer = Volunteer(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com"
    )
    assert volunteer.first_name == "John"
    assert volunteer.last_name == "Doe"
    assert volunteer.email == "john.doe@example.com"
```

### **Example: Fix Documentation**
```markdown
# docs/living/Onboarding.md
- [ ] **Test Run** (15 minutes)  # Fixed typo
+ [ ] **Test Run** (15 minutes)
```

### **Best Practices**
- **Small Changes**: Keep changes focused and manageable
- **Clear Messages**: Write descriptive commit messages
- **Test Coverage**: Ensure new code is tested
- **Documentation**: Update docs if needed

## 📤 **Submit PR (10 minutes)**

### **1. Commit Your Changes**
```bash
git add .
git commit -m "feat: add volunteer creation test case

- Added test_volunteer_creation test
- Covers basic volunteer model functionality
- Improves test coverage for models"
```

### **2. Push to Your Branch**
```bash
git push origin feature/your-feature-name
```

### **3. Create Pull Request**
- Go to GitHub repository
- Click "Compare & pull request"
- Fill in PR template:
  - **Title**: Clear, descriptive title
  - **Description**: What changed and why
  - **Type**: Feature, Bug Fix, Documentation, etc.
  - **Testing**: How you tested the changes

### **4. PR Template Example**
```markdown
## Description
Added test case for volunteer model creation to improve test coverage.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [x] Documentation update
- [ ] Test addition

## Testing
- [x] Ran existing tests (all pass)
- [x] Added new test case
- [x] Verified test coverage improved

## Checklist
- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Documentation updated if needed
```

## 🎉 **Congratulations!**

You've successfully:
- ✅ Set up your development environment
- ✅ Understood the project structure
- ✅ Run tests and quality checks
- ✅ Made your first contribution
- ✅ Submitted a pull request

## 🔄 **Next Steps**

### **Continue Contributing**
- **Pick Issues**: Check Bugs.md and Features.md for tasks
- **Join Discussions**: Participate in project planning
- **Improve Tests**: Help increase test coverage
- **Documentation**: Help improve docs and guides

### **Learning Path**
1. **Week 1**: Understand core models and routes
2. **Week 2**: Work on small features and bug fixes
3. **Week 3**: Contribute to larger features
4. **Month 2**: Take ownership of specific areas

### **Resources**
- **Code Quality**: See Philosophy.md for development standards
- **Architecture**: Review Overview.md and TechStack.md
- **Testing**: Check tests/ directory for examples
- **API**: Review API specification in docs

## 🆘 **Troubleshooting**

### **Common Issues**

#### **Database Connection Error**
```bash
# Check database file exists
ls instance/vms.db

# Recreate database if needed
flask db upgrade
```

#### **Import Errors**
```bash
# Ensure virtual environment is activated
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Check Python path
python -c "import sys; print(sys.path)"
```

#### **Test Failures**
```bash
# Check test database
flask db upgrade --directory tests/migrations

# Run tests with verbose output
python -m pytest -v -s
```

#### **Port Already in Use**
```bash
# Check what's using port 5050
# Windows: netstat -ano | findstr 5050
# macOS/Linux: lsof -i :5050

# Use different port
flask run --port 5051
```

## 🔗 **Related Documents**

- **System Overview**: `/docs/living/Overview.md`
- **Technology Stack**: `/docs/living/TechStack.md`
- **Development Guide**: `/docs/old/05-dev-guide.md`
- **API Specification**: `/docs/old/04-api-spec.md`
- **Test Guide**: `/docs/old/07-test-guide.md`

## 📝 **Ask me (examples)**

- "How do I set up the development environment?"
- "What's the project structure and where should I start?"
- "How do I run tests and check code quality?"
- "What's a good first contribution for a new developer?"
- "How do I submit a pull request and what should I include?"
