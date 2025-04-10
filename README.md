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

## 7. Future Plans

- Email Management System
- Enhanced reporting capabilities
- Mobile-responsive interface improvements
- Advanced search functionality
- API integrations

---

For support or questions, please contact the development team.
