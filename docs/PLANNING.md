# 🧱 Foundation-to-Finish Planning Document

A roadmap to solidify core features, improve reliability, and build documentation useful to humans and AI.

---

## 0. Snapshot of Current State

| Area | Strengths | Gaps & Risks |
|------|-----------|--------------|
| **Feature coverage** | Strong event/org/volunteer reporting features implemented | Import automation and some modules unfinished (e.g. “Schools”, “Client Projects”) |
| **README** | Setup & stack described well | Missing architecture overview, data flow, contributor info |
| **Testing & CI** | `pytest` and coverage hooks exist | No lint/type CI; no coverage gate |
| **Data sync** | Salesforce + spreadsheet import partially implemented | Sequential import and error alerting not complete |
| **Documentation tooling** | Markdown already in use | No consistent structure, AI-readable cues, or doc site generation |

---

## 1. Documentation Layout

Create a new `/docs` folder and add these files:

```
/docs/
├── 01-overview.md
├── 02-architecture.md
├── 03-data-model.md
├── 04-api-spec.md
├── 05-dev-guide.md
├── 06-ops-guide.md
├── 07-test-guide.md
├── 08-release-notes/
├── 09-faq.md
├── FEATURE_MATRIX.md
└── templates/
```

**Bonus**: Add `.github/PULL_REQUEST_TEMPLATE.md` and `/checklists/`.

---

## 2. Step-by-Step Execution Plan

### 🟢 Phase A – Establish Baseline (Week 1)

- [x] Create `docs/` folder structure
- [x] Improve README:
  - Add architecture summary or Mermaid diagram
  - Add project purpose at top
- [ ] Setup pre-commit:
  - `black`, `isort`, `flake8`, `bandit`
- [ ] Add CI fail on test or lint failure
- [ ] Convert current feature list into `/docs/FEATURE_MATRIX.md`

### 🟢 Phase B – Harden Core Functionality (Weeks 2–3)

| Task | Why | Checklist |
|------|-----|-----------|
| Finish key “To Do” features | Stability | UX tested, tests added, doc updated |
| Single-click import process | Data consistency | CLI/Cron, logs, alerts |
| RBAC on destructive actions | Secure delete | Role checks, audit logs |

### 🟢 Phase C – Documentation Deep-Dive (Weeks 3–4)

- [ ] Write 3–5 ADRs (design decisions)
- [ ] Generate API docs (OpenAPI, Swagger)
- [ ] Create data dictionary (field names/types/enums)
- [ ] Add AI-readable YAML frontmatter to all docs:
  ```yaml
  ---
  title: "Volunteer Directory"
  description: "Search, edit, import volunteers"
  tags: [volunteer, ui, admin]
  ---
  ```

### 🟢 Phase D – Ops & QA (Week 5)

- [ ] Add `structlog` and request IDs
- [ ] Run `bandit` and secret scanners
- [ ] Document backup + restore in `06-ops-guide.md`
- [ ] Add load test (Locust or JMeter)

### 🟢 Phase E – Release Prep (Week 6)

- [ ] Lock scope for `v1.0.0`
- [ ] Write CHANGELOG (`08-release-notes/v1.0.0.md`)
- [ ] Record E2E usage demo
- [ ] Hold retrospective

---

## 3. Universal Checklists

### ✅ Pull Request Checklist

- [ ] Linked to issue  
- [ ] Relevant docs updated  
- [ ] Tests pass  
- [ ] Lint passes  
- [ ] Clear explanation  

### ✅ Feature Spec Template

\`\`\`markdown
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
\`\`\`

### ✅ Data Import Runbook

1. Confirm `.env` is up to date  
2. Run:
   \`\`\`bash
   python manage_imports.py --sequential
   \`\`\`
3. Watch logs:
   \`\`\`bash
   tail -f logs/import.log
   \`\`\`
4. On failure:
   - Check traceback
   - Rerun with `--only` option
   - File bug report

---

## 4. Tooling Suggestions

| Purpose | Tool |
|--------|------|
| Static site | `mkdocs-material` |
| Diagrams | `mermaid`, `plantuml`, `pyreverse` |
| AI PR reviews | GitHub Copilot Chat or `gh ai comment` |
| Semantic versioning | `commitizen`, `cz changelog` |

---

## 5. This Week’s Action Items

- [ ] Create `/docs/` layout and stub files
- [ ] Draft Mermaid system diagram
- [ ] Enable pre-commit and CI lint/test
- [ ] Assign owners for incomplete features in `FEATURE_MATRIX.md`
- [ ] Write first ADR: “Why SQLite with Salesforce Sync”

---

## 🎯 Outcome

By following this plan, you’ll:

✅ Complete unfinished key functionality  
✅ Provide AI-usable, human-readable documentation  
✅ Establish a safe, automated dev pipeline  
✅ Support new contributors and future integrations  
✅ Ship a 1.0 milestone with confidence