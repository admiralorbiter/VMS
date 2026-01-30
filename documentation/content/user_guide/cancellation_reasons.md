# Cancellation Reasons Reference

**Predefined codes for tracking why virtual sessions are cancelled**

---

## Overview

When a virtual session is cancelled, staff or district administrators must select a cancellation reason. This data supports pattern analysis and helps identify systemic issues affecting session delivery.

**Related Documentation:**
- [Virtual Event Management](virtual_events)
- [Pathful Import Recommendations](../dev/pathful_import_recommendations#dec-008)
- [Requirements](../requirements#fr-virtual-227)

---

## Cancellation Reason Codes

| Code | Label | Description | Typical Resolution |
|------|-------|-------------|-------------------|
| `WEATHER` | Weather/Snow Day | Session cancelled due to inclement weather or school closure | Reschedule via Pathful |
| `PRESENTER_CANCELLED` | Presenter Cancelled | Volunteer/presenter unable to attend | Find replacement presenter |
| `TEACHER_CANCELLED` | Teacher Cancelled | Teacher withdrew or became unavailable | Contact school coordinator |
| `SCHOOL_CONFLICT` | School Conflict | Scheduling conflict with school activities (testing, assemblies, etc.) | Reschedule via school |
| `TECHNICAL_ISSUES` | Technical Issues | Platform, connectivity, or equipment problems | IT support, reschedule |
| `LOW_ENROLLMENT` | Low Enrollment | Insufficient student signups to run session | Marketing follow-up |
| `SCHEDULING_ERROR` | Scheduling Error | Session created in error or double-booked | Data cleanup, training |
| `OTHER` | Other | Reason not covered by predefined codes | ⚠️ Notes required |

---

## Usage Guidelines

### When to Set a Reason

- **Required** for any event with status = `Cancelled`
- Should be set as soon as cancellation is known
- Can be updated if more information becomes available

### Who Can Set Cancellation Reasons

| Role | Access |
|------|--------|
| PrepKC Staff | All virtual events |
| District Admin | Events at schools in their assigned district(s) only |

### Notes Field

- **Required** when selecting "Other"
- **Recommended** for context on any reason
- Helps with pattern analysis and follow-up

---

## Auto-Flagging

Events with `status = Cancelled` and no cancellation reason set are automatically flagged as `NEEDS_REASON` during post-import processing.

**Flag Resolution:**
1. Navigate to the flagged event
2. Select appropriate cancellation reason from dropdown
3. Add notes if applicable
4. Save — flag is automatically resolved

---

## Reporting

Cancellation reasons support:

- **Trend Analysis**: Identify patterns by reason type
- **District Reporting**: Cancellation rates by school/district
- **Presenter Reliability**: Track presenter-initiated cancellations
- **Technical Issues**: Identify systemic platform problems

---

## Data Model

```
Event
├── status: EventStatus (CANCELLED)
├── cancellation_reason: CancellationReason (enum)
├── cancellation_notes: String (optional, required for OTHER)
└── cancelled_at: DateTime
```

### CancellationReason Enum

```python
class CancellationReason(enum.Enum):
    WEATHER = "Weather/Snow Day"
    PRESENTER_CANCELLED = "Presenter Cancelled"
    TEACHER_CANCELLED = "Teacher Cancelled"
    SCHOOL_CONFLICT = "School Conflict"
    TECHNICAL_ISSUES = "Technical Issues"
    LOW_ENROLLMENT = "Low Enrollment"
    SCHEDULING_ERROR = "Scheduling Error"
    OTHER = "Other"
```

---

## Related Requirements

- [FR-VIRTUAL-227](../requirements#fr-virtual-227): Cancellation reason codes
- [FR-VIRTUAL-228](../requirements#fr-virtual-228): Auto-flagging for missing reasons
- [FR-VIRTUAL-231](../requirements#fr-virtual-231): District admin can set reasons

## Related User Stories

- [US-311](../user_stories#us-311): Set Cancellation Reasons for Virtual Sessions

---

*Last updated: January 2026*
