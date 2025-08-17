---
title: "Engineering & Documentation Philosophy"
status: active
doc_type: overview
project: "global"
owner: "@jlane"
updated: 2025-08-16
tags: ["docs-as-code","governance","ai","rag","adr"]
summary: "How we structure, maintain, and retrieve knowledge so humans stay clear and AI stays effective."
canonical: "/docs/living/Philosophy.md"
---

# Engineering & Documentation Philosophy

> Humans need clarity. AI can handle volume. We design so both thrive.

This document defines how we create, evolve, and retrieve knowledge with minimal friction. It favors a few **living sources of truth** for humans and a deep, well-labeled **archive** that AI can mine safely.

---

## TL;DR (Policy on One Page)

- Keep **a tiny set of living docs** (Overview, Roadmap, DecisionLog, Onboarding, essential Runbooks).
- Everything else lives under **/projects/** while active, then moves to **/archive/YYYY/MM/** with a stub left behind.
- Every doc has **front matter** (owner, status, updated, summary, canonical). No owner → no doc.
- **Lifecycle:** `draft → active (living) → deprecated → archived`. Auto-review if untouched for 60 days.
- Write for retrieval: short sections, stable headings, 5–8 line summaries, one sentence per line.
- Decisions are immutable **ADRs**. Never edit history; supersede.
- RAG/search ranks `status: active` first; archived appears with a warning banner.

---

## Goals

1. **Human clarity:** quick orientation, consistent navigation, and “what changed?” signals.
2. **AI effectiveness:** stable anchors, rich metadata, chunkable structure, and predictable lifecycles.
3. **Low maintenance:** guardrails via templates, CI checks, and light ownership.

---

## Folder Contract

```
/docs/
  /living/
    Overview.md
    Roadmap.md
    DecisionLog.md
    Onboarding.md
    /Runbooks/
      deploy.md
      incident_response.md
  /projects/{project_slug}/
    Spec_{short}.md
    /ADR/
    /Runbooks/
    /Notes/
  /archive/YYYY/MM/
  /templates/
    template_adr.md
    template_runbook.md
    template_spec.md
```

- **Living** is small and always current.
- **Projects** contain working materials and ADRs while active.
- **Archive** is write-once: closed projects and superseded material.
- **Templates** keep style and metadata consistent.

---

## Lifecycle & Governance

**States:** `draft → active → deprecated → archived`

- **Promote to active (living)** when a doc becomes a source of truth (e.g., a runbook used in prod).
- **Auto-stale check:** if an active doc isn't updated in **60 days**, open a review PR.
- **Deprecate** when a better source exists; **Archive** when a project closes or a doc is superseded.
- **Stub rule:** when archiving, leave a 1-paragraph stub at the old path that links to the new canonical source.

**Ownership**
- Each doc lists an **owner** in front matter; CODEOWNERS gate PRs to `/docs/living/`.
- If ownership changes, update the front matter immediately.

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

- **Top-load context:** start with `summary`, then “Key decisions / Risks / Next actions” bullets.
- **One sentence per line** in prose; it’s diff-friendly and chunk-friendly.
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

## Scaling Horizontally & Vertically

- **Hierarchy:** `org → initiative → project → component` and mirror that in `/projects/`.
- Each level has a lightweight `INDEX.md` with one-line summaries and links.
- Use **tags** for cross-cutting topics (e.g., `security`, `data-pipeline`) instead of deep nesting.

---

## Change Management & Sync

- **PR template requires:**
  - `updated` date, accurate `summary`, correct `status`.
  - Link updates in any relevant `INDEX.md` and `DecisionLog.md`.
- **CI gates:**
  - markdownlint + broken link check.
  - Stale-doc job to open a review after 60 days of inactivity for `active`.
  - Redirect map validates `canonical` paths for moved docs.
- **Release notes:** append notable doc updates under “What changed” in `Overview.md`.

PR checklist snippet:

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
- Rank `status: active` first; if returning `archived`, prepend a “This is archived” note.
- Prefer chunks with recent `updated` and exact `project`/`doc_type` matches.

**Gold paths:** each living doc ends with “Ask me” examples to improve retrieval:

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
- **Runbooks/**: deploy, rollback, paging, incident response.

---

## Archive Strategy

- On archive, move the file to `/archive/YYYY/MM/`.
- Leave a stub at the old path with:
  - 1-paragraph summary,
  - “Superseded by” link to the new canonical doc,
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
- **Status reviews:** 60-day auto-review for all `active` docs.

---

## Quick Start

1. Create `/docs/living/` with the five living docs above.
2. Add `/docs/templates/` with `template_adr.md`, `template_runbook.md`, `template_spec.md`.
3. Add the PR checklist to your repo template.
4. Set up CI for markdownlint, link check, stale-doc review, and canonical redirects.
5. Hook your RAG pipeline to ingest on merge and filter by `status: active`.

---

## Change Log

- **2025-08-16:** Initial version.
