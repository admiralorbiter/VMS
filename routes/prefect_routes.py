"""
Prefect Integration Routes Module
================================

This module provides Flask routes for triggering and monitoring Prefect workflows
from the VMS admin interface.

Key Features:
- Trigger individual sync workflows
- Trigger full Salesforce sync
- Monitor workflow status and progress
- View workflow results and statistics
- Error handling and reporting

Routes:
- /prefect/trigger-sync: Trigger full Salesforce sync
- /prefect/trigger-organizations: Trigger organizations sync
- /prefect/trigger-volunteers: Trigger volunteers sync
- /prefect/trigger-students: Trigger students sync
- /prefect/trigger-teachers: Trigger teachers sync
- /prefect/trigger-events: Trigger events sync
- /prefect/trigger-pathways: Trigger pathways sync
- /prefect/trigger-history: Trigger history sync
- /prefect/trigger-schools-districts: Trigger schools and districts sync
- /prefect/trigger-classes: Trigger classes sync
- /prefect/status/<flow_run_id>: Get workflow status
- /prefect/results/<flow_run_id>: Get workflow results

Dependencies:
- Prefect client for workflow management
- Flask-Login for authentication
- VMS models for database operations
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from prefect.client.orchestration import get_client
from datetime import datetime, timezone
import traceback

from workflows.salesforce_sync import (
    full_salesforce_sync_flow,
    organizations_sync_flow,
    volunteers_sync_flow,
    students_sync_flow,
    teachers_sync_flow,
    events_sync_flow,
    pathways_sync_flow,
    history_sync_flow,
    schools_districts_sync_flow,
    classes_sync_flow
)

# Create Flask Blueprint for Prefect routes
prefect_bp = Blueprint('prefect', __name__, url_prefix='/prefect')


@prefect_bp.route('/trigger-sync', methods=['POST'])
@login_required
def trigger_full_sync():
    """
    Trigger full Salesforce sync workflow.
    
    This endpoint starts the comprehensive sync workflow that runs all
    individual sync operations in the correct dependency order.
    
    Returns:
        JSON response with workflow ID and status
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Start the full sync workflow
        flow_run = full_salesforce_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Full Salesforce sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start full sync workflow'
        }), 500


@prefect_bp.route('/trigger-organizations', methods=['POST'])
@login_required
def trigger_organizations_sync():
    """Trigger organizations sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = organizations_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Organizations sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start organizations sync workflow'
        }), 500


@prefect_bp.route('/trigger-volunteers', methods=['POST'])
@login_required
def trigger_volunteers_sync():
    """Trigger volunteers sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = volunteers_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Volunteers sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start volunteers sync workflow'
        }), 500


@prefect_bp.route('/trigger-students', methods=['POST'])
@login_required
def trigger_students_sync():
    """Trigger students sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = students_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Students sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start students sync workflow'
        }), 500


@prefect_bp.route('/trigger-teachers', methods=['POST'])
@login_required
def trigger_teachers_sync():
    """Trigger teachers sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = teachers_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Teachers sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start teachers sync workflow'
        }), 500


@prefect_bp.route('/trigger-events', methods=['POST'])
@login_required
def trigger_events_sync():
    """Trigger events sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = events_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Events sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start events sync workflow'
        }), 500


@prefect_bp.route('/trigger-pathways', methods=['POST'])
@login_required
def trigger_pathways_sync():
    """Trigger pathways sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = pathways_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Pathways sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start pathways sync workflow'
        }), 500


@prefect_bp.route('/trigger-history', methods=['POST'])
@login_required
def trigger_history_sync():
    """Trigger history sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = history_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'History sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start history sync workflow'
        }), 500


@prefect_bp.route('/trigger-schools-districts', methods=['POST'])
@login_required
def trigger_schools_districts_sync():
    """Trigger schools and districts sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = schools_districts_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Schools and districts sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start schools and districts sync workflow'
        }), 500


@prefect_bp.route('/trigger-classes', methods=['POST'])
@login_required
def trigger_classes_sync():
    """Trigger classes sync workflow."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        flow_run = classes_sync_flow()
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'message': 'Classes sync completed successfully',
            'result': flow_run
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start classes sync workflow'
        }), 500


@prefect_bp.route('/status/<flow_run_id>')
@login_required
def get_flow_status(flow_run_id):
    """
    Get status of a Prefect flow run.
    
    Args:
        flow_run_id: The ID of the flow run to check
        
    Returns:
        JSON response with flow run status and metadata
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        client = get_client()
        flow_run = client.read_flow_run(flow_run_id)
        
        return jsonify({
            'flow_run_id': flow_run_id,
            'status': flow_run.state.name,
            'start_time': flow_run.start_time.isoformat() if flow_run.start_time else None,
            'end_time': flow_run.end_time.isoformat() if flow_run.end_time else None,
            'duration': (flow_run.end_time - flow_run.start_time).total_seconds() if flow_run.start_time and flow_run.end_time else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get flow run status'
        }), 500


@prefect_bp.route('/results/<flow_run_id>')
@login_required
def get_flow_results(flow_run_id):
    """
    Get results of a completed Prefect flow run.
    
    Args:
        flow_run_id: The ID of the flow run to get results for
        
    Returns:
        JSON response with flow run results and statistics
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        client = get_client()
        flow_run = client.read_flow_run(flow_run_id)
        
        # Get the result if the flow completed
        result = None
        if flow_run.state.is_completed():
            try:
                result = flow_run.state.result()
            except Exception:
                result = None
        
        return jsonify({
            'flow_run_id': flow_run_id,
            'status': flow_run.state.name,
            'start_time': flow_run.start_time.isoformat() if flow_run.start_time else None,
            'end_time': flow_run.end_time.isoformat() if flow_run.end_time else None,
            'duration': (flow_run.end_time - flow_run.start_time).total_seconds() if flow_run.start_time and flow_run.end_time else None,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get flow run results'
        }), 500


@prefect_bp.route('/dashboard')
@login_required
def prefect_dashboard():
    """
    Prefect monitoring dashboard.
    
    This endpoint provides a view for monitoring Prefect workflows
    and their status.
    
    Returns:
        Rendered dashboard template
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        client = get_client()
        
        # Get recent flow runs
        recent_runs = client.read_flow_runs(
            limit=20,
            sort="-start_time"
        )
        
        return render_template(
            'prefect/dashboard.html',
            recent_runs=recent_runs,
            current_user=current_user
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to load dashboard'
        }), 500 