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

1. Confirm `.env` is up to date
2. Run: `python manage_imports.py --sequential`
3. Watch logs: `tail -f logs/import.log`
4. On failure:
   - Check traceback
   - Rerun with `--only` option
   - File bug report

