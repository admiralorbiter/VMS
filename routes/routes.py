from flask import flash, redirect, render_template, url_for, request, jsonify, send_file
from flask_login import current_user, login_required, login_user, logout_user
from config import Config
from forms import LoginForm, VolunteerForm
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.upcoming_events import UpcomingEvent
from models.user import User, db
from models.event import CancellationReason, District, Event, EventType, EventFormat, EventStatus
from werkzeug.security import check_password_hash, generate_password_hash
from models.volunteer import Address, ContactTypeEnum, Email, Engagement, EventParticipation, GenderEnum, LocalStatusEnum, Phone, Skill, SkillSourceEnum, Volunteer , VolunteerSkill
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import io
import csv
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import or_
from models.tech_job_board import JobOpportunity, EntryLevelJob, WorkLocationType
from io import StringIO
import zipfile
from io import BytesIO
from routes.auth.routes import auth_bp
from routes.history.routes import history_bp
from routes.volunteers.routes import volunteers_bp
from routes.organizations.routes import organizations_bp
from routes.events.routes import events_bp, process_event_row, process_participation_row
from routes.job_board.routes import job_board_bp
from routes.job_board.filters import init_filters
from routes.utils import parse_date


def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(job_board_bp)
    init_filters(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    
    @app.route('/sync_upcoming_events', methods=['POST'])
    def sync_upcoming_events():
        try:
            today = datetime.now().date()
            
            # 1. Remove past events AND filled/overfilled events
            deleted_count = UpcomingEvent.query.filter(
                or_(
                    UpcomingEvent.start_date <= today,
                    UpcomingEvent.filled_volunteer_jobs >= UpcomingEvent.available_slots  # Compare filled vs needed
                )
            ).delete()
            db.session.commit()

            # 2. Connect to Salesforce and query
            sf = Salesforce(
                username=Config.SF_USERNAME,
                password=Config.SF_PASSWORD,
                security_token=Config.SF_SECURITY_TOKEN,
                domain='login'
            )

            query = """
                SELECT Id, Name, Available_slots__c, Filled_Volunteer_Jobs__c, 
                Date_and_Time_for_Cal__c, Session_Type__c, Registration_Link__c, 
                Display_on_Website__c, Start_Date__c 
                FROM Session__c 
                WHERE Start_Date__c > TODAY 
                AND Available_slots__c > Filled_Volunteer_Jobs__c  # Modified to compare slots
                ORDER BY Start_Date__c ASC
            """
            result = sf.query(query)
            events = result.get('records', [])

            # 3. Update database with new events
            new_count, updated_count = UpcomingEvent.upsert_from_salesforce(events)
            
            return jsonify({
                'success': True,
                'new_count': new_count,
                'updated_count': updated_count,
                'deleted_count': deleted_count,
                'message': f'Successfully synced: {new_count} new, {updated_count} updated, {deleted_count} removed (past or filled)'
            })

        except SalesforceAuthenticationFailed as e:
            return jsonify({
                'success': False,
                'message': 'Failed to authenticate with Salesforce'
            }), 401

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An unexpected error occurred: {str(e)}'
            }), 500
    
    @app.route('/volunteer_signup')
    def volunteer_signup():
        # Get initial events from database where display_on_website is True, ordered by date
        events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]
        return render_template('events/signup.html', initial_events=events)
    
    @app.route('/volunteer_signup_api')
    def volunteer_signup_api():
        # Get initial events from database where display_on_website is True, ordered by date
        events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]
    
        # Return JSON response directly
        return jsonify(events)
    
    @app.route('/toggle-event-visibility', methods=['POST'])
    @login_required
    def toggle_event_visibility():
        try:
            data = request.get_json()
            event_id = data.get('event_id')
            visible = data.get('visible')
            
            print(f"Toggling event {event_id} to visibility: {visible}")  # Debug log
            
            event = UpcomingEvent.query.filter_by(salesforce_id=event_id).first()
            if not event:
                print(f"Event not found with ID: {event_id}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Event not found'
                }), 404
            
            # Print before state
            print(f"Before update - Event {event_id} visibility: {event.display_on_website}")
            
            event.display_on_website = visible
            db.session.commit()
            
            # Verify the update
            db.session.refresh(event)
            print(f"After update - Event {event_id} visibility: {event.display_on_website}")
            
            return jsonify({
                'success': True,
                'message': f'Event visibility {"enabled" if visible else "disabled"}',
                'current_state': event.display_on_website
            })
            
        except Exception as e:
            print(f"Error in toggle_event_visibility: {str(e)}")  # Debug log
            db.session.rollback()  # Roll back on error
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500

    @app.route('/upcoming_event_management')
    @login_required
    def upcoming_event_management():
        # Get initial events from database and convert to dict
        events = [event.to_dict() for event in UpcomingEvent.query.all()]
        return render_template('events/upcoming_event_management.html', initial_events=events)
    

    @app.template_filter('format_date')
    def format_date(date):
        if date:
            return date.strftime('%B %d, %Y')
        return ''
    
    @app.route('/admin')
    @login_required
    def admin():
        users = User.query.all()
        return render_template('management/admin.html', users=users)

    @app.route('/admin/users', methods=['POST'])
    @login_required
    def create_user():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
        
        return redirect(url_for('admin'))

    @app.route('/admin/users/<int:id>', methods=['DELETE'])
    @login_required
    def delete_user(id):
        print(f"Delete request received for user {id}")  # Add this line
        if current_user.id == id:
            return jsonify({'error': 'Cannot delete yourself'}), 400
        
        user = User.query.get_or_404(id)
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error deleting user: {str(e)}")  # Add this line
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/change_password', methods=['POST'])
    @login_required
    def change_password():
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verify all fields are provided
        if not all([new_password, confirm_password]):
            flash('Both password fields are required', 'danger')
            return redirect(url_for('admin'))
        
        # Verify new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('admin'))
        
        try:
            # Update password
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Password updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating password: {str(e)}', 'danger')
        
        return redirect(url_for('admin'))