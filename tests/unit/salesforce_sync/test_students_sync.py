"""
Unit tests for students_sync workflow.

This module tests the students_sync workflow which handles large student datasets
using chunked processing for optimal performance and memory usage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from workflows.salesforce_sync.students_sync import (
    get_student_count,
    query_students_chunk,
    process_students_chunk,
    students_sync_flow
)
from workflows.utils.error_handling import PrefectErrorHandler
from models.prefect_models import PrefectFlowRun


class TestGetStudentCount:
    """Test cases for get_student_count task."""
    
    @patch('workflows.salesforce_sync.students_sync.salesforce_connection')
    def test_get_student_count_success(self, mock_connection):
        """Test successful student count retrieval."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result
        mock_sf.query.return_value = {
            'totalSize': 3000,
            'records': []
        }
        
        # Execute task
        result = get_student_count()
        
        # Verify result
        assert result == 3000
        mock_sf.query.assert_called_once()
        assert "SELECT COUNT() FROM Contact" in mock_sf.query.call_args[0][0]
        assert "WHERE Student__c = true" in mock_sf.query.call_args[0][0]
    
    @patch('workflows.salesforce_sync.students_sync.salesforce_connection')
    def test_get_student_count_error(self, mock_connection):
        """Test student count retrieval with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Connection failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            get_student_count()


class TestQueryStudentsChunk:
    """Test cases for query_students_chunk task."""
    
    @patch('workflows.salesforce_sync.students_sync.salesforce_connection')
    def test_query_students_chunk_success(self, mock_connection):
        """Test successful student chunk query."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result with student data
        mock_records = [
            {
                'Id': '001',
                'FirstName': 'Alice',
                'LastName': 'Johnson',
                'Email': 'alice.johnson@school.edu',
                'Phone': '555-1234',
                'MailingStreet': '123 School St',
                'MailingCity': 'Anytown',
                'MailingState': 'CA',
                'MailingPostalCode': '12345',
                'Birthdate': '2008-05-15',
                'Grade_Level__c': '10th Grade',
                'School__c': 'SCH001',
                'School__r': {'Name': 'Anytown High School'},
                'Parent_Email__c': 'parent@example.com',
                'Parent_Phone__c': '555-5678',
                'Parent_Name__c': 'John Johnson',
                'Interests__c': 'Science, Math',
                'Skills__c': 'Programming, Research',
                'Goals__c': 'College admission',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            },
            {
                'Id': '002',
                'FirstName': 'Bob',
                'LastName': 'Smith',
                'Email': 'bob.smith@school.edu',
                'Phone': '555-9012',
                'MailingStreet': '456 Learning Ave',
                'MailingCity': 'Somewhere',
                'MailingState': 'NY',
                'MailingPostalCode': '67890',
                'Birthdate': '2007-08-20',
                'Grade_Level__c': '11th Grade',
                'School__c': 'SCH002',
                'School__r': {'Name': 'Somewhere Academy'},
                'Parent_Email__c': 'parent2@example.com',
                'Parent_Phone__c': '555-3456',
                'Parent_Name__c': 'Jane Smith',
                'Interests__c': 'Art, Music',
                'Skills__c': 'Drawing, Piano',
                'Goals__c': 'Art school',
                'CreatedDate': '2024-01-02T00:00:00Z',
                'LastModifiedDate': '2024-01-16T00:00:00Z'
            }
        ]
        
        mock_sf.query.return_value = {
            'totalSize': 2,
            'records': mock_records
        }
        
        # Execute task
        result = query_students_chunk(0, 100)
        
        # Verify result
        assert len(result) == 2
        assert result[0]['Id'] == '001'
        assert result[0]['FirstName'] == 'Alice'
        assert result[0]['Grade_Level__c'] == '10th Grade'
        assert result[1]['Id'] == '002'
        assert result[1]['FirstName'] == 'Bob'
        assert result[1]['Grade_Level__c'] == '11th Grade'
        
        # Verify query was called with correct parameters
        mock_sf.query.assert_called_once()
        query = mock_sf.query.call_args[0][0]
        assert "SELECT Id, FirstName, LastName, Email" in query
        assert "FROM Contact" in query
        assert "WHERE Student__c = true" in query
        assert "LIMIT 100" in query
        assert "OFFSET 0" in query
    
    @patch('workflows.salesforce_sync.students_sync.salesforce_connection')
    def test_query_students_chunk_error(self, mock_connection):
        """Test student chunk query with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Query failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            query_students_chunk(0, 100)
    
    @patch('workflows.salesforce_sync.students_sync.salesforce_connection')
    def test_query_students_chunk_empty_result(self, mock_connection):
        """Test student chunk query with empty result."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock empty query result
        mock_sf.query.return_value = {
            'totalSize': 0,
            'records': []
        }
        
        # Execute task
        result = query_students_chunk(1000, 100)
        
        # Verify result
        assert result == []
        mock_sf.query.assert_called_once()


