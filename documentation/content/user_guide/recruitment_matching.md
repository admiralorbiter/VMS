# Volunteer Recruitment & Matching

## Overview

The Volunteer Matching System is an intelligent algorithm that **automatically finds and ranks** the best volunteer candidates for specific events. It uses a multi-dimensional approach combining event characteristics, volunteer profiles, and historical data to provide explainable recommendations.

**Access:** Reports → Recruitment → Event Candidates (`/reports/recruitment/candidates`)

---

## How Matching Works

### 1. Event Analysis

The system derives keywords from multiple sources to understand what type of volunteer best fits an event:

| Source | Priority | Description |
|--------|----------|-------------|
| **Custom Keywords** | Highest | User-specified comma-separated terms (e.g., "python, data science") |
| **Event Type** | High | Curated keywords per event type (see below) |
| **Title/Description** | Medium | NLP-like extraction of domains, tools, and levels |
| **Format** | Low | Virtual/in-person indicators |

#### Event Type Keywords

Each event type has predefined matching keywords:

- **DATA_VIZ**: data, analytics, bi, visualization, tableau, power bi, excel, sql, python, r, statistics
- **CAREER_FAIR**: career, job search, networking, professional, resume, interview, employment
- **CAREER_SPEAKER**: career, professional development, leadership, industry, expertise, mentoring
- **FINANCIAL_LITERACY**: finance, accounting, budgeting, investing, banking, economics
- **VIRTUAL_SESSION**: *(No type keywords - focuses on content analysis)*
- **CLASSROOM_SPEAKER**: education, teaching, presentation, communication, public speaking

> [!TIP]
> For **VIRTUAL_SESSION** events, keywords come entirely from title analysis, allowing maximum flexibility.

---

### 2. Candidate Scoring

Each volunteer receives a score based on these factors:

| Factor | Weight | Criteria |
|--------|--------|----------|
| **Past Event Type Participation** | +1.0 | Per past event of the same type |
| **Skill Overlap** | +0.8 | Keywords match volunteer skills |
| **Title/Industry Match** | +0.6 | Keywords in job title, department, or industry |
| **Connector Profile** | +0.4 | Has an established connector profile |
| **Recency Boost** | +0.35 / +0.15 | Active within 90 days / 180 days |
| **Frequency** | +0.3 / +0.2 / +0.1 | 10+ / 5+ / 2+ events attended |
| **Geographic Proximity** | +0.2 / +0.1 | Local / Partial local status |

> [!NOTE]
> Volunteers with **do-not-contact**, **email opt-out**, or **inactive** status are automatically excluded.

---

## Using the Interface

### Basic Workflow

1. Navigate to **Reports → Recruitment → Event Candidates**
2. Select an event from upcoming or recent events
3. Review ranked candidates with score breakdowns
4. Optionally add custom keywords to refine results
5. Export to CSV for outreach

### Custom Keywords

Add comma-separated terms to fine-tune matching:

**Effective examples:**
- Technical skills: `python, pandas, jupyter, sql`
- Industry focus: `healthcare, medical, clinical, patient care`
- Experience level: `senior, executive, director`

**Avoid:**
- Too generic: "professional", "experienced"
- Too niche: terms few volunteers will have
- Special characters that cause parsing issues

### Filtering Options

| Parameter | Description |
|-----------|-------------|
| `min_score` | Minimum score threshold |
| `limit` | Maximum candidates returned (default: 100) |
| `custom_keywords` | Comma-separated additional keywords |

---

## API Reference

### Candidate List

```
GET /reports/recruitment/candidates?event_id={id}
GET /reports/recruitment/candidates?event_id={id}&min_score=1.5&limit=50
GET /reports/recruitment/candidates?event_id={id}&custom_keywords=python,data
```

### CSV Export

```
GET /reports/recruitment/candidates.csv?event_id={id}
```

---

## KCTAA Special Report

A specialized tool for matching a list of KCTAA personnel names against volunteers.

**Access:** Reports → Volunteer Reports → KCTAA Volunteer Matches (`/reports/kctaa`)

### Features

- **Exact Match**: First + last name identical (case-insensitive)
- **Fuzzy Match**: 90% similarity threshold using `difflib.SequenceMatcher`
- **Participation Stats**: Event count, total hours, last event date

### Match Quality Indicators

| Type | Badge | Score | Action |
|------|-------|-------|--------|
| Exact Match | 🟢 Green | 1.0 | Most reliable |
| Fuzzy Match | 🟡 Yellow | 0.9 - 0.999 | Review recommended |
| No Match | 🔴 Red | 0.0 | Manual review needed |

### Configuration

- **CSV Path**: `data/kctaa_first_last_names.csv`
- **Fuzzy Threshold**: 90% (configurable via `FUZZY_MATCH_THRESHOLD`)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low match quality | Check keyword derivation for event type; add custom keywords |
| Slow performance | Verify caching is working; reduce result limit |
| Missing volunteers | Check governance filter settings (opt-out, inactive) |
| Custom keywords not working | Verify comma separation; avoid special characters |
