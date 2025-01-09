from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SelectField, SubmitField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Email, Optional
from models.contact import (
    SalutationEnum, SuffixEnum, GenderEnum, 
    RaceEthnicityEnum, EducationEnum, LocalStatusEnum
)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(message="Username is required.")])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required.")])
    submit = SubmitField('Login')

class VolunteerForm(FlaskForm):
    salutation = SelectField('Salutation', choices=SalutationEnum.choices(), validators=[Optional()])
    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    suffix = SelectField('Suffix', choices=SuffixEnum.choices(), validators=[Optional()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    email_type = StringField('Email Type', default='personal')
    phone = StringField('Phone', validators=[Optional()])
    phone_type = StringField('Phone Type', default='personal')
    organization_name = StringField('Organization Name', validators=[Optional()])
    title = StringField('Title', validators=[Optional()])
    department = StringField('Department', validators=[Optional()])
    industry = StringField('Industry', validators=[Optional()])
    local_status = SelectField('Local Status', choices=LocalStatusEnum.choices(), validators=[Optional()])
    skills = TextAreaField('Skills', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    gender = SelectField(
        'Gender',
        choices=GenderEnum.choices(),
        validators=[Optional()]
    )
    race_ethnicity = SelectField(
        'Race/Ethnicity',
        choices=RaceEthnicityEnum.choices(),
        validators=[Optional()]
    )
    education = SelectField(
        'Education',
        choices=EducationEnum.choices(),
        validators=[Optional()]
    )