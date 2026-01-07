# Volunteer Matching System Documentation

## Overview

The Volunteer Matching System is an intelligent, transparent algorithm that automatically finds and ranks the best volunteer candidates for specific events. It uses a multi-dimensional approach combining event characteristics, volunteer profiles, and historical data to provide explainable recommendations.

## System Architecture

### 1. Event Analysis & Keyword Derivation
The system analyzes events through multiple lenses to generate comprehensive matching criteria:

#### Custom Keywords (Highest Priority - User-Specified)
Users can add their own comma-separated keywords to fine-tune volunteer matching:

- **Input Format**: Comma-separated keywords (e.g., "python, data science, machine learning")
- **Priority**: Highest priority - these keywords are processed first and given full weight in matching
- **Use Cases**:
  - Add specific technical skills not covered by automatic detection
  - Include industry-specific terminology
  - Specify preferred volunteer characteristics
  - Add local or contextual terms relevant to the event
- **Example**: For a "Data Science Workshop", users might add "python, pandas, numpy, jupyter" to find volunteers with specific technical expertise

#### Event Type-Based Keywords (Most Reliable)
Each event type has a curated set of relevant keywords:

- **DATA_VIZ**: data, analytics, bi, visualization, tableau, power bi, excel, sql, python, r, statistics, reporting
- **CAREER_FAIR**: career, job search, networking, professional, resume, interview, employment, workforce
- **CAREER_SPEAKER**: career, professional development, leadership, industry, expertise, experience, mentoring
- **CAREER_JUMPING**: career transition, skill development, professional growth, industry change, adaptability
- **EMPLOYABILITY_SKILLS**: soft skills, communication, teamwork, problem solving, leadership, professional, workplace
- **FINANCIAL_LITERACY**: finance, financial, accounting, budgeting, investing, banking, economics, money management
- **MATH_RELAYS**: mathematics, math, stem, education, teaching, problem solving, analytical
- **CLASSROOM_SPEAKER**: education, teaching, presentation, communication, public speaking, knowledge sharing
- **MENTORING**: mentoring, guidance, coaching, leadership, experience, development, support
- **INTERNSHIP**: internship, entry level, learning, experience, professional development, career start
- **VIRTUAL_SESSION**: No type keywords - focuses entirely on content analysis
- **CONNECTOR_SESSION**: networking, connections, relationship building, professional network, collaboration
- **WORKPLACE_VISIT**: workplace, office, corporate, business, professional environment, industry exposure, real world
- **CAMPUS_VISIT**: campus, college, university, higher education, academic, student life, college preparation
- **COLLEGE_OPTIONS**: college, university, higher education, academic planning, college preparation, admissions
- **FAFSA**: fafsa, financial aid, college funding, scholarships, student loans, college costs
- **IGNITE**: ignite, leadership, youth development, empowerment, community service, social impact
- **DIA**: dia, diversity, inclusion, access, equity, representation, social justice

#### Text Analysis Keywords
The system analyzes event titles and descriptions to identify:

**Professional Domains:**
- Technology: tech, software, programming, coding, developer, engineer, it, computer
- Business: business, management, strategy, operations, consulting, entrepreneur
- Healthcare: health, medical, clinical, patient, healthcare, nursing, pharmacy
- Education: education, teaching, learning, academic, curriculum, instruction
- Finance: finance, financial, accounting, banking, investment, audit
- Marketing: marketing, advertising, branding, social media, digital marketing
- Sales: sales, business development, account management, client relations
- Engineering: engineering, mechanical, electrical, civil, chemical, design
- Science: science, research, laboratory, experiment, analysis, scientific
- Arts: arts, creative, design, visual, media, production, paint, painting, artistic, creativity, craft, drawing, sculpture, photography, music, dance, theater, performance, expression, imagination

**Specific Tools & Technologies:**
- excel, tableau, power bi, sql, python, r, spss, sas, quickbooks, salesforce

**Professional Level Indicators:**
- entry level, mid level, senior, executive, director, manager, lead, principal

#### Event Format Keywords
Based on how the event is conducted:
- **Virtual**: virtual, remote, online, digital
- **In-Person**: in-person, onsite, face-to-face

**Note**: For VIRTUAL_SESSION events, format keywords are intentionally excluded to focus matching on content relevance rather than delivery method.

#### Hybrid Fallback System
Ensures every event has meaningful matching criteria, even when primary keyword sources fail:

**Fallback Text Analysis:**
- Extracts meaningful words from event titles
- Removes common stop words (the, a, an, and, or, etc.)
- Focuses on content-relevant terms
- Example: "Paint Outside the Lines" → ["paint", "outside", "lines"]

**Contextual Keywords:**
- Generates relevant keywords based on event type and title patterns
- VIRTUAL_SESSION: presentation, interactive, engagement
- CLASSROOM_SPEAKER: education, learning, presentation
- CAREER_FAIR: professional, networking, opportunity
- Title patterns: artistic events → ["artistic", "creativity", "expression"]