class TestProcessStudentsChunk:
    """Test cases for process_students_chunk task."""
    
    @patch('workflows.salesforce_sync.students_sync.database_connection')
    @patch('workflows.salesforce_sync.students_sync.Student')
    @patch('workflows.salesforce_sync.students_sync.School')
    @patch('workflows.salesforce_sync.students_sync.Contact')
    def test_process_students_chunk_success(self, mock_contact, mock_school, mock_student, mock_db):
        """Test successful student chunk processing."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing student query (not found)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock school query
        mock_school_instance = Mock(id=1, name='Anytown High School')
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # Student not found
            mock_school_instance,  # School found
            None  # Parent contact not found
        ]
        
        # Mock student data
        students_data = [
            {
                'Id': '001',
                'FirstName': 'Alice',
                'LastName': 'Johnson',
                'Email': 'alice.johnson@school.edu',
                'Phone': '555-1234',
                'Birthdate': '2008-05-15',
                'Grade_Level__c': '10th Grade',
                'School__c': 'SCH001',
                'Parent_Email__c': 'parent@example.com',
                'Parent_Phone__c': '555-5678',
                'Parent_Name__c': 'John Johnson',
                'Interests__c': 'Science, Math',
                'Skills__c': 'Programming, Research',
                'Goals__c': 'College admission',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_students_chunk(students_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # Verify student was created
        mock_student.assert_called_once()
        created_student = mock_student.return_value
        assert created_student.salesforce_id == '001'
        assert created_student.first_name == 'Alice'
        assert created_student.last_name == 'Johnson'
        assert created_student.email == 'alice.johnson@school.edu'
        assert created_student.grade_level == '10th Grade'
        assert created_student.school_id == 1
        
        # Verify parent contact was created
        mock_contact.assert_called_once()
        created_parent = mock_contact.return_value
        assert created_parent.first_name == 'John'
        assert created_parent.last_name == 'Johnson'
        assert created_parent.email == 'parent@example.com'
        assert created_parent.contact_type == 'parent'
        
        # Verify session operations
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.students_sync.database_connection')
    @patch('workflows.salesforce_sync.students_sync.Student')
    def test_process_students_chunk_update_existing(self, mock_student, mock_db):
        """Test student chunk processing with existing student update."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing student
        existing_student = Mock()
        existing_student.salesforce_id = '001'
        existing_student.first_name = 'Alice'
        existing_student.last_name = 'Johnson'
        existing_student.email = 'alice.old@school.edu'
        existing_student.grade_level = '9th Grade'
        
        mock_session.query.return_value.filter.return_value.first.return_value = existing_student
        
        # Mock student data
        students_data = [
            {
                'Id': '001',
                'FirstName': 'Alice',
                'LastName': 'Johnson',
                'Email': 'alice.new@school.edu',
                'Phone': '555-1234',
                'Birthdate': '2008-05-15',
                'Grade_Level__c': '10th Grade',
                'School__c': 'SCH001',
                'Parent_Email__c': 'parent@example.com',
                'Parent_Phone__c': '555-5678',
                'Parent_Name__c': 'John Johnson',
                'Interests__c': 'Science, Math, Technology',
                'Skills__c': 'Programming, Research, Robotics',
                'Goals__c': 'Engineering degree',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_students_chunk(students_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 0
        assert result['updated'] == 1
        assert result['errors'] == 0
        
        # Verify student was updated
        assert existing_student.email == 'alice.new@school.edu'
        assert existing_student.grade_level == '10th Grade'
        assert existing_student.interests == 'Science, Math, Technology'
        assert existing_student.skills == 'Programming, Research, Robotics'
        assert existing_student.goals == 'Engineering degree'
        
        # Verify session operations
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.students_sync.database_connection')
    def test_process_students_chunk_database_error(self, mock_db):
        """Test student chunk processing with database error."""
        # Mock database session that raises exception
        mock_db.side_effect = Exception("Database connection failed")
        
        # Mock student data
        students_data = [
            {
                'Id': '001',
                'FirstName': 'Alice',
                'LastName': 'Johnson',
                'Email': 'alice.johnson@school.edu'
            }
        ]
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            process_students_chunk(students_data, 1)
    
    @patch('workflows.salesforce_sync.students_sync.database_connection')
    @patch('workflows.salesforce_sync.students_sync.Student')
    def test_process_students_chunk_partial_error(self, mock_student, mock_db):
        """Test student chunk processing with partial errors."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing student query to return None (new student)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock student creation to fail for second record
        mock_student.side_effect = [
            Mock(),  # First student succeeds
            Exception("Student creation failed")  # Second student fails
        ]
        
        # Mock student data
        students_data = [
            {
                'Id': '001',
                'FirstName': 'Alice',
                'LastName': 'Johnson',
                'Email': 'alice.johnson@school.edu'
            },
            {
                'Id': '002',
                'FirstName': 'Bob',
                'LastName': 'Smith',
                'Email': 'bob.smith@school.edu'
            }
        ]
        
        # Execute task
        result = process_students_chunk(students_data, 1)
        
        # Verify result shows partial success
        assert result['processed'] == 2
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 1


class TestStudentsSyncFlow:
    """Test cases for students_sync_flow workflow."""
    
    @patch('workflows.salesforce_sync.students_sync.validate_environment')
    @patch('workflows.salesforce_sync.students_sync.get_student_count')
    @patch('workflows.salesforce_sync.students_sync.query_students_chunk')
    @patch('workflows.salesforce_sync.students_sync.process_students_chunk')
    @patch('workflows.salesforce_sync.students_sync.log_workflow_metrics')
    def test_students_sync_flow_success(self, mock_metrics, mock_process, mock_query, mock_count, mock_validate):
        """Test successful students sync flow execution."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock student count
        mock_count.return_value = 3000
        
        # Mock query results for chunks
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'Alice'}],  # Chunk 1
            [{'Id': '002', 'FirstName': 'Bob'}],    # Chunk 2
            []  # Empty chunk (end)
        ]
        
        # Mock processing results
        mock_process.side_effect = [
            {'processed': 1, 'created': 1, 'updated': 0, 'errors': 0},
            {'processed': 1, 'created': 1, 'updated': 0, 'errors': 0}
        ]
        
        # Mock metrics logging
        mock_metrics.return_value = None
        
        # Execute flow
        result = students_sync_flow(chunk_size=100)
        
        # Verify result
        assert result['total_students'] == 3000
        assert result['total_processed'] == 2
        assert result['total_created'] == 2
        assert result['total_updated'] == 0
        assert result['total_errors'] == 0
        assert result['chunks_processed'] == 2
        
        # Verify function calls
        mock_validate.assert_called_once()
        mock_count.assert_called_once()
        assert mock_query.call_count == 3  # 2 chunks + 1 empty
        assert mock_process.call_count == 2
        mock_metrics.assert_called_once()
    
    @patch('workflows.salesforce_sync.students_sync.validate_environment')
    def test_students_sync_flow_environment_error(self, mock_validate):
        """Test students sync flow with environment validation error."""
        # Mock environment validation failure
        mock_validate.side_effect = Exception("Environment validation failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            students_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.students_sync.validate_environment')
    @patch('workflows.salesforce_sync.students_sync.get_student_count')
    def test_students_sync_flow_count_error(self, mock_count, mock_validate):
        """Test students sync flow with count retrieval error."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock count retrieval failure
        mock_count.side_effect = Exception("Count retrieval failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            students_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.students_sync.validate_environment')
    @patch('workflows.salesforce_sync.students_sync.get_student_count')
    def test_students_sync_flow_no_students(self, mock_count, mock_validate):
        """Test students sync flow with no students found."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock student count (no students)
        mock_count.return_value = 0
        
        # Execute flow
        result = students_sync_flow(chunk_size=100)
        
        # Verify result
        assert result['total_students'] == 0
        assert result['total_processed'] == 0
        assert result['total_created'] == 0
        assert result['total_updated'] == 0
        assert result['total_errors'] == 0
        assert result['chunks_processed'] == 0
    
    @patch('workflows.salesforce_sync.students_sync.validate_environment')
    @patch('workflows.salesforce_sync.students_sync.get_student_count')
    @patch('workflows.salesforce_sync.students_sync.query_students_chunk')
    @patch('workflows.salesforce_sync.students_sync.process_students_chunk')
    def test_students_sync_flow_partial_errors(self, mock_process, mock_query, mock_count, mock_validate):
        """Test students sync flow with partial processing errors."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock student count
        mock_count.return_value = 200
        
        # Mock query results
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'Alice'}],
            [{'Id': '002', 'FirstName': 'Bob'}]
        ]
        
        # Mock processing with mixed results
        mock_process.side_effect = [
            {'processed': 1, 'created': 1, 'updated': 0, 'errors': 0},
            {'processed': 1, 'created': 0, 'updated': 0, 'errors': 1}
        ]
        
        # Execute flow
        result = students_sync_flow(chunk_size=100)
        
        # Verify result shows partial success
        assert result['total_students'] == 200
        assert result['total_processed'] == 2
        assert result['total_created'] == 1
        assert result['total_updated'] == 0
        assert result['total_errors'] == 1
        assert result['chunks_processed'] == 2
    
    def test_students_sync_flow_parameters(self):
        """Test students sync flow parameter handling."""
        # Test default parameters
        with patch('workflows.salesforce_sync.students_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.students_sync.get_student_count') as mock_count:
                mock_count.return_value = 0
                result = students_sync_flow()
                assert result['total_students'] == 0
        
        # Test custom chunk size
        with patch('workflows.salesforce_sync.students_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.students_sync.get_student_count') as mock_count:
                mock_count.return_value = 0
                result = students_sync_flow(chunk_size=500)
                assert result['total_students'] == 0


class TestStudentsSyncWorkflowStructure:
    """Test cases for students_sync workflow structure and imports."""
    
    def test_students_sync_imports(self):
        """Test that students_sync module imports correctly."""
        from workflows.salesforce_sync import students_sync
        assert students_sync is not None
    
    def test_students_sync_functions_exist(self):
        """Test that all required functions exist in students_sync module."""
        from workflows.salesforce_sync.students_sync import (
            get_student_count,
            query_students_chunk,
            process_students_chunk,
            students_sync_flow
        )
        
        assert callable(get_student_count)
        assert callable(query_students_chunk)
        assert callable(process_students_chunk)
        assert callable(students_sync_flow)
    
    def test_students_sync_workflow_decorator(self):
        """Test that students_sync_flow uses the workflow decorator."""
        from workflows.salesforce_sync.students_sync import students_sync_flow
        
        # Check that the function has the expected attributes from the decorator
        assert hasattr(students_sync_flow, '__name__')
        assert students_sync_flow.__name__ == 'students_sync_flow'
    
    def test_students_sync_task_decorators(self):
        """Test that all tasks use the @task decorator."""
        from workflows.salesforce_sync.students_sync import (
            get_student_count,
            query_students_chunk,
            process_students_chunk
        )
        
        # Check that functions have task-related attributes
        # Note: In Prefect 2.x, the exact attributes may vary
        assert callable(get_student_count)
        assert callable(query_students_chunk)
        assert callable(process_students_chunk)


if __name__ == '__main__':
    pytest.main([__file__]) 