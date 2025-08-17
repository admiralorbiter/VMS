# models/validation/result.py
"""
ValidationResult model for storing individual validation findings.
"""

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class ValidationResult(db.Model):
    """
    Stores individual validation findings.

    This model captures the results of individual validation checks
    including severity, messages, and contextual information.
    """

    __tablename__ = "validation_results"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key to validation run
    run_id = Column(
        Integer,
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entity identification
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # 'volunteer', 'organization', 'event', etc.
    entity_id = Column(Integer, index=True)  # ID of the specific entity being validated
    entity_name = Column(String(255))  # Human-readable name of the entity

    # Field information
    field_name = Column(String(100), index=True)  # Specific field being validated
    field_path = Column(String(255))  # Nested field path (e.g., 'address.city')

    # Validation details
    severity = Column(
        String(20), nullable=False, index=True
    )  # 'info', 'warning', 'error', 'critical'
    validation_type = Column(
        String(50), nullable=False
    )  # 'count', 'completeness', 'data_type', 'relationship', 'business_logic'
    rule_name = Column(
        String(100)
    )  # Name of the validation rule that generated this result

    # Result information
    message = Column(Text, nullable=False)  # Human-readable description
    expected_value = Column(Text)  # What was expected
    actual_value = Column(Text)  # What was found
    difference = Column(Text)  # Calculated difference or variance

    # Context and metadata
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    result_metadata = Column(Text)  # JSON string for additional context

    # Performance and debugging
    execution_time_ms = Column(
        Integer
    )  # Time taken for this validation check in milliseconds
    memory_usage_kb = Column(Integer)  # Memory used for this validation check in KB

    # Relationships
    # Note: back_populates removed to avoid circular import issues

    # Indexes for performance
    __table_args__ = (
        Index("idx_validation_results_run_entity", "run_id", "entity_type"),
        Index("idx_validation_results_entity_severity", "entity_type", "severity"),
        Index("idx_validation_results_severity_timestamp", "severity", "timestamp"),
        Index("idx_validation_results_type_timestamp", "validation_type", "timestamp"),
        Index(
            "idx_validation_results_run_entity_severity",
            "run_id",
            "entity_type",
            "severity",
        ),
    )

    # Severity constants
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_ERROR = "error"
    SEVERITY_CRITICAL = "critical"

    # Validation type constants
    TYPE_COUNT = "count"
    TYPE_COMPLETENESS = "completeness"
    TYPE_DATA_TYPE = "data_type"
    TYPE_RELATIONSHIP = "relationship"
    TYPE_BUSINESS_LOGIC = "business_logic"
    TYPE_FORMAT = "format"
    TYPE_RANGE = "range"
    TYPE_CONSISTENCY = "consistency"

    def __repr__(self):
        """String representation of the validation result."""
        return f"<ValidationResult(id={self.id}, entity={self.entity_type}, severity={self.severity})>"

    @property
    def is_info(self) -> bool:
        """Check if the result is informational."""
        return self.severity == self.SEVERITY_INFO

    @property
    def is_warning(self) -> bool:
        """Check if the result is a warning."""
        return self.severity == self.SEVERITY_WARNING

    @property
    def is_error(self) -> bool:
        """Check if the result is an error."""
        return self.severity == self.SEVERITY_ERROR

    @property
    def is_critical(self) -> bool:
        """Check if the result is critical."""
        return self.severity == self.SEVERITY_CRITICAL

    @property
    def is_issue(self) -> bool:
        """Check if the result represents an issue (warning, error, or critical)."""
        return self.severity in [
            self.SEVERITY_WARNING,
            self.SEVERITY_ERROR,
            self.SEVERITY_CRITICAL,
        ]

    @property
    def metadata_dict(self) -> dict:
        """Get metadata as a dictionary."""
        if not self.result_metadata:
            return {}
        try:
            return json.loads(self.result_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_metadata(self, data: dict):
        """Set metadata from a dictionary."""
        self.result_metadata = json.dumps(data) if data else None

    def add_metadata(self, key: str, value: any):
        """Add a key-value pair to metadata."""
        current_metadata = self.metadata_dict
        current_metadata[key] = value
        self.set_metadata(current_metadata)

    def get_metadata(self, key: str, default: any = None) -> any:
        """Get a value from metadata."""
        return self.metadata_dict.get(key, default)

    def to_dict(self) -> dict:
        """Convert the validation result to a dictionary."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "field_name": self.field_name,
            "field_path": self.field_path,
            "severity": self.severity,
            "validation_type": self.validation_type,
            "rule_name": self.rule_name,
            "message": self.message,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata_dict,
            "execution_time_ms": self.execution_time_ms,
            "memory_usage_kb": self.memory_usage_kb,
            "is_issue": self.is_issue,
        }

    def to_json(self) -> str:
        """Convert the validation result to a JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def create_result(
        cls,
        run_id: int,
        entity_type: str,
        severity: str,
        message: str,
        validation_type: str = None,
        entity_id: int = None,
        entity_name: str = None,
        field_name: str = None,
        field_path: str = None,
        rule_name: str = None,
        expected_value: str = None,
        actual_value: str = None,
        difference: str = None,
        metadata: dict = None,
        execution_time_ms: int = None,
        memory_usage_kb: int = None,
    ) -> "ValidationResult":
        """
        Create a new validation result with the given parameters.

        Args:
            run_id: ID of the validation run
            entity_type: Type of entity being validated
            severity: Severity level of the result
            message: Human-readable message
            validation_type: Type of validation performed
            entity_id: ID of the specific entity
            entity_name: Name of the entity
            field_name: Name of the field being validated
            field_path: Nested field path
            rule_name: Name of the validation rule
            expected_value: Expected value
            actual_value: Actual value found
            difference: Calculated difference
            metadata: Additional metadata
            execution_time_ms: Execution time in milliseconds
            memory_usage_kb: Memory usage in KB

        Returns:
            New ValidationResult instance
        """
        result = cls(
            run_id=run_id,
            entity_type=entity_type,
            severity=severity,
            message=message,
            validation_type=validation_type,
            entity_id=entity_id,
            entity_name=entity_name,
            field_name=field_name,
            field_path=field_path,
            rule_name=rule_name,
            expected_value=expected_value,
            actual_value=actual_value,
            difference=difference,
            execution_time_ms=execution_time_ms,
            memory_usage_kb=memory_usage_kb,
        )

        if metadata:
            result.set_metadata(metadata)

        return result

    @classmethod
    def get_results_by_run(
        cls,
        run_id: int,
        severity: str = None,
        entity_type: str = None,
        validation_type: str = None,
        limit: int = None,
    ):
        """Get validation results for a specific run with optional filtering."""
        query = cls.query.filter_by(run_id=run_id)

        if severity:
            query = query.filter_by(severity=severity)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if validation_type:
            query = query.filter_by(validation_type=validation_type)

        query = query.order_by(cls.timestamp.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_results_by_entity(
        cls,
        entity_type: str,
        entity_id: int = None,
        severity: str = None,
        limit: int = None,
    ):
        """Get validation results for a specific entity type or instance."""
        query = cls.query.filter_by(entity_type=entity_type)

        if entity_id:
            query = query.filter_by(entity_id=entity_id)
        if severity:
            query = query.filter_by(severity=severity)

        query = query.order_by(cls.timestamp.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_critical_issues(cls, entity_type: str = None, limit: int = 50):
        """Get recent critical validation issues."""
        query = cls.query.filter_by(severity=cls.SEVERITY_CRITICAL)

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_error_summary(cls, run_id: int) -> dict:
        """Get a summary of errors for a validation run."""
        results = cls.query.filter_by(run_id=run_id).all()

        summary = {
            "total": len(results),
            "info": len([r for r in results if r.is_info]),
            "warnings": len([r for r in results if r.is_warning]),
            "errors": len([r for r in results if r.is_error]),
            "critical": len([r for r in results if r.is_critical]),
            "issues": len([r for r in results if r.is_issue]),
        }

        # Add entity type breakdown
        entity_breakdown = {}
        for result in results:
            if result.entity_type not in entity_breakdown:
                entity_breakdown[result.entity_type] = {
                    "total": 0,
                    "info": 0,
                    "warnings": 0,
                    "errors": 0,
                    "critical": 0,
                }

            entity_breakdown[result.entity_type]["total"] += 1
            if result.is_info:
                entity_breakdown[result.entity_type]["info"] += 1
            elif result.is_warning:
                entity_breakdown[result.entity_type]["warnings"] += 1
            elif result.is_error:
                entity_breakdown[result.entity_type]["errors"] += 1
            elif result.is_critical:
                entity_breakdown[result.entity_type]["critical"] += 1

        summary["entity_breakdown"] = entity_breakdown

        return summary
