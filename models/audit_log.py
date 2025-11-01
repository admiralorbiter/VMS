"""
Audit Log Model
===============

Lightweight audit log for admin/destructive actions. Records who did what, where,
and optional metadata. Designed to be append-only.
"""

from datetime import datetime, timezone

from sqlalchemy.sql import func

from models import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=False, index=True)
    resource_id = db.Column(db.String(64), nullable=True, index=True)
    method = db.Column(db.String(10), nullable=True)
    path = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    # 'metadata' is reserved by SQLAlchemy's Declarative API; use 'meta' instead
    meta = db.Column(db.JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id} by {self.user_id}>"