**Universal Fallback:**
- Ensures every event has at least basic matching criteria
- Provides general volunteer matching when all else fails
- Keywords: ["volunteer", "event", "participation"]

#### Phase 2: Smart Enhancement System
Advanced pattern recognition and semantic analysis for intelligent keyword generation:

**Pattern Recognition:**
- **Skill Development**: "How to...", "Learning to..." → tutorial, learning, skill building
- **Industry Focus**: "Career in...", "Working in..." → career guidance, industry knowledge
- **Project-Based**: "Building...", "Creating..." → hands-on, project work, creation
- **Knowledge Discovery**: "Understanding...", "Exploring..." → research, exploration, investigation
- **Relationship Building**: "Connecting...", "Networking..." → networking, collaboration, partnerships
- **Preparation**: "Preparing for...", "Getting Ready for..." → planning, preparation, readiness

**Semantic Context Analysis:**
- **Emotional/Engagement**: inspiring, motivating → motivation, inspiration, empowerment
- **Problem-Solving**: solving, addressing, challenges → problem solving, critical thinking, analytical
- **Innovation/Creativity**: innovative, creative, groundbreaking → innovation, creativity, breakthrough
- **Leadership/Management**: leading, managing, coordinating → leadership, management, supervision
- **Community/Service**: community, service, volunteering → community service, helping others, social impact

**Dynamic Characteristics:**
- **Event Complexity**: Title length analysis for detailed vs. focused events
- **Audience Level**: Beginner, intermediate, expert, or all levels detection
- **Content Type**: Hands-on, theoretical, networking, or skill-building classification

#### Location Context Keywords
Geographic and environmental context:
- **Urban**: downtown, urban, city
- **Suburban**: suburban, suburb
- **Rural**: rural, country

### 2. Volunteer Profile Analysis

The system examines multiple volunteer attributes:

- **Professional Information**: title, department, industry
- **Skills**: explicit skills listed in volunteer profile
- **Geographic Location**: local status (local, partial, non-local)
- **Activity History**: past participation, recency, frequency
- **Contact Preferences**: opt-out status, do-not-contact flags

### 3. Matching Algorithm

#### Phase 1: Initial Filtering
1. **Governance Filters**: Exclude volunteers with:
   - Inactive status
   - Do-not-contact flags
   - Email opt-outs
   - Report exclusions

2. **Keyword Pre-filtering**: When keywords exist, reduce candidate pool by matching against:
   - **Custom Keywords** (user-specified, highest priority)
   - Volunteer title
   - Department
   - Industry
   - Skills

#### Phase 2: Scoring & Ranking

Each volunteer receives a score based on multiple factors:

##### Past Event Type Participation (Weight: 1.0)
- **Score**: +1.0 for each past event of the same type
- **Rationale**: Proven experience with similar events
- **Example**: "Past Career Fair event (3x): +1.00 (count 3)"

##### Title/Industry Keyword Match (Weight: 0.6)
- **Score**: +0.6 for keyword matches in professional profile
- **Rationale**: Professional alignment with event requirements
- **Example**: "Title/industry keyword (career, professional): +0.60"

##### Skill Overlap (Weight: 0.8)
- **Score**: +0.8 for matching skills
- **Rationale**: Direct skill relevance to event needs
- **Example**: "Skill overlap (python, data analysis): +0.80"

##### Connector Profile (Weight: 0.4)
- **Score**: +0.4 for volunteers with established connector profiles
- **Rationale**: Connector profiles indicate established, engaged volunteers who are more likely to respond
- **Example**: "Connector profile: +0.40"

##### Recency Boost (Weight: 0.35 max)
- **Score**: +0.35 for activity within 90 days, +0.15 for 180 days
- **Rationale**: Active volunteers are more likely to respond
- **Example**: "Recency: +0.35"

##### Geographic Proximity (Weight: 0.2 max)
- **Score**: +0.2 for local volunteers, +0.1 for partial
- **Rationale**: Local volunteers have better attendance rates
- **Example**: "Locality: +0.20"

##### Participation Frequency (Weight: 0.3 max)
- **Score**: +0.3 for 10+ events, +0.2 for 5+ events, +0.1 for 2+ events
- **Rationale**: Reliable volunteers with proven commitment
- **Example**: "Frequency (15): +0.30"

#### Phase 3: Final Ranking
1. **Sort by Total Score**: Highest scores first
2. **Apply Runtime Filters**: Minimum score thresholds, result limits
3. **Cache Results**: Store for performance optimization

### 4. Transparency Features

The system provides complete visibility into the matching process:

