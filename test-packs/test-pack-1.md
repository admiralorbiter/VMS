---
title: "Test Pack 1: District Progress Dashboard"
subtitle: Teacher magic links + progress status validation
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-501–503 (Dashboard), FR-508 (Status definitions), FR-505–507 (Magic links), FR-521–524 (RBAC/Scoping)</div>
</div>
<h2>Test Data Setup</h2>
<p><strong>District: KCK</strong></p>
<ul>
<li>School A, School B</li>
</ul>
<h4>Teacher Roster</h4>
<div class="table-wrapper">
<table>
<thead>
<tr><th>Teacher</th><th>Email</th><th>School</th><th>Expected Status</th></tr>
</thead>
<tbody>
<tr><td>Alice Achieved</td><td>alice@kck.edu</td><td>A</td><td><strong>Achieved</strong> (≥1 completed)</td></tr>
<tr><td>Ian InProgress</td><td>ian@kck.edu</td><td>A</td><td><strong>In Progress</strong> (future signup, 0 completed)</td></tr>
<tr><td>Nora NotStarted</td><td>nora@kck.edu</td><td>B</td><td><strong>Not Started</strong> (no signups)</td></tr>
<tr><td>Evan Edgecase</td><td>evan@kck.edu</td><td>B</td><td><strong>Achieved</strong> (completed + future = still Achieved)</td></tr>
</tbody>
</table>
</div>
<h2>Test Cases</h2>
<h3>Auth / Access Control</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-001</td><td>District Viewer login</td><td>Dashboard loads for own district</td></tr>
<tr><td>TC-002</td><td>District scoping via URL tampering</td><td>Access denied to other districts</td></tr>
<tr><td>TC-003</td><td>Magic link scoping</td><td>Cannot view other teachers via URL change</td></tr>
</tbody>
</table>
</div>
<h3>Dashboard Summary + Status Math</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-010</td><td>Summary counts</td><td>Schools=2, Teachers=4, Achieved=2, In Progress=1, Not Started=1</td></tr>
<tr><td>TC-011</td><td>School A drilldown</td><td>Shows Alice + Ian only</td></tr>
<tr><td>TC-012</td><td>Status labels correct</td><td>Alice=Achieved, Ian=In Progress</td></tr>
<tr><td>TC-013</td><td>Edgecase: completed + future</td><td>Evan=Achieved (precedence rule)</td></tr>
<tr><td>TC-014</td><td>Not Started definition</td><td>Nora=Not Started</td></tr>
</tbody>
</table>
</div>
<h3>Teacher Magic Link</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-020</td><td>Request for roster teacher</td><td>Email received with link</td></tr>
<tr><td>TC-021</td><td>Request for unknown email</td><td>Generic response (no roster leak)</td></tr>
<tr><td>TC-022</td><td>Link shows correct data</td><td>Alice sees Achieved status</td></tr>
<tr><td>TC-023</td><td>Flag submission</td><td>Flag stored, visible to staff</td></tr>
<tr><td>TC-024</td><td>Single-teacher scope</td><td>URL tampering fails</td></tr>
</tbody>
</table>
</div>
<h3>Roster Import</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-030</td><td>New teacher appears</td><td>Count increases, shows Not Started</td></tr>
<tr><td>TC-031</td><td>Removed teacher behavior</td><td>Consistent with chosen policy</td></tr>
</tbody>
</table>
</div>
