# In-Person Event Requirements

**Salesforce + VolunTeach + Website**

> [!NOTE]
> **System Locations**
> - **Salesforce**: [prep-kc.my.salesforce.com](https://prep-kc.my.salesforce.com/) — Core CRM for data entry and event management
> - **VolunTeach**: [voluntold-prepkc.pythonanywhere.com](https://voluntold-prepkc.pythonanywhere.com/dashboard) — Admin interface for sync controls
> - **Public Website**: [prepkc.org/volunteer.html](https://prepkc.org/volunteer.html) — Volunteer hub with signup pages

---

## Core Event Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-inperson-101"></a>**FR-INPERSON-101** | Staff shall create and maintain in-person event records in Salesforce. | [TC-100](test-pack-2#tc-100) | [US-101](user-stories#us-101) |
| <a id="fr-inperson-102"></a>**FR-INPERSON-102** | VolunTeach shall sync in-person events from Salesforce at least once per hour via automated scheduled sync. The system also supports scheduled daily batch imports that process events, volunteer participations, and student participations. | [TC-101](test-pack-2#tc-101), [TC-103](test-pack-2#tc-103) | [US-102](user-stories#us-102) |
| <a id="fr-inperson-103"></a>**FR-INPERSON-103** | VolunTeach shall provide a manual "sync now" action for immediate synchronization. Manual sync operations shall support large datasets with configurable batch sizes and progress indicators. | [TC-100](test-pack-2#tc-100), [TC-102](test-pack-2#tc-102) | [US-102](user-stories#us-102) |
| <a id="fr-inperson-104"></a>**FR-INPERSON-104** | VolunTeach shall allow staff to control whether an event appears on the public in-person events page via a visibility toggle. | [TC-110](test-pack-2#tc-110), [TC-111](test-pack-2#tc-111) | [US-103](user-stories#us-103) |
| <a id="fr-inperson-105"></a>**FR-INPERSON-105** | The system shall support events that are not displayed on the public in-person page (e.g., orientations). | [TC-112](test-pack-2#tc-112) | [US-103](user-stories#us-103) |
| <a id="fr-inperson-106"></a>**FR-INPERSON-106** | The website shall display for each event at minimum: volunteer slots needed, slots filled, date/time, district (if linked), and event description/type. | [TC-120](test-pack-2#tc-120), [TC-121](test-pack-2#tc-121) | [US-105](user-stories#us-105) |
| <a id="fr-inperson-107"></a>**FR-INPERSON-107** | VolunTeach shall allow staff to link events to one or more districts for district-specific website pages. | [TC-113](test-pack-2#tc-113), [TC-114](test-pack-2#tc-114) | [US-104](user-stories#us-104) |
| <a id="fr-inperson-109"></a>**FR-INPERSON-109** | Any event linked to a district shall appear on that district's website page regardless of the in-person-page visibility toggle. | [TC-113](test-pack-2#tc-113), [TC-115](test-pack-2#tc-115) | [US-104](user-stories#us-104) |
| <a id="fr-inperson-128"></a>**FR-INPERSON-128** | The system shall automatically display Data in Action (DIA) events on the website regardless of visibility toggle, provided they have a future start date and available slots. | Context only | [US-103](user-stories#us-103) |

---

## Reporting Integration

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-inperson-132"></a>**FR-INPERSON-132** | Event sync operations shall trigger cache invalidation for reports that depend on event data. | [TC-221](test-pack-2#tc-221) | *Technical* |
| <a id="fr-inperson-133"></a>**FR-INPERSON-133** | Manual cache refresh for event-based reports shall be available when automated sync is insufficient for large datasets. | [TC-222](test-pack-2#tc-222) | *Technical* |

---

## Public Volunteer Signup

> [!NOTE]
> **System Location**
> - **Volunteer Hub**: [prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)
> - **DIA Events**: [prepkc.org/dia.html](https://prepkc.org/dia.html)

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-signup-121"></a>**FR-SIGNUP-121** | The website shall allow volunteers to sign up for an event via a public form (Form Assembly integration) without authentication. | TC-130–TC-140 | [US-201](user-stories#us-201) |
| <a id="fr-signup-122"></a>**FR-SIGNUP-122** | Each signup shall create a participation record (in Salesforce) associated with the event and the volunteer identity. | TC-140, TC-142 | [US-201](user-stories#us-201) |
| <a id="fr-signup-123"></a>**FR-SIGNUP-123** | The system (Salesforce) shall send a confirmation email upon successful signup. | TC-150 | [US-203](user-stories#us-203) |
| <a id="fr-signup-124"></a>**FR-SIGNUP-124** | The system (Salesforce) shall send a calendar invite upon successful signup. | TC-151 | [US-203](user-stories#us-203) |
| <a id="fr-signup-125"></a>**FR-SIGNUP-125** | The calendar invite shall include event details and location/map information derived from the Salesforce event record. | TC-152 | [US-203](user-stories#us-203) |
| <a id="fr-signup-126"></a>**FR-SIGNUP-126** | The signup form (Form Assembly) shall collect: First Name, Last Name, Email, Organization, Title, Volunteer Skills, Age Group, Education, Gender, Race/Ethnicity. | TC-130–TC-132 | [US-202](user-stories#us-202) |
| <a id="fr-signup-127"></a>**FR-SIGNUP-127** | The system shall store the submitted signup attributes for use in reporting, recruitment search, and volunteer profiles. | TC-141 | [US-201](user-stories#us-201), [US-202](user-stories#us-202) |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [Test Pack 2](test-pack-2) — In-person event test cases

---

*Last updated: February 2026 · Version 1.0*
