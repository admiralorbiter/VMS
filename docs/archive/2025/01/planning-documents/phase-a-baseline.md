---
title: "Phase A – Establish Baseline (Week 1)"
description: "Set up dev productivity, guardrails, and docs baseline"
tags: [phase-a, baseline, pre-commit, ci]
---

## Goals

- Ship formatting, linting, and security guardrails that run locally and in CI
- Ensure onboarding docs are accurate and fast to execute

## Milestones

- Day 1–2: Local guardrails working on all files
- Day 3–4: CI green with tests + lint + security
- Day 5: Docs updated; team aligned

## Detailed Tasks

### 1) Pre-commit
- [x] Add `requirements-dev.txt` with dev tools
- [x] Install: `pip install pre-commit`
- [x] Create `.pre-commit-config.yaml` with:
  - [x] black (line length 88)
  - [x] isort (profile black)
  - [x] flake8 (ignore E203, W503; max-line-length 88)
  - [x] bandit (exclude tests/)
  - [x] pre-commit-hooks (trailing-whitespace, end-of-file-fixer)
- [x] Install git hooks: `pre-commit install`
- [x] First run: `pre-commit run --all-files` and fix findings

Acceptance criteria:
- [x] All hooks pass locally on a clean checkout

### 2) Documentation baseline
- [x] Update `docs/01-overview.md` with purpose and outcomes
- [x] Add a simple Mermaid diagram to `docs/02-architecture.md`
- [x] Verify quick start in `docs/05-dev-guide.md`
- [x] Ensure links in `docs/README.md` are valid

Acceptance criteria:
- [x] New developer can set up and run tests in <30 minutes

## Dependencies

- None

## Risks

- Tool conflicts (flake8 vs black vs isort) → Resolve with shared settings above

## Deliverables

- `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, updated docs
