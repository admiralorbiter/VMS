from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FieldList, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from models.volunteer import LocalStatusEnum

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(message="Username is required.")])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required.")])
    submit = SubmitField('Login')

class VolunteerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name')
    last_name = StringField('Last Name', validators=[DataRequired()])
    organization_name = StringField('Organization')
    title = StringField('Title')
    department = StringField('Department')
    industry = StringField('Industry')
    local_status = SelectField('Local Status', 
                             choices=[('true', 'True'), 
                                    ('partial', 'Partial'), 
                                    ('false', 'False'), 
                                    ('unknown', 'Unknown')],
                             validators=[DataRequired()])
    emails = FieldList(StringField('Email', validators=[Email()]), min_entries=1)
    skills = FieldList(StringField('Skill'), min_entries=1)