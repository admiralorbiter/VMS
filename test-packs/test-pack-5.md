---
title: "Test Pack 5: Student Attendance"
subtitle: Roster + attendance + impact metrics
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-601–604 (Student roster + attendance + metrics)</div>
</div>
<h2>Test Data</h2>
<p><strong>District:</strong> KCK (School A, School B)</p>
<h4>Students</h4>
<ul>
<li>S1, S2, S3 — School A</li>
<li>S4, S5 — School B</li>
</ul>
<h4>Events + Attendance</h4>
<ul>
<li><strong>E1 (School A):</strong> S1=Attended, S2=Attended, S3=Absent</li>
<li><strong>E2 (School B):</strong> S2=Attended, S4=Attended, S5=Attended</li>
</ul>
<p><strong>Expected unique attended:</strong> S1, S2, S4, S5 = <strong>4</strong></p>
<h2>Test Cases</h2>
<h3>A. Roster Creation</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-600</td><td>Add students to E1</td><td>Roster entries created</td></tr>
<tr><td>TC-601</td><td>Add students to E2</td><td>Entries created</td></tr>
<tr><td>TC-602</td><td>Duplicate prevention</td><td>No double-counting</td></tr>
</tbody>
</table>
</div>
<h3>B. Attendance Recording</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-610</td><td>Record E1 attendance</td><td>Statuses saved</td></tr>
<tr><td>TC-611</td><td>Record E2 attendance</td><td>Statuses saved</td></tr>
<tr><td>TC-612</td><td>Edit propagates</td><td>S3 Absent→Attended updates metrics</td></tr>
</tbody>
</table>
</div>
<h3>C. Polaris Reporting</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-620</td><td>District unique students</td><td>=4 (attendance-based)</td></tr>
<tr><td>TC-621</td><td>School A breakdown</td><td>=2 (S1, S2)</td></tr>
<tr><td>TC-622</td><td>School B breakdown</td><td>=3 (S2, S4, S5)</td></tr>
<tr><td>TC-623</td><td>Multi-event student</td><td>S2 counted once at district level</td></tr>
<tr><td>TC-624</td><td>Edit affects metrics</td><td>Total becomes 5 after TC-612</td></tr>
</tbody>
</table>
</div>
<p><h3>D. Filters</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-640</td><td>Event type filter</td><td>In-person only works</td></tr>
<tr><td>TC-641</td><td>Date range filter</td><td>Excludes out-of-range events</td></tr>
<tr><td>TC-642</td><td>District filter</td><td>Only KCK events contribute</td></tr>
</tbody>
</table>
</div>
<h3>E. Privacy</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-690</td><td>District Viewer access</td><td>Aggregates only, no student PII</td></tr>
<tr><td>TC-691</td><td>Internal role access</td><td>Allowed per policy</td></tr>
</tbody>
</table>
</div>
