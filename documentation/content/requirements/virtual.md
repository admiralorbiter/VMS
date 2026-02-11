# Virtual Event Requirements

**Polaris + Pathful**

---

## Core Virtual Event Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-virtual-201"></a>**FR-VIRTUAL-201** | Polaris shall allow staff to create and maintain virtual event records. | [TC-200](test-pack-3#tc-200), [TC-201](test-pack-3#tc-201) | [US-301](user-stories#us-301) |
| <a id="fr-virtual-202"></a>**FR-VIRTUAL-202** | Polaris shall allow staff to search for and tag teachers using locally synced Salesforce-linked teacher records. | [TC-202](test-pack-3#tc-202), [TC-204](test-pack-3#tc-204) | [US-302](user-stories#us-302) |
| <a id="fr-virtual-203"></a>**FR-VIRTUAL-203** | Polaris shall allow staff to search for and tag presenters/volunteers using locally synced Salesforce-linked records. | [TC-203](test-pack-3#tc-203), [TC-204](test-pack-3#tc-204) | [US-303](user-stories#us-303) |
| <a id="fr-virtual-204"></a>**FR-VIRTUAL-204** | The system shall support importing 2–4 years of historical virtual event data from Google Sheets, preserving event–teacher relationships. *(Implemented via Pathful direct import per US-304)* | TC-270–TC-275 | [US-306](user-stories#us-306) |
| <a id="fr-virtual-206"></a>**FR-VIRTUAL-206** | Polaris shall ingest Pathful export data to update virtual attendance and participation tracking, triggering post-import data quality checks. | TC-250–TC-260 | [US-304](user-stories#us-304) |
| <a id="fr-virtual-207"></a>**FR-VIRTUAL-207** | The system should support automation to pull Pathful exports and load them into Polaris. | TC-280 | *Near-term* |
| <a id="fr-virtual-208"></a>**FR-VIRTUAL-208** | The system shall track whether a virtual volunteer is local vs non-local. | TC-230–TC-232 | [US-305](user-stories#us-305) |
| <a id="fr-virtual-209"></a>**FR-VIRTUAL-209** | The system should support sending automated communications that connect local volunteers. | TC-281 | *Near-term* |
| <a id="fr-virtual-220"></a>**FR-VIRTUAL-220** | The system shall support importing historical virtual event data from Salesforce (2–4 years). | [TC-210](test-pack-2#tc-210) | *Technical* |
| <a id="fr-virtual-221"></a>**FR-VIRTUAL-221** | Historical virtual import shall preserve event-participant relationships and maintain data integrity. | [TC-211](test-pack-2#tc-211) | *Technical* |
| <a id="fr-virtual-222"></a>**FR-VIRTUAL-222** | The system shall allow creation of new teacher records locally in Polaris during virtual session creation if not found in search. | [TC-206](test-pack-3#tc-206) | [US-308](user-stories#us-308) |
| <a id="fr-virtual-223"></a>**FR-VIRTUAL-223** | The system shall allow creation of new presenter/volunteer records locally in Polaris during virtual session creation if not found in search. | [TC-207](test-pack-3#tc-207) | [US-309](user-stories#us-309) |

---

## Presenter Recruitment View

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-virtual-210"></a>**FR-VIRTUAL-210** | Polaris shall provide a view listing upcoming virtual events that do not have a presenter assigned. | TC-290–TC-299 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-211"></a>**FR-VIRTUAL-211** | The presenter recruitment view shall filter to show only future events (start_datetime > current date/time). | TC-291 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-212"></a>**FR-VIRTUAL-212** | The presenter recruitment view shall support filtering by date range, school, district, and event type. | TC-292–TC-295 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-213"></a>**FR-VIRTUAL-213** | The presenter recruitment view shall display for each event: title, date/time, school/district, teacher count, and days until event. | TC-298 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-214"></a>**FR-VIRTUAL-214** | Staff shall be able to navigate directly from a presenter-needed event to the volunteer search/recruitment workflow. | TC-299 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-215"></a>**FR-VIRTUAL-215** | Once a presenter is tagged to an event, that event shall no longer appear in the presenter recruitment view. | TC-296, TC-297 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-216"></a>**FR-VIRTUAL-216** | The presenter recruitment view shall support filtering by academic year (Aug 1 – Jul 31 cycle). | TC-292 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-217"></a>**FR-VIRTUAL-217** | The presenter recruitment view shall display urgency indicators: red (≤7 days), yellow (8-14 days), blue (>14 days). | TC-298 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-218"></a>**FR-VIRTUAL-218** | The presenter recruitment view shall support text search across event title and teacher names. | TC-292 | [US-307](user-stories#us-307) |
| <a id="fr-virtual-219"></a>**FR-VIRTUAL-219** | The presenter recruitment view shall display a success message when all upcoming virtual sessions have presenters assigned. | Context only | [US-307](user-stories#us-307) |

---

## Post-Import Data Management (Phase D)

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-virtual-224"></a>**FR-VIRTUAL-224** | The system shall automatically flag imported virtual events that have status=Draft and session_date < current date. | [TC-285](test-pack-3#tc-285) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-225"></a>**FR-VIRTUAL-225** | The system shall automatically flag imported virtual events that have no teacher tagged. | [TC-286](test-pack-3#tc-286) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-226"></a>**FR-VIRTUAL-226** | The system shall automatically flag completed virtual events that have no presenter assigned. | [TC-287](test-pack-3#tc-287) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-227"></a>**FR-VIRTUAL-227** | The system shall support recording cancellation reasons for cancelled virtual sessions using predefined codes (Weather, Presenter Cancelled, Teacher Cancelled, School Conflict, Technical Issues, Low Enrollment, Scheduling Error, Other). | [TC-288](test-pack-3#tc-288), [TC-289](test-pack-3#tc-289) | [US-311](user-stories#us-311) |
| <a id="fr-virtual-228"></a>**FR-VIRTUAL-228** | The system shall automatically flag cancelled virtual events that do not have a cancellation reason set. | [TC-290](test-pack-3#tc-290) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-229"></a>**FR-VIRTUAL-229** | District administrators shall be able to view virtual events scoped to schools within their district(s). | [TC-291](test-pack-3#tc-291) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-230"></a>**FR-VIRTUAL-230** | District administrators shall be able to tag/untag teachers and presenters on virtual events within their district scope. | [TC-292](test-pack-3#tc-292), [TC-293](test-pack-3#tc-293) | [US-310](user-stories#us-310) |
| <a id="fr-virtual-231"></a>**FR-VIRTUAL-231** | District administrators shall be able to set cancellation reasons on virtual events within their district scope. | [TC-294](test-pack-3#tc-294) | [US-311](user-stories#us-311) |
| <a id="fr-virtual-232"></a>**FR-VIRTUAL-232** | The system shall log all changes to virtual event data including: user identity, user role, timestamp, action type, field changed, old value, and new value. | [TC-295](test-pack-3#tc-295) | [US-312](user-stories#us-312) |
| <a id="fr-virtual-233"></a>**FR-VIRTUAL-233** | Staff shall be able to view audit logs for virtual events filtered by event, user, district, or date range. | [TC-296](test-pack-3#tc-296), [TC-297](test-pack-3#tc-297) | [US-312](user-stories#us-312) |

---

## Attendance Override Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-virtual-234"></a>**FR-VIRTUAL-234** | The system shall allow virtual admins to add a teacher from the TeacherProgress roster to a completed virtual session as an attendance override. | *TBD* | [US-313](user-stories#us-313) |
| <a id="fr-virtual-235"></a>**FR-VIRTUAL-235** | The system shall require a reason/note when creating or removing an attendance override. | *TBD* | [US-313](user-stories#us-313), [US-314](user-stories#us-314) |
| <a id="fr-virtual-236"></a>**FR-VIRTUAL-236** | Attendance overrides shall be stored separately from original import/match data so that the original data is preserved and rollback is possible. | *TBD* | [US-313](user-stories#us-313), [US-314](user-stories#us-314) |
| <a id="fr-virtual-237"></a>**FR-VIRTUAL-237** | The system shall allow virtual admins to remove an attendance override or original attendance credit for a teacher on a session. | *TBD* | [US-314](user-stories#us-314) |
| <a id="fr-virtual-238"></a>**FR-VIRTUAL-238** | Attendance overrides shall immediately affect teacher progress calculations (session counts and goal status). | *TBD* | [US-313](user-stories#us-313), [US-314](user-stories#us-314) |
| <a id="fr-virtual-239"></a>**FR-VIRTUAL-239** | Attendance overrides shall be scoped to the admin's tenant district — admins cannot override attendance for sessions outside their tenant scope. | *TBD* | [US-313](user-stories#us-313), [US-314](user-stories#us-314) |
| <a id="fr-virtual-240"></a>**FR-VIRTUAL-240** | The system shall display attendance overrides distinctly from original attendance in the teacher detail view (e.g., badge or icon indicating admin override). | *TBD* | [US-313](user-stories#us-313) |
| <a id="fr-virtual-241"></a>**FR-VIRTUAL-241** | The system shall log all attendance overrides with: admin identity, admin role, timestamp, teacher, session, action type (add/remove), and reason. | *TBD* | [US-315](user-stories#us-315) |
| <a id="fr-virtual-242"></a>**FR-VIRTUAL-242** | Staff shall be able to view attendance override audit logs filtered by admin, teacher, session, date range, or tenant. | *TBD* | [US-315](user-stories#us-315) |
| <a id="fr-virtual-243"></a>**FR-VIRTUAL-243** | Staff shall be able to reverse an attendance override, restoring the original attendance state. | *TBD* | [US-315](user-stories#us-315) |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [Test Pack 3](test-pack-3) — Virtual event test cases

---

*Last updated: February 2026 · Version 1.1*
