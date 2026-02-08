"""Custom Jinja2 template filters."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models import WorkerState


def format_datetime_tz(dt, fmt="%Y-%m-%d %H:%M:%S"):
    """
    Convert UTC datetime to configured display timezone and format.
    
    Args:
        dt: datetime object (assumed UTC if naive)
        fmt: strftime format string
    
    Returns:
        Formatted datetime string with timezone name
    """
    if dt is None:
        return ""
    
    # Get configured timezone from database
    state = db.session.get(WorkerState, 1)
    tz_name = state.display_timezone if state else "UTC"
    
    # Ensure datetime is timezone-aware (UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to target timezone
    try:
        target_tz = ZoneInfo(tz_name)
        dt_local = dt.astimezone(target_tz)
        return f"{dt_local.strftime(fmt)} ({tz_name})"
    except Exception:
        # Fallback to UTC if timezone conversion fails
        return f"{dt.strftime(fmt)} (UTC)"


def register_filters(app):
    """Register custom template filters with Flask app."""
    app.jinja_env.filters["format_datetime_tz"] = format_datetime_tz
