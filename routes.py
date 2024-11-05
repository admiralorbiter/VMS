from flask import flash, redirect, render_template, url_for, request, jsonify
from flask_login import login_required, login_user, logout_user
from forms import LoginForm, VolunteerForm
from models.user import User, db
from werkzeug.security import check_password_hash, generate_password_hash
from models.volunteer import Email, Phone, Skill, Volunteer, LocalStatusEnum
from sqlalchemy import or_

def init_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')
        return render_template('login.html', form=form)
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))
    
    @app.route('/volunteers')
    @login_required
    def volunteers():
        # Get search parameters
        search_name = request.args.get('search_name', '').strip()
        org_search = request.args.get('org_search', '').strip()
        email_search = request.args.get('email_search', '').strip()
        skill_search = request.args.get('skill_search', '').strip()
        local_status = request.args.get('local_status', '')
        sort_by = request.args.get('sort_by', 'last_volunteer_date')
        sort_direction = request.args.get('sort_direction', 'desc')

        # Build query
        query = Volunteer.query

        if search_name:
            search_term = f"%{search_name}%"
            query = query.filter(or_(
                Volunteer.first_name.ilike(search_term),
                Volunteer.last_name.ilike(search_term),
                Volunteer.middle_name.ilike(search_term)
            ))

        if org_search:
            search_term = f"%{org_search}%"
            query = query.filter(or_(
                Volunteer.organization_name.ilike(search_term),
                Volunteer.title.ilike(search_term),
                Volunteer.department.ilike(search_term)
            ))

        if email_search:
            search_term = f"%{email_search}%"
            query = query.join(Email).filter(Email.email.ilike(search_term))

        if skill_search:
            search_term = f"%{skill_search}%"
            query = query.join(Volunteer.skills).filter(Skill.name.ilike(search_term))

        if local_status:
            query = query.filter(Volunteer.local_status == local_status)

        # Apply sorting
        sort_column = getattr(Volunteer, sort_by)
        if sort_direction == 'desc':
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)

        volunteers = query.all()

        return render_template('volunteers/volunteers.html',
                             volunteers=volunteers,
                             current_filters=request.args)
    
    @app.route('/volunteers/add', methods=['GET', 'POST'])
    @login_required
    def add_volunteer():
        form = VolunteerForm()
        if form.validate_on_submit():
            volunteer = Volunteer(
                salutation=form.salutation.data,
                first_name=form.first_name.data,
                middle_name=form.middle_name.data,
                last_name=form.last_name.data,
                suffix=form.suffix.data,
                organization_name=form.organization_name.data,
                title=form.title.data,
                department=form.department.data,
                industry=form.industry.data,
                local_status=form.local_status.data,
                notes=form.notes.data
            )

            # Add email with type
            email = Email(
                email=form.email.data,
                type=form.email_type.data
            )
            volunteer.emails.append(email)

            # Add phone if provided
            if form.phone.data:
                phone = Phone(
                    number=form.phone.data,
                    type=form.phone_type.data
                )
                volunteer.phones.append(phone)

            # Add skills
            if form.skills.data:
                for skill_name in form.skills.data:
                    if skill_name:
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                        volunteer.skills.append(skill)

            db.session.add(volunteer)
            db.session.commit()
            flash('Volunteer added successfully!', 'success')
            return redirect(url_for('volunteers'))

        return render_template('/volunteers/add_volunteer.html', form=form)