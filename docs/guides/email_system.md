# Email System Feature Documentation

## Overview

The **Email System** is a safe-by-default, testable Mailjet-based email subsystem integrated into the VMS admin panel. It provides comprehensive email management capabilities with strong safeguards against accidental delivery, first-class observability, and a clear path to Data Tracker integration.

The primary goals of the Email System are to:

- Prevent accidental email delivery, especially in dev/test/staging environments
- Make every email send auditable and reproducible (who/what/when/why)
- Make failures easy to discover, triage, and fix (clear statuses + surfacing in admin)
- Make it testable at multiple layers (unit, integration, end-to-end "dry run")
- Lay groundwork for Data Tracker-triggered notifications without coupling too early

## Architecture

### Core Components

1. **EmailTemplate**: Versioned email templates (HTML + text) with stable "purpose keys"
2. **EmailMessage (Outbox)**: Immutable intent to send, including rendered content and metadata
3. **EmailDeliveryAttempt**: Individual provider calls (Mailjet) recorded separately with full traceability

### Email Lifecycle

```
DRAFT → QUEUED → SENT
         ↓
      FAILED
         ↓
    BLOCKED (by safety gates)
         ↓
   CANCELLED (manual)
```

## Safety Architecture

### Two-Phase Sending (Always)

- **Phase A**: Create message intent in outbox (draft/queued)
- **Phase B**: Separate sender process performs delivery (manual action or scheduled runner)

### Environment Gates

- **Global kill-switch**: Delivery disabled unless `EMAIL_DELIVERY_ENABLED=true`
- **Non-prod allowlist enforcement**: Only allow sends to configured addresses/domains
- **Proof mode**: Ability to run full pipeline and record attempts without delivery (dry-run)

### Permission Gates

- Admin-panel actions require elevated permissions (`@security_level_required(3)` - ADMIN only)
- Optional "two-person rule" can be added later for campaigns (creator vs approver)

### Rate/Volume Guards

- Per-message hard cap (max recipients, configurable via `EMAIL_MAX_RECIPIENTS`)
- Daily cap and per-minute cap (protects from loops)

### Recipient Quality Checks

- Validate email format
- Required consent flags (if/when added)
- Deduplication
- Suppress known-bad addresses

## Admin Panel

### Email Overview Dashboard (`/management/email`)

Quick health metrics:
- Delivery enabled/disabled status
- Allowlist active status
- Sender queue size
- Failures in last 24h
- Links to all email management sections

### Templates (`/management/email/templates`)

- List templates by purpose key and version
- Preview rendering with sample context
- Validation: required placeholders present, both HTML and text versions exist

### Outbox / Messages (`/management/email/outbox`)

- Search/filter by status, template key, district, created_by, created_at
- "View message" shows:
  - Rendered subject/body
  - Resolved recipients + exclusions
  - Quality-check results
  - Linked resources (e.g., `bug_report_id`, `teacher_id`)
- Actions (role-gated): create draft, queue, cancel, requeue

### Delivery Attempts (`/management/email/attempts`)

- Timeline of attempts with provider payload summary (never secrets)
- Mailjet IDs and status
- Easy copy/paste of error details

### Settings & Safety (`/management/email/settings`)

