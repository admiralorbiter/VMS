"""
Volunteer Enumerations
======================

Extracted from volunteer.py (TD-012) for better code organization.
Contains enum types specific to the volunteer domain.

These enums are re-exported from volunteer.py for backward compatibility,
so existing ``from models.volunteer import VolunteerStatus`` imports continue to work.
"""

from models.contact_enums import FormEnum


class ConnectorSubscriptionEnum(FormEnum):
    """
    Enum representing the subscription status of a connector.

    Used to track whether a volunteer is actively participating in the connector program.
    This is a specialized program within the volunteer system that has additional
    requirements and tracking mechanisms.

    Values:
    - NONE: No subscription status (default)
    - ACTIVE: Currently active in connector program
    - INACTIVE: Previously active but currently inactive
    - PENDING: Awaiting activation or approval
    """

    NONE = ""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"


class VolunteerStatus(FormEnum):
    """
    Enum defining the possible states of a volunteer's engagement.

    Used to track whether a volunteer is currently active, inactive, or on hold.
    This helps with volunteer management and communication strategies.

    Values:
    - NONE: No status set (default)
    - ACTIVE: Currently active and available for volunteering
    - INACTIVE: Not currently active but may return
    - ON_HOLD: Temporarily on hold (e.g., due to scheduling conflicts)
    """

    NONE = ""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_HOLD = "on_hold"
