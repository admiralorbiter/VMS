"""
Recruitment keyword derivation and scoring helpers.

Provides keyword extraction (type-based, text-based, semantic, contextual,
pattern-based), fallback keyword generation, and scoring utility functions
for the volunteer recruitment candidate matching system.

Extracted from routes/reports/recruitment.py (TD-041).
"""

from datetime import datetime, timezone

from models.contact import LocalStatusEnum
from models.event import EventType

# ── Type-Based Keyword Derivation ──────────────────────────────────────


def derive_type_keywords(event_type: EventType) -> list[str]:
    """Derive keywords based on event type with comprehensive mappings."""
    type_mappings = {
        EventType.DATA_VIZ: [
            "data",
            "analytics",
            "bi",
            "visualization",
            "tableau",
            "power bi",
            "excel",
            "sql",
            "python",
            "r",
            "statistics",
            "reporting",
        ],
        EventType.CAREER_FAIR: [
            "career",
            "job search",
            "networking",
            "professional",
            "resume",
            "interview",
            "employment",
            "workforce",
        ],
        EventType.CAREER_SPEAKER: [
            "career",
            "professional development",
            "leadership",
            "industry",
            "expertise",
            "experience",
            "mentoring",
        ],
        EventType.CAREER_JUMPING: [
            "career transition",
            "skill development",
            "professional growth",
            "industry change",
            "adaptability",
        ],
        EventType.EMPLOYABILITY_SKILLS: [
            "soft skills",
            "communication",
            "teamwork",
            "problem solving",
            "leadership",
            "professional",
            "workplace",
        ],
        EventType.FINANCIAL_LITERACY: [
            "finance",
            "financial",
            "accounting",
            "budgeting",
            "investing",
            "banking",
            "economics",
            "money management",
        ],
        EventType.MATH_RELAYS: [
            "mathematics",
            "math",
            "stem",
            "education",
            "teaching",
            "problem solving",
            "analytical",
        ],
        EventType.CLASSROOM_SPEAKER: [
            "education",
            "teaching",
            "presentation",
            "communication",
            "public speaking",
            "knowledge sharing",
        ],
        EventType.MENTORING: [
            "mentoring",
            "guidance",
            "coaching",
            "leadership",
            "experience",
            "development",
            "support",
        ],
        EventType.INTERNSHIP: [
            "internship",
            "entry level",
            "learning",
            "experience",
            "professional development",
            "career start",
        ],
        EventType.VIRTUAL_SESSION: [
            # No type keywords for virtual sessions — focus on content analysis
        ],
        EventType.CONNECTOR_SESSION: [
            "networking",
            "connections",
            "relationship building",
            "professional network",
            "collaboration",
        ],
        EventType.WORKPLACE_VISIT: [
            "workplace",
            "office",
            "corporate",
            "business",
            "professional environment",
            "industry exposure",
            "real world",
        ],
        EventType.CAMPUS_VISIT: [
            "campus",
            "college",
            "university",
            "higher education",
            "academic",
            "student life",
            "college preparation",
        ],
        EventType.COLLEGE_OPTIONS: [
            "college",
            "university",
            "higher education",
            "academic planning",
            "college preparation",
            "admissions",
        ],
        EventType.FAFSA: [
            "fafsa",
            "financial aid",
            "college funding",
            "scholarships",
            "student loans",
            "college costs",
        ],
        EventType.IGNITE: [
            "ignite",
            "leadership",
            "youth development",
            "empowerment",
            "community service",
            "social impact",
        ],
        EventType.DIA: [
            "dia",
            "diversity",
            "inclusion",
            "access",
            "equity",
            "representation",
            "social justice",
        ],
    }

    return type_mappings.get(event_type, [])


# ── Text-Based Keyword Derivation ──────────────────────────────────────


