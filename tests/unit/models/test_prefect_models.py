"""
Unit Tests for Prefect Models
============================

Tests for the prefect_models module functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from models.prefect_models import (
    PrefectFlowRun,
    PrefectTaskRun,
    PrefectWorkflowStats
)


class TestPrefectFlowRun:
    """Test cases for PrefectFlowRun model."""
    
    def test_prefect_flow_run_creation(self, db_session):
        """Test creating a PrefectFlowRun instance."""
        flow_run = PrefectFlowRun(
            flow_run_id="test-flow-run-123",
            flow_name="test-flow",
            status="completed",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            error_message=None
        )
        
        db_session.add(flow_run)
        db_session.commit()
        
        assert flow_run.id is not None
        assert flow_run.flow_run_id == "test-flow-run-123"
        assert flow_run.flow_name == "test-flow"
        assert flow_run.status == "completed"
        assert flow_run.created_at is not None
        assert flow_run.updated_at is not None
    
    def test_prefect_flow_run_with_error(self, db_session):
        """Test creating a PrefectFlowRun with error."""
        flow_run = PrefectFlowRun(
            flow_run_id="test-flow-run-456",
            flow_name="test-flow",
            status="failed",
            start_time=datetime.now(timezone.utc),
            error_message="Test error message"
        )
        
        db_session.add(flow_run)
        db_session.commit()
        
        assert flow_run.error_message == "Test error message"
        assert flow_run.end_time is None
    
    def test_prefect_flow_run_to_dict(self, db_session):
        """Test converting PrefectFlowRun to dictionary."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=5)
        
        flow_run = PrefectFlowRun(
            flow_run_id="test-flow-run-789",
            flow_name="test-flow",
            status="completed",
            start_time=start_time,
            end_time=end_time,
            parameters={"param1": "value1"},
            result_summary={"success": True},
            duration_seconds=300.0,
            retry_count=2,
            is_successful=True
        )
        
        db_session.add(flow_run)
        db_session.commit()
        
        flow_dict = flow_run.to_dict()
        
        assert flow_dict['flow_run_id'] == "test-flow-run-789"
        assert flow_dict['flow_name'] == "test-flow"
        assert flow_dict['status'] == "completed"
        assert flow_dict['parameters'] == {"param1": "value1"}
        assert flow_dict['result_summary'] == {"success": True}
        assert flow_dict['duration_seconds'] == 300.0
        assert flow_dict['retry_count'] == 2
        assert flow_dict['is_successful'] is True
        assert 'created_at' in flow_dict
        assert 'updated_at' in flow_dict
    
    def test_create_from_prefect_flow_run(self):
        """Test creating PrefectFlowRun from Prefect flow run object."""
        # Mock Prefect flow run object
        mock_flow_run = MagicMock()
        mock_flow_run.id = "prefect-flow-run-123"
        mock_flow_run.flow.name = "test-flow"
        mock_flow_run.state.name = "completed"
        mock_flow_run.start_time = datetime.now(timezone.utc)
        mock_flow_run.end_time = datetime.now(timezone.utc)
        mock_flow_run.state.message = None
        mock_flow_run.state.is_completed.return_value = True
        mock_flow_run.state.is_failed.return_value = False
        
        flow_run = PrefectFlowRun.create_from_prefect_flow_run(mock_flow_run)
        
        assert flow_run.flow_run_id == "prefect-flow-run-123"
        assert flow_run.flow_name == "test-flow"
        assert flow_run.status == "completed"
        assert flow_run.is_successful is True
    
    def test_create_from_prefect_flow_run_with_error(self):
        """Test creating PrefectFlowRun from failed Prefect flow run."""
        # Mock Prefect flow run object with error
        mock_flow_run = MagicMock()
        mock_flow_run.id = "prefect-flow-run-456"
        mock_flow_run.flow.name = "test-flow"
        mock_flow_run.state.name = "failed"
        mock_flow_run.start_time = datetime.now(timezone.utc)
        mock_flow_run.end_time = datetime.now(timezone.utc)
        mock_flow_run.state.message = "Test error message"
        mock_flow_run.state.is_completed.return_value = True
        mock_flow_run.state.is_failed.return_value = True
        
        flow_run = PrefectFlowRun.create_from_prefect_flow_run(mock_flow_run)
        
        assert flow_run.status == "failed"
        assert flow_run.error_message == "Test error message"
        assert flow_run.is_successful is False
    
    def test_update_from_prefect_flow_run(self, db_session):
        """Test updating PrefectFlowRun from Prefect flow run object."""
        flow_run = PrefectFlowRun(
            flow_run_id="test-flow-run-123",
            flow_name="test-flow",
            status="running",
            start_time=datetime.now(timezone.utc)
        )
        
        db_session.add(flow_run)
        db_session.commit()
        
        # Mock updated Prefect flow run object
        mock_flow_run = MagicMock()
        mock_flow_run.state.name = "completed"
        mock_flow_run.start_time = flow_run.start_time
        mock_flow_run.end_time = datetime.now(timezone.utc)
        mock_flow_run.state.message = None
        mock_flow_run.state.is_completed.return_value = True
        mock_flow_run.state.is_failed.return_value = False
        
        flow_run.update_from_prefect_flow_run(mock_flow_run)
        db_session.commit()
        
        assert flow_run.status == "completed"
        assert flow_run.end_time is not None
        assert flow_run.is_successful is True
        assert flow_run.duration_seconds is not None


