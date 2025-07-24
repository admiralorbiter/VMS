"""
Prefect Models Module
====================

Database models for tracking Prefect workflow runs in the VMS application.
These models provide integration between Prefect workflows and the VMS database.
"""

from datetime import datetime, timezone
from models import db
from sqlalchemy import String, DateTime, Text, Integer, Boolean


class PrefectFlowRun(db.Model):
    """
    Model for tracking Prefect flow runs in VMS database.
    
    This model stores information about Prefect workflow executions
    for monitoring and audit purposes.
    
    Database Table:
        prefect_flow_runs - Tracks Prefect workflow executions
        
    Key Features:
        - Flow run tracking with unique identifiers
        - Status monitoring and history
        - Error tracking and debugging
        - Performance metrics storage
        - Integration with VMS database
    """
    __tablename__ = 'prefect_flow_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_run_id = db.Column(String(255), unique=True, nullable=False, index=True)
    flow_name = db.Column(String(255), nullable=False, index=True)
    status = db.Column(String(50), nullable=False, index=True)
    start_time = db.Column(DateTime(timezone=True), nullable=True)
    end_time = db.Column(DateTime(timezone=True), nullable=True)
    error_message = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    parameters = db.Column(db.JSON, nullable=True)
    result_summary = db.Column(db.JSON, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    retry_count = db.Column(Integer, default=0)
    is_successful = db.Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<PrefectFlowRun {self.flow_name}:{self.status}>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'flow_run_id': self.flow_run_id,
            'flow_name': self.flow_name,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parameters': self.parameters,
            'result_summary': self.result_summary,
            'duration_seconds': self.duration_seconds,
            'retry_count': self.retry_count,
            'is_successful': self.is_successful
        }
    
    @classmethod
    def create_from_prefect_flow_run(cls, prefect_flow_run, flow_name: str = None):
        """
        Create a PrefectFlowRun record from a Prefect flow run object.
        
        Args:
            prefect_flow_run: Prefect flow run object
            flow_name: Optional flow name override
            
        Returns:
            PrefectFlowRun instance
        """
        return cls(
            flow_run_id=prefect_flow_run.id,
            flow_name=flow_name or prefect_flow_run.flow.name,
            status=prefect_flow_run.state.name,
            start_time=prefect_flow_run.start_time,
            end_time=prefect_flow_run.end_time,
            error_message=str(prefect_flow_run.state.message) if prefect_flow_run.state.message else None,
            is_successful=prefect_flow_run.state.is_completed() and not prefect_flow_run.state.is_failed()
        )
    
    def update_from_prefect_flow_run(self, prefect_flow_run):
        """
        Update this record with data from a Prefect flow run object.
        
        Args:
            prefect_flow_run: Prefect flow run object
        """
        self.status = prefect_flow_run.state.name
        self.start_time = prefect_flow_run.start_time
        self.end_time = prefect_flow_run.end_time
        self.error_message = str(prefect_flow_run.state.message) if prefect_flow_run.state.message else None
        self.is_successful = prefect_flow_run.state.is_completed() and not prefect_flow_run.state.is_failed()
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate duration if both times are available
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()


