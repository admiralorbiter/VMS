---
title: "Test Pack 3: Virtual Events"
subtitle: Polaris creation + Pathful import + historical data
---

<hr>
<div class="callout callout-info">
<div class="callout-title">Coverage</div>
<div>FR-201–206 (Virtual events), FR-208 (Local/non-local), FR-204 (Historical import), FR-210–219 (Presenter recruitment)</div>
</div>
<h2>Test Data</h2>
<ul>
<li><strong>VE1 Virtual Career Talk</strong> — Future date</li>
<li><strong>VE2 Virtual Panel</strong> — Future date</li>
<li><strong>P1 Local Presenter</strong> — local=true</li>
<li><strong>P2 NonLocal Presenter</strong> — local=false</li>
</ul>
<h2>Test Cases</h2>
<h3>A. Virtual Event Creation</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-200</td><td>Create event</td><td>Persists and reloads</td></tr>
<tr><td>TC-201</td><td>Edit event</td><td>Changes persist</td></tr>
<tr><td>TC-202</td><td>Tag teacher (SF search)</td><td>Link persists after save</td></tr>
<tr><td>TC-203</td><td>Tag presenter</td><td>Link persists</td></tr>
<tr><td>TC-204</td><td>Multi-teacher/presenter</td><td>All relationships preserved</td></tr>
<tr><td>TC-205</td><td>SF search failure</td><td>Clear error shown</td></tr>
</tbody>
</table>
</div>
<h3>B. Local/Non-Local</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-230</td><td>Flag persists</td><td>P1=local, P2=non-local displayed</td></tr>
<tr><td>TC-231</td><td>Filter by local</td><td>P1 appears, P2 doesn’t</td></tr>
<tr><td>TC-232</td><td>Unknown flag handling</td><td>Displays "unknown", no crash</td></tr>
</tbody>
</table>
</div>
<h3>C. Pathful Import</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-250</td><td>Upcoming signup</td><td>Teacher becomes In Progress</td></tr>
<tr><td>TC-251</td><td>Completed attendance</td><td>Teacher becomes Achieved</td></tr>
<tr><td>TC-252</td><td>Idempotency</td><td>Re-import = no duplicates</td></tr>
<tr><td>TC-253</td><td>Duplicate rows in file</td><td>Deduplicated</td></tr>
<tr><td>TC-254</td><td>Status update</td><td>Upcoming → completed works</td></tr>
<tr><td>TC-255</td><td>Missing columns</td><td>Clear failure message</td></tr>
<tr><td>TC-256</td><td>Column rename</td><td>Alias mapping or clear error</td></tr>
<tr><td>TC-257</td><td>Unknown teacher</td><td>Row flagged unmatched</td></tr>
<tr><td>TC-258</td><td>Unknown event</td><td>Row flagged</td></tr>
</tbody>
</table>
</div>
<h3>D. Historical Google Sheets</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-270</td><td>Multi-line → one event</td><td>No duplicate events</td></tr>
<tr><td>TC-271</td><td>Teacher relationships</td><td>All teachers linked</td></tr>
<tr><td>TC-272</td><td>Presenter relationships</td><td>All presenters linked</td></tr>
<tr><td>TC-273</td><td>Idempotency</td><td>Double import = no duplicates</td></tr>
</tbody>
</table>
</div>
<h3>E. Presenter Recruitment View</h3>
<div class="table-wrapper">
<table>
<thead>
<tr><th>TC</th><th>Description</th><th>Expected</th></tr>
</thead>
<tbody>
<tr><td>TC-290</td><td>View shows only unpresented events</td><td>Events with no presenter appear; events with presenters excluded</td></tr>
<tr><td>TC-291</td><td>Future events only</td><td>Past events excluded regardless of presenter status</td></tr>
<tr><td>TC-292</td><td>Date range filter</td><td>Results match selected date range</td></tr>
<tr><td>TC-293</td><td>School filter</td><td>Results match selected school</td></tr>
<tr><td>TC-294</td><td>District filter</td><td>Results match selected district</td></tr>
<tr><td>TC-295</td><td>Multiple filters</td><td>Results match intersection of all applied filters</td></tr>
<tr><td>TC-296</td><td>Event disappears on presenter tag</td><td>Tag presenter → event removed from view immediately</td></tr>
<tr><td>TC-297</td><td>Presenter removed → event reappears</td><td>Remove last presenter → event returns to view</td></tr>
<tr><td>TC-298</td><td>Display required fields</td><td>Shows title, date/time, school/district, teacher count, days-until</td></tr>
<tr><td>TC-299</td><td>Navigate to volunteer search</td><td>Link/button opens volunteer recruitment correctly</td></tr>
<tr><td>TC-300</td><td>Academic year filter</td><td>Only events within selected academic year (Aug 1–Jul 31) displayed</td></tr>
<tr><td>TC-301</td><td>Text search</td><td>Search across event title and teacher names returns matches</td></tr>
<tr><td>TC-302</td><td>Urgency indicators</td><td>Red (≤7 days), Yellow (8-14 days), Blue (>14 days) badges display correctly</td></tr>
<tr><td>TC-303</td><td>Access control — global user</td><td>User with scope_type='global' can access view</td></tr>
<tr><td>TC-304</td><td>Access control — district user</td><td>District-scoped user receives access denied, redirected to usage report</td></tr>
<tr><td>TC-305</td><td>Access control — admin</td><td>Admin user (any scope) can access view</td></tr>
<tr><td>TC-306</td><td>Empty state</td><td>When all events have presenters, shows success message</td></tr>
<tr><td>TC-307</td><td>Sort order</td><td>Events sorted by start_date ASC (earliest/most urgent first)</td></tr>
<tr><td>TC-308</td><td>Reset filters</td><td>Reset button clears all filters and returns to defaults</td></tr>
</tbody>
</table>
</div>
<p><strong>Test Data:</strong></p>
<ul>
<li><strong>VE3</strong> — Future virtual event, no presenter, 5 days away (red badge)</li>
<li><strong>VE4</strong> — Future virtual event with presenter (P1)</li>
<li><strong>VE5</strong> — Past virtual event, no presenter</li>
<li><strong>VE6</strong> — Future virtual event, no presenter, 10 days away (yellow badge)</li>
<li><strong>VE7</strong> — Future virtual event, no presenter, 20 days away (blue badge)</li>
<li><strong>User-Global</strong> — Regular user with <code>scope_type='global'</code></li>
<li><strong>User-District</strong> — Regular user with <code>scope_type='district'</code></li>
</ul>
