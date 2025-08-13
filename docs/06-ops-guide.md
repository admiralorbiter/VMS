---
title: "VMS Operations Guide"
description: "Complete operations guide for deploying, monitoring, and maintaining the Volunteer Management System"
tags: [operations, deployment, monitoring, maintenance, troubleshooting]
---

# VMS Operations Guide

## 🚀 Deployment

### Production Environment Setup

#### Prerequisites

- **Server**: Ubuntu 20.04 LTS or higher
- **Python**: 3.8 or higher
- **Database**: PostgreSQL 12 or higher (recommended for production)
- **Web Server**: Nginx
- **Process Manager**: Systemd or Supervisor
- **SSL Certificate**: Let's Encrypt or commercial certificate

#### Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib

# Create application user
sudo useradd -m -s /bin/bash vms
sudo usermod -aG sudo vms
```

#### Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE vms_production;
CREATE USER vms_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE vms_production TO vms_user;
\q
```

#### Application Deployment

```bash
# Switch to application user
sudo su - vms

# Clone repository
git clone <repository-url> /home/vms/vms
cd /home/vms/vms

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://vms_user:secure_password@localhost/vms_production
SALESFORCE_CLIENT_ID=your-salesforce-client-id
SALESFORCE_CLIENT_SECRET=your-salesforce-client-secret
LOG_LEVEL=INFO
EOF

# Initialize database
python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.create_all()"

# Create admin user
python scripts/create_admin.py
```

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/vms
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Static files
    location /static/ {
        alias /home/vms/vms/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Systemd Service

```ini
# /etc/systemd/system/vms.service
[Unit]
Description=VMS Application
After=network.target

[Service]
Type=simple
User=vms
Group=vms
WorkingDirectory=/home/vms/vms
Environment=PATH=/home/vms/vms/venv/bin
ExecStart=/home/vms/vms/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Test renewal
sudo certbot renew --dry-run
```

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd -m vms && chown -R vms:vms /app
USER vms

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://vms_user:password@db:5432/vms
      - SECRET_KEY=your-secret-key
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=vms
      - POSTGRES_USER=vms_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
```

## 📅 Scheduling Imports

You can schedule nightly imports using your OS scheduler.

### Windows Task Scheduler

1. Open Task Scheduler → Create Task…
2. Triggers: Daily at 2:00 AM (or preferred time)
3. Actions: Start a program
   - Program/script: `python`
   - Add arguments: `manage_imports.py --sequential --timeout 0 --base-url http://localhost:5050 --username %ADMIN_USERNAME% --password %ADMIN_PASSWORD%`
   - Start in: path to your VMS repo
4. Conditions: Uncheck “Start only if the computer is on AC power” if needed
5. Settings: Stop the task if it runs longer than X hours (optional)

Notes:
- Ensure a Python venv is activated via a wrapper `.cmd` if needed. Example action target:
  - Program/script: `C:\\Windows\\System32\\cmd.exe`
  - Add arguments: `/c "C:\\path\\to\\venv\\Scripts\\activate && python manage_imports.py --sequential --timeout 0 --base-url http://localhost:5050 --username %ADMIN_USERNAME% --password %ADMIN_PASSWORD%"`

### Linux/macOS (cron)

Edit crontab with `crontab -e`:

```
0 2 * * * cd /path/to/VMS && /path/to/venv/bin/python manage_imports.py --sequential --timeout 0 --base-url http://localhost:5050 --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD" >> logs/import_cron.log 2>&1
```

Tips:
- Use `--exclude` to skip heavy steps on weekdays, and run full imports weekly
- Use `--plan-only` with logging on a different schedule to validate connectivity

### PythonAnywhere (Web)

Use a Scheduled Task with a bash command that activates your venv, changes to the repo, and runs the CLI excluding students:

```bash
cd /home/yourusername/VMS && \
source /home/yourusername/.virtualenvs/your_venv/bin/activate && \
ADMIN_USERNAME=youradmin ADMIN_PASSWORD=yourpass \
VMS_BASE_URL=https://yourusername.pythonanywhere.com \
python manage_imports.py --sequential --exclude students --timeout 0 --base-url "$VMS_BASE_URL"
```

Alternatively, place your command logic into `scripts/nightly_import_no_students.sh` and schedule:

```bash
cd /home/yourusername/VMS && \
VENV_PATH=/home/yourusername/.virtualenvs/your_venv \
ADMIN_USERNAME=youradmin ADMIN_PASSWORD=yourpass \
VMS_BASE_URL=https://yourusername.pythonanywhere.com \
bash scripts/nightly_import_no_students.sh
```

## 📊 Monitoring

### Application Monitoring

#### Health Check Endpoint

```python
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')

        # Check Salesforce connection
        sf_status = check_salesforce_connection()

        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'salesforce': sf_status,
            'version': app.config.get('VERSION', 'unknown')
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }, 500
```

#### Logging Configuration

```python
# config.py
import logging
import structlog
from logging.handlers import RotatingFileHandler

def configure_logging(app):
    """Configure structured logging."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # File handler
    file_handler = RotatingFileHandler(
        'logs/vms.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Configure app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # Disable Werkzeug logger
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
```

#### Performance Monitoring

```python
# utils/monitoring.py
import time
import functools
from flask import request, g
import structlog

logger = structlog.get_logger()

def monitor_performance(f):
    """Decorator to monitor function performance."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        try:
            result = f(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                "function_execution",
                function=f.__name__,
                execution_time=execution_time,
                success=True
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                "function_execution",
                function=f.__name__,
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
            raise

    return decorated_function

def log_request():
    """Log incoming requests."""
    g.start_time = time.time()

def log_response(response):
    """Log response details."""
    if hasattr(g, 'start_time'):
        execution_time = time.time() - g.start_time

        logger.info(
            "request_processed",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            execution_time=execution_time,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )

    return response
```

### System Monitoring

#### System Metrics Script

```bash
#!/bin/bash
# scripts/monitor.sh

# System metrics
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)

# Application metrics
APP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
DB_CONNECTIONS=$(psql -U vms_user -d vms_production -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tail -1)

# Log metrics
echo "$(date): CPU: ${CPU_USAGE}%, Memory: ${MEMORY_USAGE}%, Disk: ${DISK_USAGE}%, App: ${APP_STATUS}, DB Connections: ${DB_CONNECTIONS}" >> /var/log/vms/metrics.log

# Alert if thresholds exceeded
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "High CPU usage: ${CPU_USAGE}%" | mail -s "VMS Alert" admin@example.com
fi

if (( $(echo "$MEMORY_USAGE > 85" | bc -l) )); then
    echo "High memory usage: ${MEMORY_USAGE}%" | mail -s "VMS Alert" admin@example.com
fi
```

#### Cron Job Setup

```bash
# Add to crontab
*/5 * * * * /home/vms/vms/scripts/monitor.sh
0 2 * * * /home/vms/vms/scripts/backup.sh
0 3 * * * /home/vms/vms/scripts/cleanup.sh
```

## 🔧 Maintenance

### Database Maintenance

#### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/home/vms/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="vms_production"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U vms_user -h localhost $DB_NAME | gzip > $BACKUP_DIR/vms_$DATE.sql.gz

# Keep only last 30 days of backups
find $BACKUP_DIR -name "vms_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/vms_$DATE.sql.gz s3://your-backup-bucket/

echo "Backup completed: vms_$DATE.sql.gz"
```

#### Database Optimization

```sql
-- Regular maintenance queries
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim storage
VACUUM ANALYZE;

-- Reindex for better performance
REINDEX DATABASE vms_production;
```

### Log Management

#### Log Rotation

```bash
# /etc/logrotate.d/vms
/home/vms/vms/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 vms vms
    postrotate
        systemctl reload vms
    endscript
}
```

#### Log Cleanup Script

```bash
#!/bin/bash
# scripts/cleanup.sh

