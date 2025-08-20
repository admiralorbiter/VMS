# Volunteer Matching System Documentation

## Overview

The Volunteer Matching System is an intelligent, transparent algorithm that automatically finds and ranks the best volunteer candidates for specific events. It uses a multi-dimensional approach combining event characteristics, volunteer profiles, and historical data to provide explainable recommendations.

## System Architecture

### 1. Event Analysis & Keyword Derivation
The system analyzes events through multiple lenses to generate comprehensive matching criteria:

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

#### Filtered Results
```
GET /reports/recruitment/candidates?event_id=123&min_score=1.5&limit=50
```
Shows only candidates with scores ≥1.5, limited to 50 results.

#### CSV Export
```
GET /reports/recruitment/candidates.csv?event_id=123
```
Exports candidate list as CSV for external analysis.

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

### 9. Troubleshooting

#### Common Issues
1. **Low Match Quality**: Check keyword derivation for event type
2. **Slow Performance**: Verify caching is working properly
3. **Missing Volunteers**: Check governance filter settings
4. **Score Inconsistencies**: Verify keyword matching logic

#### Debug Tools
- Debug keyword display shows all keywords used
- Score breakdowns show individual component calculations
- Cache status indicates if results are fresh or cached

## Conclusion

The Volunteer Matching System provides a robust, transparent, and efficient way to connect volunteers with events. By combining multiple data sources and providing clear explanations, it ensures that both administrators and volunteers understand how matches are made, leading to better outcomes and increased trust in the system.

The system is designed to be maintainable and extensible, allowing for easy updates to keyword mappings, scoring algorithms, and filtering criteria as organizational needs evolve.