def derive_text_keywords(title: str, description: str = "") -> list[str]:
    """Extract keywords from event title and description using NLP-like techniques."""
    text = f"{title or ''} {description or ''}".lower()
    keywords = set()

    # Common professional domains
    domain_patterns = {
        "technology": [
            "tech",
            "software",
            "programming",
            "coding",
            "developer",
            "engineer",
            "it",
            "computer",
        ],
        "business": [
            "business",
            "management",
            "strategy",
            "operations",
            "consulting",
            "entrepreneur",
        ],
        "healthcare": [
            "health",
            "medical",
            "clinical",
            "patient",
            "healthcare",
            "nursing",
            "pharmacy",
        ],
        "education": [
            "education",
            "teaching",
            "learning",
            "academic",
            "curriculum",
            "instruction",
            "classroom",
            "student",
            "elementary",
            "primary",
            "k-1",
            "k-2",
            "k-3",
            "k-4",
            "k-5",
            "early childhood",
        ],
        "finance": [
            "finance",
            "financial",
            "accounting",
            "banking",
            "investment",
            "audit",
        ],
        "marketing": [
            "marketing",
            "advertising",
            "branding",
            "social media",
            "digital marketing",
        ],
        "sales": [
            "sales",
            "business development",
            "account management",
            "client relations",
        ],
        "engineering": [
            "engineering",
            "mechanical",
            "electrical",
            "civil",
            "chemical",
            "design",
        ],
        "science": [
            "science",
            "research",
            "laboratory",
            "experiment",
            "analysis",
            "scientific",
        ],
        "arts": [
            "arts",
            "creative",
            "design",
            "visual",
            "media",
            "production",
            "paint",
            "painting",
            "artistic",
            "creativity",
            "craft",
            "drawing",
            "sculpture",
            "photography",
            "music",
            "dance",
            "theater",
            "performance",
            "expression",
            "imagination",
        ],
        "civics": [
            "civics",
            "citizenship",
            "government",
            "democracy",
            "community",
            "social studies",
            "responsible",
            "citizen",
            "civic",
            "patriotism",
            "rights",
            "responsibilities",
        ],
    }

    # Check for domain matches — use word boundaries to avoid false positives
    for domain, terms in domain_patterns.items():
        domain_matches = []
        for term in terms:
            if (
                f" {term} " in f" {text} "
                or text.startswith(term)
                or text.endswith(term)
            ):
                domain_matches.append(term)

        if domain_matches:
            keywords.update(domain_matches[:3])  # Limit to top 3 terms per domain

    # Specific tool/technology detection — only if explicitly mentioned
    tools = [
        "excel",
        "tableau",
        "power bi",
        "sql",
        "python",
        "r",
        "spss",
        "sas",
        "quickbooks",
        "salesforce",
    ]
    for tool in tools:
        if f" {tool} " in f" {text} " or text.startswith(tool) or text.endswith(tool):
            keywords.add(tool)

    # Professional level indicators
    levels = [
        "entry level",
        "mid level",
        "senior",
        "executive",
        "director",
        "manager",
        "lead",
        "principal",
    ]
    for level in levels:
        if level in text:
            keywords.add(level)

    return list(keywords)


def derive_format_keywords(event_format) -> list[str]:
    """Derive keywords based on event format."""
    if hasattr(event_format, "value"):
        if "virtual" in event_format.value.lower():
            return ["virtual", "remote", "online", "digital"]
        elif "in_person" in event_format.value.lower():
            return ["in-person", "onsite", "face-to-face"]
    return []


def derive_location_keywords(location: str, school: str) -> list[str]:
    """Derive keywords based on location context."""
    keywords = []
    if location:
        location_lower = location.lower()
        if any(word in location_lower for word in ["downtown", "urban", "city"]):
            keywords.extend(["urban", "city", "downtown"])
        if any(word in location_lower for word in ["suburban", "suburb"]):
            keywords.extend(["suburban", "suburb"])
        if any(word in location_lower for word in ["rural", "country"]):
            keywords.extend(["rural", "country"])
    return keywords


# ── Hybrid Fallback System ─────────────────────────────────────────────

_STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "up",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "among",
    "inside",
    "outside",
}


def extract_meaningful_words(text: str) -> list[str]:
    """Extract meaningful words from event titles for fallback keyword generation."""
    words = [word.lower().strip('.,!?()[]{}":;') for word in text.split()]
    meaningful_words = [
        word for word in words if word not in _STOP_WORDS and len(word) > 2
    ]
    return meaningful_words[:5]


