from flask import Blueprint, flash, jsonify, redirect, request, url_for, render_template
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import User, db  # Adjust import path as needed
from forms import LoginForm  # Adjust import path as needed
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))  # Update to use main blueprint
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))  # Update to use main blueprint

@auth_bp.route('/admin')
@login_required
def admin():
    users = User.query.all()
    return render_template('management/admin.html', users=users)

@auth_bp.route('/admin/users', methods=['POST'])
@login_required
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not all([username, email, password]):
        flash('All fields are required', 'danger')
        return redirect(url_for('auth.admin'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('auth.admin'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'danger')
        return redirect(url_for('auth.admin'))
    
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
    
    return redirect(url_for('auth.admin'))

@auth_bp.route('/admin/users/<int:id>', methods=['DELETE'])
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

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
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