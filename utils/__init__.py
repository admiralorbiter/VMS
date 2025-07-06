# Utils package 

def short_date(value):
    """Format a date as m/d/yy, cross-platform."""
    if value is None:
        return ''
    try:
        return value.strftime('%-m/%-d/%y')  # Unix
    except (ValueError, AttributeError):
        try:
            return value.strftime('%#m/%#d/%y')  # Windows
        except Exception:
            return str(value) 