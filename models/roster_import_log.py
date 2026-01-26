from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from models import db


class RosterImportLog(db.Model):
    """
    Model for logging roster import results (audit trail).
    """

    __tablename__ = "roster_import_log"

    id = Column(Integer, primary_key=True)
    district_name = Column(String(200), nullable=False)
    academic_year = Column(String(10), nullable=False)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    imported_by = Column(Integer, ForeignKey("users.id"))
    source_sheet_id = Column(String(100))
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_deactivated = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # 'success', 'failed', 'partial'
    error_message = Column(Text)

    def __repr__(self):
        return f"<RosterImportLog {self.district_name} - {self.academic_year} ({self.status})>"
