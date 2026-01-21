# Test Pack 2: In-Person Event Publish

SF sync + website signup + email/calendar

> [!INFO]
> **Coverage**
> [FR-101](requirements#fr-101)–[FR-109](requirements#fr-109) (Events + visibility), [FR-121](requirements#fr-121)–[FR-127](requirements#fr-127) (Signup + email)

---

## Test Data

- **E1_Public** — Full location, 5 slots
- **E2_HiddenOrientation** — "Do not publish" type, 20 slots
- **E3_DistrictOnly** — For KCK district page only

## Test Cases

### A. SF → VT Sync

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-100"></a>**TC-100** | Manual sync | Event appears with correct fields |
| <a id="tc-101"></a>**TC-101** | Hourly sync | New event appears within cycle |
| <a id="tc-102"></a>**TC-102** | Idempotency | No duplicates on double sync |
| <a id="tc-103"></a>**TC-103** | Update propagates | Changed slots reflected in VT |
| <a id="tc-104"></a>**TC-104** | Failure detection | Error visible, not silent |

### B. Publish Controls + District Linking

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-110"></a>**TC-110** | Toggle ON → public page | E1 visible |
| <a id="tc-111"></a>**TC-111** | Toggle OFF → hidden | E1 not on public page |
| <a id="tc-112"></a>**TC-112** | Hidden orientation | E2 not on public page |
| <a id="tc-113"></a>**TC-113** | District link (toggle OFF) | E3 visible on KCK page |
| <a id="tc-114"></a>**TC-114** | No cross-district leak | E3 not on other district pages |
| <a id="tc-115"></a>**TC-115** | Unlink removes | E3 gone from KCK page |

### C. Signup Validation

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-130"></a>**TC-130** | Required fields | Blocked with clear error |
| <a id="tc-131"></a>**TC-131** | Email format | Invalid rejected |
| <a id="tc-132"></a>**TC-132** | Dropdown validation | Tampered values rejected |
| <a id="tc-133"></a>**TC-133** | Data sanitized | Whitespace trimmed, no XSS |

### D. Persistence + Email

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-140"></a>**TC-140** | Participation created | Record exists, linked correctly |
| <a id="tc-141"></a>**TC-141** | Values match form | All fields persisted |
| <a id="tc-142"></a>**TC-142** | Duplicate prevention | No double signups |
| <a id="tc-150"></a>**TC-150** | Confirmation email | Received with event details |
| <a id="tc-151"></a>**TC-151** | Calendar invite | Received |
| <a id="tc-152"></a>**TC-152** | Invite has location | SF location in invite |

---

*Last updated: January 2026*
*Version: 1.0*
