"""
Salesforce Import Utility Module
===============================

This module provides a standardized framework for importing data from Salesforce
into the local SQLite database. It includes batch processing, error handling,
retry logic, validation, and progress tracking.

Key Features:
- Standardized import process with configurable batch sizes
- Comprehensive error handling and reporting
- Retry logic for transient failures
- Data validation and quality checks
- Progress tracking and logging
- Memory-efficient processing
- Transaction management
- Import statistics and reporting

Usage:
    from utils.salesforce_importer import SalesforceImporter

    importer = SalesforceImporter()
    result = importer.import_data(
        model_class=Organization,
        salesforce_query="SELECT Id, Name FROM Account",
        process_record_func=process_organization_record,
        batch_size=1000
    )
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import Config
from models import db


@dataclass
class ImportResult:
    """Result of an import operation"""

    success: bool
    total_records: int
    processed_count: int
    success_count: int
    error_count: int
    skipped_count: int
    errors: List[str]
    warnings: List[str]
    duration_seconds: float
    start_time: datetime
    end_time: datetime


@dataclass
class ImportConfig:
    """Configuration for import operations"""

    batch_size: int = 1000
    max_retries: int = 3
    retry_delay_seconds: int = 5
    validate_data: bool = True
    log_progress: bool = True
    commit_frequency: int = 100  # Commit every N records
    timeout_seconds: int = 300  # 5 minutes timeout


class SalesforceImporter:
    """
    Standardized Salesforce import utility with batch processing and error handling.

    This class provides a common framework for all Salesforce import operations,
    including authentication, batch processing, error handling, retry logic,
    and comprehensive reporting.
    """

    def __init__(self, config: Optional[ImportConfig] = None):
        """
        Initialize the Salesforce importer.

        Args:
            config: Import configuration, uses defaults if not provided
        """
        self.config = config or ImportConfig()
        self.logger = logging.getLogger(__name__)
        self.sf = None

    def _connect_salesforce(self) -> Salesforce:
        """
        Establish connection to Salesforce with retry logic.

        Returns:
            Salesforce connection object

        Raises:
            SalesforceAuthenticationFailed: If authentication fails after retries
        """
        for attempt in range(self.config.max_retries):
            try:
                self.sf = Salesforce(username=Config.SF_USERNAME, password=Config.SF_PASSWORD, security_token=Config.SF_SECURITY_TOKEN, domain="login")
                return self.sf
            except SalesforceAuthenticationFailed as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                self.logger.warning(f"Salesforce authentication failed, retrying in {self.config.retry_delay_seconds}s...")
                time.sleep(self.config.retry_delay_seconds)

    def _execute_query_with_retry(self, query: str) -> Dict[str, Any]:
        """
        Execute Salesforce query with retry logic.

        Args:
            query: SOQL query to execute

        Returns:
            Query result dictionary

        Raises:
            Exception: If query fails after all retries
        """
        for attempt in range(self.config.max_retries):
            try:
                result = self.sf.query_all(query)
                return result
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                self.logger.warning(f"Query failed, retrying in {self.config.retry_delay_seconds}s... Error: {str(e)}")
                time.sleep(self.config.retry_delay_seconds)

    def _validate_record(self, record: Dict[str, Any], validation_func: Optional[Callable] = None) -> Tuple[bool, List[str]]:
        """
        Validate a record before processing.

        Args:
            record: Record to validate
            validation_func: Optional custom validation function

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Basic validation
        if not record.get("Id"):
            errors.append("Missing Salesforce ID")

        # Custom validation if provided
        if validation_func:
            try:
                custom_errors = validation_func(record)
                if custom_errors:
                    errors.extend(custom_errors)
            except Exception as e:
                errors.append(f"Validation function error: {str(e)}")

        return len(errors) == 0, errors

    def _process_batch(self, records: List[Dict[str, Any]], process_func: Callable, session: Session, stats: Dict[str, int]) -> List[str]:
        """
        Process a batch of records.

        Args:
            records: List of records to process
            process_func: Function to process each record
            session: Database session
            stats: Statistics dictionary to update

        Returns:
            List of error messages
        """
        batch_errors = []

        for record in records:
            try:
                # Validate record
                is_valid, validation_errors = self._validate_record(record)
                if not is_valid:
                    stats["error_count"] += 1
                    batch_errors.extend(validation_errors)
                    continue

                # Process record
                result = process_func(record, session)
                if result:
                    stats["success_count"] += 1
                else:
                    stats["skipped_count"] += 1

            except Exception as e:
                stats["error_count"] += 1
                error_msg = f"Error processing record {record.get('Id', 'Unknown')}: {str(e)}"
                batch_errors.append(error_msg)
                self.logger.error(error_msg)

        return batch_errors

    def import_data(
        self, query: str, process_func: Callable, validation_func: Optional[Callable] = None, progress_callback: Optional[Callable] = None
    ) -> ImportResult:
        """
        Import data from Salesforce using standardized process.

        Args:
            query: SOQL query to execute
            process_func: Function to process each record (record, session) -> bool
            validation_func: Optional validation function (record) -> List[str]
            progress_callback: Optional progress callback (current, total, message)

        Returns:
            ImportResult with comprehensive statistics
        """
        start_time = datetime.now()
        stats = {"total_records": 0, "processed_count": 0, "success_count": 0, "error_count": 0, "skipped_count": 0}
        all_errors = []
        all_warnings = []

        try:
            # Connect to Salesforce
            self.logger.info("Connecting to Salesforce...")
            self._connect_salesforce()

            # Execute query
            self.logger.info(f"Executing query: {query[:100]}...")
            result = self._execute_query_with_retry(query)
            records = result.get("records", [])
            stats["total_records"] = len(records)

            if not records:
                self.logger.warning("No records returned from Salesforce")
                return ImportResult(
                    success=True,
                    total_records=0,
                    processed_count=0,
                    success_count=0,
                    error_count=0,
                    skipped_count=0,
                    errors=[],
                    warnings=["No records found in Salesforce"],
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    start_time=start_time,
                    end_time=datetime.now(),
                )

            # Process records in batches
            self.logger.info(f"Processing {len(records)} records in batches of {self.config.batch_size}")

            for i in range(0, len(records), self.config.batch_size):
                batch = records[i : i + self.config.batch_size]
                batch_num = (i // self.config.batch_size) + 1
                total_batches = (len(records) + self.config.batch_size - 1) // self.config.batch_size

                if progress_callback:
                    progress_callback(i, len(records), f"Processing batch {batch_num}/{total_batches}")

                # Process batch within transaction
                try:
                    with db.session.begin_nested():  # Create savepoint
                        batch_errors = self._process_batch(batch, process_func, db.session, stats)
                        all_errors.extend(batch_errors)

                        # Commit batch if successful
                        db.session.commit()

                except SQLAlchemyError as e:
                    db.session.rollback()
                    error_msg = f"Database error in batch {batch_num}: {str(e)}"
                    all_errors.append(error_msg)
                    stats["error_count"] += len(batch)
                    self.logger.error(error_msg)

                stats["processed_count"] += len(batch)

                # Log progress
                if self.config.log_progress:
                    self.logger.info(f"Batch {batch_num}/{total_batches} complete: " f"{stats['success_count']} success, {stats['error_count']} errors")

            # Final validation
            if stats["error_count"] > stats["total_records"] * 0.1:  # More than 10% errors
                all_warnings.append(f"High error rate: {stats['error_count']}/{stats['total_records']} records failed")

            duration = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"Import complete: {stats['success_count']} success, " f"{stats['error_count']} errors, {stats['skipped_count']} skipped " f"in {duration:.2f}s"
            )

            return ImportResult(
                success=stats["error_count"] == 0,
                total_records=stats["total_records"],
                processed_count=stats["processed_count"],
                success_count=stats["success_count"],
                error_count=stats["error_count"],
                skipped_count=stats["skipped_count"],
                errors=all_errors,
                warnings=all_warnings,
                duration_seconds=duration,
                start_time=start_time,
                end_time=datetime.now(),
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Import failed: {str(e)}"
            self.logger.error(error_msg)

            return ImportResult(
                success=False,
                total_records=stats["total_records"],
                processed_count=stats["processed_count"],
                success_count=stats["success_count"],
                error_count=stats["error_count"],
                skipped_count=stats["skipped_count"],
                errors=[error_msg] + all_errors,
                warnings=all_warnings,
                duration_seconds=duration,
                start_time=start_time,
                end_time=datetime.now(),
            )


class ImportHelpers:
    """
    Helper functions for common import operations.
    """

    @staticmethod
    def create_or_update_record(model_class, salesforce_id: str, update_data: Dict[str, Any], session: Session) -> Tuple[Any, bool]:
        """
        Create or update a database record.

        Args:
            model_class: SQLAlchemy model class
            salesforce_id: Salesforce ID to search by
            update_data: Data to update/create
            session: Database session

        Returns:
            Tuple of (record, is_new_record)
        """
        # Try to find existing record by salesforce_id
        record = session.query(model_class).filter_by(salesforce_id=salesforce_id).first()

        if record:
            # Update existing record
            for key, value in update_data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return record, False
        else:
            # Create new record
            record = model_class(**update_data)
            session.add(record)
            return record, True

    @staticmethod
    def safe_parse_int(value: Any, default: int = 0) -> int:
        """Safely parse integer value."""
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_parse_float(value: Any, default: float = 0.0) -> float:
        """Safely parse float value."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def clean_string(value: Any) -> str:
        """Clean and standardize string values."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def validate_required_fields(record: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Validate that required fields are present."""
        errors = []
        for field in required_fields:
            if not record.get(field):
                errors.append(f"Missing required field: {field}")
        return errors

    @staticmethod
    def is_valid_salesforce_id(salesforce_id: str) -> bool:
        """
        Validate Salesforce ID format.

        Salesforce IDs are 15 or 18 characters long and contain only alphanumeric characters.

        Args:
            salesforce_id: The Salesforce ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not salesforce_id or not isinstance(salesforce_id, str):
            return False

        # Remove any whitespace
        salesforce_id = salesforce_id.strip()

        # Check length (15 or 18 characters)
        if len(salesforce_id) not in [15, 18]:
            return False

        # Check that it contains only alphanumeric characters
        if not salesforce_id.isalnum():
            return False

        return True
