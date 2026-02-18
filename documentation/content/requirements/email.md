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

---

> [!NOTE]
> **System Location**: `/management/email`
>
> The email system provides safe-by-default email delivery with comprehensive tracking, quality checks, and safety gates.

---

## Template CRUD

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-801"></a>**FR-EMAIL-801** | The admin panel shall provide a **Create Template** form at `/management/email/templates/new` accessible to Admin users (security level 3+). | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-802"></a>**FR-EMAIL-802** | The Create Template form shall require: **name**, **purpose key**, **subject template**, **HTML template**, and **plain-text template**. Description is optional. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-803"></a>**FR-EMAIL-803** | The system shall enforce **unique purpose keys** — creating a template with a purpose key that already exists shall be rejected with a clear error message directing the user to create a new version instead. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-804"></a>**FR-EMAIL-804** | The admin panel shall provide an **Edit Template** form at `/management/email/templates/<id>/edit` that allows modifying name, description, subject, HTML body, and text body of an existing template. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-805"></a>**FR-EMAIL-805** | Editing a template shall **not** change its purpose key or version number. To change content significantly, the admin should create a new version (see [FR-EMAIL-810](#fr-email-810)). | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-806"></a>**FR-EMAIL-806** | The templates list at `/management/email/templates` shall display all templates grouped by purpose key, showing: name, purpose key, version, active status, created date, and created by. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-807"></a>**FR-EMAIL-807** | All template create and edit operations shall be **audit-logged** with the acting user's identity and timestamp. | *TBD* | [US-801](user-stories#us-801) |

---

## Template Versioning

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-810"></a>**FR-EMAIL-810** | The admin panel shall provide a **Create New Version** action from a template detail page, which copies the current template content into a new record with version number incremented by one. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-811"></a>**FR-EMAIL-811** | When a new version is created, the previous version shall be automatically **deactivated** (`is_active = false`) and the new version shall be **active** by default. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-812"></a>**FR-EMAIL-812** | Only **one version per purpose key** shall be active at any time. Activating a version shall deactivate all other versions with the same purpose key. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-813"></a>**FR-EMAIL-813** | The template detail page shall display a **version history** showing all versions for that purpose key, with indicators for which version is currently active. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-814"></a>**FR-EMAIL-814** | Admins shall be able to **revert** to a previous version by activating it, which deactivates the currently active version. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-815"></a>**FR-EMAIL-815** | A template version that has been used to send messages (has associated `EmailMessage` records) shall **not be deletable**, but may be deactivated. | *TBD* | [US-801](user-stories#us-801) |

---

## Template Preview & Placeholders

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-820"></a>**FR-EMAIL-820** | Templates shall define **required placeholders** (must be provided at send time) and **optional placeholders** (default values acceptable), entered as comma-separated lists in the create/edit form. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-821"></a>**FR-EMAIL-821** | The template detail page shall provide a **live preview** panel that renders the HTML template with sample context data, automatically filling required and optional placeholders with test values. | *TBD* | [US-801](user-stories#us-801) |
| <a id="fr-email-822"></a>**FR-EMAIL-822** | Each template shall include both **HTML and plain text versions** for maximum deliverability; the create/edit form shall validate that both are provided. | *TBD* | [US-801](user-stories#us-801) |

---

## Delivery Monitoring

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-830"></a>**FR-EMAIL-830** | Polaris shall provide an admin dashboard showing email delivery status: **Queued**, **Sent**, **Failed**, **Blocked**. | *TBD* | [US-802](user-stories#us-802) |
| <a id="fr-email-831"></a>**FR-EMAIL-831** | The dashboard shall display **delivery metrics** including: total sent, success rate, failure rate, and blocked count. | *TBD* | [US-802](user-stories#us-802) |
| <a id="fr-email-832"></a>**FR-EMAIL-832** | Each email record shall track **delivery attempts** with timestamp, status, and error details. | *TBD* | [US-802](user-stories#us-802) |
| <a id="fr-email-833"></a>**FR-EMAIL-833** | The system shall support filtering emails by: date range, status, template, and recipient domain. | *TBD* | [US-802](user-stories#us-802) |

---

## Admin Email Sending

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-840"></a>**FR-EMAIL-840** | Admins shall be able to compose and send emails via the admin panel using defined templates. | *TBD* | [US-803](user-stories#us-803) |
| <a id="fr-email-841"></a>**FR-EMAIL-841** | Email sending shall follow a **two-phase process**: Draft → Queued → Sent, allowing review before delivery. | *TBD* | [US-803](user-stories#us-803) |
| <a id="fr-email-842"></a>**FR-EMAIL-842** | Admins shall be able to **cancel queued emails** before delivery. | *TBD* | [US-803](user-stories#us-803) |

---

## Safety Gates

> [!CAUTION]
> Safety gates prevent accidental email delivery in non-production environments.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-850"></a>**FR-EMAIL-850** | The system shall enforce a **global kill-switch** (`EMAIL_DELIVERY_ENABLED`): when disabled, no emails are sent. | *TBD* | *Technical* |
| <a id="fr-email-851"></a>**FR-EMAIL-851** | In non-production environments, the system shall enforce an **allowlist**: only approved email domains/addresses receive delivery. | *TBD* | *Technical* |
| <a id="fr-email-852"></a>**FR-EMAIL-852** | Emails blocked by safety gates shall be logged with reason code: `GLOBALLY_DISABLED` or `NOT_ON_ALLOWLIST`. | *TBD* | *Technical* |
| <a id="fr-email-853"></a>**FR-EMAIL-853** | The admin dashboard shall clearly indicate current safety gate status (enabled/disabled, allowlist in effect). | *TBD* | *Technical* |
| <a id="fr-email-854"></a>**FR-EMAIL-854** | The system shall support **dry-run mode** for testing email rendering and validation without actual delivery. | *TBD* | *Technical* |

---

## Quality Assurance

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-860"></a>**FR-EMAIL-860** | The system shall validate recipient email addresses before queuing for delivery. | *TBD* | *Technical* |
| <a id="fr-email-861"></a>**FR-EMAIL-861** | The system shall validate that all **required placeholders** are provided before sending. | *TBD* | *Technical* |
| <a id="fr-email-862"></a>**FR-EMAIL-862** | The system shall perform **template rendering validation** before queuing to catch syntax errors. | *TBD* | *Technical* |
| <a id="fr-email-863"></a>**FR-EMAIL-863** | Failed email deliveries requiring human action shall automatically generate **BugReport** entries. | *TBD* | *Technical* |

---

## Infrastructure

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-email-870"></a>**FR-EMAIL-870** | The system shall integrate with **Mailjet** as the email delivery provider. | *TBD* | *Technical* |
| <a id="fr-email-871"></a>**FR-EMAIL-871** | Delivery attempt records shall capture **Mailjet response data** including message IDs and status codes. | *TBD* | *Technical* |
| <a id="fr-email-872"></a>**FR-EMAIL-872** | Provider credentials and API keys shall be stored securely and never logged or exposed in error messages. | *TBD* | *Technical* |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [Email System Guide](monitoring) — Operations documentation
- [User Stories](user-stories) — Business value context

---

*Last updated: February 2026 · Version 2.0*
