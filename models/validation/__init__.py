# models/validation/__init__.py
"""
Validation models package for Salesforce Data Validation System.

This package provides the core data models for tracking validation runs,
results, metrics, and historical data for trend analysis.
"""

from .history import ValidationHistory
from .metric import ValidationMetric
from .result import ValidationResult
from .run import ValidationRun

__all__ = [
    "ValidationRun",
    "ValidationResult",
    "ValidationMetric",
    "ValidationHistory",
]

# Version information
__version__ = "1.0.0"
__author__ = "VMS Development Team"
__description__ = "Salesforce Data Validation System Models"
