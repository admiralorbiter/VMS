"""
Authentication Routes Module
==========================

This module provides all authentication and user management functionality
for the Volunteer Management System (VMS). It handles user login, logout,
admin functions, and user management operations.

Key Features:
- User authentication (login/logout)
- Admin panel functionality
- User creation and management
- Password change operations
- Security level management
- User deletion with safety checks

Main Endpoints:
- /login: User login form and authentication
- /logout: User logout and session cleanup
- /admin: Admin panel for user management
- /admin/users: Create new users (POST)
- /admin/users/<id>: Delete users (DELETE)
- /change_password: Change user password (POST)

Security Features:
- Password hashing with Werkzeug
- Session management with Flask-Login
- Security level validation
- Self-deletion prevention
- Admin permission checks

Dependencies:
- Flask-Login for session management
- Werkzeug for password hashing
- User model for database operations
- LoginForm for form validation

Models Used:
- User: User account and authentication data
- Database session for persistence

Template Dependencies:
- login.html: Login form template
- management/admin.html: Admin panel template
"""

from flask import Blueprint, flash, jsonify, redirect, request, url_for, render_template
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import User, db  # Adjust import path as needed
from forms import LoginForm  # Adjust import path as needed
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login functionality.
    
    Provides both GET (login form) and POST (authentication) methods.
    Validates user credentials and creates user session on successful login.
    
    GET:
        Returns login form template
        
    POST:
        Validates form data and authenticates user
        - Checks username/email and password
        - Creates user session on success
        - Shows error message on failure
        
    Returns:
        Rendered login template or redirect to index on success
    """
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_username_or_email(form.username.data)
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))  # Update to use main blueprint
        else:
            flash('Invalid username/email or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout functionality.
    
    Clears the current user session and redirects to the index page.
    Requires user to be logged in.
    
    Returns:
        Redirect to index page with logout message
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))  # Update to use main blueprint

@auth_bp.route('/admin')
@login_required
def admin():
    """
    Admin panel for user management.
    
    Displays all users in the system for administrative management.
    Requires user to be logged in.
    
    Returns:
        Rendered admin template with user list
    """
    users = User.query.all()
    return render_template('management/admin.html', users=users)

@auth_bp.route('/admin/users', methods=['POST'])
@login_required
def create_user():
    """
    Create a new user account.
    
    Handles user creation with validation and security checks.
    Only admin users can create new accounts.
    
    Form Parameters:
        username: Unique username for the new user
        email: Unique email address for the new user
        password: Password for the new user
        security_level: Security level (0-3) for the new user
        
    Security Checks:
        - Admin permission required
        - All fields must be provided
        - Username and email must be unique
        - Security level validation
        - Non-admin users can only create lower security levels
        
    Returns:
        Redirect to admin panel with success/error message
    """
    if not current_user.is_admin:
        flash('Permission denied', 'danger')
        return redirect(url_for('auth.admin'))

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    security_level = request.form.get('security_level', type=int)
    
    if not all([username, email, password, security_level is not None]):
        flash('All fields are required', 'danger')
        return redirect(url_for('auth.admin'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('auth.admin'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'danger')
        return redirect(url_for('auth.admin'))
    
    # For admin users (security_level 3), allow creating any valid security level
    # For non-admin users, ensure they can only create users with lower security levels
    if not (0 <= security_level <= 3) or (not current_user.is_admin and security_level >= current_user.security_level):
        flash('Invalid security level or insufficient permissions', 'danger')
        return redirect(url_for('auth.admin'))
    
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        security_level=security_level
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        flash('User created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
    
    return redirect(url_for('auth.admin'))

@auth_bp.route('/admin/users/<int:id>', methods=['DELETE'])
@login_required
def delete_user(id):
    """
    Delete a user account.
    
    Handles user deletion with safety checks and error handling.
    Prevents users from deleting themselves.
    
    Args:
        id: Database ID of the user to delete
        
    Safety Checks:
        - Cannot delete own account
        - User must exist in database
        
    Returns:
        JSON response with success/error status
    """
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

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """
    Change the current user's password.
    
    Validates password change request and updates user's password hash.
    Requires user to be logged in.
    
    Form Parameters:
        new_password: New password for the user
        confirm_password: Password confirmation
        
    Validation:
        - Both password fields must be provided
        - Passwords must match
        - Current user must be logged in
        
    Returns:
        Redirect to admin panel with success/error message
    """
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify all fields are provided
    if not all([new_password, confirm_password]):
        flash('Both password fields are required', 'danger')
        return redirect(url_for('auth.admin'))
    
    # Verify new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('auth.admin'))
    
    try:
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Password updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating password: {str(e)}', 'danger')
    
    return redirect(url_for('auth.admin'))