def derive_contextual_keywords(event_type: EventType, title: str) -> list[str]:
    """Generate subject-relevant keywords based on event type and title patterns."""
    contextual_keywords = []
    title_lower = title.lower()

    # Arts & Creativity
    if any(
        word in title_lower
        for word in [
            "paint",
            "art",
            "creative",
            "design",
            "drawing",
            "sculpture",
        ]
    ):
        contextual_keywords.extend(
            ["artistic", "creativity", "visual arts", "design", "painting"]
        )
    # STEM & Technical
    elif any(
        word in title_lower
        for word in [
            "math",
            "science",
            "stem",
            "technology",
            "engineering",
            "coding",
        ]
    ):
        contextual_keywords.extend(
            ["stem", "technical", "analytical", "problem-solving", "engineering"]
        )
    # Business & Professional
    elif any(
        word in title_lower
        for word in [
            "career",
            "job",
            "work",
            "business",
            "professional",
        ]
    ):
        contextual_keywords.extend(
            ["business", "professional", "workplace", "career development"]
        )
    # Civic & Community
    elif any(
        word in title_lower
        for word in [
            "civics",
            "citizen",
            "government",
            "community",
            "social",
        ]
    ):
        contextual_keywords.extend(
            ["civic", "community", "government", "social responsibility"]
        )
    # Financial & Economic
    elif any(
        word in title_lower
        for word in [
            "finance",
            "money",
            "budget",
            "investment",
            "economic",
        ]
    ):
        contextual_keywords.extend(
            ["financial", "economics", "money management", "investment"]
        )
    # Health & Wellness
    elif any(
        word in title_lower
        for word in [
            "health",
            "medical",
            "wellness",
            "fitness",
            "nutrition",
        ]
    ):
        contextual_keywords.extend(["health", "medical", "wellness", "healthcare"])
    # Education & Learning
    elif any(
        word in title_lower
        for word in [
            "education",
            "learning",
            "teaching",
            "academic",
            "student",
        ]
    ):
        contextual_keywords.extend(["education", "learning", "academic", "teaching"])

    return contextual_keywords


def derive_fallback_keywords(event) -> tuple[dict[str, list], dict[str, dict]]:
    """Generate fallback keywords when primary methods fail."""
    keywords = {}
    explanations = {}

    # Extract meaningful words from title
    meaningful_words = extract_meaningful_words(event.title)
    if meaningful_words:
        keywords["fallback_text"] = meaningful_words
        explanations["fallback_text"] = {
            "explanation": f"Meaningful words from title: '{event.title}'",
            "keywords": meaningful_words,
        }

    # Add contextual keywords
    contextual_kw = derive_contextual_keywords(event.type, event.title)
    if contextual_kw:
        keywords["contextual"] = contextual_kw
        explanations["contextual"] = {
            "explanation": f"Contextual keywords for {event.type.value.replace('_', ' ').title()} event",
            "keywords": contextual_kw,
        }

    # Universal fallback — ensure we always have something
    if not keywords:
        universal_keywords = ["volunteer", "event", "participation"]
        keywords["universal"] = universal_keywords
        explanations["universal"] = {
            "explanation": "General volunteer matching criteria",
            "keywords": universal_keywords,
        }

    return keywords, explanations


# ── Phase 2: Smart Enhancement Functions ───────────────────────────────


def detect_event_patterns(title: str) -> dict[str, list]:
    """Detect common event title patterns and extract relevant keywords."""
    patterns = {}
    title_lower = title.lower()

    if any(
        phrase in title_lower
        for phrase in [
            "how to",
            "learning to",
            "guide to",
            "introduction to",
        ]
    ):
        patterns["skill_development"] = [
            "tutorial",
            "learning",
            "skill building",
            "instruction",
        ]
    if any(
        phrase in title_lower
        for phrase in [
            "career in",
            "working in",
            "jobs in",
            "opportunities in",
        ]
    ):
        patterns["industry_focus"] = [
            "career guidance",
            "industry knowledge",
            "professional development",
            "workplace insights",
        ]
    if any(
        phrase in title_lower
        for phrase in [
            "building",
            "creating",
            "developing",
            "designing",
        ]
    ):
        patterns["project_based"] = [
            "hands-on",
            "project work",
            "creation",
            "development",
        ]
    if any(
        phrase in title_lower
        for phrase in [
            "understanding",
            "exploring",
            "discovering",
            "investigating",
        ]
    ):
        patterns["knowledge_discovery"] = [
            "research",
            "exploration",
            "investigation",
            "discovery",
        ]
    if any(
        phrase in title_lower
        for phrase in [
            "connecting",
            "networking",
            "building relationships",
            "collaborating",
        ]
    ):
        patterns["relationship_building"] = [
            "networking",
            "collaboration",
            "relationship building",
            "partnerships",
        ]
    if any(
        phrase in title_lower
        for phrase in [
            "preparing for",
            "getting ready for",
            "planning for",
            "preparing to",
        ]
    ):
        patterns["preparation"] = [
            "planning",
            "preparation",
            "readiness",
            "organization",
        ]

    return patterns


