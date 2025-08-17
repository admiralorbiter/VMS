---
title: "Project Checklists and Templates"
description: "PR checklist, feature spec template, and runbooks"
tags: [checklists, templates]
---

## Pull Request Checklist

- [ ] Linked to issue
- [ ] Relevant docs updated
- [ ] Tests pass
- [ ] Lint passes
- [ ] Clear explanation

## Feature Spec Template

```markdown
# <Feature Name>

## Problem
...

## Acceptance Criteria
- [ ] ...

## Users
- As a [user], I want to ...

## Edge Cases
...

## Out of Scope
...

## Questions
...
```

## Data Import Runbook

1. Confirm `.env` is up to date and app is running (e.g., `flask run` or `python app.py`)
2. Install CLI dependency: `pip install requests` (one-time)
3. Full import: `python manage_imports.py --sequential --base-url http://localhost:5050 --username <admin> --password <pwd>`
4. Dry run (no changes): `python manage_imports.py --sequential --plan-only`
5. Skip heavy steps: `python manage_imports.py --sequential --exclude schools,classes,students`
   - Note: the CLI sequence now ends with `pathway_events_sync` (calls `/pathway-events/sync-unaffiliated-events`).
6. Fast student smoke test (one chunk): `python manage_imports.py --only students --students-max-chunks 1`
7. Long-running endpoints: increase read timeout, or disable timeout entirely
   - Example (20 min read timeout): `python manage_imports.py --sequential --read-timeout 1200`
   - Example (no timeout): `python manage_imports.py --sequential --timeout 0`
8. Watch logs: `tail -f logs/import.log`
9. On failure:
   - Check last error in log
   - Rerun with `--only students` (or another step) to continue
   - File bug report
