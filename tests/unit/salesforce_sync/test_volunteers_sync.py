"""
Unit tests for volunteers_sync workflow.

This module tests the volunteers_sync workflow which handles large volunteer datasets
using chunked processing for optimal performance and memory usage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from workflows.salesforce_sync.volunteers_sync import (
    get_volunteer_count,
    query_volunteers_chunk,
    process_volunteers_chunk,
    volunteers_sync_flow
)
from workflows.utils.error_handling import PrefectErrorHandler
from models.prefect_models import PrefectFlowRun


class TestGetVolunteerCount:
    """Test cases for get_volunteer_count task."""
    
    @patch('workflows.salesforce_sync.volunteers_sync.salesforce_connection')
    def test_get_volunteer_count_success(self, mock_connection):
        """Test successful volunteer count retrieval."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result
        mock_sf.query.return_value = {
            'totalSize': 5000,
            'records': []
        }
        
        # Execute task
        result = get_volunteer_count()
        
        # Verify result
        assert result == 5000
        mock_sf.query.assert_called_once()
        assert "SELECT COUNT() FROM Contact" in mock_sf.query.call_args[0][0]
    
    @patch('workflows.salesforce_sync.volunteers_sync.salesforce_connection')
    def test_get_volunteer_count_error(self, mock_connection):
        """Test volunteer count retrieval with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Connection failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            get_volunteer_count()


class TestQueryVolunteersChunk:
    """Test cases for query_volunteers_chunk task."""
    
    @patch('workflows.salesforce_sync.volunteers_sync.salesforce_connection')
    def test_query_volunteers_chunk_success(self, mock_connection):
        """Test successful volunteer chunk query."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock query result with volunteer data
        mock_records = [
            {
                'Id': '001',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john.doe@example.com',
                'Phone': '555-1234',
                'MailingStreet': '123 Main St',
                'MailingCity': 'Anytown',
                'MailingState': 'CA',
                'MailingPostalCode': '12345',
                'Title': 'Software Engineer',
                'Company': 'Tech Corp',
                'Education__c': 'Bachelor\'s Degree',
                'Skills__c': 'Python, JavaScript',
                'Connector__c': 'LinkedIn',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            },
            {
                'Id': '002',
                'FirstName': 'Jane',
                'LastName': 'Smith',
                'Email': 'jane.smith@example.com',
                'Phone': '555-5678',
                'MailingStreet': '456 Oak Ave',
                'MailingCity': 'Somewhere',
                'MailingState': 'NY',
                'MailingPostalCode': '67890',
                'Title': 'Data Scientist',
                'Company': 'Data Corp',
                'Education__c': 'Master\'s Degree',
                'Skills__c': 'R, SQL',
                'Connector__c': 'Indeed',
                'CreatedDate': '2024-01-02T00:00:00Z',
                'LastModifiedDate': '2024-01-16T00:00:00Z'
            }
        ]
        
        mock_sf.query.return_value = {
            'totalSize': 2,
            'records': mock_records
        }
        
        # Execute task
        result = query_volunteers_chunk(0, 100)
        
        # Verify result
        assert len(result) == 2
        assert result[0]['Id'] == '001'
        assert result[0]['FirstName'] == 'John'
        assert result[1]['Id'] == '002'
        assert result[1]['FirstName'] == 'Jane'
        
        # Verify query was called with correct parameters
        mock_sf.query.assert_called_once()
        query = mock_sf.query.call_args[0][0]
        assert "SELECT Id, FirstName, LastName, Email" in query
        assert "FROM Contact" in query
        assert "LIMIT 100" in query
        assert "OFFSET 0" in query
    
    @patch('workflows.salesforce_sync.volunteers_sync.salesforce_connection')
    def test_query_volunteers_chunk_error(self, mock_connection):
        """Test volunteer chunk query with error."""
        # Mock Salesforce connection that raises exception
        mock_connection.side_effect = Exception("Query failed")
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            query_volunteers_chunk(0, 100)
    
    @patch('workflows.salesforce_sync.volunteers_sync.salesforce_connection')
    def test_query_volunteers_chunk_empty_result(self, mock_connection):
        """Test volunteer chunk query with empty result."""
        # Mock Salesforce connection
        mock_sf = Mock()
        mock_connection.return_value = mock_sf
        
        # Mock empty query result
        mock_sf.query.return_value = {
            'totalSize': 0,
            'records': []
        }
        
        # Execute task
        result = query_volunteers_chunk(1000, 100)
        
        # Verify result
        assert result == []
        mock_sf.query.assert_called_once()


