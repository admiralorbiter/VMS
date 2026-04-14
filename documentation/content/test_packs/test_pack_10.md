# Test Pack 10: Email System

Admin email template management + delivery pipeline + safety gates + quality assurance

> [!NOTE]
> **Coverage**
> [FR-EMAIL-801](requirements-email#fr-email-801)–[FR-EMAIL-807](requirements-email#fr-email-807) (Template CRUD), [FR-EMAIL-810](requirements-email#fr-email-810)–[FR-EMAIL-815](requirements-email#fr-email-815) (Versioning), [FR-EMAIL-820](requirements-email#fr-email-820)–[FR-EMAIL-822](requirements-email#fr-email-822) (Preview & Placeholders), [FR-EMAIL-830](requirements-email#fr-email-830)–[FR-EMAIL-833](requirements-email#fr-email-833) (Delivery Monitoring), [FR-EMAIL-840](requirements-email#fr-email-840)–[FR-EMAIL-842](requirements-email#fr-email-842) (Admin Sending), [FR-EMAIL-850](requirements-email#fr-email-850)–[FR-EMAIL-854](requirements-email#fr-email-854) (Safety Gates), [FR-EMAIL-860](requirements-email#fr-email-860)–[FR-EMAIL-863](requirements-email#fr-email-863) (Quality Assurance), [FR-EMAIL-870](requirements-email#fr-email-870)–[FR-EMAIL-872](requirements-email#fr-email-872) (Infrastructure), [FR-EMAIL-880](requirements-email#fr-email-880)–[FR-EMAIL-885](requirements-email#fr-email-885) (Compose & Send)

---

## Test Data Setup

**Users:**

| User | Role | Purpose |
|------|------|---------|
| admin_user | Admin (security level 3) | Template CRUD, sending, settings |
| regular_user | Non-Admin | Tests access restrictions |

**Templates:**

| Template | Purpose Key | Placeholders | Description |
|----------|-------------|-------------|-------------|
| Test Template | `test_template` | `user_name` (required) | Standard test template with HTML + plain text |

---

## Test Cases

### A. Template CRUD

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1400"></a>**TC-1400** | Admin accesses Create Template form (GET /management/email/templates/new) | 200 with form HTML | Automated | 2026-02 |
| <a id="tc-1401"></a>**TC-1401** | Create template with name, purpose key, subject, HTML body | Template persisted; redirect to detail page with success flash | Automated | 2026-02 |
| <a id="tc-1402"></a>**TC-1402** | Create template with duplicate purpose key | Rejected with error message directing to versioning | Automated | 2026-02 |
| <a id="tc-1403"></a>**TC-1403** | Admin accesses Edit Template form (GET /management/email/templates/<id>/edit) | 200 with pre-populated form | Automated | 2026-02 |
| <a id="tc-1404"></a>**TC-1404** | Edit template name, description, subject, body | Fields updated; purpose key and version unchanged | Automated | 2026-02 |
| <a id="tc-1405"></a>**TC-1405** | Delete template with no associated messages | Template removed from DB | Automated | 2026-02 |
| <a id="tc-1406"></a>**TC-1406** | Delete template that has sent messages | Rejected — template preserved, may be deactivated | Automated | 2026-02 |
| <a id="tc-1407"></a>**TC-1407** | Non-admin attempts template CRUD | 403 Forbidden on all template routes | Automated | 2026-02 |

### B. Template Versioning

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1410"></a>**TC-1410** | Create new version from template detail page | New record created with version+1; old version deactivated | Automated | 2026-02 |
| <a id="tc-1411"></a>**TC-1411** | Activate an older version | Selected version becomes active; all others with same purpose key deactivated | Automated | 2026-02 |
| <a id="tc-1412"></a>**TC-1412** | Template detail shows version history | All versions listed with active indicator | Automated | 2026-02 |

### C. Preview & Placeholders

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1415"></a>**TC-1415** | Template detail shows live preview | HTML preview rendered with sample placeholder values | Automated | 2026-02 |
| <a id="tc-1416"></a>**TC-1416** | Create template with only HTML body | Plain-text auto-generated from HTML | Automated | 2026-02 |
| <a id="tc-1417"></a>**TC-1417** | Create template with only plain-text body | HTML auto-generated from plain text | Automated | 2026-02 |

### D. Delivery Monitoring

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1420"></a>**TC-1420** | Admin views email overview dashboard | 200 with delivery metrics (sent, failed, blocked counts) | Automated | 2026-02 |
| <a id="tc-1421"></a>**TC-1421** | Admin views outbox list | 200 with message list; filterable by status | Automated | 2026-02 |
| <a id="tc-1422"></a>**TC-1422** | Admin views delivery attempts list | 200 with attempt records showing timestamps and status | Automated | 2026-02 |
| <a id="tc-1423"></a>**TC-1423** | View individual message detail | Message details with recipients, delivery history, quality score | Automated | 2026-02 |
| <a id="tc-1424"></a>**TC-1424** | View individual delivery attempt detail | Attempt details with Mailjet response and error info | Automated | 2026-02 |

### E. Admin Email Sending

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1430"></a>**TC-1430** | Admin sends test email (dry-run) | Message created in outbox with DRY_RUN status; no actual delivery | Automated | 2026-02 |
| <a id="tc-1431"></a>**TC-1431** | Admin views email settings page | 200 with safety gate status and test send form | Automated | 2026-02 |
| <a id="tc-1432"></a>**TC-1432** | Create email message with Draft → Queued → Sent flow | Message transitions through statuses correctly | Automated | 2026-02 |

### F. Safety Gates

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1440"></a>**TC-1440** | Delivery blocked when EMAIL_DELIVERY_ENABLED=false | Safety gate rejects send; reason code GLOBALLY_DISABLED | Automated | 2026-02 |
| <a id="tc-1441"></a>**TC-1441** | Allowlist enforcement in non-production | Only allowlisted emails/domains pass; others excluded with NOT_ON_ALLOWLIST | Automated | 2026-02 |
| <a id="tc-1442"></a>**TC-1442** | All recipients blocked by allowlist | Send rejected entirely with clear error | Automated | 2026-02 |
| <a id="tc-1443"></a>**TC-1443** | Dry-run bypasses delivery check | Dry-run succeeds even when delivery is disabled | Automated | 2026-02 |
| <a id="tc-1444"></a>**TC-1444** | Max recipients limit enforced | Send rejected when recipient count exceeds limit | Automated | 2026-02 |

### G. Quality Assurance

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1450"></a>**TC-1450** | Recipient validation rejects invalid email formats | Invalid/empty emails excluded with reasons; valid emails accepted | Automated | 2026-02 |
| <a id="tc-1451"></a>**TC-1451** | Recipient validation deduplicates list | Duplicate emails excluded; only unique addresses sent | Automated | 2026-02 |
| <a id="tc-1452"></a>**TC-1452** | Missing required placeholders caught before send | EmailQualityError raised with list of missing placeholders | Automated | 2026-02 |
| <a id="tc-1453"></a>**TC-1453** | Template rendering validation on message creation | Subject, HTML, and text bodies rendered correctly; quality score set | Automated | 2026-02 |
| <a id="tc-1454"></a>**TC-1454** | Quality score < 50 blocks queued messages | Message status set to BLOCKED instead of QUEUED | Automated | 2026-02 |
| <a id="tc-1455"></a>**TC-1455** | Delivery failure auto-creates BugReport | BugReport record created with EMAIL_DELIVERY_FAILED and message ID | Automated | 2026-02 |
| <a id="tc-1456"></a>**TC-1456** | Dry-run validates without actual delivery | DRY_RUN status set; message NOT marked as SENT | Automated | 2026-02 |

### H. Infrastructure

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1460"></a>**TC-1460** | End-to-end send via Mailjet (real email) | Message sent; Mailjet message ID captured on attempt | Manual | 2026-02 |
| <a id="tc-1461"></a>**TC-1461** | Delivery attempt captures Mailjet response data | Response payload stored on attempt record | Manual | 2026-02 |
| <a id="tc-1462"></a>**TC-1462** | Delivery enabled/disabled environment check | Correct boolean returned based on EMAIL_DELIVERY_ENABLED env var | Automated | 2026-02 |
| <a id="tc-1463"></a>**TC-1463** | Production environment detection | Correct boolean returned based on FLASK_ENV env var | Automated | 2026-02 |

### I. Compose & Send

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1470"></a>**TC-1470** | Admin accesses Compose page (GET /management/email/compose) | 200 with template dropdown, recipients textarea, placeholder section | Automated | 2026-02 |
| <a id="tc-1471"></a>**TC-1471** | Compose POST with valid data and action=draft | Message created as DRAFT with correct recipients | Automated | 2026-02 |
| <a id="tc-1472"></a>**TC-1472** | Compose POST with action=send and dry_run=true | Message queued and dry-run attempt created without real delivery | Automated | 2026-02 |
| <a id="tc-1473"></a>**TC-1473** | Compose POST with empty recipients | Rejected with error message about missing recipients | Automated | 2026-02 |
| <a id="tc-1474"></a>**TC-1474** | Compose POST missing required placeholder | Rejected with error identifying the missing placeholder | Automated | 2026-02 |
| <a id="tc-1475"></a>**TC-1475** | GET /management/email/templates/<id>/placeholders | JSON with required, optional arrays and subject | Automated | 2026-02 |

---

## Automated Test Mapping

| TC Range | Python Test Class | Test File |
|----------|------------------|-----------|
| TC-1400–1407 | `TestTemplateCRUD` | `tests/integration/test_email_routes.py` |
| TC-1410–1412 | `TestTemplateCRUD` | `tests/integration/test_email_routes.py` |
| TC-1415–1417 | `TestEmailTemplates` | `tests/integration/test_email_routes.py` |
| TC-1420–1424 | `TestEmailOverview`, `TestEmailOutbox`, `TestEmailDeliveryAttempts` | `tests/integration/test_email_routes.py` |
| TC-1430–1432 | `TestEmailSettings`, `TestMessageCreation` | `tests/integration/test_email_routes.py`, `tests/unit/utils/test_email_utils.py` |
| TC-1440–1444 | `TestSafetyGates` | `tests/unit/utils/test_email_utils.py` |
| TC-1450–1456 | `TestEmailValidation`, `TestTemplateRendering`, `TestEmailQualityAssurance` | `tests/unit/utils/test_email_utils.py`, `tests/integration/test_email_routes.py` |
| TC-1460–1463 | `TestEmailRealSending`, `TestEnvironmentFunctions` | `tests/integration/test_email_routes.py`, `tests/unit/utils/test_email_utils.py` |
| TC-1470–1475 | `TestComposeEmail` | `tests/integration/test_email_routes.py` |

---

*Last updated: February 2026*
*Version: 1.1*