class PrefectTaskRun(db.Model):
    """
    Model for tracking Prefect task runs in VMS database.
    
    This model stores detailed information about individual task executions
    within Prefect workflows for debugging and monitoring.
    
    Database Table:
        prefect_task_runs - Tracks individual Prefect task executions
        
    Key Features:
        - Task-level execution tracking
        - Error tracking and debugging
        - Performance metrics storage
        - Relationship to flow runs
    """
    __tablename__ = 'prefect_task_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_run_id = db.Column(String(255), nullable=False, index=True)
    task_name = db.Column(String(255), nullable=False, index=True)
    status = db.Column(String(50), nullable=False, index=True)
    start_time = db.Column(DateTime(timezone=True), nullable=True)
    end_time = db.Column(DateTime(timezone=True), nullable=True)
    error_message = db.Column(Text, nullable=True)
    retry_count = db.Column(Integer, default=0)
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    parameters = db.Column(db.JSON, nullable=True)
    result_summary = db.Column(db.JSON, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    is_successful = db.Column(Boolean, default=False)
    
    # Relationship to flow run
    flow_run = db.relationship('PrefectFlowRun', 
                              foreign_keys=[flow_run_id],
                              primaryjoin="PrefectTaskRun.flow_run_id == PrefectFlowRun.flow_run_id")
    
    def __repr__(self):
        return f"<PrefectTaskRun {self.task_name}:{self.status}>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'flow_run_id': self.flow_run_id,
            'task_name': self.task_name,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parameters': self.parameters,
            'result_summary': self.result_summary,
            'duration_seconds': self.duration_seconds,
            'is_successful': self.is_successful
        }
    
    @classmethod
    def create_from_prefect_task_run(cls, prefect_task_run, flow_run_id: str):
        """
        Create a PrefectTaskRun record from a Prefect task run object.
        
        Args:
            prefect_task_run: Prefect task run object
            flow_run_id: ID of the parent flow run
            
        Returns:
            PrefectTaskRun instance
        """
        return cls(
            flow_run_id=flow_run_id,
            task_name=prefect_task_run.task.name,
            status=prefect_task_run.state.name,
            start_time=prefect_task_run.start_time,
            end_time=prefect_task_run.end_time,
            error_message=str(prefect_task_run.state.message) if prefect_task_run.state.message else None,
            retry_count=prefect_task_run.run_count - 1,  # Prefect counts from 1
            is_successful=prefect_task_run.state.is_completed() and not prefect_task_run.state.is_failed()
        )
    
    def update_from_prefect_task_run(self, prefect_task_run):
        """
        Update this record with data from a Prefect task run object.
        
        Args:
            prefect_task_run: Prefect task run object
        """
        self.status = prefect_task_run.state.name
        self.start_time = prefect_task_run.start_time
        self.end_time = prefect_task_run.end_time
        self.error_message = str(prefect_task_run.state.message) if prefect_task_run.state.message else None
        self.retry_count = prefect_task_run.run_count - 1
        self.is_successful = prefect_task_run.state.is_completed() and not prefect_task_run.state.is_failed()
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate duration if both times are available
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()


class PrefectWorkflowStats(db.Model):
    """
    Model for storing aggregated workflow statistics.
    
    This model provides quick access to workflow performance metrics
    and success rates for monitoring and reporting.
    
    Database Table:
        prefect_workflow_stats - Aggregated workflow statistics
        
    Key Features:
        - Daily/weekly/monthly statistics
        - Success rate tracking
        - Performance metrics
        - Error rate monitoring
    """
    __tablename__ = 'prefect_workflow_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_name = db.Column(String(255), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    period = db.Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    
    # Statistics
    total_runs = db.Column(Integer, default=0)
    successful_runs = db.Column(Integer, default=0)
    failed_runs = db.Column(Integer, default=0)
    avg_duration_seconds = db.Column(db.Float, nullable=True)
    min_duration_seconds = db.Column(db.Float, nullable=True)
    max_duration_seconds = db.Column(db.Float, nullable=True)
    
    # Error tracking
    total_errors = db.Column(Integer, default=0)
    error_types = db.Column(db.JSON, nullable=True)  # Dict of error type counts
    
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<PrefectWorkflowStats {self.flow_name}:{self.date}:{self.period}>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'flow_name': self.flow_name,
            'date': self.date.isoformat() if self.date else None,
            'period': self.period,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'success_rate': self.success_rate,
            'avg_duration_seconds': self.avg_duration_seconds,
            'min_duration_seconds': self.min_duration_seconds,
            'max_duration_seconds': self.max_duration_seconds,
            'total_errors': self.total_errors,
            'error_types': self.error_types,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def success_rate(self):
        """Calculate success rate as a percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100
    
    @classmethod
    def get_or_create_stats(cls, flow_name: str, date: datetime, period: str = 'daily'):
        """
        Get or create statistics for a specific flow, date, and period.
        
        Args:
            flow_name: Name of the workflow
            date: Date for the statistics
            period: Time period (daily, weekly, monthly)
            
        Returns:
            PrefectWorkflowStats instance
        """
        # Normalize date based on period
        if period == 'daily':
            normalized_date = date.date()
        elif period == 'weekly':
            # Get the start of the week (Monday)
            normalized_date = date.date() - timedelta(days=date.weekday())
        elif period == 'monthly':
            normalized_date = date.replace(day=1).date()
        else:
            raise ValueError(f"Invalid period: {period}")
        
        stats = cls.query.filter_by(
            flow_name=flow_name,
            date=normalized_date,
            period=period
        ).first()
        
        if not stats:
            stats = cls(
                flow_name=flow_name,
                date=normalized_date,
                period=period
            )
            db.session.add(stats)
        
        return stats


# Import timedelta for date calculations
from datetime import timedelta 