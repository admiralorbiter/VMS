---
title: "Tooling and Automation"
description: "Recommended tools and configurations for quality and security"
tags: [tooling, automation, quality]
---

## Recommendations

| Purpose | Tool |
|--------|------|
| Static site | mkdocs-material |
| Diagrams | mermaid, plantuml, pyreverse |
| AI PR reviews | GitHub Copilot Chat or gh ai comment |
| Semantic versioning | commitizen, cz changelog |

## Code Quality & Automation Details

### Code Formatting
Black (88), isort (profile black)

### Linting
flake8 (ignore E203, W503)

### Security
bandit (exclude tests/), safety (dependencies)

### Type Checking (optional)
mypy (gradual strict)

### Advanced
semgrep, tox, coverage gates

## Configuration Strategy

1. Start simple: black + isort + flake8 + bandit
2. Add tools gradually; keep CI fast
3. Align on team conventions

