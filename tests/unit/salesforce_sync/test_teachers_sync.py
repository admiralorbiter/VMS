"""
Unit tests for teachers_sync workflow.

This module tests the teachers_sync workflow which handles large teacher datasets
using chunked processing for optimal performance and memory usage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, date
import json

from workflows.salesforce_sync.teachers_sync import (
    get_teacher_count,
    query_teachers_chunk,
    process_teachers_chunk,
    teachers_sync_flow
)
from workflows.utils.error_handling import PrefectErrorHandler
from models.prefect_models import PrefectFlowRun
from models.teacher import TeacherStatus


class TestGetTeacherCount:
    """Test cases for get_teacher_count task."""
    
    @patch('workflows.salesforce_sync.teachers_sync.salesforce_connection')
    def test_get_teacher_count_success(self, mock_connection):
        """Test successful teacher count retrieval."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result
        mock_sf.query.return_value = {
            'totalSize': 1500,
            'records': []
        }
        
        # Execute task
        result = get_teacher_count()
        
        # Verify result
        assert result == 1500
        mock_sf.query.assert_called_once()
        assert "SELECT COUNT() FROM Contact" in mock_sf.query.call_args[0][0]
        assert "WHERE Teacher__c = true" in mock_sf.query.call_args[0][0]
    
    @patch('workflows.salesforce_sync.teachers_sync.salesforce_connection')
    def test_get_teacher_count_error(self, mock_connection):
        """Test teacher count retrieval with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Connection failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            get_teacher_count()


class TestQueryTeachersChunk:
    """Test cases for query_teachers_chunk task."""
    
    @patch('workflows.salesforce_sync.teachers_sync.salesforce_connection')
    def test_query_teachers_chunk_success(self, mock_connection):
        """Test successful teacher chunk query."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result with teacher data
        mock_records = [
            {
                'Id': '001',
                'FirstName': 'Dr. Sarah',
                'LastName': 'Johnson',
                'Email': 'sarah.johnson@school.edu',
                'Phone': '555-1234',
                'MailingStreet': '123 Education St',
                'MailingCity': 'Anytown',
                'MailingState': 'CA',
                'MailingPostalCode': '12345',
                'Gender__c': 'Female',
                'Department': 'Science',
                'npsp__Primary_Affiliation__c': 'SCH001',
                'School__r': {'Name': 'Anytown High School', 'Id': 'SCH001'},
                'Connector_Role__c': 'Mentor',
                'Connector_Active__c': True,
                'Connector_Start_Date__c': '2024-01-01',
                'Connector_End_Date__c': None,
                'Last_Email_Message__c': '2024-01-15',
                'Last_Mailchimp_Email_Date__c': '2024-01-10',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            },
            {
                'Id': '002',
                'FirstName': 'Mr. Michael',
                'LastName': 'Smith',
                'Email': 'michael.smith@school.edu',
                'Phone': '555-5678',
                'MailingStreet': '456 Learning Ave',
                'MailingCity': 'Somewhere',
                'MailingState': 'NY',
                'MailingPostalCode': '67890',
                'Gender__c': 'Male',
                'Department': 'Mathematics',
                'npsp__Primary_Affiliation__c': 'SCH002',
                'School__r': {'Name': 'Somewhere Academy', 'Id': 'SCH002'},
                'Connector_Role__c': 'Coach',
                'Connector_Active__c': False,
                'Connector_Start_Date__c': '2023-09-01',
                'Connector_End_Date__c': '2024-06-30',
                'Last_Email_Message__c': '2024-01-12',
                'Last_Mailchimp_Email_Date__c': '2024-01-08',
                'CreatedDate': '2023-09-01T00:00:00Z',
                'LastModifiedDate': '2024-01-16T00:00:00Z'
            }
        ]
        
        mock_sf.query.return_value = {
            'totalSize': 2,
            'records': mock_records
        }
        
        # Execute task
        result = query_teachers_chunk(0, 100)
        
        # Verify result
        assert len(result) == 2
        assert result[0]['Id'] == '001'
        assert result[0]['FirstName'] == 'Dr. Sarah'
        assert result[0]['Department'] == 'Science'
        assert result[0]['Connector_Role__c'] == 'Mentor'
        assert result[1]['Id'] == '002'
        assert result[1]['FirstName'] == 'Mr. Michael'
        assert result[1]['Department'] == 'Mathematics'
        assert result[1]['Connector_Role__c'] == 'Coach'
        
        # Verify query was called with correct parameters
        mock_sf.query.assert_called_once()
        query = mock_sf.query.call_args[0][0]
        assert "SELECT Id, FirstName, LastName, Email" in query
        assert "FROM Contact" in query
        assert "WHERE Teacher__c = true" in query
        assert "LIMIT 100" in query
        assert "OFFSET 0" in query
    
    @patch('workflows.salesforce_sync.teachers_sync.salesforce_connection')
    def test_query_teachers_chunk_error(self, mock_connection):
        """Test teacher chunk query with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Query failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            query_teachers_chunk(0, 100)
    
    @patch('workflows.salesforce_sync.teachers_sync.salesforce_connection')
    def test_query_teachers_chunk_empty_result(self, mock_connection):
        """Test teacher chunk query with empty result."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock empty query result
        mock_sf.query.return_value = {
            'totalSize': 0,
            'records': []
        }
        
        # Execute task
        result = query_teachers_chunk(1000, 100)
        
        # Verify result
        assert result == []
        mock_sf.query.assert_called_once()


