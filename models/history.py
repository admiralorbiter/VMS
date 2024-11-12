from models import db
from datetime import datetime

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete="CASCADE"))
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id', ondelete="CASCADE"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"))
    action = db.Column(db.String(255))
    summary = db.Column(db.Text)  # Mapped from "Subject"
    description = db.Column(db.Text)
    activity_type = db.Column(db.String(100), index=True)
    activity_date = db.Column(db.DateTime)
    activity_status = db.Column(db.String(50), index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    last_modified_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = db.Column(db.Boolean, default=False)
    email_message_id = db.Column(db.String(255), nullable=True)
