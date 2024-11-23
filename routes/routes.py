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
from routes.upcoming_events.routes import upcoming_events_bp
from routes.job_board.filters import init_filters
from routes.utils import parse_date


def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(job_board_bp)
    app.register_blueprint(upcoming_events_bp)
    init_filters(app)

    @app.route('/')
    def index():
        return render_template('index.html')