LOG_DIR="/home/vms/vms/logs"
DAYS_TO_KEEP=30

# Remove old log files
find $LOG_DIR -name "*.log" -mtime +$DAYS_TO_KEEP -delete

# Remove old backup files
find /home/vms/backups -name "*.sql.gz" -mtime +30 -delete

echo "Cleanup completed: $(date)"
```

### Application Updates

#### Update Script

```bash
#!/bin/bash
# scripts/update.sh

set -e

APP_DIR="/home/vms/vms"
BACKUP_DIR="/home/vms/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting VMS update..."

# Create backup
echo "Creating backup..."
pg_dump -U vms_user -h localhost vms_production | gzip > $BACKUP_DIR/pre_update_$DATE.sql.gz

# Stop application
echo "Stopping application..."
sudo systemctl stop vms

# Update code
echo "Updating code..."
cd $APP_DIR
git fetch origin
git reset --hard origin/main

# Update dependencies
echo "Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.create_all()"

# Start application
echo "Starting application..."
sudo systemctl start vms

# Health check
echo "Performing health check..."
sleep 10
if curl -f http://localhost:5000/health; then
    echo "Update completed successfully!"
else
    echo "Health check failed! Rolling back..."
    # Rollback logic here
    exit 1
fi
```

## 🐛 Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check service status
sudo systemctl status vms

# Check logs
sudo journalctl -u vms -f

# Check application logs
tail -f /home/vms/vms/logs/vms.log

# Check permissions
ls -la /home/vms/vms/
```

