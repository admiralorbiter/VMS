"""
Pending Participation Import Model
==================================

Tracks orphaned Salesforce participation records that failed to import
because the associated Volunteer or Event did not exist locally.
These are held in a retry queue and automatically processed on subsequent imports.
"""

from datetime import datetime, timezone

from models import db


class PendingParticipationImport(db.Model):
    __tablename__ = "pending_participation_imports"

    id = db.Column(db.Integer, primary_key=True)
    sf_participation_id = db.Column(
        db.String(18), unique=True, nullable=False, index=True
    )
    sf_contact_id = db.Column(db.String(18), index=True)
    sf_session_id = db.Column(db.String(18), index=True)
    status = db.Column(db.String(50))
    delivery_hours = db.Column(db.Float)
    age_group = db.Column(db.String(50))
    email = db.Column(db.String(255))
    title = db.Column(db.String(100))

    # Retry lifecycle tracking
    first_seen_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    retry_count = db.Column(db.Integer, default=0)
    last_retry_at = db.Column(db.DateTime(timezone=True))
    resolved_at = db.Column(db.DateTime(timezone=True))  # NULL = still pending
    error_reason = db.Column(db.String(200))

    def __repr__(self):
        return f"<PendingParticipationImport {self.sf_participation_id} (Contact: {self.sf_contact_id})>"
