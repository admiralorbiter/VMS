---
title: "VMS Technology Stack"
status: active
doc_type: overview
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["tech-stack", "dependencies", "infrastructure", "vms"]
summary: "Complete technology stack documentation for the VMS system including backend, frontend, database, external integrations, and deployment infrastructure."
canonical: "/docs/living/TechStack.md"
---

# VMS Technology Stack

## 🔧 **Backend Technologies**

### **Core Framework**
- **Python**: 3.8+ (production), 3.9+ (development)
- **Flask**: 2.3+ - Web application framework
- **Werkzeug**: 2.3+ - WSGI utilities (Flask dependency)

### **Database & ORM**
- **SQLite**: 3.35+ - Primary database (development and production)
- **SQLAlchemy**: 1.4+ - Object-relational mapping
- **Alembic**: 1.8+ - Database migration management

### **Authentication & Security**
- **Flask-Login**: 0.6+ - User session management
- **Flask-WTF**: 1.1+ - Form handling and CSRF protection
- **Werkzeug**: Password hashing and security utilities

### **Data Processing & Validation**
- **Pandas**: 1.5+ - Data manipulation and analysis
- **NumPy**: 1.21+ - Numerical computing (Pandas dependency)
- **Pydantic**: 1.10+ - Data validation and settings management

### **API & Integration**
- **Requests**: 2.28+ - HTTP library for external APIs
- **Simple-Salesforce**: 1.12+ - Salesforce API client
- **gspread**: 5.7+ - Google Sheets API client

## 🏗️ **System Architecture Patterns**

### **Data Model Design**
- **Polymorphic Inheritance**: Contact base class with Volunteer/Teacher/Student specialization
- **Normalized Schema**: Follows relational database best practices
- **Audit Trail**: Comprehensive change tracking with timestamps
- **Soft Deletes**: Data preservation with logical deletion

### **Validation Architecture**
- **5-Tier Validation System**: Count, Completeness, Data Type, Relationship, Business Rules
- **Context-Aware Scoring**: Business logic understanding for quality assessment
- **Graduated Severity**: Info (100%), Warning (85%), Error (60%), Critical (30%)
- **Real-time Processing**: Automated validation with immediate feedback

### **Integration Patterns**
- **API-First Design**: RESTful endpoints for all major operations
- **Event-Driven Updates**: Real-time synchronization with external systems
- **Conflict Resolution**: Automated handling of data inconsistencies
- **Rate Limiting**: Protection against API abuse and overload

## 🎨 **Frontend Technologies**

### **Core Technologies**
- **HTML5**: Semantic markup and modern web standards
- **CSS3**: Custom design system with CSS Grid and Flexbox
- **JavaScript**: Vanilla JS (ES6+) - No frameworks

### **Styling & Design**
- **Custom CSS**: Proprietary design system
- **CSS Grid**: Layout system for complex interfaces
- **Flexbox**: Component-level layout
- **CSS Variables**: Theme and color management
- **Responsive Design**: Mobile-first approach

### **JavaScript Libraries**
- **Chart.js**: 3.9+ - Data visualization and charts
- **Date-fns**: 2.29+ - Date manipulation utilities
- **Luxon**: 3.0+ - Advanced date/time handling

## 🗄️ **Database & Storage**

### **Primary Database**
- **SQLite**: File-based database for simplicity
- **Location**: `instance/vms.db` (development), production path TBD
- **Backup**: Automated daily backups to cloud storage

### **External Data Sources**
- **Salesforce CRM**: Primary data source via API
- **Google Sheets**: Secondary data source and export
- **Local Files**: CSV imports and exports

### **Data Models**
- **Core Entities**: Volunteer, Organization, Event, Student, Teacher, School, District
- **Relationships**: Complex many-to-many relationships with junction tables
- **Audit Trail**: Comprehensive change tracking and history

## 🌐 **Infrastructure & Deployment**