def analyze_semantic_context(title: str, description: str = "") -> dict[str, list]:
    """Analyze semantic context of event title and description."""
    semantic_keywords = {}
    text = f"{title} {description}".lower()

    # Emotional/Engagement Context
    engagement_words = [
        "inspire",
        "empower",
        "transform",
        "discover",
        "explore",
        "innovate",
        "challenge",
        "achieve",
    ]
    if any(word in text for word in engagement_words):
        semantic_keywords["engagement"] = [
            "motivational",
            "inspirational",
            "engaging",
            "dynamic",
        ]

    # Collaborative Context
    collab_words = [
        "team",
        "together",
        "group",
        "collaborate",
        "partner",
        "community",
        "collective",
    ]
    if any(word in text for word in collab_words):
        semantic_keywords["collaborative"] = [
            "teamwork",
            "collaboration",
            "partnership",
            "cooperative",
        ]

    # Hands-on/Practical Context
    practical_words = [
        "hands-on",
        "practical",
        "workshop",
        "lab",
        "demo",
        "demonstration",
        "project",
        "build",
    ]
    if any(word in text for word in practical_words):
        semantic_keywords["practical"] = [
            "hands-on",
            "practical",
            "experiential",
            "applied",
        ]

    # Leadership Context
    leadership_words = [
        "lead",
        "leadership",
        "manage",
        "director",
        "executive",
        "decision",
        "strategic",
    ]
    if any(word in text for word in leadership_words):
        semantic_keywords["leadership"] = [
            "leadership",
            "management",
            "strategic",
            "executive",
        ]

    # Social Impact Context
    impact_words = [
        "community",
        "social",
        "nonprofit",
        "volunteer",
        "service",
        "impact",
        "give back",
    ]
    if any(word in text for word in impact_words):
        semantic_keywords["social_impact"] = [
            "community service",
            "social responsibility",
            "volunteering",
            "helping others",
            "social impact",
        ]

    return semantic_keywords


def generate_dynamic_keywords(event) -> dict[str, list]:
    """Generate dynamic keywords based on event characteristics and patterns."""
    dynamic_keywords = {}

    # Pattern detection
    patterns = detect_event_patterns(event.title)
    if patterns:
        dynamic_keywords["patterns"] = []
        for pattern_keywords in patterns.values():
            dynamic_keywords["patterns"].extend(pattern_keywords)

    # Semantic analysis
    semantic_context = analyze_semantic_context(
        event.title, getattr(event, "description", "")
    )
    if semantic_context:
        dynamic_keywords["semantic"] = []
        for semantic_keywords in semantic_context.values():
            dynamic_keywords["semantic"].extend(semantic_keywords)

    # Event complexity analysis
    title_words = len(event.title.split())
    if title_words > 8:
        dynamic_keywords["complexity"] = [
            "detailed",
            "comprehensive",
            "in-depth",
            "thorough",
        ]
    elif title_words < 4:
        dynamic_keywords["complexity"] = [
            "focused",
            "targeted",
            "specific",
            "concentrated",
        ]

    # Audience level detection
    audience_indicators = {
        "beginner": ["intro", "basics", "101", "fundamentals", "getting started"],
        "intermediate": [
            "intermediate",
            "advanced",
            "expert",
            "professional",
            "experienced",
        ],
        "all_levels": ["all levels", "everyone", "beginners welcome", "open to all"],
    }

    title_lower = event.title.lower()
    for level, indicators in audience_indicators.items():
        if any(indicator in title_lower for indicator in indicators):
            dynamic_keywords["audience_level"] = [
                level,
                "appropriate for",
                "suitable for",
            ]
            break

    return dynamic_keywords


# ── Main Keyword Orchestrator ──────────────────────────────────────────


