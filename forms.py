from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, NumberRange, Optional

from models.contact import (
    EducationEnum,
    GenderEnum,
    LocalStatusEnum,
    RaceEthnicityEnum,
    SalutationEnum,
    SuffixEnum,
)
from models.event import CancellationReason, EventFormat, EventStatus, EventType


class LoginForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(message="Username is required.")]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(message="Password is required.")]
    )
    submit = SubmitField("Login")


class VolunteerForm(FlaskForm):
    salutation = SelectField(
        "Salutation", choices=SalutationEnum.choices(), validators=[Optional()]
    )
    first_name = StringField("First Name", validators=[DataRequired()])
    middle_name = StringField("Middle Name", validators=[Optional()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    suffix = SelectField(
        "Suffix", choices=SuffixEnum.choices(), validators=[Optional()]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    email_type = StringField("Email Type", default="personal")
    phone = StringField("Phone", validators=[Optional()])
    phone_type = StringField("Phone Type", default="personal")
    organization_name = StringField("Organization Name", validators=[Optional()])
    title = StringField("Title", validators=[Optional()])
    department = StringField("Department", validators=[Optional()])
    industry = StringField("Industry", validators=[Optional()])
    local_status = SelectField(
        "Local Status", choices=LocalStatusEnum.choices(), validators=[Optional()]
    )
    skills = TextAreaField("Skills", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    gender = SelectField(
        "Gender", choices=GenderEnum.choices(), validators=[Optional()]
    )
    race_ethnicity = SelectField(
        "Race/Ethnicity", choices=RaceEthnicityEnum.choices(), validators=[Optional()]
    )
    education = SelectField(
        "Education", choices=EducationEnum.choices(), validators=[Optional()]
    )


class EventForm(FlaskForm):
    title = StringField("Event Title", validators=[DataRequired()])
    type = SelectField(
        "Event Type",
        choices=[("", "Select Type")]
        + [(t.value, t.value.replace("_", " ").title()) for t in EventType],
        validators=[DataRequired()],
    )
    format = SelectField(
        "Format",
        choices=[("", "Select Format")]
        + [(f.value, f.value.replace("_", " ").title()) for f in EventFormat],
        validators=[DataRequired()],
    )
    start_date = DateTimeLocalField("Start Date & Time", validators=[DataRequired()])
    end_date = DateTimeLocalField("End Date & Time", validators=[DataRequired()])
    location = StringField("Location", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("", "Select Status")] + [(s.value, s.value) for s in EventStatus],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description", validators=[Optional()])
    volunteers_needed = IntegerField(
        "Volunteers Needed", validators=[Optional(), NumberRange(min=0)], default=0
    )
    # Cancellation reason fields (DEC-008)
    cancellation_reason = SelectField(
        "Cancellation Reason",
        choices=[("", "Select Reason")]
        + [(r.value, r.value) for r in CancellationReason],
        validators=[Optional()],
    )
    cancellation_notes = TextAreaField("Cancellation Notes", validators=[Optional()])
    submit = SubmitField("Save Event")