### **Hosting Platform**
- **Production**: PythonAnywhere
- **Development**: Local Flask server
- **Port**: 5050 (development), 80/443 (production)

### **Web Server**
- **Development**: Flask development server
- **Production**: WSGI server (PythonAnywhere managed)
- **Static Files**: Served directly by web server

### **Environment Management**
- **Virtual Environment**: Python venv
- **Dependencies**: requirements.txt and requirements-dev.txt
- **Environment Variables**: .env file for configuration

## 🔌 **External Integrations**

### **Salesforce Integration**
- **API Version**: 58.0+
- **Authentication**: OAuth 2.0 with refresh tokens
- **Data Sync**: Automated daily synchronization
- **Entities**: All core VMS entities mapped to Salesforce objects

### **Google Workspace Integration**
- **Google Sheets API**: v4
- **Authentication**: Service account with OAuth 2.0
- **Data Import/Export**: Automated processes
- **File Management**: Google Drive integration

### **Email Services**
- **SMTP**: PythonAnywhere managed
- **Templates**: Jinja2 templating engine
- **Notifications**: Automated email alerts and reports

## 🛠️ **Development Tools**

### **Version Control**
- **Git**: 2.30+
- **GitHub**: Repository hosting and collaboration
- **Branching Strategy**: Feature branches with main branch protection

### **Testing Framework**
- **Pytest**: 7.0+ - Unit and integration testing
- **Coverage**: 6.5+ - Code coverage reporting
- **Test Data**: Fixtures and factories for testing

### **Code Quality**
- **Black**: 22.0+ - Code formatting
- **Flake8**: 5.0+ - Linting and style checking
- **Bandit**: 1.7+ - Security linting
- **Pre-commit**: Git hooks for code quality

### **Documentation**
- **Markdown**: All documentation in Markdown format
- **Mermaid**: Diagrams and flowcharts
- **Static Site**: Documentation served via Flask routes

## 📊 **Monitoring & Logging**

### **Application Logging**
- **Python Logging**: Standard library logging module
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Daily log rotation with compression

### **Performance Monitoring**
- **Flask Profiler**: Development performance profiling
- **Database Queries**: SQLAlchemy query logging
- **Response Times**: Request/response timing

### **Error Tracking**
- **Exception Handling**: Comprehensive try-catch blocks
- **Error Logging**: Detailed error information and stack traces
- **User Feedback**: Bug report system integrated

## 🔒 **Security & Compliance**

### **Authentication & Authorization**
- **Session Management**: Flask-Login with secure sessions
- **Role-Based Access**: Admin, coordinator, and user roles
- **Password Security**: Werkzeug password hashing

### **Data Protection**
- **CSRF Protection**: Flask-WTF CSRF tokens
- **Input Validation**: Pydantic data validation
- **SQL Injection Prevention**: SQLAlchemy parameterized queries

### **API Security**
- **Rate Limiting**: Basic request throttling
- **API Keys**: Secure API key management
- **CORS**: Cross-origin resource sharing configuration

## 📈 **Scalability Considerations**

### **Current Architecture**
- **Single Server**: Monolithic Flask application
- **Database**: Single SQLite instance
- **Caching**: In-memory caching (planned enhancement)

### **Future Enhancements**
- **Database**: Migration to PostgreSQL for production scale
- **Caching**: Redis integration for performance
- **Load Balancing**: Multiple application instances
- **Microservices**: Service decomposition for large scale

## 🔗 **Related Documents**

- **System Overview**: `/docs/living/Overview.md`
- **Development Guide**: `/docs/old/05-dev-guide.md`
- **API Specification**: `/docs/old/04-api-spec.md`
- **Data Model**: `/docs/old/03-data-model.md`

## 📝 **Ask me (examples)**

- "What technologies are used in the VMS backend?"
- "How does the system integrate with Salesforce and Google Sheets?"
- "What is the current hosting and deployment setup?"
- "What are the planned scalability improvements?"
- "How is the development environment configured?"
