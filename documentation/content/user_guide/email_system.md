# Email System Management

The **Email System** is a safe-by-default, testable email subsystem integrated into the VMS admin panel. It provides comprehensive email management with strong safeguards against accidental delivery.

## System Overview

- **Location**: `Management > Email`
- **Primary Use**: Sending consistent, branded communications to volunteers and stakeholders
- **Provider**: Mailjet
- **Key Feature**: "Two-Phase Sending" preventing accidental blasts

---

## Core Features

### 1. Templates

Manage versioned email templates ensuring consistency.

- **View Templates**: Go to `Management > Email > Templates`
- **Preview**: See how emails will look with sample data before sending
- Templates use "purpose keys" for stable identification

### 2. Outbox & Sending

All emails start in the **Outbox**.

| Status | Description |
|--------|-------------|
| Draft | Message created but not ready |
| Queued | Ready for delivery |
| Sent | Successfully handed off to Mailjet |
| Failed | Delivery failed (see Attempts) |
| Blocked | Stopped by safety gates |
| Cancelled | Manually cancelled |

### 3. Safety Gates

| Gate | Description |
|------|-------------|
| Global kill-switch | Delivery disabled unless `EMAIL_DELIVERY_ENABLED=true` |
| Non-prod allowlist | Only configured addresses/domains receive emails |
| Proof mode | Dry-run without actual delivery |
| Rate limiting | Per-message max recipients, daily/minute caps |
| Permission gates | Admin-only access (`@security_level_required(3)`) |

---

## Admin Panel Routes

| Route | Purpose |
|-------|---------|
| `/management/email` | Email overview dashboard |
| `/management/email/templates` | List email templates |
| `/management/email/templates/<id>` | Template detail |
| `/management/email/outbox` | Message outbox with filtering |
| `/management/email/outbox/<id>` | Message detail |
| `/management/email/attempts` | Delivery attempts list |
| `/management/email/settings` | Email settings |

### Actions (Admin Only)

- Queue message for delivery: `POST /management/email/outbox/<id>/queue`
- Send immediately: `POST /management/email/outbox/<id>/send`
- Cancel message: `POST /management/email/outbox/<id>/cancel`
- Test send: `POST /management/email/test-send`

---

## User Guide

### How to Monitor Delivery

1. Navigate to **Email Dashboard** (`/management/email`)
2. Check the **Health Metrics** (Queue size, Failures)
3. Click **Delivery Attempts** to see detailed logs

### How to Send a Test Email

1. Go to **Settings** (`/management/email/settings`)
2. Use the **Test Send** tool
3. In non-production: sends to first allowlist email
4. Supports dry-run preview

---

## Configuration

### Required Environment Variables

```bash
# Mailjet API credentials
MJ_APIKEY_PUBLIC=your_public_key
MJ_APIKEY_PRIVATE=your_private_key

# Email delivery control
EMAIL_DELIVERY_ENABLED=true  # Only set true in production

# Sender information
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME="VMS System"

# Non-production allowlist (comma-separated)
EMAIL_ALLOWLIST=admin@example.com,@testdomain.com

# Rate limiting
EMAIL_MAX_RECIPIENTS=100
```

### Non-Production Safety

When `FLASK_ENV != 'production'`:
- Delivery blocked unless `EMAIL_DELIVERY_ENABLED=true`
- Only allowlist addresses/domains can receive emails
- Other recipients excluded with reason tracking

---

## Data Quality Integration

Every message creation runs **quality checks**:

- Recipient resolution (count, dedupe, allowlist compliance)
- Context completeness (required IDs present)
- Template render validation (no missing placeholders)

Quality score (0-100) calculated per message.

---

## Troubleshooting

### Emails Not Sending

1. Check `EMAIL_DELIVERY_ENABLED` is `true`
2. Verify Mailjet credentials
3. Check allowlist in non-production
4. Review delivery attempts for errors
5. Check Bug Reports for system alerts

### Quality Checks Failing

1. Review quality check results in message detail
2. Ensure all required placeholders provided
3. Verify recipient email format
4. Check allowlist compliance

### Template Rendering Issues

1. Verify placeholders match context keys
2. Check for missing required placeholders
3. Review template preview in admin panel

---

## Database Schema

### email_templates
- `purpose_key` — Stable identifier
- `version` — Template version
- `subject_template`, `html_template`, `text_template`
- `required_placeholders`, `optional_placeholders` (JSON)

### email_messages
- `template_id` — Links to template
- `subject`, `html_body`, `text_body`
- `recipients`, `excluded_recipients` (JSON)
- `status`, `quality_score`
- `created_by_id`, `created_at`, `sent_at`

### email_delivery_attempts
- `message_id` — Links to message
- `status`, `mailjet_message_id`
- `error_message`, `error_details`
- `is_dry_run`

---

## Technical Scope & Traceability

| Component | Items |
|-----------|-------|
| **User Stories** | [US-801](user_stories#us-801), [US-802](user_stories#us-802), [US-803](user_stories#us-803) |
| **Requirements** | [FR-EMAIL-801](requirements#fr-email-801), [FR-EMAIL-802](requirements#fr-email-802), [FR-EMAIL-803](requirements#fr-email-803), [FR-EMAIL-804](requirements#fr-email-804) |

### Key Files

| Category | Files |
|----------|-------|
| **Routes** | `routes/management/email.py` |
| **Models** | `models/email_template.py`, `models/email_message.py`, `models/email_delivery_attempt.py` |
| **Utils** | `utils/email.py` |
