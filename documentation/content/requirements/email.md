# Email System Requirements

**Polaris Admin Panel**

---

## Quick Navigation

| Category | Description |
|----------|-------------|
| [Template CRUD](#template-crud) | Create, read, update templates via admin UI |
| [Template Versioning](#template-versioning) | Version history, activation, rollback |
| [Template Preview & Placeholders](#template-preview--placeholders) | Live preview, placeholder management |
| [Delivery Monitoring](#delivery-monitoring) | Track delivery status and metrics |
| [Admin Email Sending](#admin-email-sending) | Manual email dispatch |
| [Safety Gates](#safety-gates) | Environment-based delivery controls |
| [Quality Assurance](#quality-assurance) | Validation and checks |
| [Infrastructure](#infrastructure) | Provider integration |
| [Compose & Send](#compose--send) | Compose to arbitrary recipients |

---

> [!NOTE]
> **System Location**: `/management/email`
>
> The email system provides safe-by-default email delivery with comprehensive tracking, quality checks, and safety gates.

---

## Template CRUD

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-801"></a>**FR-EMAIL-801** | The admin panel shall provide a **Create Template** form at `/management/email/templates/new` accessible to Admin users (security level 3+). | [TC-1400](test-packs/test-pack-10#tc-1400), [TC-1407](test-packs/test-pack-10#tc-1407) | [US-801](user-stories#us-801) |
| <a id="fr-email-802"></a>**FR-EMAIL-802** | The Create Template form shall require: **name**, **purpose key**, **subject template**, and at least one of **HTML template** or **plain-text template**. Description is optional. | [TC-1401](test-packs/test-pack-10#tc-1401) | [US-801](user-stories#us-801) |
| <a id="fr-email-803"></a>**FR-EMAIL-803** | The system shall enforce **unique purpose keys** — creating a template with a purpose key that already exists shall be rejected with a clear error message directing the user to create a new version instead. | [TC-1402](test-packs/test-pack-10#tc-1402) | [US-801](user-stories#us-801) |
| <a id="fr-email-804"></a>**FR-EMAIL-804** | The admin panel shall provide an **Edit Template** form at `/management/email/templates/<id>/edit` that allows modifying name, description, subject, HTML body, and text body of an existing template. | [TC-1403](test-packs/test-pack-10#tc-1403), [TC-1404](test-packs/test-pack-10#tc-1404) | [US-801](user-stories#us-801) |
| <a id="fr-email-805"></a>**FR-EMAIL-805** | Editing a template shall **not** change its purpose key or version number. To change content significantly, the admin should create a new version (see [FR-EMAIL-810](#fr-email-810)). | [TC-1404](test-packs/test-pack-10#tc-1404) | [US-801](user-stories#us-801) |
| <a id="fr-email-806"></a>**FR-EMAIL-806** | The templates list at `/management/email/templates` shall display all templates grouped by purpose key, showing: name, purpose key, version, active status, created date, and created by. | [TC-1412](test-packs/test-pack-10#tc-1412) | [US-801](user-stories#us-801) |
| <a id="fr-email-807"></a>**FR-EMAIL-807** | All template create and edit operations shall be **audit-logged** with the acting user's identity and timestamp. | [TC-1401](test-packs/test-pack-10#tc-1401), [TC-1404](test-packs/test-pack-10#tc-1404) | [US-801](user-stories#us-801) |

---

## Template Versioning

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-810"></a>**FR-EMAIL-810** | The admin panel shall provide a **Create New Version** action from a template detail page, which copies the current template content into a new record with version number incremented by one. | [TC-1410](test-packs/test-pack-10#tc-1410) | [US-801](user-stories#us-801) |
| <a id="fr-email-811"></a>**FR-EMAIL-811** | When a new version is created, the previous version shall be automatically **deactivated** (`is_active = false`) and the new version shall be **active** by default. | [TC-1410](test-packs/test-pack-10#tc-1410) | [US-801](user-stories#us-801) |
| <a id="fr-email-812"></a>**FR-EMAIL-812** | Only **one version per purpose key** shall be active at any time. Activating a version shall deactivate all other versions with the same purpose key. | [TC-1411](test-packs/test-pack-10#tc-1411) | [US-801](user-stories#us-801) |
| <a id="fr-email-813"></a>**FR-EMAIL-813** | The template detail page shall display a **version history** showing all versions for that purpose key, with indicators for which version is currently active. | [TC-1412](test-packs/test-pack-10#tc-1412) | [US-801](user-stories#us-801) |
| <a id="fr-email-814"></a>**FR-EMAIL-814** | Admins shall be able to **revert** to a previous version by activating it, which deactivates the currently active version. | [TC-1411](test-packs/test-pack-10#tc-1411) | [US-801](user-stories#us-801) |
| <a id="fr-email-815"></a>**FR-EMAIL-815** | A template version that has been used to send messages (has associated `EmailMessage` records) shall **not be deletable**, but may be deactivated. | [TC-1406](test-packs/test-pack-10#tc-1406) | [US-801](user-stories#us-801) |

---

## Template Preview & Placeholders

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-820"></a>**FR-EMAIL-820** | Templates shall define **required placeholders** (must be provided at send time) and **optional placeholders** (default values acceptable), entered as comma-separated lists in the create/edit form. | [TC-1401](test-packs/test-pack-10#tc-1401) | [US-801](user-stories#us-801) |
| <a id="fr-email-821"></a>**FR-EMAIL-821** | The template detail page shall provide a **live preview** panel that renders the HTML template with sample context data, automatically filling required and optional placeholders with test values. | [TC-1415](test-packs/test-pack-10#tc-1415) | [US-801](user-stories#us-801) |
| <a id="fr-email-822"></a>**FR-EMAIL-822** | Each template shall include both **HTML and plain text versions** for maximum deliverability; at least one must be provided and the other is auto-generated. | [TC-1416](test-packs/test-pack-10#tc-1416), [TC-1417](test-packs/test-pack-10#tc-1417) | [US-801](user-stories#us-801) |

---

## Delivery Monitoring

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-830"></a>**FR-EMAIL-830** | Polaris shall provide an admin dashboard showing email delivery status: **Queued**, **Sent**, **Failed**, **Blocked**. | [TC-1420](test-packs/test-pack-10#tc-1420) | [US-802](user-stories#us-802) |
| <a id="fr-email-831"></a>**FR-EMAIL-831** | The dashboard shall display **delivery metrics** including: total sent, success rate, failure rate, and blocked count. | [TC-1420](test-packs/test-pack-10#tc-1420) | [US-802](user-stories#us-802) |
| <a id="fr-email-832"></a>**FR-EMAIL-832** | Each email record shall track **delivery attempts** with timestamp, status, and error details. | [TC-1422](test-packs/test-pack-10#tc-1422), [TC-1424](test-packs/test-pack-10#tc-1424) | [US-802](user-stories#us-802) |
| <a id="fr-email-833"></a>**FR-EMAIL-833** | The system shall support filtering emails by: date range, status, template, and recipient domain. | [TC-1421](test-packs/test-pack-10#tc-1421) | [US-802](user-stories#us-802) |

---

## Admin Email Sending

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-840"></a>**FR-EMAIL-840** | Admins shall be able to compose and send emails via the admin panel using defined templates. | [TC-1430](test-packs/test-pack-10#tc-1430) | [US-803](user-stories#us-803) |
| <a id="fr-email-841"></a>**FR-EMAIL-841** | Email sending shall follow a **two-phase process**: Draft → Queued → Sent, allowing review before delivery. | [TC-1432](test-packs/test-pack-10#tc-1432) | [US-803](user-stories#us-803) |
| <a id="fr-email-842"></a>**FR-EMAIL-842** | Admins shall be able to **cancel queued emails** before delivery. | [TC-1421](test-packs/test-pack-10#tc-1421) | [US-803](user-stories#us-803) |

---

## Safety Gates

> [!CAUTION]
> Safety gates prevent accidental email delivery in non-production environments.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-850"></a>**FR-EMAIL-850** | The system shall enforce a **global kill-switch** (`EMAIL_DELIVERY_ENABLED`): when disabled, no emails are sent. | [TC-1440](test-packs/test-pack-10#tc-1440) | *Technical* |
| <a id="fr-email-851"></a>**FR-EMAIL-851** | In non-production environments, the system shall enforce an **allowlist**: only approved email domains/addresses receive delivery. | [TC-1441](test-packs/test-pack-10#tc-1441) | *Technical* |
| <a id="fr-email-852"></a>**FR-EMAIL-852** | Emails blocked by safety gates shall be logged with reason code: `GLOBALLY_DISABLED` or `NOT_ON_ALLOWLIST`. | [TC-1442](test-packs/test-pack-10#tc-1442) | *Technical* |
| <a id="fr-email-853"></a>**FR-EMAIL-853** | The admin dashboard shall clearly indicate current safety gate status (enabled/disabled, allowlist in effect). | [TC-1431](test-packs/test-pack-10#tc-1431) | *Technical* |
| <a id="fr-email-854"></a>**FR-EMAIL-854** | The system shall support **dry-run mode** for testing email rendering and validation without actual delivery. | [TC-1456](test-packs/test-pack-10#tc-1456) | *Technical* |

---

## Quality Assurance

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-860"></a>**FR-EMAIL-860** | The system shall validate recipient email addresses before queuing for delivery. | [TC-1450](test-packs/test-pack-10#tc-1450), [TC-1451](test-packs/test-pack-10#tc-1451) | *Technical* |
| <a id="fr-email-861"></a>**FR-EMAIL-861** | The system shall validate that all **required placeholders** are provided before sending. | [TC-1452](test-packs/test-pack-10#tc-1452) | *Technical* |
| <a id="fr-email-862"></a>**FR-EMAIL-862** | The system shall perform **template rendering validation** before queuing to catch syntax errors. | [TC-1453](test-packs/test-pack-10#tc-1453), [TC-1454](test-packs/test-pack-10#tc-1454) | *Technical* |
| <a id="fr-email-863"></a>**FR-EMAIL-863** | Failed email deliveries requiring human action shall automatically generate **BugReport** entries. | [TC-1455](test-packs/test-pack-10#tc-1455) | *Technical* |

---

## Infrastructure

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-870"></a>**FR-EMAIL-870** | The system shall integrate with **Mailjet** as the email delivery provider. | [TC-1460](test-packs/test-pack-10#tc-1460) | *Technical* |
| <a id="fr-email-871"></a>**FR-EMAIL-871** | Delivery attempt records shall capture **Mailjet response data** including message IDs and status codes. | [TC-1461](test-packs/test-pack-10#tc-1461) | *Technical* |
| <a id="fr-email-872"></a>**FR-EMAIL-872** | Provider credentials and API keys shall be stored securely and never logged or exposed in error messages. | Code review | *Technical* |

---

## Compose & Send

> [!NOTE]
> The compose feature allows admins to send emails to arbitrary recipients using existing templates.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-880"></a>**FR-EMAIL-880** | The admin panel shall provide a **Compose Email** page at `/management/email/compose` with a template dropdown, recipient textarea, and dynamic placeholder fields. | [TC-1470](test-packs/test-pack-10#tc-1470) | [US-803](user-stories#us-803) |
| <a id="fr-email-881"></a>**FR-EMAIL-881** | The compose form shall allow saving a composed email as a **Draft** for later review and sending. | [TC-1471](test-packs/test-pack-10#tc-1471) | [US-803](user-stories#us-803) |
| <a id="fr-email-882"></a>**FR-EMAIL-882** | The compose form shall allow immediate **Queue & Send** with optional dry-run mode for validation without delivery. | [TC-1472](test-packs/test-pack-10#tc-1472) | [US-803](user-stories#us-803) |
| <a id="fr-email-883"></a>**FR-EMAIL-883** | Submitting a compose form without recipients shall be rejected with a clear error message. | [TC-1473](test-packs/test-pack-10#tc-1473) | [US-803](user-stories#us-803) |
| <a id="fr-email-884"></a>**FR-EMAIL-884** | Submitting a compose form with missing **required placeholders** shall be rejected with a validation error before message creation. | [TC-1474](test-packs/test-pack-10#tc-1474) | [US-803](user-stories#us-803) |
| <a id="fr-email-885"></a>**FR-EMAIL-885** | The system shall provide a JSON API at `/management/email/templates/<id>/placeholders` to dynamically load required and optional placeholder fields for a selected template. | [TC-1475](test-packs/test-pack-10#tc-1475) | [US-803](user-stories#us-803) |

---

## Session Reminders

> [!NOTE]
> The session reminder feature sends personalized emails to teachers about upcoming virtual career sessions using a multi-gate safety system.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-890"></a>**FR-EMAIL-890** | The system shall provide a seeded `teacher_session_reminder` email template with personalized placeholders for teacher name, building, district branding, session list, and progress tracking. | `test_email_reminders.py` | *Technical* |
| <a id="fr-email-891"></a>**FR-EMAIL-891** | The admin panel shall provide a **Batch Send** workflow at `/management/email/batch/new` with 5 safety gates (create, canary, cooldown, confirmation code, execute). | `test_email_reminders.py` | *Technical* |
| <a id="fr-email-892"></a>**FR-EMAIL-892** | The batch send shall query upcoming virtual sessions (`EventType.VIRTUAL_SESSION`) with active statuses and future start dates. | `test_email_reminders.py` | *Technical* |
| <a id="fr-email-893"></a>**FR-EMAIL-893** | The batch send shall send a **canary email** to `DAILY_IMPORT_RECIPIENT` before any batch delivery, then enforce a configurable cooldown (default 10 minutes) with auto-cancel on timeout. | Code review | *Technical* |
| <a id="fr-email-894"></a>**FR-EMAIL-894** | The batch send shall require a **6-digit confirmation code** entry to proceed past the canary stage. | Code review | *Technical* |
| <a id="fr-email-895"></a>**FR-EMAIL-895** | All batch send actions shall be **audit-logged** with sent/skipped/error counts and state transitions. | Code review | *Technical* |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [Email System Guide](monitoring) — Operations documentation
- [User Stories](user-stories) — Business value context

---

*Last updated: February 2026 · Version 2.1*
