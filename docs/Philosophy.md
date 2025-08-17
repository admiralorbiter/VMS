---
title: "Engineering & Documentation Philosophy"
status: active
doc_type: overview
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["docs-as-code","governance","ai","rag","adr"]
summary: "How we structure, maintain, and retrieve knowledge so humans stay clear and AI stays effective."
canonical: "/docs/living/Philosophy.md"
---

# Engineering & Documentation Philosophy

> Humans need clarity. AI can handle volume. We design so both thrive.

This document defines how we create, evolve, and retrieve knowledge with minimal friction. It favors a few **living sources of truth** for humans and a deep, well-labeled **archive** that AI can mine safely.

---

## TL;DR (Policy on One Page)

- Keep **10 living docs** (Overview, Roadmap, DecisionLog, Onboarding, Bugs, Features, Status, TechStack, Commands, Testing).
- **Bugs.md** tracks issues by priority (Critical, High, Medium, Low).
- **Features.md** separates high-level features from low-level tasks.
- **Status.md** shows current system health and recent changes.
- **TechStack.md** documents your technology choices and dependencies.
- **Commands.md** provides quick reference for CLI commands and operations.
- **Testing.md** covers test setup, patterns, and quality assurance.
- Everything else lives under **/projects/** while active, then moves to **/archive/YYYY/MM/**.
- Every doc has **front matter** (owner, status, updated, summary, canonical).
- **Lifecycle:** `draft → active (living) → deprecated → archived`.
- Write for retrieval: short sections, stable headings, 5–8 line summaries, one sentence per line.
- Decisions are immutable **ADRs**. Never edit history; supersede.

---

## Goals

1. **Human clarity:** quick orientation, consistent navigation, and "what changed?" signals.
2. **AI effectiveness:** stable anchors, rich metadata, chunkable structure, and predictable lifecycles.
3. **Low maintenance:** simple templates and light ownership for solo development.

---

## Folder Contract

```
/docs/
  /living/
    Overview.md
    Roadmap.md
    DecisionLog.md
    Onboarding.md
    Bugs.md
    Features.md
    Status.md
    TechStack.md
    Commands.md
    Testing.md
  /archive/
```

- **Living** is small and always current - your daily working docs.
- **Bugs.md** is your issue tracker with simple priority categories.
- **Features.md** separates big picture from implementation details.
- **Status.md** shows system health and recent changes.
- **TechStack.md** documents your technology choices and dependencies.
- **Commands.md** provides quick CLI reference for operations.
- **Testing.md** covers test setup, patterns, and quality assurance.
- **Projects** contain working materials and ADRs while active.
- **Archive** is write-once: closed projects and superseded material.

---

## Living Docs Structure

### Bugs.md - Issue Tracking
Simple priority-based categories:
- **Critical:** System down, data loss, security issues
- **High:** Core functionality broken, user blocking
- **Medium:** Important but not blocking
- **Low:** Nice to have, cosmetic issues

### Features.md - Development Planning
Two-tier structure:
- **High-level features:** Major capabilities, user stories, business goals
- **Low-level tasks:** Implementation details, technical debt, refactoring

### Status.md - System Health
Quick overview of:
- **Current status:** All systems operational, partial outage, etc.
- **Recent changes:** What deployed in last 24-48 hours
- **Known issues:** Quick reference to active bugs
- **Next deployments:** What's coming up

### TechStack.md - Technology Documentation
Essential for AI understanding:
- **Core technologies:** Python, Flask, PostgreSQL, etc.
- **Key dependencies:** Major libraries and versions
- **Infrastructure:** Hosting, deployment, monitoring
- **Data sources:** APIs, databases, external systems

### Commands.md - CLI Reference
Quick access to common operations:
- **Development commands:** Setup, testing, code quality
- **Database operations:** Migrations, backups, queries
- **System operations:** Deployment, monitoring, troubleshooting
- **Validation commands:** Running data quality checks

### **Testing.md - Quality Assurance**
Comprehensive testing coverage:
- **Test setup** and environment configuration
- **Test patterns** and best practices
- **Data management** and fixtures
- **CI/CD integration** and automation

---

## Lifecycle & Governance

**States:** `draft → active → deprecated → archived`

- **Promote to active (living)** when a doc becomes a source of truth.
- **Deprecate** when a better source exists; **Archive** when a project closes.
- **Stub rule:** when archiving, leave a 1-paragraph stub at the old path that links to the new canonical source.

**Ownership**
- Each doc lists an **owner** in front matter.
- Update ownership immediately when it changes.

---

## Metadata (Front Matter Contract)

All Markdown docs carry the following **minimum** front matter:

```yaml
---
title: "<clear title>"
status: draft | active | deprecated | archived
doc_type: overview | roadmap | adr | spec | runbook | note
project: "<project_slug or global>"
owner: "@handle-or-team"
updated: YYYY-MM-DD
tags: ["a","few","tags"]
summary: "<5–8 line executive summary>"
canonical: "/absolute/repo/path/to/this/doc.md"
---
```

**Why it matters:** consistent fields enable filtered retrieval, ranking by `status`, and redirect handling when files move.

---

## Writing Rules (Human- & AI-Friendly)

- **Top-load context:** start with `summary`, then "Key decisions / Risks / Next actions" bullets.
- **One sentence per line** in prose; it's diff-friendly and chunk-friendly.
- **Headings every ~300–500 tokens**; keep sections self-contained.
- **Line length:** soft wrap around ~100 chars for prose; let language formatters handle code.
- **Code fences** for commands/logs; small examples; link to larger samples.
- **Stable anchors:** avoid casual heading renames; if you move a doc, keep `canonical` and add a redirect entry.

---

## Decision Hygiene (ADRs)

- Log every non-trivial decision as an **ADR** under `/projects/{project_slug}/ADR/`.
- Filenames: `NNNN-short-slug.md` (monotonic number).
- Old ADRs are **immutable**; supersede with a new ADR and cross-link both ways.
- Maintain `/docs/living/DecisionLog.md` as the **index of ADRs** across projects.

Minimal ADR template (see `/docs/templates/template_adr.md` for the full version):

```md
---
title: "NNNN: <short decision>"
status: accepted
doc_type: adr
project: "<project_slug>"
owner: "@handle"
date: YYYY-MM-DD
summary: "<one paragraph what/why>"
---
## Context
## Decision
## Consequences
## Alternatives considered
## Links
```

---

## Change Management & Sync

- **Update living docs** when you make changes to Bugs.md or Features.md.
- **Keep front matter current:** especially `updated` date and `summary`.
- **Link updates:** update any relevant `INDEX.md` and `DecisionLog.md`.
- **Simple validation:** markdownlint + broken link check.

Basic checklist:
```md
- [ ] Front matter updated (`updated`, `summary`, `status`, `canonical`).
- [ ] Links added/updated in `INDEX.md` / `DecisionLog.md`.
- [ ] markdownlint + link checker pass locally.
```

---

## Search & AI (RAG Contract)

**Ingestion (on merge to main):**
1. Parse Markdown; drop nav boilerplate.
2. **Chunk by headings**, then by tokens to ~300–500 tokens with ~50 token overlap.
3. Embed chunk text and attach front-matter as metadata (`project`, `doc_type`, `status`, `updated`, `tags`, `canonical`).
4. Push to the vector store (namespace = repo).

**Retrieval rules:**
- Rank `status: active` first; if returning `archived`, prepend a "This is archived" note.
- Prefer chunks with recent `updated` and exact `project`/`doc_type` matches.

**Gold paths:** each living doc ends with "Ask me" examples to improve retrieval:

```md
### Ask me (examples)
- "How do I deploy the API gateway and roll back?"
- "What decisions led us to choose Postgres over MySQL?"
- "What changed in the system this month?"
```

---

## Minimal Living Set (Keep It Tiny)

- **Overview.md:** what the system is; diagrams, repos, environments.
- **Roadmap.md:** next-quarter themes and top 5 initiatives.
- **DecisionLog.md:** ADR index; pointers to per-project ADRs.
- **Onboarding.md:** 90-minute path to first PR (env setup, tests, access).
- **Bugs.md:** your issue tracker with priority categories.
- **Features.md:** high-level features and low-level tasks.
- **Status.md:** system health and recent changes.
- **TechStack.md:** technology choices and dependencies.
- **Commands.md:** CLI commands and operational procedures.
- **Testing.md:** test setup, patterns, and quality assurance.

---

## Archive Strategy

- On archive, move the file to `/archive/YYYY/MM/`.
- Leave a stub at the old path with:
  - 1-paragraph summary,
  - "Superseded by" link to the new canonical doc,
  - The old `canonical` retained for redirects.
- Archived docs remain ingestible but rank lower in retrieval.

Stub example:

```md
---
title: "Spec: Legacy Data Sync"
status: archived
doc_type: spec
canonical: "/docs/projects/data-sync/Spec_legacy.md"
summary: "Superseded by the 2025-08 streaming design."
---
This document is archived. See **/docs/projects/data-streaming/Spec_streaming.md**.
```

---

## Defaults You Can Adopt Today

- **Formatters:** prose uses one-sentence-per-line; code uses language formatters.
- **Soft wraps:** aim for ~100 chars in prose.
- **Heading cadence:** new heading every 300–500 tokens.
- **Simple validation:** markdownlint + link check.

---

## Quick Start

1. Create `/docs/living/` with the ten living docs above.
2. Add `/docs/templates/` with `template_adr.md`, `template_runbook.md`, `template_spec.md`.
3. Set up simple validation (markdownlint + link check).
4. Use Bugs.md and Features.md as your primary tracking tools.
5. Update Status.md daily/weekly for system health.
6. Keep TechStack.md current when you change dependencies.
7. Maintain Commands.md with frequently used CLI operations.
8. Use Testing.md for test setup and quality assurance.

---

## Change Log

- **2025-01-27:** Updated for solo development focus, added Bugs.md and Features.md structure.
- **2025-08-16:** Initial version.