#### Database Connection Issues

```bash
# Test database connection
psql -U vms_user -h localhost -d vms_production -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### High Memory Usage

```bash
# Check memory usage
free -h

# Check process memory usage
ps aux --sort=-%mem | head -10

# Check for memory leaks
python -c "import gc; gc.collect(); print('Garbage collection completed')"
```

#### Slow Performance

```bash
# Check database performance
psql -U vms_user -d vms_production -c "
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Check slow queries
tail -f /var/log/postgresql/postgresql-*.log | grep "duration:"
```

### Debug Mode

#### Enable Debug Logging

```python
# Temporarily enable debug mode
import logging
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

#### Database Query Logging

```python
# Enable SQL query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Emergency Procedures

#### Rollback Procedure

```bash
#!/bin/bash
# scripts/rollback.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Rolling back to: $BACKUP_FILE"

# Stop application
sudo systemctl stop vms

# Restore database
gunzip -c $BACKUP_FILE | psql -U vms_user -d vms_production

# Start application
sudo systemctl start vms

echo "Rollback completed"
```

#### Emergency Maintenance Mode

```python
# Enable maintenance mode
MAINTENANCE_MODE = True

@app.before_request
def maintenance_mode():
    if MAINTENANCE_MODE and request.path != '/maintenance':
        return render_template('maintenance.html'), 503
```

## 📈 Performance Optimization

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_volunteers_email ON volunteers(email);
CREATE INDEX CONCURRENTLY idx_events_date ON events(start_date);
CREATE INDEX CONCURRENTLY idx_attendance_event ON attendance(event_id);

-- Analyze table statistics
ANALYZE volunteers;
ANALYZE events;
ANALYZE attendance;
```

### Application Optimization

```python
# Enable caching
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0'
})

# Cache expensive queries
@cache.memoize(timeout=300)
def get_volunteer_stats():
    return Volunteer.query.count()

# Use connection pooling
from sqlalchemy import create_engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### Monitoring Dashboard

```python
# /admin/metrics endpoint
@app.route('/admin/metrics')
@admin_required
def metrics():
    """System metrics dashboard."""

    # Database metrics
    db_stats = db.session.execute("""
        SELECT
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes
        FROM pg_stat_user_tables
    """).fetchall()

    # Application metrics
    app_stats = {
        'total_volunteers': Volunteer.query.count(),
        'total_events': Event.query.count(),
        'total_organizations': Organization.query.count(),
        'active_sessions': len(current_app.login_manager._session_protector._sessions)
    }

    return render_template('admin/metrics.html',
                         db_stats=db_stats,
                         app_stats=app_stats)
```

## 🔗 Related Documentation

- [System Overview](01-overview.md)
- [Architecture](02-architecture.md)
- [Development Guide](05-dev-guide.md)
- [API Specification](04-api-spec.md)

---

*Last updated: August 2025*