#### Keyword Criteria Display
- Shows how each keyword category was derived
- Explains the source of each keyword set
- Lists all keywords used for matching
- **Custom Keywords**: Displayed with special user-edit icon (🔧) and clear explanation of user input

#### Debug Information
- Displays all flattened keywords used in matching
- Shows the complete keyword set for troubleshooting

#### Matching Strategy Summary
- Explains the 3-step matching process
- Details the scoring algorithm
- Provides context for understanding results

#### Individual Score Breakdowns
- Collapsible detailed breakdown for each candidate
- Shows exactly how each score component was calculated
- Lists specific keywords that matched

### 5. Performance Optimizations

#### Caching Strategy
- **RecruitmentCandidatesCache**: Stores computed candidate lists
- **Refresh Control**: Manual refresh option for updated results
- **Keyword Reconstruction**: Rebuilds keywords for cached results

#### Database Query Optimization
- **Eager Loading**: Uses `eagerload_volunteer_bundle` for efficient data retrieval
- **Prefiltering**: Reduces candidate pool before detailed scoring
- **Batch Processing**: Processes up to 2000 volunteers per event

### 6. Usage Examples

#### Basic Event Selection
```
GET /reports/recruitment/candidates
```
Shows event selector with upcoming and recent events.

#### Specific Event Analysis
```
GET /reports/recruitment/candidates?event_id=123
```
Analyzes event 123 and shows ranked volunteer candidates.

#### Custom Keyword Matching
```
GET /reports/recruitment/candidates?event_id=123&custom_keywords=python,data%20science,machine%20learning
```
Analyzes event 123 with custom keywords "python, data science, machine learning" for enhanced matching.

#### Filtered Results
```
GET /reports/recruitment/candidates?event_id=123&min_score=1.5&limit=50&custom_keywords=senior,tech
```
Shows only candidates with scores ≥1.5, limited to 50 results, including custom keywords "senior, tech".

#### CSV Export
```
GET /reports/recruitment/candidates.csv?event_id=123
```
Exports candidate list as CSV for external analysis.

#### CSV Export with Custom Keywords
```
GET /reports/recruitment/candidates.csv?event_id=123&custom_keywords=python,data
```
Exports candidate list as CSV with filename including custom keywords (e.g., "event_123_custom_pythondata_candidates.csv").

### 7. Configuration & Customization

#### Keyword Mappings
- Event type keywords are configurable in the `derive_type_keywords` function
- Domain patterns can be adjusted in `derive_text_keywords`
- Tool/technology lists can be updated as needed

#### Scoring Weights
- All scoring weights are defined as constants in the `score_and_reasons` function
- Weights can be adjusted to prioritize different factors
- New scoring factors can be easily added

#### Filtering Options
- Minimum score thresholds
- Result limits
- Geographic preferences
- Skill requirements

### 8. Monitoring & Maintenance

#### Performance Metrics
- Query execution time
- Cache hit rates
- Result quality feedback
- User satisfaction scores

#### Regular Updates
- Keyword mappings should be reviewed quarterly
- Scoring weights can be adjusted based on outcomes
- New event types should be added to keyword mappings
- Tool/technology lists should be kept current

### 9. Custom Keyword Best Practices

#### Effective Custom Keywords
- **Be Specific**: Use precise terms like "python" instead of "programming"
- **Include Variations**: Add synonyms and related terms (e.g., "data analysis, analytics, bi")
- **Consider Context**: Include industry-specific terminology relevant to the event
- **Use Commas Properly**: Separate keywords with commas, avoid spaces within multi-word terms

#### Common Use Cases
- **Technical Skills**: "python, pandas, numpy, jupyter, sql, tableau"
- **Industry Terms**: "healthcare, medical, clinical, patient care"
- **Experience Levels**: "senior, executive, director, manager, lead"
- **Geographic Terms**: "downtown, urban, suburban, rural, local"
- **Professional Roles**: "consultant, analyst, engineer, designer, educator"

#### Avoiding Common Mistakes
- **Too Generic**: Avoid terms like "professional" or "experienced" that are too broad
- **Over-Specific**: Don't use overly niche terms that few volunteers will have
- **Mixed Categories**: Keep related keywords together (e.g., all technical skills in one set)
- **Special Characters**: Avoid special characters that might cause parsing issues

### 10. Troubleshooting

#### Common Issues
1. **Low Match Quality**: Check keyword derivation for event type
2. **Slow Performance**: Verify caching is working properly
3. **Missing Volunteers**: Check governance filter settings
4. **Score Inconsistencies**: Verify keyword matching logic
5. **Custom Keywords Not Working**: Verify comma separation and check for special characters

#### Debug Tools
- Debug keyword display shows all keywords used
- Score breakdowns show individual component calculations
- Cache status indicates if results are fresh or cached
- Custom keywords are displayed with special user-edit icon for easy identification

### 11. KCTAA Special Report

