"""
Cache management functions for virtual session reports.

Provides CRUD operations for VirtualSessionReportCache and
VirtualSessionDistrictCache models.
"""

from datetime import datetime, timezone

from models import db
from models.reports import VirtualSessionDistrictCache, VirtualSessionReportCache
from routes.reports.common import is_cache_valid


def get_virtual_session_cache(virtual_year, date_from=None, date_to=None):
    """
    Get cached virtual session report data.

    Args:
        virtual_year: The virtual year to get cache for
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        VirtualSessionReportCache or None if not found/expired
    """
    cache_query = VirtualSessionReportCache.query.filter_by(
        virtual_year=virtual_year,
        date_from=date_from.date() if date_from else None,
        date_to=date_to.date() if date_to else None,
    )

    cache_record = cache_query.first()

    if is_cache_valid(cache_record):
        return cache_record

    return None


def save_virtual_session_cache(
    virtual_year,
    date_from,
    date_to,
    session_data,
    district_summaries,
    overall_summary,
    filter_options,
):
    """
    Save virtual session report data to cache.

    Args:
        virtual_year: The virtual year
        date_from: Start date filter
        date_to: End date filter
        session_data: Session data to cache
        district_summaries: District summary data
        overall_summary: Overall summary data
        filter_options: Filter options data
    """
    try:
        # Check if cache record exists
        cache_record = VirtualSessionReportCache.query.filter_by(
            virtual_year=virtual_year,
            date_from=date_from.date() if date_from else None,
            date_to=date_to.date() if date_to else None,
        ).first()

        if cache_record:
            # Update existing record
            cache_record.session_data = session_data
            cache_record.district_summaries = district_summaries
            cache_record.overall_summary = overall_summary
            cache_record.filter_options = filter_options
            cache_record.last_updated = datetime.now(timezone.utc)
        else:
            # Create new record
            cache_record = VirtualSessionReportCache(
                virtual_year=virtual_year,
                date_from=date_from.date() if date_from else None,
                date_to=date_to.date() if date_to else None,
                session_data=session_data,
                district_summaries=district_summaries,
                overall_summary=overall_summary,
                filter_options=filter_options,
            )
            db.session.add(cache_record)

        db.session.commit()
        print(f"Virtual session cache saved for {virtual_year}")

    except Exception as e:
        db.session.rollback()
        print(f"Error saving virtual session cache: {str(e)}")


def get_virtual_session_district_cache(
    district_name, virtual_year, date_from=None, date_to=None
):
    """
    Get cached district virtual session report data.

    Args:
        district_name: The district name
        virtual_year: The virtual year to get cache for
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        VirtualSessionDistrictCache or None if not found/expired
    """
    cache_query = VirtualSessionDistrictCache.query.filter_by(
        district_name=district_name,
        virtual_year=virtual_year,
        date_from=date_from.date() if date_from else None,
        date_to=date_to.date() if date_to else None,
    )

    cache_record = cache_query.first()

    if is_cache_valid(cache_record):
        return cache_record

    return None


def save_virtual_session_district_cache(
    district_name,
    virtual_year,
    date_from,
    date_to,
    session_data,
    monthly_stats,
    school_breakdown,
    teacher_breakdown,
    summary_stats,
):
    """
    Save district virtual session report data to cache.

    Args:
        district_name: The district name
        virtual_year: The virtual year
        date_from: Start date filter
        date_to: End date filter
        session_data: Session data to cache
        monthly_stats: Monthly statistics
        school_breakdown: School breakdown data
        teacher_breakdown: Teacher breakdown data
        summary_stats: Summary statistics
    """
    try:
        # Check if cache record exists
        cache_record = VirtualSessionDistrictCache.query.filter_by(
            district_name=district_name,
            virtual_year=virtual_year,
            date_from=date_from.date() if date_from else None,
            date_to=date_to.date() if date_to else None,
        ).first()

        if cache_record:
            # Update existing record
            cache_record.session_data = session_data
            cache_record.monthly_stats = monthly_stats
            cache_record.school_breakdown = school_breakdown
            cache_record.teacher_breakdown = teacher_breakdown
            cache_record.summary_stats = summary_stats
            cache_record.last_updated = datetime.now(timezone.utc)
        else:
            # Create new record
            cache_record = VirtualSessionDistrictCache(
                district_name=district_name,
                virtual_year=virtual_year,
                date_from=date_from.date() if date_from else None,
                date_to=date_to.date() if date_to else None,
                session_data=session_data,
                monthly_stats=monthly_stats,
                school_breakdown=school_breakdown,
                teacher_breakdown=teacher_breakdown,
                summary_stats=summary_stats,
            )
            db.session.add(cache_record)

        db.session.commit()
        print(
            f"Virtual session district cache saved for {district_name} {virtual_year}"
        )

    except Exception as e:
        db.session.rollback()
        print(f"Error saving virtual session district cache: {str(e)}")


def invalidate_virtual_session_caches(virtual_year=None):
    """
    Invalidate virtual session caches for a specific year or all years.

    Args:
        virtual_year: Specific year to invalidate, or None for all years
    """
    try:
        if virtual_year:
            # Invalidate specific year
            VirtualSessionReportCache.query.filter_by(
                virtual_year=virtual_year
            ).delete()
            VirtualSessionDistrictCache.query.filter_by(
                virtual_year=virtual_year
            ).delete()
        else:
            # Invalidate all caches
            VirtualSessionReportCache.query.delete()
            VirtualSessionDistrictCache.query.delete()

        db.session.commit()
        print(f"Virtual session caches invalidated for {virtual_year or 'all years'}")

    except Exception as e:
        db.session.rollback()
        print(f"Error invalidating virtual session caches: {str(e)}")
