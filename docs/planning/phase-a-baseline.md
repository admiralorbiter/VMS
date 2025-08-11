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
- [ ] Add `requirements-dev.txt` with dev tools
- [ ] Install: `pip install pre-commit`
- [ ] Create `.pre-commit-config.yaml` with:
  - [ ] black (line length 88)
  - [ ] isort (profile black)
  - [ ] flake8 (ignore E203, W503; max-line-length 88)
  - [ ] bandit (exclude tests/)
  - [ ] pre-commit-hooks (trailing-whitespace, end-of-file-fixer)
- [ ] Install git hooks: `pre-commit install`
- [ ] First run: `pre-commit run --all-files` and fix findings

Acceptance criteria:
- [ ] All hooks pass locally on a clean checkout

### 2) CI pipeline
- [ ] Create `.github/workflows/ci.yml` with matrix (3.8–3.11)
- [ ] Steps: install deps, run pre-commit, run pytest, run bandit
- [ ] Cache pip for speed
- [ ] Add README badges (build, coverage)

Acceptance criteria:
- [ ] CI passes on PRs and main

### 3) Documentation baseline
- [ ] Update `docs/01-overview.md` with purpose and outcomes
- [ ] Add a simple Mermaid diagram to `docs/02-architecture.md`
- [ ] Verify quick start in `docs/05-dev-guide.md`
- [ ] Ensure links in `docs/README.md` are valid

Acceptance criteria:
- [ ] New developer can set up and run tests in <30 minutes

## Dependencies

- None

## Risks

- Tool conflicts (flake8 vs black vs isort) → Resolve with shared settings above

## Deliverables

- `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, updated docs

