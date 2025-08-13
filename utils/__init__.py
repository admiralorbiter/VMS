# Utils package


def short_date(value):
    """Format a date as m/d/yy, cross-platform."""
    if value is None:
        return ""
    try:
        return value.strftime("%-m/%-d/%y")  # Unix
    except (ValueError, AttributeError):
        try:
            return value.strftime("%#m/%#d/%y")  # Windows
        except Exception:
            return str(value)


def format_event_type_for_badge(event_type):
    """
    Format event type for use in CSS class names and display text.

    This utility function ensures consistent formatting of event types
    across all templates and components.

    Args:
        event_type (str): The raw event type value

    Returns:
        tuple: (css_class, display_text) where:
            - css_class: event type formatted for CSS class names (underscores to dashes)
            - display_text: event type formatted for human-readable display
    """
    if not event_type:
        return "unknown", "Unknown"

    # Convert to string and handle enum values
    if hasattr(event_type, "value"):
        event_type = event_type.value

    event_type = str(event_type)

    # Create CSS class (replace underscores with dashes)
    css_class = event_type.replace("_", "-").lower()

    # Create display text (replace underscores with spaces and title case)
    display_text = event_type.replace("_", " ").title()

    return css_class, display_text
