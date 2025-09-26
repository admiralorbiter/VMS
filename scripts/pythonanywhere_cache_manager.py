#!/usr/bin/env python3
"""
PythonAnywhere Cache Manager
============================

This script is optimized for PythonAnywhere deployment and handles both
24-hour cache refresh scheduling and status monitoring in a single script.

Key Features:
- Single script for PythonAnywhere scheduled tasks
- 24-hour automated cache refresh
- Status monitoring and reporting
- Error handling and logging
- Production-optimized for PythonAnywhere environment

Usage:
    # Run as scheduled task (every 24 hours)
    python scripts/pythonanywhere_cache_manager.py refresh

    # Check status
    python scripts/pythonanywhere_cache_manager.py status

    # Manual refresh
    python scripts/pythonanywhere_cache_manager.py refresh --force

    # Health check
    python scripts/pythonanywhere_cache_manager.py health
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for PythonAnywhere
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

# Configure logging with UTF-8 encoding for emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "cache_manager.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def setup_flask_app():
    """Setup Flask app context for PythonAnywhere."""
    try:
        from app import app
        return app
    except Exception as e:
        logger.error(f"Failed to import Flask app: {e}")
        return None

def refresh_all_caches():
    """Refresh all caches with comprehensive error handling."""
    logger.info("Starting cache refresh process...")
    start_time = datetime.now(timezone.utc)
    
    try:
        from utils.cache_refresh_scheduler import refresh_all_caches as refresh_caches
        refresh_caches()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Cache refresh completed successfully in {duration:.2f} seconds")
        return True
        
    except Exception as e:
        logger.error(f"Cache refresh failed: {str(e)}")
        return False

def refresh_specific_cache(cache_type):
    """Refresh a specific cache type."""
    logger.info(f"Refreshing {cache_type} caches...")
    start_time = datetime.now(timezone.utc)
    
    try:
        from utils.cache_refresh_scheduler import refresh_specific_cache as refresh_cache
        refresh_cache(cache_type)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"{cache_type.title()} caches refreshed successfully in {duration:.2f} seconds")
        return True
        
    except Exception as e:
        logger.error(f"{cache_type.title()} cache refresh failed: {str(e)}")
        return False

def get_cache_status():
    """Get comprehensive cache status."""
    try:
        from utils.cache_refresh_scheduler import get_cache_status as get_status
        status = get_status()
        
        print("Cache Refresh Status")
        print("=" * 50)
        print(f"Status: {'Running' if status['is_running'] else 'Stopped'}")
        print(f"Refresh Interval: {status['refresh_interval_hours']} hours")
        print(f"Last Refresh: {status['last_refresh'] or 'Never'}")
        print("\nStatistics:")
        stats = status['stats']
        print(f"  Total Refreshes: {stats['total_refreshes']}")
        print(f"  Successful: {stats['successful_refreshes']}")
        print(f"  Failed: {stats['failed_refreshes']}")
        if stats['last_error']:
            print(f"  Last Error: {stats['last_error']}")
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {str(e)}")
        return None

def health_check():
    """Perform comprehensive health check."""
    logger.info("Performing health check...")
    
    health_status = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'flask_app': False,
        'database': False,
        'cache_system': False,
        'overall': False
    }
    
    # Check Flask app
    try:
        app = setup_flask_app()
        if app:
            with app.app_context():
                from models import db
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                health_status['flask_app'] = True
                health_status['database'] = True
                logger.info("Flask app and database connection OK")
    except Exception as e:
        logger.error(f"Flask app or database check failed: {e}")
    
    # Check cache system
    try:
        status = get_cache_status()
        if status:
            health_status['cache_system'] = True
            logger.info("Cache system OK")
    except Exception as e:
        logger.error(f"Cache system check failed: {e}")
    
    # Overall health
    health_status['overall'] = all([
        health_status['flask_app'],
        health_status['database'],
        health_status['cache_system']
    ])
    
    # Print health report
    print("Health Check Report")
    print("=" * 30)
    print(f"Timestamp: {health_status['timestamp']}")
    print(f"Flask App: {'OK' if health_status['flask_app'] else 'FAIL'}")
    print(f"Database: {'OK' if health_status['database'] else 'FAIL'}")
    print(f"Cache System: {'OK' if health_status['cache_system'] else 'FAIL'}")
    print(f"Overall: {'HEALTHY' if health_status['overall'] else 'UNHEALTHY'}")
    
    return health_status

def should_refresh_cache():
    """Check if cache should be refreshed based on last refresh time."""
    try:
        from utils.cache_refresh_scheduler import get_cache_status
        status = get_cache_status()
        
        if not status['last_refresh']:
            logger.info("No previous refresh found, refreshing caches")
            return True
        
        last_refresh = datetime.fromisoformat(status['last_refresh'].replace('Z', '+00:00'))
        time_since_refresh = datetime.now(timezone.utc) - last_refresh
        
        # Refresh if more than 20 hours have passed (allowing some buffer)
        should_refresh = time_since_refresh > timedelta(hours=20)
        
        if should_refresh:
            logger.info(f"Last refresh was {time_since_refresh} ago, refreshing caches")
        else:
            logger.info(f"Last refresh was {time_since_refresh} ago, skipping refresh")
        
        return should_refresh
        
    except Exception as e:
        logger.error(f"Error checking refresh status: {e}")
        # If we can't determine, err on the side of refreshing
        return True

def main():
    """Main entry point for the cache manager."""
    parser = argparse.ArgumentParser(description="PythonAnywhere Cache Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh caches")
    refresh_parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force refresh even if recently refreshed"
    )
    refresh_parser.add_argument(
        "--type",
        choices=["district", "organization", "virtual_session", "volunteer", "recruitment"],
        help="Refresh specific cache type"
    )
    
    # Status command
    subparsers.add_parser("status", help="Get cache status")
    
    # Health command
    subparsers.add_parser("health", help="Perform health check")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup Flask app context
    app = setup_flask_app()
    if not app:
        logger.error("Failed to setup Flask app")
        return 1
    
    with app.app_context():
        if args.command == "refresh":
            if args.type:
                success = refresh_specific_cache(args.type)
            elif args.force or should_refresh_cache():
                success = refresh_all_caches()
            else:
                logger.info("Skipping refresh - recently refreshed")
                success = True
            
            return 0 if success else 1
        
        elif args.command == "status":
            status = get_cache_status()
            return 0 if status else 1
        
        elif args.command == "health":
            health = health_check()
            return 0 if health['overall'] else 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