- Delivery enabled flag (environment-driven; admin can see state)
- Non-prod allowlist config viewer
- Default From name/email (environment-driven)
- "Test send" tool: sends to first allowlist email in non-production (or current user's email if no allowlist), supports dry-run preview

### Errors & Alerts (Integrated with Bug Reports)

- If a delivery attempt fails in a way that needs human action, creates a **system-generated BugReport** entry (`BugReportType.OTHER`) with structured description
- Filterable in `/bug-reports` admin panel
- Also logged to audit logs for traceability

## Data Quality Integration

Every message creation runs **quality checks** and stores results alongside the outbox record:

- Recipient resolution checks (count, dedupe, allowlist compliance)
- Context completeness (required district/teacher/session ids present depending on template)
- Template render validation (no missing placeholders)

Quality score (0-100) calculated per message, with weekly summary capability (future enhancement).

## Configuration

### Required Environment Variables

```bash
# Mailjet API credentials
MJ_APIKEY_PUBLIC=your_public_key
MJ_APIKEY_PRIVATE=your_private_key

# Email delivery control
EMAIL_DELIVERY_ENABLED=true  # Only set to true in production

# Sender information
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME="VMS System"

# Non-production allowlist (comma-separated)
EMAIL_ALLOWLIST=admin@example.com,@testdomain.com

# Rate limiting
EMAIL_MAX_RECIPIENTS=100  # Max recipients per message
```

### Non-Production Safety

In non-production environments (when `FLASK_ENV != 'production'`):
- Delivery is blocked unless `EMAIL_DELIVERY_ENABLED=true`
- If `EMAIL_ALLOWLIST` is set, only those addresses/domains can receive emails
- All other recipients are automatically excluded with reason tracking

## Usage Examples

### Creating an Email Message

```python
from models.email import EmailTemplate, EmailMessageStatus
from utils.email import create_email_message

# Get template
template = EmailTemplate.query.filter_by(purpose_key="data_error_received", is_active=True).first()

# Create message
message = create_email_message(
    template=template,
    recipients=["admin@example.com"],
    context={
        "user_name": "John Doe",
        "district_name": "Example District",
        "bug_report_id": "123"
    },
    created_by_id=current_user.id,
    status=EmailMessageStatus.DRAFT
)
```

### Queueing and Sending

```python
from utils.email import queue_message_for_delivery, create_delivery_attempt

# Queue message
message = queue_message_for_delivery(message.id)

# Send immediately (or use dry-run)
attempt = create_delivery_attempt(message, is_dry_run=False)
```

### Testing with Dry-Run

```python
# Create attempt in dry-run mode (no actual delivery)
attempt = create_delivery_attempt(message, is_dry_run=True)
```

## API Endpoints

### Admin Routes

- `GET /management/email` - Email overview dashboard
- `GET /management/email/templates` - List email templates
- `GET /management/email/templates/<id>` - Template detail
- `GET /management/email/outbox` - Message outbox (with filtering)
- `GET /management/email/outbox/<id>` - Message detail
- `POST /management/email/outbox/<id>/queue` - Queue message for delivery
- `POST /management/email/outbox/<id>/send` - Send message immediately
- `POST /management/email/outbox/<id>/cancel` - Cancel message
- `GET /management/email/attempts` - Delivery attempts list
- `GET /management/email/settings` - Email settings
- `POST /management/email/test-send` - Send test email

## Integration with Data Tracker

The email system is designed to integrate with the Data Tracker feature for notifications. Future integration points:

- Notify admins when new `DATA_ERROR` BugReport is created
- Send weekly quality summary emails
- Alert on recurring missing-data conditions
- Magic link emails for teacher authentication

## Testing Strategy

### Unit Tests
- Template rendering
- Quality checks
- Allowlist enforcement

### Integration Tests
- Compose → queue → sender runner (dry-run/fake provider) → outbox statuses

### Manual Test Path
- Admin panel: render preview + dry-run + test send (uses allowlist email in non-production)

### CI Safety
- Never requires real Mailjet delivery for CI
- All tests use dry-run mode or fake provider

## Database Schema

### email_templates
- `id` (Primary Key)
- `purpose_key` (String, indexed)
- `version` (Integer)
- `name`, `description`
- `subject_template`, `html_template`, `text_template` (Text)
- `required_placeholders`, `optional_placeholders` (JSON)
- `is_active` (Boolean)
- `created_at`, `created_by_id`

### email_messages
- `id` (Primary Key)
- `template_id` (Foreign Key)
- `subject`, `html_body`, `text_body` (Text)
- `recipients` (JSON array)
- `recipient_count` (Integer)
- `excluded_recipients` (JSON)
- `status` (Integer, indexed)
- `quality_checks` (JSON)
- `quality_score` (Integer)
- `context_metadata` (JSON)
- `created_by_id` (Foreign Key)
- `created_at`, `queued_at`, `sent_at` (DateTime)

### email_delivery_attempts
- `id` (Primary Key)
- `message_id` (Foreign Key)
- `status` (Integer, indexed)
- `mailjet_message_id` (String, indexed)
- `mailjet_response` (JSON)
- `error_message` (Text)
- `error_details` (JSON)
- `provider_payload_summary` (JSON)
- `attempted_at`, `completed_at` (DateTime, indexed)
- `is_dry_run` (Boolean)

## Security Considerations

1. **Admin-only access**: All email management routes require ADMIN security level
2. **Environment-based safety**: Non-production environments have strict allowlist enforcement
3. **Audit logging**: All email actions are logged via audit log system
4. **No secrets in logs**: Provider payload summaries never include API keys
5. **Two-phase approval**: Messages must be explicitly queued and then sent

## Future Enhancements

### Phase 2: Data Tracker Notifications
- Notify admins when new `DATA_ERROR` BugReport is created
- Weekly quality summary emails
- Alert on recurring missing-data conditions

### Phase 3: Campaigns
- Approval workflow (two-person rule)
- Recipient segmentation
- Unsubscribe/suppression management
- Scheduled sending

## Troubleshooting

### Emails Not Sending

1. Check `EMAIL_DELIVERY_ENABLED` is set to `true`
2. Verify Mailjet credentials (`MJ_APIKEY_PUBLIC`, `MJ_APIKEY_PRIVATE`)
3. Check allowlist in non-production environments
4. Review delivery attempts for error messages
5. Check Bug Reports for system alerts

### Quality Checks Failing

1. Review quality check results in message detail view
2. Ensure all required placeholders are provided in context
3. Verify recipient email format is valid
4. Check allowlist compliance in non-production

### Template Rendering Issues

1. Verify all placeholders in template match context keys
2. Check for missing required placeholders
3. Review template preview in admin panel

## Summary

The Email System provides a robust, safe-by-default email infrastructure for VMS with comprehensive tracking, quality checks, and safety gates. It integrates seamlessly with the existing admin panel and Bug Reports system, providing full observability and control over email delivery.
