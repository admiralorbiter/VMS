---
title: "Test Pack 6: Reporting Dashboards"
subtitle: Exports + ad hoc queries + access control
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-401–406 (Dashboards + exports), FR-521–522 (RBAC)</div>
</div>
<h2>Test Data: Leaderboards</h2>
<div class="table-wrapper">
<table>
<thead>
<tr><th>Volunteer</th><th>Events</th><th>Hours</th></tr>
</thead>
<tbody>
<tr><td>V1 Victor</td><td>4</td><td>10</td></tr>
<tr><td>V7 Jordan</td><td>2</td><td>8</td></tr>
<tr><td>V6 Casey</td><td>3</td><td>6</td></tr>
<tr><td>V2 Ella</td><td>2</td><td>3</td></tr>
<tr><td>V3 Sam</td><td>1</td><td>1</td></tr>
</tbody>
</table>
</div>
<h2>Test Cases</h2>
<h3>A. Volunteer Thank-You Dashboard</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-700</td><td>Leaderboard by hours</td><td>Victor > Jordan > Casey > Ella > Sam</td></tr>
<tr><td>TC-701</td><td>Leaderboard by events</td><td>Ranked by event count</td></tr>
<tr><td>TC-702</td><td>Tie handling</td><td>Consistent tie-breaker</td></tr>
<tr><td>TC-703</td><td>Time range filter</td><td>Rankings update</td></tr>
</tbody>
</table>
</div>
<p><h3>B. Organization Dashboard</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-720</td><td>Org totals</td><td>TechCorp highest</td></tr>
<tr><td>TC-721</td><td>Unique org count</td><td>Correct count</td></tr>
<tr><td>TC-722</td><td>Org drilldown</td><td>Lists volunteers correctly</td></tr>
</tbody>
</table>
</div>
<h3>C. District Impact Dashboard</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-740</td><td>Required metrics shown</td><td>Students, volunteers, hours, orgs</td></tr>
<tr><td>TC-741</td><td>Metrics match data</td><td>Numbers match fixtures</td></tr>
<tr><td>TC-742</td><td>School drilldown</td><td>School totals correct</td></tr>
<tr><td>TC-743</td><td>Event type filter</td><td>In-person only works</td></tr>
</tbody>
</table>
</div>
<h3>D. Exports</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-780</td><td>Export volunteer report</td><td>CSV matches UI</td></tr>
<tr><td>TC-781</td><td>Export org report</td><td>CSV matches UI</td></tr>
<tr><td>TC-782</td><td>Export district report</td><td>Filters respected</td></tr>
<tr><td>TC-783</td><td>CSV formatting</td><td>Proper headers, no corruption</td></tr>
</tbody>
</table>
</div>
<p><h3>E. Access Control</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-800</td><td>District Viewer → district dashboards</td><td>Access allowed, scoped</td></tr>
<tr><td>TC-801</td><td>District Viewer → global dashboards</td><td>Denied or restricted</td></tr>
<tr><td>TC-802</td><td>District Viewer → restricted export</td><td>Blocked or scoped</td></tr>
<tr><td>TC-803</td><td>No student PII in reports</td><td>Aggregates only</td></tr>
</tbody>
</table>
</div>
<h3>F. Reliability</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-820</td><td>Report failure visible</td><td>Clear error, not partial</td></tr>
<tr><td>TC-821</td><td>Export failure visible</td><td>No silent empty file</td></tr>
<tr><td>TC-822</td><td>Export audit logged</td><td>User, report, timestamp recorded</td></tr>
</tbody>
</table>
</div>
