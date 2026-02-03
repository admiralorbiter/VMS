# Developer Guide

Get from zero to contributing in under 90 minutes.

---

## Quick Start Checklist

- [ ] Environment Setup (30 min)
- [ ] Code Review (15 min)
- [ ] Test Run (15 min)
- [ ] First Change (20 min)
- [ ] Submit PR (10 min)

---

## Environment Setup

### Prerequisites

- **Python**: 3.9+
- **Git**: 2.30+
- **Editor**: VS Code, PyCharm, or preference

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/your-username/VMS.git
cd VMS

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Create virtual environment (macOS/Linux)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env
```

**Essential variables in `.env`:**

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/your_database.db

# Salesforce (optional for local dev)
SF_USERNAME=your-salesforce-username
SF_PASSWORD=your-salesforce-password
SF_SECURITY_TOKEN=your-salesforce-security-token

# Google Sheets (optional for local dev)
CLIENT_PROJECTS_SHEET_ID=your-google-sheet-id
```

### 3. Database Setup

```bash
# Initialize database
flask db upgrade

# Create admin user (optional)
python scripts/create_admin.py
```

### 4. Start Development Server

```bash
python app.py
# Or: flask run --port 5050
```

**Verify**: Open http://localhost:5050

---

## Project Structure

```
VMS/
├── app.py                 # Application entry point
├── models/               # Database models
├── routes/               # Flask route handlers
├── static/               # CSS, JS, assets
├── templates/            # HTML templates
├── utils/                # Utility functions
├── tests/                # Test suite
└── documentation/        # Project documentation
```

### Key Files

| File | Purpose |
|------|---------|
| `app.py` | App configuration and initialization |
| `models/__init__.py` | Database setup and model registration |
| `routes/__init__.py` | Route registration and blueprints |
| `config/__init__.py` | Configuration management |

---

## Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific file
python -m pytest tests/unit/test_models.py

# Verbose output
python -m pytest -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Security checks
bandit -r .
```

**Expected Results:**
- All tests pass
- 80%+ coverage target
- No critical lint issues

---

## Making Your First Change

### Good First Tasks

1. Fix a typo in documentation
2. Add a missing test case
3. Small CSS/HTML improvement
4. Fix a minor bug

### Example: Add a Test

```python
# tests/unit/test_models.py
def test_volunteer_creation():
    """Test volunteer model creation."""
    volunteer = Volunteer(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com"
    )
    assert volunteer.first_name == "John"
    assert volunteer.last_name == "Doe"
```

---

## Submitting a PR

### 1. Commit Changes

```bash
git add .
git commit -m "feat: add volunteer creation test case

- Added test_volunteer_creation test
- Improves test coverage for models"
```

### 2. Push & Create PR

```bash
git push origin feature/your-feature-name
```

Then on GitHub:
1. Click "Compare & pull request"
2. Fill in title and description
3. Select reviewers

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [x] Test addition

## Testing
- [x] Ran existing tests
- [x] Added new tests if needed

## Checklist
- [x] Code follows style guidelines
- [x] Self-review completed
```

---

## Troubleshooting

### Database Connection Error

```bash
# Check database exists
ls instance/vms.db

# Recreate if needed
flask db upgrade
```

### Import Errors

```bash
# Ensure venv is activated
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Check Python path
python -c "import sys; print(sys.path)"
```

### Port Already in Use

```bash
# Windows
netstat -ano | findstr 5050

# macOS/Linux
lsof -i :5050

# Use different port
flask run --port 5051
```

---

## Next Steps

### Learning Path

| Week | Focus |
|------|-------|
| 1 | Understand core models and routes |
| 2 | Work on small features and bug fixes |
| 3 | Contribute to larger features |
| 4+ | Take ownership of specific areas |

### Resources

- [Codebase Structure](codebase-structure) — Detailed code organization
- [CLI Reference](cli-reference) — Common commands
- [Architecture](architecture) — System design
