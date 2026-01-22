# Contract B: Website ↔ VolunTeach API

**Event display + volunteer signup**

## Reference

- Signup fields in [Data Dictionary - Volunteer](data_dictionary#entity-volunteer)
- Validation rules in [Field Mappings - Website Signup](field_mappings#2-website-signup--sf--polaris)
- Architecture: [Architecture - VolunTeach → Website](architecture#volunteach--website)
- Use Cases: [UC-3](use_cases#uc-3)

## Purpose

Website consumes VolunTeach data to display event listings and accept volunteer signups.

## B1: Event Listing API (Read)

### Endpoint

```
GET /api/events
```

### Query Parameters

- `page` — pagination
- `event_type=in_person`
- `district_id` — for district pages
- `start_date`, `end_date`

### Response Fields

- `event_id`, `sf_event_id`, `title`
- `start_datetime`, `school_name`
- `volunteer_slots_needed`, `volunteer_slots_filled`

### Visibility Rules (Contracted Behavior)

> [!WARNING]
> **Critical:** Visibility rules must be enforced as specified.

- **Public in-person page:** includes event only if `inperson_page_visible = true`
- **District pages:** includes event if `district_links` contains that district, **regardless** of toggle

**Reference:** [Architecture - VolunTeach → Website](architecture#volunteach--website)

## B2: Signup Submission API (Write)

### Endpoint

```
POST /api/events/{event_id}/signup
```

### Request Body (Required)

- `first_name`, `last_name`, `email`
- `organization`, `title`
- `volunteer_skills`, `age_group`, `education_attainment`, `gender`, `race_ethnicity`
- Event reference (`event_id` or `sf_event_id`)

**Reference:** [Data Dictionary - Volunteer](data_dictionary#entity-volunteer) for field definitions

## Idempotency

**Idempotency key:** `event_id + normalized_email`

**Duplicate signup:** Return HTTP 200 "already signed up" OR 409 conflict. Must NOT create duplicate participation.

**Reference:** [Field Mappings - Canonical Join Keys](field_mappings#canonical-join-keys)

## Validation Rules

- Required fields enforced (no empty names/email/org/title)
- Email format valid
- Dropdown values must match controlled vocabulary (reject tampered values)

**Reference:** [Field Mappings - Normalization Rules](field_mappings#normalization-rules-apply-everywhere)

## Email + Calendar Invite

On successful signup:

- Send confirmation email
- Send calendar invite with SF location fields

### Failure Policy (Recommended)

- Participation created even if email fails
- Email failure logged and queued for retry
- User receives success + "If no email, contact support"

**Reference:** [Runbook - Calendar Invites Not Sending](runbook#runbook-104-calendar-invites-not-sending)

## Related Documentation

- [Field Mappings - Website Signup](field_mappings#2-website-signup--sf--polaris)
- [Architecture - VolunTeach → Website](architecture#volunteach--website)
- [Data Dictionary - Volunteer](data_dictionary#entity-volunteer)
- [Use Cases - UC-3](use_cases#uc-3)
- [Runbook - Calendar Invites Not Sending](runbook#runbook-104-calendar-invites-not-sending)

---

*Last updated: January 2026*
*Version: 1.0*
