---
title: "Test Pack 4: Volunteer Recruitment"
subtitle: Search + communication history + sync health
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-301–306 (Search + history), FR-308–309 (Comm sync + health UX)</div>
</div>
<h2>Test Data: Volunteer Set</h2>
<div class="table-wrapper">
<table>
<thead>
<tr><th>ID</th><th>Name</th><th>Org</th><th>Career</th><th>Local</th><th>Participation</th><th>Comms</th></tr>
</thead>
<tbody>
<tr><td>V1</td><td>Victor Cyber</td><td>TechCorp</td><td>Technology</td><td>Yes</td><td>In-person + Virtual</td><td>Yes</td></tr>
<tr><td>V2</td><td>Ella Data</td><td>TechCorp</td><td>Technology</td><td>No</td><td>Virtual-only</td><td>Yes</td></tr>
<tr><td>V3</td><td>Sam Teacher</td><td>EduOrg</td><td>Education</td><td>Yes</td><td>In-person only</td><td>No</td></tr>
<tr><td>V4</td><td>Riley HR</td><td>PeopleCo</td><td>Business</td><td>Yes</td><td>None</td><td>Yes</td></tr>
</tbody>
</table>
</div>
<h2>Test Cases</h2>
<h3>A. Volunteer Search</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-300</td><td>Name search "Vict"</td><td>Returns V1 only</td></tr>
<tr><td>TC-301</td><td>Org filter: TechCorp</td><td>Returns V1, V2</td></tr>
<tr><td>TC-302</td><td>Skill filter</td><td>Returns matching volunteers</td></tr>
<tr><td>TC-303</td><td>Career type: Education</td><td>Returns V3</td></tr>
<tr><td>TC-304</td><td>Local filter</td><td>Returns V1, V3, V4</td></tr>
<tr><td>TC-305</td><td>Combined filters</td><td>Intersection works</td></tr>
</tbody>
</table>
</div>
<h3>B. Virtual-Only</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-320</td><td>Virtual-only filter</td><td>Returns V2 only</td></tr>
<tr><td>TC-321</td><td>Excludes mixed</td><td>V1 not included</td></tr>
<tr><td>TC-322</td><td>Excludes in-person only</td><td>V3 not included</td></tr>
</tbody>
</table>
</div>
<h3>C. Communication History</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-360</td><td>Comm history displays</td><td>V1 shows logged emails</td></tr>
<tr><td>TC-361</td><td>Last contacted correct</td><td>Matches most recent email</td></tr>
<tr><td>TC-362</td><td>Correct association</td><td>V2’s email on V2, not V1</td></tr>
<tr><td>TC-363</td><td>No comms state</td><td>V3 shows "No history logged"</td></tr>
<tr><td>TC-364</td><td>Sync failure state</td><td>Shows error, not "no comms"</td></tr>
<tr><td>TC-365</td><td>Idempotency</td><td>Re-sync = no duplicates</td></tr>
</tbody>
</table>
</div>