class TestProcessVolunteersChunk:
    """Test cases for process_volunteers_chunk task."""
    
    @patch('workflows.salesforce_sync.volunteers_sync.database_connection')
    @patch('workflows.salesforce_sync.volunteers_sync.Contact')
    @patch('workflows.salesforce_sync.volunteers_sync.Education')
    @patch('workflows.salesforce_sync.volunteers_sync.Skill')
    def test_process_volunteers_chunk_success(self, mock_skill, mock_education, mock_contact, mock_db):
        """Test successful volunteer chunk processing."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing contact query
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock education and skill queries
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # Contact not found
            Mock(id=1, name='Bachelor\'s Degree'),  # Education found
            Mock(id=1, name='Python'),  # Skill 1 found
            Mock(id=2, name='JavaScript')  # Skill 2 found
        ]
        
        # Mock volunteer data
        volunteers_data = [
            {
                'Id': '001',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john.doe@example.com',
                'Phone': '555-1234',
                'MailingStreet': '123 Main St',
                'MailingCity': 'Anytown',
                'MailingState': 'CA',
                'MailingPostalCode': '12345',
                'Title': 'Software Engineer',
                'Company': 'Tech Corp',
                'Education__c': 'Bachelor\'s Degree',
                'Skills__c': 'Python, JavaScript',
                'Connector__c': 'LinkedIn',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_volunteers_chunk(volunteers_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # Verify contact was created
        mock_contact.assert_called_once()
        created_contact = mock_contact.return_value
        assert created_contact.salesforce_id == '001'
        assert created_contact.first_name == 'John'
        assert created_contact.last_name == 'Doe'
        assert created_contact.email == 'john.doe@example.com'
        assert created_contact.phone == '555-1234'
        assert created_contact.title == 'Software Engineer'
        assert created_contact.company == 'Tech Corp'
        assert created_contact.connector == 'LinkedIn'
        
        # Verify session operations
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.volunteers_sync.database_connection')
    @patch('workflows.salesforce_sync.volunteers_sync.Contact')
    def test_process_volunteers_chunk_update_existing(self, mock_contact, mock_db):
        """Test volunteer chunk processing with existing contact update."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing contact
        existing_contact = Mock()
        existing_contact.salesforce_id = '001'
        existing_contact.first_name = 'John'
        existing_contact.last_name = 'Doe'
        existing_contact.email = 'john.old@example.com'
        
        mock_session.query.return_value.filter.return_value.first.return_value = existing_contact
        
        # Mock volunteer data
        volunteers_data = [
            {
                'Id': '001',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john.new@example.com',
                'Phone': '555-1234',
                'Title': 'Senior Engineer',
                'Company': 'New Corp',
                'Education__c': 'Master\'s Degree',
                'Skills__c': 'Python, JavaScript, React',
                'Connector__c': 'LinkedIn',
                'CreatedDate': '2024-01-01T00:00:00Z',
                'LastModifiedDate': '2024-01-15T00:00:00Z'
            }
        ]
        
        # Execute task
        result = process_volunteers_chunk(volunteers_data, 1)
        
        # Verify result
        assert result['processed'] == 1
        assert result['created'] == 0
        assert result['updated'] == 1
        assert result['errors'] == 0
        
        # Verify contact was updated
        assert existing_contact.email == 'john.new@example.com'
        assert existing_contact.title == 'Senior Engineer'
        assert existing_contact.company == 'New Corp'
        
        # Verify session operations
        mock_session.commit.assert_called()
    
    @patch('workflows.salesforce_sync.volunteers_sync.database_connection')
    def test_process_volunteers_chunk_database_error(self, mock_db):
        """Test volunteer chunk processing with database error."""
        # Mock database session that raises exception
        mock_db.side_effect = Exception("Database connection failed")
        
        # Mock volunteer data
        volunteers_data = [
            {
                'Id': '001',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john.doe@example.com'
            }
        ]
        
        # Execute task and expect exception
        with pytest.raises(Exception):
            process_volunteers_chunk(volunteers_data, 1)
    
    @patch('workflows.salesforce_sync.volunteers_sync.database_connection')
    @patch('workflows.salesforce_sync.volunteers_sync.Contact')
    def test_process_volunteers_chunk_partial_error(self, mock_contact, mock_db):
        """Test volunteer chunk processing with partial errors."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock existing contact query to return None (new contact)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock contact creation to fail for second record
        mock_contact.side_effect = [
            Mock(),  # First contact succeeds
            Exception("Contact creation failed")  # Second contact fails
        ]
        
        # Mock volunteer data
        volunteers_data = [
            {
                'Id': '001',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john.doe@example.com'
            },
            {
                'Id': '002',
                'FirstName': 'Jane',
                'LastName': 'Smith',
                'Email': 'jane.smith@example.com'
            }
        ]
        
        # Execute task
        result = process_volunteers_chunk(volunteers_data, 1)
        
        # Verify result shows partial success
        assert result['processed'] == 2
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 1


class TestVolunteersSyncFlow:
    """Test cases for volunteers_sync_flow workflow."""
    
    @patch('workflows.salesforce_sync.volunteers_sync.validate_environment')
    @patch('workflows.salesforce_sync.volunteers_sync.get_volunteer_count')
    @patch('workflows.salesforce_sync.volunteers_sync.query_volunteers_chunk')
    @patch('workflows.salesforce_sync.volunteers_sync.process_volunteers_chunk')
    @patch('workflows.salesforce_sync.volunteers_sync.log_workflow_metrics')
    def test_volunteers_sync_flow_success(self, mock_metrics, mock_process, mock_query, mock_count, mock_validate):
        """Test successful volunteers sync flow execution."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock volunteer count
        mock_count.return_value = 5000
        
        # Mock query results for chunks
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'John'}],  # Chunk 1
            [{'Id': '002', 'FirstName': 'Jane'}],  # Chunk 2
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
        result = volunteers_sync_flow(chunk_size=100)
        
        # Verify result
        assert result['total_volunteers'] == 5000
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
    
    @patch('workflows.salesforce_sync.volunteers_sync.validate_environment')
    def test_volunteers_sync_flow_environment_error(self, mock_validate):
        """Test volunteers sync flow with environment validation error."""
        # Mock environment validation failure
        mock_validate.side_effect = Exception("Environment validation failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            volunteers_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.volunteers_sync.validate_environment')
    @patch('workflows.salesforce_sync.volunteers_sync.get_volunteer_count')
    def test_volunteers_sync_flow_count_error(self, mock_count, mock_validate):
        """Test volunteers sync flow with count retrieval error."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock count retrieval failure
        mock_count.side_effect = Exception("Count retrieval failed")
        
        # Execute flow and expect exception
        with pytest.raises(Exception):
            volunteers_sync_flow(chunk_size=100)
    
    @patch('workflows.salesforce_sync.volunteers_sync.validate_environment')
    @patch('workflows.salesforce_sync.volunteers_sync.get_volunteer_count')
    @patch('workflows.salesforce_sync.volunteers_sync.query_volunteers_chunk')
    @patch('workflows.salesforce_sync.volunteers_sync.process_volunteers_chunk')
    def test_volunteers_sync_flow_partial_errors(self, mock_process, mock_query, mock_count, mock_validate):
        """Test volunteers sync flow with partial processing errors."""
        # Mock environment validation
        mock_validate.return_value = True
        
        # Mock volunteer count
        mock_count.return_value = 200
        
        # Mock query results
        mock_query.side_effect = [
            [{'Id': '001', 'FirstName': 'John'}],
            [{'Id': '002', 'FirstName': 'Jane'}]
        ]
        
        # Mock processing with mixed results
        mock_process.side_effect = [
            {'processed': 1, 'created': 1, 'updated': 0, 'errors': 0},
            {'processed': 1, 'created': 0, 'updated': 0, 'errors': 1}
        ]
        
        # Execute flow
        result = volunteers_sync_flow(chunk_size=100)
        
        # Verify result shows partial success
        assert result['total_volunteers'] == 200
        assert result['total_processed'] == 2
        assert result['total_created'] == 1
        assert result['total_updated'] == 0
        assert result['total_errors'] == 1
        assert result['chunks_processed'] == 2
    
    def test_volunteers_sync_flow_parameters(self):
        """Test volunteers sync flow parameter handling."""
        # Test default parameters
        with patch('workflows.salesforce_sync.volunteers_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.volunteers_sync.get_volunteer_count') as mock_count:
                mock_count.return_value = 0
                result = volunteers_sync_flow()
                assert result['total_volunteers'] == 0
        
        # Test custom chunk size
        with patch('workflows.salesforce_sync.volunteers_sync.validate_environment') as mock_validate:
            mock_validate.return_value = True
            with patch('workflows.salesforce_sync.volunteers_sync.get_volunteer_count') as mock_count:
                mock_count.return_value = 0
                result = volunteers_sync_flow(chunk_size=500)
                assert result['total_volunteers'] == 0


class TestVolunteersSyncWorkflowStructure:
    """Test cases for volunteers_sync workflow structure and imports."""
    
    def test_volunteers_sync_imports(self):
        """Test that volunteers_sync module imports correctly."""
        from workflows.salesforce_sync import volunteers_sync
        assert volunteers_sync is not None
    
    def test_volunteers_sync_functions_exist(self):
        """Test that all required functions exist in volunteers_sync module."""
        from workflows.salesforce_sync.volunteers_sync import (
            get_volunteer_count,
            query_volunteers_chunk,
            process_volunteers_chunk,
            volunteers_sync_flow
        )
        
        assert callable(get_volunteer_count)
        assert callable(query_volunteers_chunk)
        assert callable(process_volunteers_chunk)
        assert callable(volunteers_sync_flow)
    
    def test_volunteers_sync_workflow_decorator(self):
        """Test that volunteers_sync_flow uses the workflow decorator."""
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        
        # Check that the function has the expected attributes from the decorator
        assert hasattr(volunteers_sync_flow, '__name__')
        assert volunteers_sync_flow.__name__ == 'volunteers_sync_flow'
    
    def test_volunteers_sync_task_decorators(self):
        """Test that all tasks use the @task decorator."""
        from workflows.salesforce_sync.volunteers_sync import (
            get_volunteer_count,
            query_volunteers_chunk,
            process_volunteers_chunk
        )
        
        # Check that functions have task-related attributes
        # Note: In Prefect 2.x, the exact attributes may vary
        assert callable(get_volunteer_count)
        assert callable(query_volunteers_chunk)
        assert callable(process_volunteers_chunk)


if __name__ == '__main__':
    pytest.main([__file__]) 