The KCTAA Special Volunteer Match Report provides a specialized tool for matching a provided list of KCTAA personnel names against volunteers in the system, showing volunteer activity and match quality indicators.

#### Purpose
- Crosswalk between KCTAA-provided name list and actual volunteers in the system
- Track volunteer participation for KCTAA personnel
- Identify exact and fuzzy name matches with quality scores
- Export results for further analysis

#### Data Source
- **CSV File**: `data/kctaa_first_last_names.csv`
- **Format**: Two columns - "First Name" and "Last Name"
- **Configuration**: File path configurable via `KCTAA_NAME_LIST_PATH` in app config (defaults to `data/kctaa_first_last_names.csv`)

#### Matching Algorithm

##### Exact Match
- First and last name match exactly (case-insensitive, punctuation-insensitive)
- Matches where normalized first + last names are identical
- Marked as **Exact Match = Yes** with match score of 1.0
- Multiple exact matches possible (returns all matches)

##### Fuzzy Match
- Similarity-based matching for near-matches
- Uses Python's `difflib.SequenceMatcher` for string similarity
- Threshold: 90% similarity (configurable via `FUZZY_MATCH_THRESHOLD`)
- Marked as **Exact Match = No** with match score between 0.9 and 1.0
- Returns all matches above threshold (not just the best one)

##### No Match
- CSV names that don't match any volunteers (below threshold or no similarity)
- Marked as **Match Type = None** with match score of 0.0
- Can be included/excluded via filter

#### Report Features

##### HTML View (`/reports/kctaa`)
- Interactive table showing all matches
- Filters:
  - **Minimum Match Score**: Filter by match quality (0.0 - 1.0, default: 0.9)
  - **Include Unmatched**: Show/hide CSV names with no matches
- Columns:
  - CSV Name (from source list)
  - Matched Volunteer Name
  - Email
  - Organization
  - Event Count (total participations)
  - Total Hours
  - Last Event Date
  - Match Type (Exact/Fuzzy/None)
  - Match Score (0.0 - 1.0)
  - Match Count (number of volunteers that matched)

##### CSV Export (`/reports/kctaa.csv`)
- Same columns as HTML view
- Includes all match metadata
- Filename: `KCTAA_Volunteer_Matches_YYYYMMDD.csv`
- Respects same filters as HTML view

#### Access
- **URL**: `/reports/kctaa`
- **Category**: Volunteer Reports
- **Icon**: `fa-solid fa-users-gear`
- **Location**: Reports index page under "Volunteer Reports" category

#### Name Normalization
Names are normalized before matching:
- Removes punctuation (periods, commas, apostrophes, etc.)
- Converts to lowercase
- Trims whitespace
- Example: "John O'Brien" → "john obrien"

#### Participation Statistics
The report aggregates volunteer participation:
- **Event Count**: Number of completed events with statuses: "Attended", "Completed", "Successfully Completed", "Simulcast"
- **Total Hours**: Sum of `delivery_hours` from event participations
- **Last Event Date**: Most recent completed event participation
- **All-time counts**: No date range filtering (includes all historical data)

#### Usage Examples

##### View All Matches
```
GET /reports/kctaa
```
Shows all matches above default threshold (0.9).

##### Filter by Match Score
```
GET /reports/kctaa?min_score=0.95
```
Shows only matches with score ≥ 0.95 (stricter matching).

##### Include Unmatched Names
```
GET /reports/kctaa?include_unmatched=1
```
Shows all CSV names, including those with no matches.

##### Export Results
```
GET /reports/kctaa.csv?min_score=0.9&include_unmatched=0
```
Exports matched results as CSV.

#### Configuration
- **File Path**: Set `KCTAA_NAME_LIST_PATH` in app config
- **Fuzzy Threshold**: Modify `FUZZY_MATCH_THRESHOLD` constant (default: 90)
- **Default Min Score**: Modify `DEFAULT_MIN_SCORE` constant (default: 0.9)

#### Matching Quality Indicators
- **Exact Match**: Green badge, score = 1.0, most reliable
- **Fuzzy Match**: Yellow badge, score 0.9 - 0.999, review recommended
- **No Match**: Red badge, score = 0.0, manual review needed
- **Match Count**: If > 1, multiple volunteers matched (ambiguous match)

## Conclusion

The Volunteer Matching System provides a robust, transparent, and efficient way to connect volunteers with events. By combining multiple data sources and providing clear explanations, it ensures that both administrators and volunteers understand how matches are made, leading to better outcomes and increased trust in the system.

The system is designed to be maintainable and extensible, allowing for easy updates to keyword mappings, scoring algorithms, and filtering criteria as organizational needs evolve.

The KCTAA Special Report extends this system by providing specialized name matching capabilities for cross-organizational volunteer tracking, enabling efficient identification and analysis of volunteer participation across different organizational contexts.
