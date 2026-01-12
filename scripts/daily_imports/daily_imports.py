#!/usr/bin/env python3
"""
Daily Imports Script for VMS
============================

A single-file script for running daily Salesforce imports on PythonAnywhere.
This script directly imports and executes the import functions from the VMS Flask application.

Usage:
    python daily_imports.py [options]

Examples:
    python daily_imports.py --daily                    # Run daily imports
    python daily_imports.py --full                     # Run all imports
    python daily_imports.py --only organizations       # Run only organizations
    python daily_imports.py --dry-run                  # Show what would be imported
    python daily_imports.py --validate                 # Validate configuration

Author: VMS Development Team
Version: 1.0
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add the VMS root directory to the path so we can import from the VMS app
script_dir = os.path.dirname(os.path.abspath(__file__))
vms_root = os.path.dirname(
    os.path.dirname(script_dir)
)  # Go up two levels: scripts/daily_imports -> scripts -> VMS
sys.path.insert(0, vms_root)

# Change to VMS root directory to ensure relative paths work correctly
os.chdir(vms_root)

# Ensure instance directory exists before importing app (fixes production path issues)
instance_dir = os.path.join(vms_root, "instance")
if not os.path.exists(instance_dir):
    try:
        os.makedirs(instance_dir, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create instance directory {instance_dir}: {e}")

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Import Flask app components
from flask import Flask

# Import Flask-Login components
from flask_login import login_user

from config import DevelopmentConfig, ProductionConfig
from models import db
from models.user import SecurityLevel, User
from routes.events.pathway_events import sync_unaffiliated_events
from routes.events.routes import (
    import_events_from_salesforce,
    sync_student_participants,
)
from routes.history.routes import import_history_from_salesforce
from routes.management.management import import_classes, import_schools

# Import route handlers
from routes.organizations.routes import (
    import_affiliations_from_salesforce,
    import_organizations_from_salesforce,
)
from routes.students.routes import import_students_from_salesforce
from routes.teachers.routes import import_teachers_from_salesforce
from routes.volunteers.routes import (
    import_from_salesforce as import_volunteers_from_salesforce,
)


class ImportStep:
    """Represents a single import step with its configuration."""

    def __init__(
        self, name: str, function, description: str = "", chunked: bool = False
    ):
        self.name = name
        self.function = function
        self.description = description
        self.chunked = chunked
        self.completed = False
        self.error = None
        self.start_time = None
        self.end_time = None
        self.records_processed = 0


class DailyImporter:
    """Main class for handling daily imports."""

    def __init__(self, app: Flask, logger: logging.Logger):
        self.app = app
        self.logger = logger
        # Use the app's existing login_manager instead of creating a new one

        # Define import sequence (matching admin.html order)
        self.import_steps = [
            # Daily/Weekly Imports
            ImportStep(
                "organizations",
                self._import_organizations,
                "Import Organizations from Salesforce",
            ),
            ImportStep(
                "volunteers",
                self._import_volunteers,
                "Import Volunteers from Salesforce (requires organizations)",
            ),
            ImportStep(
                "affiliations",
                self._import_affiliations,
                "Import Volunteer-Organization Affiliations (requires organizations, volunteers)",
            ),
            ImportStep(
                "events",
                self._import_events,
                "Import Events from Salesforce (requires organizations, schools, teachers)",
            ),
            ImportStep(
                "history",
                self._import_history,
                "Import History from Salesforce (requires events, volunteers, students)",
            ),
            # Quarterly Imports
            ImportStep(
                "schools",
                self._import_schools,
                "Import Schools from Salesforce (requires districts)",
            ),
            ImportStep(
                "classes",
                self._import_classes,
                "Import Classes from Salesforce (requires schools)",
            ),
            ImportStep(
                "teachers",
                self._import_teachers,
                "Import Teachers from Salesforce (requires schools)",
            ),
            ImportStep(
                "student_participations",
                self._import_student_participations,
                "Import Student Participations (requires students, events)",
            ),
            # Yearly Imports
            ImportStep(
                "students",
                self._import_students,
                "Import Students from Salesforce (requires schools, classes, teachers)",
                chunked=True,
            ),
            # Management Functions
            ImportStep(
                "sync_unaffiliated_events",
                self._sync_unaffiliated_events,
                "Sync Unaffiliated Events (requires students, events)",
            ),
        ]

        self.admin_user = None

    def setup_admin_user(self):
        """Set up admin user for authentication."""
        with self.app.app_context():
            # Find or create admin user
            admin_user = User.query.filter_by(username="admin").first()
            if not admin_user:
                # Import password hashing
                from werkzeug.security import generate_password_hash

                # Create admin user if it doesn't exist
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    security_level=SecurityLevel.ADMIN,
                    scope_type="global",  # Global scope for admin user
                    password_hash=generate_password_hash(
                        "admin123"
                    ),  # Default password
                )
                db.session.add(admin_user)
                db.session.commit()
                self.logger.warning(
                    "Created default admin user with password 'admin123'"
                )

            # Ensure admin user has global scope
            if (
                not hasattr(admin_user, "scope_type")
                or admin_user.scope_type != "global"
            ):
                admin_user.scope_type = "global"
                db.session.commit()

            self.admin_user = admin_user
            self.logger.info(f"Using admin user: {admin_user.username}")

    def authenticate(self):
        """Authenticate as admin user."""
        with self.app.app_context():
            if not self.admin_user:
                self.setup_admin_user()

            # Create a request context and mock authentication
            with self.app.test_request_context():
                # Mock the current_user for Flask-Login
                from unittest.mock import patch

                from flask_login import current_user

                # Patch current_user to return our admin user
                with patch("flask_login.current_user", self.admin_user):
                    self.logger.info("Authenticated as admin user (mocked)")

    def _run_with_auth(self, func, *args, **kwargs):
        """Run a function with proper Flask-Login authentication."""
        with self.app.app_context():
            if not self.admin_user:
                self.setup_admin_user()

            # Ensure admin user has global scope
            if (
                not hasattr(self.admin_user, "scope_type")
                or self.admin_user.scope_type != "global"
            ):
                self.admin_user.scope_type = "global"
                db.session.commit()

            # Use Flask-Login's login_user() within request context
            with self.app.test_request_context():
                from flask_login import login_user

                # Properly log in the user using Flask-Login
                login_user(self.admin_user)

                # Now current_user will work properly
                return func(*args, **kwargs)

    def _parse_import_result(
        self, result, default_success_message: str = "Import completed"
    ):
        """
        Parse the result from an import function and return a standardized dict.

        Handles:
        - Flask Response objects
        - Tuple responses like (jsonify({...}), status_code)
        - Dict responses
        - Other response types
        """
        if result is None:
            return {
                "success": False,
                "message": "Import function returned None",
            }

        # Handle Flask Response objects (not in tuple)
        if hasattr(result, "status_code"):
            if result.status_code == 302:
                return {
                    "success": False,
                    "message": "Authentication failed - redirect to login",
                }
            elif result.status_code == 200:
                try:
                    return result.get_json() or {
                        "success": True,
                        "message": default_success_message,
                    }
                except:
                    return {"success": True, "message": default_success_message}
            else:
                try:
                    json_data = result.get_json() or {}
                    return {
                        "success": False,
                        "message": json_data.get(
                            "message",
                            json_data.get("error", f"HTTP {result.status_code}"),
                        ),
                    }
                except:
                    return {
                        "success": False,
                        "message": f"HTTP {result.status_code}",
                    }

        # Handle dict responses
        if hasattr(result, "json"):
            return result.json

        # Handle tuple responses like (jsonify({...}), status_code)
        if isinstance(result, tuple):
            response_obj = result[0]
            status_code = result[1] if len(result) > 1 else 200

            # If first element is a Response object, extract JSON
            if hasattr(response_obj, "get_json"):
                try:
                    json_data = response_obj.get_json() or {}
                    return {
                        "success": json_data.get("success", status_code == 200),
                        "message": json_data.get("message", json_data.get("error", "")),
                    }
                except:
                    return {
                        "success": status_code == 200,
                        "message": f"HTTP {status_code}",
                    }
            # If first element is a dict, use it directly
            elif isinstance(response_obj, dict):
                return {
                    "success": response_obj.get("success", False),
                    "message": response_obj.get("message", ""),
                }
            else:
                return {
                    "success": status_code == 200,
                    "message": f"Unexpected response type: {type(response_obj)}",
                }

        # Default success case
        return {
            "success": True,
            "message": default_success_message,
        }

    def _import_organizations(self) -> Dict:
        """Import organizations from Salesforce."""

        def _call_import():
            try:
                # Call the function directly without decorators
                from routes.organizations.routes import (
                    import_organizations_from_salesforce,
                )

                # Get the original function without decorators
                original_func = import_organizations_from_salesforce.__wrapped__
                result = original_func()

                self.logger.debug(f"Import result type: {type(result)}")
                self.logger.debug(f"Import result: {result}")

                if result is None:
                    return {
                        "success": False,
                        "message": "Import function returned None",
                    }

                # Handle Flask Response objects
                if hasattr(result, "status_code"):
                    if result.status_code == 302:
                        return {
                            "success": False,
                            "message": "Authentication failed - redirect to login",
                        }
                    elif result.status_code == 200:
                        # Try to get JSON from response
                        try:
                            return result.get_json() or {
                                "success": True,
                                "message": "Import completed",
                            }
                        except:
                            return {"success": True, "message": "Import completed"}
                    else:
                        return {
                            "success": False,
                            "message": f"HTTP {result.status_code}",
                        }

                if hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Organizations imported successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_volunteers(self) -> Dict:
        """Import volunteers from Salesforce."""

        def _call_import():
            try:
                from routes.volunteers.routes import import_from_salesforce

                original_func = import_from_salesforce.__wrapped__

                # Patch current_user specifically for this module
                from unittest.mock import patch

                with patch("routes.volunteers.routes.current_user", self.admin_user):
                    result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Volunteers imported successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_affiliations(self) -> Dict:
        """Import volunteer-organization affiliations from Salesforce."""

        def _call_import():
            try:
                from routes.organizations.routes import (
                    import_affiliations_from_salesforce,
                )

                original_func = import_affiliations_from_salesforce.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Affiliations imported successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_events(self) -> Dict:
        """Import events from Salesforce."""

        def _call_import():
            try:
                from routes.events.routes import import_events_from_salesforce

                original_func = import_events_from_salesforce.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {"success": True, "message": "Events imported successfully"}
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_history(self) -> Dict:
        """Import history from Salesforce."""

        def _call_import():
            try:
                from routes.history.routes import import_history_from_salesforce

                original_func = import_history_from_salesforce.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {"success": True, "message": "History imported successfully"}
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_schools(self) -> Dict:
        """Import schools from Salesforce."""

        def _call_import():
            try:
                from routes.management.management import import_schools

                original_func = import_schools.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {"success": True, "message": "Schools imported successfully"}
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_classes(self) -> Dict:
        """Import classes from Salesforce."""

        def _call_import():
            try:
                from routes.management.management import import_classes

                original_func = import_classes.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {"success": True, "message": "Classes imported successfully"}
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_teachers(self) -> Dict:
        """Import teachers from Salesforce."""

        def _call_import():
            try:
                from routes.teachers.routes import import_teachers_from_salesforce

                original_func = import_teachers_from_salesforce.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Teachers imported successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_student_participations(self) -> Dict:
        """Import student participations from Salesforce."""

        def _call_import():
            try:
                from routes.events.routes import sync_student_participants

                original_func = sync_student_participants.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Student participations imported successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _import_students(
        self, chunk_size: int = 2000, last_id: Optional[str] = None
    ) -> Dict:
        """Import students from Salesforce (chunked)."""

        def _call_import():
            try:
                from routes.students.routes import import_students_from_salesforce

                original_func = import_students_from_salesforce.__wrapped__

                # For students, we need to mock the request with JSON data
                from unittest.mock import MagicMock, patch

                mock_request = MagicMock()
                mock_request.method = "POST"
                mock_request.json = {"chunk_size": chunk_size, "last_id": last_id}
                mock_request.form = {}

                with patch("flask.request", mock_request):
                    result = original_func()

                    if hasattr(result, "status_code") and result.status_code == 200:
                        try:
                            return result.get_json() or {
                                "success": True,
                                "message": "Import completed",
                            }
                        except:
                            return {"success": True, "message": "Import completed"}
                    elif hasattr(result, "json"):
                        return result.json
                    elif isinstance(result, tuple):
                        # Handle tuple responses like (jsonify({...}), status_code)
                        response_obj = result[0]
                        status_code = result[1] if len(result) > 1 else 200

                        # If first element is a Response object, extract JSON
                        if hasattr(response_obj, "get_json"):
                            try:
                                json_data = response_obj.get_json() or {}
                                return {
                                    "success": json_data.get(
                                        "success", status_code == 200
                                    ),
                                    "message": json_data.get(
                                        "message", json_data.get("error", "")
                                    ),
                                }
                            except:
                                return {
                                    "success": status_code == 200,
                                    "message": f"HTTP {status_code}",
                                }
                        # If first element is a dict, use it directly
                        elif isinstance(response_obj, dict):
                            return {
                                "success": response_obj.get("success", False),
                                "message": response_obj.get("message", ""),
                            }
                        else:
                            return {
                                "success": status_code == 200,
                                "message": f"Unexpected response type: {type(response_obj)}",
                            }
                    else:
                        return {
                            "success": True,
                            "message": "Students imported successfully",
                        }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def _sync_unaffiliated_events(self) -> Dict:
        """Sync unaffiliated events."""

        def _call_import():
            try:
                from routes.events.pathway_events import sync_unaffiliated_events

                original_func = sync_unaffiliated_events.__wrapped__
                result = original_func()

                if hasattr(result, "status_code") and result.status_code == 200:
                    try:
                        return result.get_json() or {
                            "success": True,
                            "message": "Import completed",
                        }
                    except:
                        return {"success": True, "message": "Import completed"}
                elif hasattr(result, "json"):
                    return result.json
                elif isinstance(result, tuple):
                    # Handle tuple responses like (jsonify({...}), status_code)
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200

                    # If first element is a Response object, extract JSON
                    if hasattr(response_obj, "get_json"):
                        try:
                            json_data = response_obj.get_json() or {}
                            return {
                                "success": json_data.get("success", status_code == 200),
                                "message": json_data.get(
                                    "message", json_data.get("error", "")
                                ),
                            }
                        except:
                            return {
                                "success": status_code == 200,
                                "message": f"HTTP {status_code}",
                            }
                    # If first element is a dict, use it directly
                    elif isinstance(response_obj, dict):
                        return {
                            "success": response_obj.get("success", False),
                            "message": response_obj.get("message", ""),
                        }
                    else:
                        return {
                            "success": status_code == 200,
                            "message": f"Unexpected response type: {type(response_obj)}",
                        }
                else:
                    return {
                        "success": True,
                        "message": "Unaffiliated events synced successfully",
                    }
            except Exception as e:
                self.logger.error(f"Import function failed: {e}", exc_info=True)
                return {"success": False, "message": f"Import failed: {str(e)}"}

        return self._run_with_auth(_call_import)

    def run_step(
        self, step: ImportStep, chunk_size: int = 2000, sleep_ms: int = 200
    ) -> bool:
        """Run a single import step."""
        step.start_time = datetime.now()
        self.logger.info(f"Starting {step.name}: {step.description}")

        try:
            if step.chunked:
                # Handle chunked imports (like students)
                last_id = None
                total_processed = 0
                chunk_index = 0

                while True:
                    self.logger.info(
                        f"Processing chunk {chunk_index + 1} for {step.name}"
                    )

                    result = step.function(chunk_size=chunk_size, last_id=last_id)

                    if not result.get("success", True):
                        step.error = result.get("message", "Unknown error")
                        self.logger.error(f"{step.name} failed: {step.error}")
                        return False

                    processed_count = result.get("processed_count", 0)
                    total_processed += processed_count
                    last_id = result.get("next_id")

                    self.logger.info(
                        f"Chunk {chunk_index + 1} processed {processed_count} records"
                    )

                    if result.get("is_complete") or not last_id:
                        step.records_processed = total_processed
                        self.logger.info(
                            f"{step.name} completed: {total_processed} total records processed"
                        )
                        break

                    chunk_index += 1
                    time.sleep(sleep_ms / 1000.0)
            else:
                # Handle regular imports
                result = step.function()

                if not result.get("success", True):
                    step.error = result.get("message", "Unknown error")
                    self.logger.error(f"{step.name} failed: {step.error}")
                    return False

                step.records_processed = result.get("processed_count", 0)
                self.logger.info(f"{step.name} completed successfully")

            step.completed = True
            step.end_time = datetime.now()
            duration = (step.end_time - step.start_time).total_seconds()
            self.logger.info(f"{step.name} completed in {duration:.2f} seconds")

            return True

        except Exception as e:
            step.error = str(e)
            step.end_time = datetime.now()
            self.logger.error(f"{step.name} failed with exception: {e}", exc_info=True)
            return False

    def run_imports(
        self,
        only_steps: Optional[List[str]] = None,
        exclude_steps: Optional[List[str]] = None,
        chunk_size: int = 2000,
        sleep_ms: int = 200,
        dry_run: bool = False,
    ) -> bool:
        """Run the import sequence."""
        # Filter steps based on only/exclude parameters
        steps_to_run = self.import_steps.copy()

        if only_steps:
            steps_to_run = [step for step in steps_to_run if step.name in only_steps]

        if exclude_steps:
            steps_to_run = [
                step for step in steps_to_run if step.name not in exclude_steps
            ]

        if not steps_to_run:
            self.logger.error("No steps to run after filtering")
            return False

        if dry_run:
            self.logger.info("DRY RUN - Steps that would be executed:")
            for step in steps_to_run:
                self.logger.info(f"  - {step.name}: {step.description}")
            return True

        # Authenticate
        self.authenticate()

        # Run each step
        overall_success = True
        for step in steps_to_run:
            self.logger.info(f"=== Running step: {step.name} ===")

            success = self.run_step(step, chunk_size, sleep_ms)
            if not success:
                overall_success = False
                self.logger.error(f"Step failed: {step.name}")
                # Continue with remaining steps for resilience

        # Log summary
        self.logger.info("=== Import Summary ===")
        completed_steps = [step for step in steps_to_run if step.completed]
        failed_steps = [step for step in steps_to_run if not step.completed]

        self.logger.info(f"Completed: {len(completed_steps)}/{len(steps_to_run)} steps")
        for step in completed_steps:
            duration = (step.end_time - step.start_time).total_seconds()
            self.logger.info(
                f"  [OK] {step.name}: {step.records_processed} records in {duration:.2f}s"
            )

        if failed_steps:
            self.logger.error(f"Failed: {len(failed_steps)} steps")
            for step in failed_steps:
                self.logger.error(f"  [FAIL] {step.name}: {step.error}")

        return overall_success


def setup_logger(
    log_file: Optional[str] = None, log_level: str = "INFO"
) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("daily_imports")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def create_app() -> Flask:
    """Create and configure Flask application - use the actual app from app.py."""
    # Preflight: ensure SQLite DATABASE_URL (if used) points at a writable, absolute path.
    #
    # In production (e.g., PythonAnywhere scheduled tasks), DATABASE_URL is sometimes set
    # to a relative sqlite path or a location that the task user can't write to, which
    # causes: sqlite3.OperationalError: unable to open database file
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite:"):
        # Accept sqlite:///relative/or/absolute.db and sqlite:////absolute.db
        raw_path = db_url.replace("sqlite:///", "", 1)
        if raw_path.startswith("/"):
            db_path = raw_path
        else:
            # Treat as relative to repo root (vms_root)
            db_path = os.path.join(vms_root, raw_path)

        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Touch the file to confirm it's writable (doesn't create tables)
        try:
            with open(db_path, "a", encoding="utf-8"):
                pass
        except OSError as e:
            raise RuntimeError(
                f"SQLite database path is not writable: {db_path} (from DATABASE_URL={db_url}). "
                f"Fix permissions or set DATABASE_URL to a writable location."
            ) from e

        # Normalize env var so app.py uses the absolute path consistently
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    elif not db_url:
        # If DATABASE_URL isn't set, force an absolute default under repo root.
        default_db_path = os.path.join(vms_root, "instance", "your_database.db")
        os.makedirs(os.path.dirname(default_db_path), exist_ok=True)
        os.environ["DATABASE_URL"] = f"sqlite:///{default_db_path}"

    # Import the actual app instance which has LoginManager properly configured
    from app import app

    return app


def validate_configuration():
    """Validate configuration."""
    errors = []
    warnings = []

    # Check required Salesforce credentials
    if not os.environ.get("SF_USERNAME"):
        errors.append("SF_USERNAME environment variable is required")
    if not os.environ.get("SF_PASSWORD"):
        errors.append("SF_PASSWORD environment variable is required")
    if not os.environ.get("SF_SECURITY_TOKEN"):
        errors.append("SF_SECURITY_TOKEN environment variable is required")

    # Check log file directory
    log_file = os.environ.get("IMPORT_LOG_FILE", "logs/daily_imports.log")
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create log directory {log_dir}: {e}")

    # Validate numeric values
    try:
        chunk_size = int(os.environ.get("STUDENTS_CHUNK_SIZE", "2000"))
        if chunk_size <= 0:
            errors.append("STUDENTS_CHUNK_SIZE must be positive")
    except ValueError:
        errors.append("STUDENTS_CHUNK_SIZE must be a valid integer")

    try:
        sleep_ms = int(os.environ.get("STUDENTS_SLEEP_MS", "200"))
        if sleep_ms < 0:
            errors.append("STUDENTS_SLEEP_MS must be non-negative")
    except ValueError:
        errors.append("STUDENTS_SLEEP_MS must be a valid integer")

    # Check log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    if log_level.upper() not in valid_log_levels:
        errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")

    # Warnings for development settings
    if os.environ.get("FLASK_ENV", "development") == "development":
        warnings.append("Running in development mode")

    if (
        os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
        == "dev-secret-key-change-in-production"
    ):
        warnings.append("Using default secret key - change in production")

    if os.environ.get("ADMIN_PASSWORD", "admin123") == "admin123":
        warnings.append("Using default admin password - change in production")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def print_config_summary():
    """Print a summary of the current configuration."""
    print("Daily Imports Configuration:")
    print("=" * 40)

    config_items = [
        ("SF_USERNAME", os.environ.get("SF_USERNAME")),
        ("SF_DOMAIN", os.environ.get("SF_DOMAIN", "login")),
        ("DATABASE_URL", os.environ.get("DATABASE_URL")),
        (
            "IMPORT_LOG_FILE",
            os.environ.get("IMPORT_LOG_FILE", "logs/daily_imports.log"),
        ),
        ("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO")),
        ("STUDENTS_CHUNK_SIZE", os.environ.get("STUDENTS_CHUNK_SIZE", "2000")),
        ("STUDENTS_SLEEP_MS", os.environ.get("STUDENTS_SLEEP_MS", "200")),
        ("FLASK_ENV", os.environ.get("FLASK_ENV", "development")),
        ("ADMIN_USERNAME", os.environ.get("ADMIN_USERNAME", "admin")),
        ("ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL", "admin@example.com")),
    ]

    for key, value in config_items:
        print(f"{key}: {value}")

    print("=" * 40)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Daily Salesforce imports for VMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python daily_imports.py --daily                    # Run daily imports
  python daily_imports.py --full                     # Run all imports
  python daily_imports.py --only organizations       # Run only organizations
  python daily_imports.py --exclude students         # Run all except students
  python daily_imports.py --dry-run                  # Show what would be imported
  python daily_imports.py --validate                 # Validate configuration
  python daily_imports.py --config                   # Show configuration
        """,
    )

    # Preset options
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Run daily imports (organizations, volunteers, affiliations, events, history)",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Run weekly imports (daily + schools, classes, teachers)",
    )
    parser.add_argument(
        "--full", action="store_true", help="Run full import sequence (all imports)"
    )
    parser.add_argument(
        "--students", action="store_true", help="Run only student imports (can be slow)"
    )

    # Custom options
    parser.add_argument(
        "--only", help="Run only specific steps (comma-separated names)"
    )
    parser.add_argument("--exclude", help="Skip specific steps (comma-separated names)")

    # Configuration options
    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration"
    )
    parser.add_argument("--config", action="store_true", help="Show configuration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without running",
    )

    # Logging options
    parser.add_argument(
        "--log-file",
        default=os.environ.get("IMPORT_LOG_FILE", "logs/daily_imports.log"),
        help="Log file path",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    # Import options
    parser.add_argument(
        "--students-chunk-size",
        type=int,
        default=int(os.environ.get("STUDENTS_CHUNK_SIZE", "2000")),
        help="Chunk size for student imports",
    )
    parser.add_argument(
        "--students-sleep-ms",
        type=int,
        default=int(os.environ.get("STUDENTS_SLEEP_MS", "200")),
        help="Sleep between student chunks in milliseconds",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Handle special commands
    if args.validate:
        validation = validate_configuration()
        if validation["valid"]:
            print("✓ Configuration is valid!")
            if validation["warnings"]:
                print("\nWarnings:")
                for warning in validation["warnings"]:
                    print(f"  WARNING: {warning}")
            return 0
        else:
            print("✗ Configuration validation failed:")
            for error in validation["errors"]:
                print(f"  ERROR: {error}")
            return 1

    if args.config:
        print_config_summary()
        return 0

    # Set up logging
    logger = setup_logger(args.log_file, args.log_level)

    logger.info("Starting daily imports script")
    logger.info(f"Log level: {args.log_level}")
    logger.info(f"Log file: {args.log_file}")

    try:
        # Create Flask app
        app = create_app()

        # Create importer
        importer = DailyImporter(app, logger)

        # Determine which steps to run
        only_steps = None
        exclude_steps = None

        if args.daily:
            only_steps = [
                "organizations",
                "volunteers",
                "affiliations",
                "events",
                "history",
            ]
        elif args.weekly:
            only_steps = [
                "organizations",
                "volunteers",
                "affiliations",
                "events",
                "history",
                "schools",
                "classes",
                "teachers",
            ]
        elif args.full:
            # Run all steps (no filtering)
            pass
        elif args.students:
            only_steps = ["students"]
        elif args.only:
            only_steps = [s.strip().lower() for s in args.only.split(",")]

        if args.exclude:
            exclude_steps = [s.strip().lower() for s in args.exclude.split(",")]

        # Run imports
        success = importer.run_imports(
            only_steps=only_steps,
            exclude_steps=exclude_steps,
            chunk_size=args.students_chunk_size,
            sleep_ms=args.students_sleep_ms,
            dry_run=args.dry_run,
        )

        if success:
            logger.info("Daily imports completed successfully")
            return 0
        else:
            logger.error("Daily imports completed with errors")
            return 1

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
