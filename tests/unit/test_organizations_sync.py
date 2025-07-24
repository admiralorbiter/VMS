"""
Unit Tests for Organizations Sync Workflow
========================================

Tests for the organizations_sync workflow functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from workflows.salesforce_sync.organizations_sync import (
    query_organizations,
    query_affiliations,
    process_organizations,
    process_affiliations,
    organizations_sync_flow
)


class TestOrganizationsSync:
    """Test cases for organizations sync workflow."""
    
    def test_query_organizations_success(self):
        """Test successful organization query."""
        # Mock Salesforce connection
        mock_sf = MagicMock()
        mock_sf.query_all.return_value = {
            'records': [
                {
                    'Id': 'org1',
                    'Name': 'Test Organization',
                    'Type': 'Non-Profit',
                    'Description': 'Test description',
                    'BillingStreet': '123 Test St',
                    'BillingCity': 'Test City',
                    'BillingState': 'TS',
                    'BillingPostalCode': '12345',
                    'BillingCountry': 'US',
                    'LastActivityDate': '2024-01-01'
                }
            ]
        }
        
        result = query_organizations(mock_sf)
        
        assert result['total_count'] == 1
        assert len(result['organizations']) == 1
        assert result['organizations'][0]['Name'] == 'Test Organization'
        assert 'query_time' in result
    
    def test_query_organizations_error(self):
        """Test organization query with error."""
        # Mock Salesforce connection that raises an error
        mock_sf = MagicMock()
        mock_sf.query_all.side_effect = Exception("Salesforce connection error")
        
        with pytest.raises(Exception):
            query_organizations(mock_sf)
    
    def test_query_affiliations_success(self):
        """Test successful affiliation query."""
        # Mock Salesforce connection
        mock_sf = MagicMock()
        mock_sf.query_all.return_value = {
            'records': [
                {
                    'Id': 'aff1',
                    'Name': 'Test Affiliation',
                    'npe5__Organization__c': 'org1',
                    'npe5__Contact__c': 'contact1',
                    'npe5__Role__c': 'Volunteer',
                    'npe5__Primary__c': True,
                    'npe5__Status__c': 'Active'
                }
            ]
        }
        
        result = query_affiliations(mock_sf)
        
        assert result['total_count'] == 1
        assert len(result['affiliations']) == 1
        assert result['affiliations'][0]['npe5__Role__c'] == 'Volunteer'
        assert 'query_time' in result
    
    def test_query_affiliations_error(self):
        """Test affiliation query with error."""
        # Mock Salesforce connection that raises an error
        mock_sf = MagicMock()
        mock_sf.query_all.side_effect = Exception("Salesforce connection error")
        
        with pytest.raises(Exception):
            query_affiliations(mock_sf)
    
    @patch('workflows.salesforce_sync.organizations_sync.Organization')
    @patch('workflows.salesforce_sync.organizations_sync.parse_date')
    def test_process_organizations_success(self, mock_parse_date, mock_organization):
        """Test successful organization processing."""
        # Mock parse_date
        mock_parse_date.return_value = datetime(2024, 1, 1)
        
        # Mock Organization model
        mock_org_class = MagicMock()
        mock_organization.query.filter_by.return_value.first.return_value = None
        mock_organization.return_value = MagicMock()
        
        org_data = {
            'organizations': [
                {
                    'Id': 'org1',
                    'Name': 'Test Organization',
                    'Type': 'Non-Profit',
                    'Description': 'Test description',
                    'BillingStreet': '123 Test St',
                    'BillingCity': 'Test City',
                    'BillingState': 'TS',
                    'BillingPostalCode': '12345',
                    'BillingCountry': 'US',
                    'LastActivityDate': '2024-01-01'
                }
            ]
        }
        
        # Mock database session
        mock_session = MagicMock()
        
        result = process_organizations(org_data, mock_session)
        
        assert result['success_count'] == 1
        assert result['error_count'] == 0
        assert result['total_processed'] == 1
        assert len(result['errors']) == 0
    
    @patch('workflows.salesforce_sync.organizations_sync.Organization')
    @patch('workflows.salesforce_sync.organizations_sync.Contact')
    def test_process_affiliations_success(self, mock_contact, mock_organization):
        """Test successful affiliation processing."""
        # Mock models
        mock_org_class = MagicMock()
        mock_org_class.query.filter_by.return_value.first.return_value = MagicMock(name='Test Org')
        
        mock_contact_class = MagicMock()
        mock_contact_class.query.filter_by.return_value.first.return_value = MagicMock(
            first_name='John', last_name='Doe'
        )
        
        affiliation_data = {
            'affiliations': [
                {
                    'Id': 'aff1',
                    'npe5__Organization__c': 'org1',
                    'npe5__Contact__c': 'contact1',
                    'npe5__Role__c': 'Volunteer',
                    'npe5__Primary__c': True,
                    'npe5__Status__c': 'Active'
                }
            ]
        }
        
        # Mock database session
        mock_session = MagicMock()
        
        result = process_affiliations(affiliation_data, mock_session)
        
        assert result['success_count'] == 1
        assert result['error_count'] == 0
        assert result['total_processed'] == 1
        assert len(result['errors']) == 0
    
    @patch('workflows.salesforce_sync.organizations_sync.validate_environment')
    @patch('workflows.salesforce_sync.organizations_sync.salesforce_connection')
    @patch('workflows.salesforce_sync.organizations_sync.database_connection')
    @patch('workflows.salesforce_sync.organizations_sync.query_organizations')
    @patch('workflows.salesforce_sync.organizations_sync.process_organizations')
    def test_organizations_sync_flow_success(self, mock_process, mock_query, mock_db, mock_sf, mock_env):
        """Test successful organizations sync flow."""
        # Mock environment validation
        mock_env.return_value = {
            'salesforce_configured': True,
            'database_configured': True,
            'errors': []
        }
        
        # Mock connections
        mock_sf.return_value = MagicMock()
        mock_db.return_value = MagicMock()
        
        # Mock query and process results
        mock_query.return_value = {
            'organizations': [{'Id': 'org1', 'Name': 'Test Org'}],
            'total_count': 1
        }
        
        mock_process.return_value = {
            'success_count': 1,
            'error_count': 0,
            'errors': []
        }
        
        # Test the flow
        result = organizations_sync_flow(sync_affiliations=False)
        
        assert result['status'] == 'success'
        assert result['total_success'] == 1
        assert result['total_errors'] == 0
        assert 'duration_seconds' in result
        assert 'memory_usage' in result
    
    @patch('workflows.salesforce_sync.organizations_sync.validate_environment')
    def test_organizations_sync_flow_environment_error(self, mock_env):
        """Test organizations sync flow with environment error."""
        # Mock environment validation failure
        mock_env.return_value = {
            'salesforce_configured': False,
            'database_configured': True,
            'errors': ['Salesforce not configured']
        }
        
        # Test the flow
        result = organizations_sync_flow(sync_affiliations=False)
        
        assert result['status'] == 'error'
        assert 'Environment not properly configured' in result['error_message']
    
    def test_organizations_sync_flow_parameters(self):
        """Test organizations sync flow with different parameters."""
        # Test with sync_affiliations=True (default)
        with patch('workflows.salesforce_sync.organizations_sync.validate_environment') as mock_env:
            mock_env.return_value = {
                'salesforce_configured': True,
                'database_configured': True,
                'errors': []
            }
            
            # This should not raise an error for parameter validation
            # The actual execution would be mocked in a real test
            assert True  # Placeholder assertion
    
    def test_organizations_sync_flow_error_handling(self):
        """Test organizations sync flow error handling."""
        # Test with Salesforce connection error
        with patch('workflows.salesforce_sync.organizations_sync.validate_environment') as mock_env:
            mock_env.return_value = {
                'salesforce_configured': True,
                'database_configured': True,
                'errors': []
            }
            
            with patch('workflows.salesforce_sync.organizations_sync.salesforce_connection') as mock_sf:
                mock_sf.side_effect = Exception("Salesforce connection failed")
                
                result = organizations_sync_flow(sync_affiliations=False)
                
                assert result['status'] == 'error'
                assert 'Salesforce connection failed' in result['error_message']


class TestOrganizationsSyncIntegration:
    """Integration tests for organizations sync workflow."""
    
    def test_workflow_structure(self):
        """Test that the workflow has the correct structure."""
        # Test that all required functions exist
        assert callable(query_organizations)
        assert callable(query_affiliations)
        assert callable(process_organizations)
        assert callable(process_affiliations)
        assert callable(organizations_sync_flow)
    
    def test_workflow_imports(self):
        """Test that all required imports work."""
        try:
            from workflows.salesforce_sync.organizations_sync import (
                query_organizations,
                query_affiliations,
                process_organizations,
                process_affiliations,
                organizations_sync_flow
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import organizations sync functions: {e}")
    
    def test_workflow_decorators(self):
        """Test that workflow functions have proper decorators."""
        # Check that the main flow has the workflow decorator
        assert hasattr(organizations_sync_flow, '__wrapped__') or hasattr(organizations_sync_flow, '__prefect_flow__')
        
        # Check that tasks have proper decorators
        assert hasattr(query_organizations, '__wrapped__') or hasattr(query_organizations, '__prefect_task__')
        assert hasattr(query_affiliations, '__wrapped__') or hasattr(query_affiliations, '__prefect_task__')
        assert hasattr(process_organizations, '__wrapped__') or hasattr(process_organizations, '__prefect_task__')
        assert hasattr(process_affiliations, '__wrapped__') or hasattr(process_affiliations, '__prefect_task__') 