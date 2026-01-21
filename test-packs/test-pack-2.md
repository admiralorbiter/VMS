---
title: "Test Pack 2: In-Person Event Publish"
subtitle: SF sync + website signup + email/calendar
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-101–109 (Events + visibility), FR-121–127 (Signup + email)</div>
</div>
<h2>Test Data</h2>
<ul>
<li><strong>E1_Public</strong> — Full location, 5 slots</li>
<li><strong>E2_HiddenOrientation</strong> — "Do not publish" type, 20 slots</li>
<li><strong>E3_DistrictOnly</strong> — For KCK district page only</li>
</ul>
<h2>Test Cases</h2>
<h3>A. SF → VT Sync</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-100</td><td>Manual sync</td><td>Event appears with correct fields</td></tr>
<tr><td>TC-101</td><td>Hourly sync</td><td>New event appears within cycle</td></tr>
<tr><td>TC-102</td><td>Idempotency</td><td>No duplicates on double sync</td></tr>
<tr><td>TC-103</td><td>Update propagates</td><td>Changed slots reflected in VT</td></tr>
<tr><td>TC-104</td><td>Failure detection</td><td>Error visible, not silent</td></tr>
</tbody>
</table>
</div>
<h3>B. Publish Controls + District Linking</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-110</td><td>Toggle ON → public page</td><td>E1 visible</td></tr>
<tr><td>TC-111</td><td>Toggle OFF → hidden</td><td>E1 not on public page</td></tr>
<tr><td>TC-112</td><td>Hidden orientation</td><td>E2 not on public page</td></tr>
<tr><td>TC-113</td><td>District link (toggle OFF)</td><td>E3 visible on KCK page</td></tr>
<tr><td>TC-114</td><td>No cross-district leak</td><td>E3 not on other district pages</td></tr>
<tr><td>TC-115</td><td>Unlink removes</td><td>E3 gone from KCK page</td></tr>
</tbody>
</table>
</div>
<h3>C. Signup Validation</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-130</td><td>Required fields</td><td>Blocked with clear error</td></tr>
<tr><td>TC-131</td><td>Email format</td><td>Invalid rejected</td></tr>
<tr><td>TC-132</td><td>Dropdown validation</td><td>Tampered values rejected</td></tr>
<tr><td>TC-133</td><td>Data sanitized</td><td>Whitespace trimmed, no XSS</td></tr>
</tbody>
</table>
</div>
<h3>D. Persistence + Email</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-140</td><td>Participation created</td><td>Record exists, linked correctly</td></tr>
<tr><td>TC-141</td><td>Values match form</td><td>All fields persisted</td></tr>
<tr><td>TC-150</td><td>Confirmation email</td><td>Received with event details</td></tr>
<tr><td>TC-151</td><td>Calendar invite</td><td>Received</td></tr>
<tr><td>TC-152</td><td>Invite has location</td><td>SF location in invite</td></tr>
</tbody>
</table>
</div>