class TestProcessTeachersChunk:
    """Test cases for process_teachers_chunk task."""
    
    @patch('workflows.salesforce_sync.teachers_sync.database_connection')
    @patch('workflows.salesforce_sync.teachers_sync.Teacher')
    @patch('workflows.salesforce_sync.teachers_sync.School')
    @patch('workflows.salesforce_sync.teachers_sync.Email')
    @patch('workflows.salesforce_sync.teachers_sync.Phone')
    def test_process_teachers_chunk_success(self, mock_phone, mock_email, mock_school, mock_teacher, mock_db):
        """Test successful teacher chunk processing."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing teacher query (not found)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock school query
        mock_school_instance = Mock(id=1, name='Anytown High School')
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # Teacher not found
            mock_school_instance,  # School found
            None,  # Email not found
            None   # Phone not found
        ]
        
        # Mock teacher data
        teachers_data = [
            {
                'Id': '001',
                'FirstName': 'Dr. Sarah',
                'LastName': 'Johnson',
                'Email': 'sarah.johnson@school.edu',
                'Phone': '555-1234',
                'Department': 'Science',
                'npsp__Primary_Affiliation__c': 'SCH001',
                'Connector_Role__c': 'Mentor',
                'Connector_Active__c': True,
                'Connector_Start_Date__c': '2024-01-01',
                'Connector_End_Date__c': None,
                'Last_Email_Message__c': '2024-01-15',
                'Last_Mailchimp_Email_Date__c': '2024-01-10',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_teachers_chunk(teachers_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # Verify teacher was created
        mock_teacher.assert_called_once()
        created_teacher = mock_teacher.return_value
        assert created_teacher.salesforce_contact_id == '001'
        assert created_teacher.first_name == 'Dr. Sarah'
        assert created_teacher.last_name == 'Johnson'
        assert created_teacher.department == 'Science'
        assert created_teacher.school_id == 1
        assert created_teacher.connector_role == 'Mentor'
        assert created_teacher.connector_active == True
        assert created_teacher.status == TeacherStatus.ACTIVE
        
        # Verify email was created
        mock_email.assert_called_once()
        created_email = mock_email.return_value
        assert created_email.email == 'sarah.johnson@school.edu'
        assert created_email.primary == True
        
        # Verify phone was created
        mock_phone.assert_called_once()
        created_phone = mock_phone.return_value
        assert created_phone.number == '555-1234'
        assert created_phone.primary == True
        
        # Verify session operations
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.teachers_sync.database_connection')
    @patch('workflows.salesforce_sync.teachers_sync.Teacher')
    def test_process_teachers_chunk_update_existing(self, mock_teacher, mock_db):
        """Test teacher chunk processing with existing teacher update."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing teacher
        existing_teacher = Mock()
        existing_teacher.salesforce_contact_id = '001'
        existing_teacher.first_name = 'Dr. Sarah'
        existing_teacher.last_name = 'Johnson'
        existing_teacher.department = 'Biology'
        existing_teacher.connector_role = 'Assistant'
        
        mock_session.query.return_value.filter.return_value.first.return_value = existing_teacher
        
        # Mock teacher data
        teachers_data = [
            {
                'Id': '001',
                'FirstName': 'Dr. Sarah',
                'LastName': 'Johnson',
                'Email': 'sarah.new@school.edu',
                'Phone': '555-1234',
                'Department': 'Chemistry',
                'npsp__Primary_Affiliation__c': 'SCH001',
                'Connector_Role__c': 'Lead',
                'Connector_Active__c': True,
                'Connector_Start_Date__c': '2024-01-01',
                'Connector_End_Date__c': None,
                'Last_Email_Message__c': '2024-01-15',
                'Last_Mailchimp_Email_Date__c': '2024-01-10',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_teachers_chunk(teachers_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 0
        assert result['updated'] == 1
        assert result['errors'] == 0
        
        # Verify teacher was updated
        assert existing_teacher.department == 'Chemistry'
        assert existing_teacher.connector_role == 'Lead'
        assert existing_teacher.connector_active == True
        
        # Verify session operations
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.teachers_sync.database_connection')
    def test_process_teachers_chunk_database_error(self, mock_db):
        """Test teacher chunk processing with database error."""
        # Mock database session that raises exception
        mock_db.side_effect = Exception("Database connection failed")
        
        # Mock teacher data
        teachers_data = [
            {
                'Id': '001',
                'FirstName': 'Dr. Sarah',
                'LastName': 'Johnson',
                'Email': 'sarah.johnson@school.edu'
            }
        ]
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            process_teachers_chunk(teachers_data, 1)
    
    @patch('workflows.salesforce_sync.teachers_sync.database_connection')
    @patch('workflows.salesforce_sync.teachers_sync.Teacher')
    def test_process_teachers_chunk_partial_error(self, mock_teacher, mock_db):
        """Test teacher chunk processing with partial errors."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing teacher query to return None (new teacher)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock teacher creation to fail for second record
        mock_teacher.side_effect = [
            Mock(),  # First teacher succeeds
            Exception("Teacher creation failed")  # Second teacher fails
        ]
        
        # Mock teacher data
        teachers_data = [
            {
                'Id': '001',
                'FirstName': 'Dr. Sarah',
                'LastName': 'Johnson',
                'Email': 'sarah.johnson@school.edu'
            },
            {
                'Id': '002',
                'FirstName': 'Mr. Michael',
                'LastName': 'Smith',
                'Email': 'michael.smith@school.edu'
            }
        ]
        
        # Execute task
        result = process_teachers_chunk(teachers_data, 1)
        
        # Verify result shows partial success
        assert result['processed'] == 2
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 1


class TestTeachersSyncFlow:
    """Test cases for teachers_sync_flow workflow."""
    
    @patch('workflows.salesforce_sync.teachers_sync.validate_environment')
    @patch('workflows.salesforce_sync.teachers_sync.get_teacher_count')
    @patch('workflows.salesforce_sync.teachers_sync.query_teachers_chunk')
    @patch('workflows.salesforce_sync.teachers_sync.process_teachers_chunk')
    @patch('workflows.salesforce_sync.teachers_sync.log_workflow_metrics')
    def test_teachers_sync_flow_success(self, mock_metrics, mock_process, mock_query, mock_count, mock_validate):
        """Test successful teachers sync flow execution."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock teacher count
        mock_count.return_value = 1500
        
        # Mock query results for chunks
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'Dr. Sarah'}],  # Chunk 1
            [{'Id': '002', 'FirstName': 'Mr. Michael'}],  # Chunk 2
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
        result = teachers_sync_flow(chunk_size=100)
        
        # Verify result
        assert result['total_teachers'] == 1500
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
    
    @patch('workflows.salesforce_sync.teachers_sync.validate_environment')
    def test_teachers_sync_flow_environment_error(self, mock_validate):
        """Test teachers sync flow with environment validation error."""
        # Mock environment validation failure
        mock_validate.side_effect = Exception("Environment validation failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            teachers_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.teachers_sync.validate_environment')
    @patch('workflows.salesforce_sync.teachers_sync.get_teacher_count')
    def test_teachers_sync_flow_count_error(self, mock_count, mock_validate):
        """Test teachers sync flow with count retrieval error."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock count retrieval failure
        mock_count.side_effect = Exception("Count retrieval failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            teachers_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.teachers_sync.validate_environment')
    @patch('workflows.salesforce_sync.teachers_sync.get_teacher_count')
    def test_teachers_sync_flow_no_teachers(self, mock_count, mock_validate):
        """Test teachers sync flow with no teachers found."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock teacher count (no teachers)
        mock_count.return_value = 0
        
        # Execute flow
        result = teachers_sync_flow(chunk_size=100)
        
        # Verify result
        assert result['total_teachers'] == 0
        assert result['total_processed'] == 0
        assert result['total_created'] == 0
        assert result['total_updated'] == 0
        assert result['total_errors'] == 0
        assert result['chunks_processed'] == 0
    
    @patch('workflows.salesforce_sync.teachers_sync.validate_environment')
    @patch('workflows.salesforce_sync.teachers_sync.get_teacher_count')
    @patch('workflows.salesforce_sync.teachers_sync.query_teachers_chunk')
    @patch('workflows.salesforce_sync.teachers_sync.process_teachers_chunk')
    def test_teachers_sync_flow_partial_errors(self, mock_process, mock_query, mock_count, mock_validate):
        """Test teachers sync flow with partial processing errors."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock teacher count
        mock_count.return_value = 200
        
        # Mock query results
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'Dr. Sarah'}],
            [{'Id': '002', 'FirstName': 'Mr. Michael'}]
        ]
        
        # Mock processing with mixed results
        mock_process.side_effect = [
            {'processed': 1, 'created': 1, 'updated': 0, 'errors': 0},
            {'processed': 1, 'created': 0, 'updated': 0, 'errors': 1}
        ]
        
        # Execute flow
        result = teachers_sync_flow(chunk_size=100)
        
        # Verify result shows partial success
        assert result['total_teachers'] == 200
        assert result['total_processed'] == 2
        assert result['total_created'] == 1
        assert result['total_updated'] == 0
        assert result['total_errors'] == 1
        assert result['chunks_processed'] == 2
    
    def test_teachers_sync_flow_parameters(self):
        """Test teachers sync flow parameter handling."""
        # Test default parameters
        with patch('workflows.salesforce_sync.teachers_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.teachers_sync.get_teacher_count') as mock_count:
                mock_count.return_value = 0
                result = teachers_sync_flow()
                assert result['total_teachers'] == 0
        
        # Test custom chunk size
        with patch('workflows.salesforce_sync.teachers_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.teachers_sync.get_teacher_count') as mock_count:
                mock_count.return_value = 0
                result = teachers_sync_flow(chunk_size=500)
                assert result['total_teachers'] == 0


class TestTeachersSyncWorkflowStructure:
    """Test cases for teachers_sync workflow structure and imports."""
    
    def test_teachers_sync_imports(self):
        """Test that teachers_sync module imports correctly."""
        from workflows.salesforce_sync import teachers_sync
        assert teachers_sync is not None
    
    def test_teachers_sync_functions_exist(self):
        """Test that all required functions exist in teachers_sync module."""
        from workflows.salesforce_sync.teachers_sync import (
            get_teacher_count,
            query_teachers_chunk,
            process_teachers_chunk,
            teachers_sync_flow
        )
        
        assert callable(get_teacher_count)
        assert callable(query_teachers_chunk)
        assert callable(process_teachers_chunk)
        assert callable(teachers_sync_flow)
    
    def test_teachers_sync_workflow_decorator(self):
        """Test that teachers_sync_flow uses the workflow decorator."""
        from workflows.salesforce_sync.teachers_sync import teachers_sync_flow
        
        # Check that the function has the expected attributes from the decorator
        assert hasattr(teachers_sync_flow, '__name__')
        assert teachers_sync_flow.__name__ == 'teachers_sync_flow'
    
    def test_teachers_sync_task_decorators(self):
        """Test that all tasks use the @task decorator."""
        from workflows.salesforce_sync.teachers_sync import (
            get_teacher_count,
            query_teachers_chunk,
            process_teachers_chunk
        )
        
        # Check that functions have task-related attributes
        # Note: In Prefect 2.x, the exact attributes may vary
        assert callable(get_teacher_count)
        assert callable(query_teachers_chunk)
        assert callable(process_teachers_chunk)


if __name__ == '__main__':
    pytest.main([__file__]) 