class TestPrefectTaskRun:
    """Test cases for PrefectTaskRun model."""
    
    def test_prefect_task_run_creation(self, db_session):
        """Test creating a PrefectTaskRun instance."""
        task_run = PrefectTaskRun(
            flow_run_id="test-flow-run-123",
            task_name="test-task",
            status="completed",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            retry_count=0
        )
        
        db_session.add(task_run)
        db_session.commit()
        
        assert task_run.id is not None
        assert task_run.flow_run_id == "test-flow-run-123"
        assert task_run.task_name == "test-task"
        assert task_run.status == "completed"
        assert task_run.retry_count == 0
    
    def test_prefect_task_run_with_retries(self, db_session):
        """Test creating a PrefectTaskRun with retries."""
        task_run = PrefectTaskRun(
            flow_run_id="test-flow-run-456",
            task_name="test-task",
            status="completed",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            retry_count=3,
            error_message="Previous attempts failed"
        )
        
        db_session.add(task_run)
        db_session.commit()
        
        assert task_run.retry_count == 3
        assert task_run.error_message == "Previous attempts failed"
    
    def test_prefect_task_run_to_dict(self, db_session):
        """Test converting PrefectTaskRun to dictionary."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(seconds=30)
        
        task_run = PrefectTaskRun(
            flow_run_id="test-flow-run-789",
            task_name="test-task",
            status="completed",
            start_time=start_time,
            end_time=end_time,
            parameters={"param1": "value1"},
            result_summary={"result": "success"},
            duration_seconds=30.0,
            retry_count=1,
            is_successful=True
        )
        
        db_session.add(task_run)
        db_session.commit()
        
        task_dict = task_run.to_dict()
        
        assert task_dict['flow_run_id'] == "test-flow-run-789"
        assert task_dict['task_name'] == "test-task"
        assert task_dict['status'] == "completed"
        assert task_dict['parameters'] == {"param1": "value1"}
        assert task_dict['result_summary'] == {"result": "success"}
        assert task_dict['duration_seconds'] == 30.0
        assert task_dict['retry_count'] == 1
        assert task_dict['is_successful'] is True
    
    def test_create_from_prefect_task_run(self):
        """Test creating PrefectTaskRun from Prefect task run object."""
        # Mock Prefect task run object
        mock_task_run = MagicMock()
        mock_task_run.task.name = "test-task"
        mock_task_run.state.name = "completed"
        mock_task_run.start_time = datetime.now(timezone.utc)
        mock_task_run.end_time = datetime.now(timezone.utc)
        mock_task_run.state.message = None
        mock_task_run.run_count = 1
        mock_task_run.state.is_completed.return_value = True
        mock_task_run.state.is_failed.return_value = False
        
        task_run = PrefectTaskRun.create_from_prefect_task_run(
            mock_task_run, "test-flow-run-123"
        )
        
        assert task_run.flow_run_id == "test-flow-run-123"
        assert task_run.task_name == "test-task"
        assert task_run.status == "completed"
        assert task_run.retry_count == 0
        assert task_run.is_successful is True
    
    def test_create_from_prefect_task_run_with_retries(self):
        """Test creating PrefectTaskRun from Prefect task run with retries."""
        # Mock Prefect task run object with retries
        mock_task_run = MagicMock()
        mock_task_run.task.name = "test-task"
        mock_task_run.state.name = "completed"
        mock_task_run.start_time = datetime.now(timezone.utc)
        mock_task_run.end_time = datetime.now(timezone.utc)
        mock_task_run.state.message = "Previous attempts failed"
        mock_task_run.run_count = 4  # 3 retries + 1 success
        mock_task_run.state.is_completed.return_value = True
        mock_task_run.state.is_failed.return_value = False
        
        task_run = PrefectTaskRun.create_from_prefect_task_run(
            mock_task_run, "test-flow-run-456"
        )
        
        assert task_run.retry_count == 3
        assert task_run.error_message == "Previous attempts failed"
    
    def test_update_from_prefect_task_run(self, db_session):
        """Test updating PrefectTaskRun from Prefect task run object."""
        task_run = PrefectTaskRun(
            flow_run_id="test-flow-run-123",
            task_name="test-task",
            status="running",
            start_time=datetime.now(timezone.utc)
        )
        
        db_session.add(task_run)
        db_session.commit()
        
        # Mock updated Prefect task run object
        mock_task_run = MagicMock()
        mock_task_run.task.name = "test-task"
        mock_task_run.state.name = "completed"
        mock_task_run.start_time = task_run.start_time
        mock_task_run.end_time = datetime.now(timezone.utc)
        mock_task_run.state.message = None
        mock_task_run.run_count = 2
        mock_task_run.state.is_completed.return_value = True
        mock_task_run.state.is_failed.return_value = False
        
        task_run.update_from_prefect_task_run(mock_task_run)
        db_session.commit()
        
        assert task_run.status == "completed"
        assert task_run.end_time is not None
        assert task_run.retry_count == 1
        assert task_run.is_successful is True
        assert task_run.duration_seconds is not None


class TestPrefectWorkflowStats:
    """Test cases for PrefectWorkflowStats model."""
    
    def test_prefect_workflow_stats_creation(self, db_session):
        """Test creating a PrefectWorkflowStats instance."""
        stats = PrefectWorkflowStats(
            flow_name="test-flow",
            date=datetime.now(timezone.utc).date(),
            period="daily",
            total_runs=10,
            successful_runs=8,
            failed_runs=2,
            avg_duration_seconds=120.0,
            min_duration_seconds=60.0,
            max_duration_seconds=180.0,
            total_errors=2,
            error_types={"NETWORK_ERROR": 1, "RATE_LIMIT_ERROR": 1}
        )
        
        db_session.add(stats)
        db_session.commit()
        
        assert stats.id is not None
        assert stats.flow_name == "test-flow"
        assert stats.period == "daily"
        assert stats.total_runs == 10
        assert stats.successful_runs == 8
        assert stats.failed_runs == 2
        assert stats.success_rate == 80.0
    
    def test_prefect_workflow_stats_to_dict(self, db_session):
        """Test converting PrefectWorkflowStats to dictionary."""
        stats = PrefectWorkflowStats(
            flow_name="test-flow",
            date=datetime.now(timezone.utc).date(),
            period="daily",
            total_runs=5,
            successful_runs=4,
            failed_runs=1,
            avg_duration_seconds=90.0,
            min_duration_seconds=45.0,
            max_duration_seconds=135.0,
            total_errors=1,
            error_types={"NETWORK_ERROR": 1}
        )
        
        db_session.add(stats)
        db_session.commit()
        
        stats_dict = stats.to_dict()
        
        assert stats_dict['flow_name'] == "test-flow"
        assert stats_dict['period'] == "daily"
        assert stats_dict['total_runs'] == 5
        assert stats_dict['successful_runs'] == 4
        assert stats_dict['failed_runs'] == 1
        assert stats_dict['success_rate'] == 80.0
        assert stats_dict['avg_duration_seconds'] == 90.0
        assert stats_dict['min_duration_seconds'] == 45.0
        assert stats_dict['max_duration_seconds'] == 135.0
        assert stats_dict['total_errors'] == 1
        assert stats_dict['error_types'] == {"NETWORK_ERROR": 1}
    
    def test_success_rate_calculation(self, db_session):
        """Test success rate calculation."""
        # Test with successful runs
        stats = PrefectWorkflowStats(
            flow_name="test-flow",
            date=datetime.now(timezone.utc).date(),
            period="daily",
            total_runs=10,
            successful_runs=8,
            failed_runs=2
        )
        
        assert stats.success_rate == 80.0
        
        # Test with no runs
        stats.total_runs = 0
        assert stats.success_rate == 0.0
        
        # Test with all successful
        stats.total_runs = 5
        stats.successful_runs = 5
        stats.failed_runs = 0
        assert stats.success_rate == 100.0
    
    def test_get_or_create_stats_daily(self, db_session):
        """Test getting or creating daily statistics."""
        date = datetime.now(timezone.utc)
        
        # Create new stats
        stats = PrefectWorkflowStats.get_or_create_stats("test-flow", date, "daily")
        
        assert stats.flow_name == "test-flow"
        assert stats.period == "daily"
        assert stats.date == date.date()
        
        # Get existing stats
        existing_stats = PrefectWorkflowStats.get_or_create_stats("test-flow", date, "daily")
        
        assert existing_stats.id == stats.id
    
    def test_get_or_create_stats_weekly(self, db_session):
        """Test getting or creating weekly statistics."""
        date = datetime.now(timezone.utc)
        
        stats = PrefectWorkflowStats.get_or_create_stats("test-flow", date, "weekly")
        
        assert stats.period == "weekly"
        # Should be normalized to start of week (Monday)
        assert stats.date.weekday() == 0  # Monday
    
    def test_get_or_create_stats_monthly(self, db_session):
        """Test getting or creating monthly statistics."""
        date = datetime.now(timezone.utc)
        
        stats = PrefectWorkflowStats.get_or_create_stats("test-flow", date, "monthly")
        
        assert stats.period == "monthly"
        # Should be normalized to first day of month
        assert stats.date.day == 1
    
    def test_get_or_create_stats_invalid_period(self, db_session):
        """Test getting or creating stats with invalid period."""
        date = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="Invalid period: invalid"):
            PrefectWorkflowStats.get_or_create_stats("test-flow", date, "invalid") 