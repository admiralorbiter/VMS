# Volunteer Management System (VMS)

A web-based application for managing volunteers, events, and organizations. The system integrates with Salesforce and uses internal datasets as the single source of truth. Additional data connectors feed secondary information (e.g., event attendance). The goal is to centralize volunteer data, track events, generate useful reports, and maintain accurate attendance records.

## 1. Project Overview

- **Purpose:** Provide a centralized tool to track volunteer activities, events, attendance, and reports.
- **Key Users:** Internal teams managing volunteer data, district coordinators, and eventually volunteers themselves.
- **Primary Datasets:**
  - Pulled from Salesforce
  - Internal datasets
  - Additional connector data (e.g., spreadsheets, attendance logs)

## 2. Tech Stack

- **Front End:** HTML5/CSS3, JavaScript
- **Back End:** Python, Flask with SQLAlchemy
- **Database:** SQLite (with Salesforce sync capability)
- **Authentication:** Flask-Login
- **Forms:** Flask-WTF

## 3. Features

Currently implemented:

1. **Event Management**
   - Create and track events
   - Interactive calendar with color-coded status
   - Event status tracking (Draft, Published, Confirmed, Completed, Cancelled)

2. **Organization Management**
   - Complete organization profiles
   - Directory system
   - Interaction tracking

3. **Volunteer Management**
   - Track volunteers and their skills
   - Engagement history
   - Profile management

4. **Attendance System**
   - Record and monitor attendance
   - Manual input and spreadsheet uploads
   - Attendance reports

5. **Student & Teacher Management**
   - Profile management
   - Attendance tracking
   - Educational program support

6. **Reporting System**
   - Usage reports
   - Organization metrics
   - Data visualization
   - Attendance analytics

7. **Calendar System**
   - Visual calendar interface
   - Color-coded events by status
   - Date range filtering
   - Event details on click

8. **Salesforce Data Validation System** ✅ **NEW - OPERATIONAL**
   - Comprehensive data integrity validation between VMS and Salesforce
   - Count validation, field completeness, and data type checking
   - CLI interface for validation operations
   - Performance monitoring and trend analysis
   - Extensible validation framework for custom business rules

## 4. Setup & Installation

1. **Clone the Repository**
   ```bash
   git clone [repository-url]
   cd VMS
   ```

2. **Set Up Python Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**
   - Create a `.env` file in the root directory
   - Add required environment variables:
     ```
     SECRET_KEY=your-secret-key
     DATABASE_URL=sqlite:///vms.db
     ```

5. **Run the Application**
   ```bash
   # On Windows
   python app.py
   # On Unix/MacOS
   python3 app.py
   ```
   The application will be available at `http://localhost:5000`

6. **Salesforce Data Validation System Setup** ✅ **COMPLETED**
   ```bash
   # Install validation dependencies
   pip install -r requirements.txt

   # Run database migrations
   alembic upgrade head

   # Test the validation system
   python scripts/validation/test_validation_basic.py

   # Run validation operations
   python scripts/validation/run_validation.py --help
   python scripts/validation/run_validation.py fast
   ```

   **Environment Variables for Validation**:
   ```
   SF_USERNAME=your-salesforce-username
   SF_PASSWORD=your-salesforce-password
   SF_SECURITY_TOKEN=your-salesforce-security-token
   VALIDATION_REDIS_HOST=localhost  # Optional: for caching
   VALIDATION_REDIS_PORT=6379       # Optional: for caching
   ```

       **Current Status**: ✅ **Phase 2 Complete - Field Completeness Validation Operational**
    - Fast validation: ✅ Working
    - Slow validation: ✅ Working
    - Count validation: ✅ Working
    - Field completeness validation: ✅ Working (all entity types)
    - Salesforce schema: ✅ Correctly configured
    - Database integration: ✅ Operational
    - Multi-entity support: ✅ Working (volunteer, organization, event, student, teacher)

6. **Create Admin User**
   ```bash
   # In a new terminal window, with virtual environment activated
   # On Windows
   python create_admin.py
   # On Unix/MacOS
   python3 create_admin.py
   ```

## 5. Usage

1. **First Time Setup**
   - After running create_admin.py, log in with the admin credentials
   - Set up initial organization profiles
   - Configure any required integrations

2. **Regular Operations**
   - Access the calendar at `/calendar`
   - Manage events through the events dashboard
   - Track attendance using the attendance system
   - Generate reports as needed

## 6. Development

- **Running Tests**
  ```bash
  pytest
  ```

- **Code Coverage**
  ```bash
  pytest --cov
  ```

## 7. Documentation

Comprehensive documentation is available in the `/docs` folder:

- **[System Overview](docs/01-overview.md)** - Complete system overview and purpose
- **[Architecture](docs/02-architecture.md)** - Technical architecture and design patterns
- **[Data Model](docs/03-data-model.md)** - Database schema and relationships
- **[API Specification](docs/04-api-spec.md)** - API endpoints and usage
- **[Development Guide](docs/05-dev-guide.md)** - Setup and development guidelines
- **[Operations Guide](docs/06-ops-guide.md)** - Deployment and maintenance
- **[Test Guide](docs/07-test-guide.md)** - Testing strategies and practices
- **[FAQ](docs/09-faq.md)** - Frequently asked questions
- **[Feature Matrix](docs/FEATURE_MATRIX.md)** - Feature tracking and status

For quick navigation, see the [Documentation Index](docs/README.md).

## 8. Future Plans

- Email Management System
- Enhanced reporting capabilities
- Mobile-responsive interface improvements
- Advanced search functionality
- API integrations

---

For support or questions, please contact the development team or check the [FAQ](docs/09-faq.md).
