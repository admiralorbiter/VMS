from flask_wtf import FlaskForm
from wtforms import (
    StringField, 
    SelectField, 
    FieldList, 
    PasswordField, 
    SubmitField, 
    TextAreaField,
    TelField,
    RadioField
)
from wtforms.validators import DataRequired, Email, Optional, Length
from models.volunteer import LocalStatusEnum, SalutationEnum, SuffixEnum

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(message="Username is required.")])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required.")])
    submit = SubmitField('Login')

class VolunteerForm(FlaskForm):
    # Personal Information
    salutation = SelectField(
        'Salutation',
        choices=[(s.name, s.value) for s in SalutationEnum],
        validators=[Optional()]
    )
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(max=50)
    ])
    middle_name = StringField('Middle Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(max=50)
    ])
    suffix = SelectField(
        'Suffix',
        choices=[(s.name, s.value) for s in SuffixEnum],
        validators=[Optional()]
    )

    # Contact Information
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address"),
        Length(max=100)
    ])
    phone = TelField('Phone Number', validators=[Optional(), Length(max=20)])
    phone_type = RadioField('Phone Type', 
                          choices=[('personal', 'Personal'), ('work', 'Work')],
                          default='personal')

    # Professional Information
    organization_name = StringField('Organization', validators=[Optional(), Length(max=100)])
    title = StringField('Title', validators=[Optional(), Length(max=100)])
    department = StringField('Department', validators=[Optional(), Length(max=100)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    
    # Additional Information
    local_status = SelectField(
        'Local Status',
        choices=[(status.name, status.value) for status in LocalStatusEnum],
        validators=[DataRequired(message="Please select a local status")]
    )
    skills = FieldList(
        StringField('Skill', validators=[Optional(), Length(max=50)]),
        min_entries=1
    )
    notes = TextAreaField('Initial Notes', validators=[Optional(), Length(max=1000)])
    email_type = RadioField('Email Type', 
                          choices=[('personal', 'Personal'), ('work', 'Work')],
                          default='personal')