def derive_keywords(event, custom_keywords: str = "") -> tuple[dict, dict]:
    """
    Enhanced keyword derivation that provides comprehensive matching criteria
    and clear explanations of how each keyword category was derived.

    Args:
        event: Event object with title, type, format, location, school, skills
        custom_keywords: Optional comma-separated custom keywords from user

    Returns:
        Tuple of (keywords_dict, explanations_dict)
    """
    keywords = {}
    explanations = {}

    # 0. Custom Keywords (HIGHEST PRIORITY — user-specified)
    if custom_keywords:
        custom_kw_list = [
            kw.strip().lower() for kw in custom_keywords.split(",") if kw.strip()
        ]
        if custom_kw_list:
            keywords["custom"] = custom_kw_list
            explanations["custom"] = {
                "explanation": f"User-specified custom keywords: '{custom_keywords}'",
                "keywords": custom_kw_list,
            }

    # 1. Title/Description Text Analysis (HIGHEST PRIORITY — content matters most)
    text_keywords = derive_text_keywords(event.title, getattr(event, "description", ""))
    if text_keywords:
        keywords["text"] = text_keywords
        explanations["text"] = {
            "explanation": f"Text analysis of: '{event.title}'",
            "keywords": text_keywords,
        }
        if getattr(event, "description", ""):
            explanations["text"]["explanation"] += " + description"

    # 2. Event Skills (most specific and relevant)
    if hasattr(event, "skills") and event.skills:
        skill_names = [skill.name.lower() for skill in event.skills if skill.name]
        if skill_names:
            keywords["skills"] = skill_names
            explanations["skills"] = {
                "explanation": f"Event skills: {', '.join(skill_names)}",
                "keywords": skill_names,
            }

    # 3. Event Type-based Keywords (contextual, not format-focused)
    type_keywords = derive_type_keywords(event.type)
    if type_keywords:
        # For VIRTUAL_SESSION, skip type keywords — focus on content
        if event.type == EventType.VIRTUAL_SESSION:
            pass
        else:
            keywords["type"] = type_keywords
            explanations["type"] = {
                "explanation": f"Event type: {event.type.value.replace('_', ' ').title()}",
                "keywords": type_keywords,
            }

    # 4. Event Format Considerations (minimal weight for virtual sessions)
    format_keywords = derive_format_keywords(event.format)
    if format_keywords:
        if event.type == EventType.VIRTUAL_SESSION:
            pass
        else:
            keywords["format"] = format_keywords
            explanations["format"] = {
                "explanation": f"Event format: {event.format.value.replace('_', ' ').title()}",
                "keywords": format_keywords,
            }

    # 5. Location/School Context
    location_keywords = derive_location_keywords(event.location, event.school)
    if location_keywords:
        keywords["location"] = location_keywords
        explanations["location"] = {
            "explanation": f"Location context: {event.location or 'N/A'}",
            "keywords": location_keywords,
        }

    # 6. Phase 2: Smart Enhancement — Pattern Recognition & Semantic Analysis
    dynamic_keywords = generate_dynamic_keywords(event)
    if dynamic_keywords:
        for category, words in dynamic_keywords.items():
            if words:
                keywords[f"smart_{category}"] = words
                explanations[f"smart_{category}"] = {
                    "explanation": f"Smart analysis: {category.replace('_', ' ').title()}",
                    "keywords": words,
                }

    # 7. Hybrid Fallback System — Ensure Universal Coverage
    if not keywords:
        fallback_kw, fallback_explanations = derive_fallback_keywords(event)
        keywords.update(fallback_kw)
        explanations.update(fallback_explanations)
    else:
        contextual_kw = derive_contextual_keywords(event.type, event.title)
        if contextual_kw:
            existing_words = set()
            for category_words in keywords.values():
                existing_words.update([w.lower() for w in category_words])

            new_contextual = [
                k for k in contextual_kw if k.lower() not in existing_words
            ]
            if new_contextual:
                keywords["contextual"] = new_contextual
                explanations["contextual"] = {
                    "explanation": "Subject-relevant keywords based on event content analysis",
                    "keywords": new_contextual,
                }

    return keywords, explanations


# ── Scoring Utilities ──────────────────────────────────────────────────


def recency_boost(last_date) -> float:
    """Calculate recency boost based on last participation date."""
    if not last_date:
        return 0.0
    try:
        days = (datetime.now(timezone.utc).date() - last_date).days
    except Exception:
        return 0.0
    if days <= 90:
        return 0.35
    if days <= 180:
        return 0.15
    return 0.0


def local_boost(local_status) -> float:
    """Calculate local status boost for scoring."""
    try:
        if local_status == LocalStatusEnum.local:
            return 0.2
        if local_status == LocalStatusEnum.partial:
            return 0.1
    except Exception:
        pass
    return 0.0
