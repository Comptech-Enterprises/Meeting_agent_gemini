"""Central configuration. All tunables and secrets are loaded here.

Secrets come from a `.env` file in the project root (see `.env.example`).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Paths -------------------------------------------------------------------
TEMP_DIR = Path("/tmp") if os.getenv("VERCEL") else BASE_DIR / "temp"  # on Vercel /tmp is writable
STATIC_DIR = BASE_DIR / "static"      # frontend files
FONTS_DIR = BASE_DIR / "fonts"        # bundled Unicode fonts for the PDF
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# --- Secrets (from .env) -----------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()       # Gemini API key
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()                # Brevo API key
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()  # Gmail App Password

# --- AWS S3 (Direct Storage) -------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1").strip()
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "eventyst-videos").strip()
S3_PREFIX = os.getenv("S3_PREFIX", "uploads/").strip()
S3_ENABLED = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME)

# --- Gemini ------------------------------------------------------------------
# Change the model here (or set GEMINI_MODEL in .env).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()
FILE_PROCESSING_TIMEOUT_S = 300   # max wait for uploaded video to become ACTIVE
POLL_INTERVAL_S = 3

# --- Email -------------------------------------------------------------------
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "brevo").strip().lower()   # brevo | gmail
# Sender address (BREVO_SENDER_EMAIL is accepted as a legacy alias).
SENDER_EMAIL = (os.getenv("SENDER_EMAIL") or os.getenv("BREVO_SENDER_EMAIL") or "rk26.ftw@gmail.com").strip()
SENDER_NAME = (os.getenv("SENDER_NAME") or os.getenv("BREVO_SENDER_NAME") or "Employee Happiness Awards").strip()
EMAIL_SUBJECT = "EHA | Insights & Analysis Report"
MAX_ATTACHMENT_MB = 5
SEND_LIMIT_PER_MINUTE = 10

# --- Uploads -----------------------------------------------------------------
MAX_UPLOAD_MB = 500
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
VIDEO_MIME_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}

# --- EHA Report Settings & Category-to-Pillar Mappings -----------------------
REPORT_TITLE = "EHA | Insights & Analysis Report"
PDF_FOOTER_TEXT = "Employee Happiness Awards | Confidential"
DEFAULT_AWARDS_EDITION = "Employee Happiness Awards UAE 2026"
EHA_LOGO_PATH = STATIC_DIR / "eha_logo.png"

# The six pillars of the employee lifecycle
EHA_LIFECYCLE_PILLARS = [
    "Attraction & Onboarding",
    "Learning & Growth",
    "Well-being",
    "Leadership & Strategy",
    "Culture",
    "Retention & Exit",
]

# Official 25 EHA Confirmed Company Categories with descriptions and pillar mappings
EHA_CONFIRMED_CATEGORIES = [
    {
        "id": 1,
        "name": "Best Employee Wellness Initiative",
        "pillars": ["Well-being", "Culture"],
        "desc": "Honours impactful wellness programs enhancing physical or emotional well-being, demonstrating strong execution and measurable improvements in productivity, and overall employee satisfaction.",
    },
    {
        "id": 2,
        "name": "Best Flexible Working Program",
        "pillars": ["Well-being", "Culture", "Leadership & Strategy"],
        "desc": "Recognizes effective remote, hybrid, or onsite models that balance performance and well-being, improve happiness, reduce costs, and align flexible working practices with overall business goals.",
    },
    {
        "id": 3,
        "name": "Best Workspace Design",
        "pillars": ["Well-being", "Culture"],
        "desc": "Celebrates smart, ergonomic, and wellness-driven workplaces that reflect company culture and boost productivity through thoughtful collaboration zones, innovative meeting spaces, and rejuvenation areas.",
    },
    {
        "id": 4,
        "name": "Most Supportive ‘Return to Work’ Program",
        "pillars": ["Attraction & Onboarding", "Learning & Growth", "Well-being", "Culture"],
        "desc": "Honours organizations enabling smooth comebacks, especially for women and caregivers, through flexibility, mentoring, fair pay, and structured growth pathways that support successful workforce reintegration.",
    },
    {
        "id": 5,
        "name": "Best Workplace for Parents in the UAE",
        "pillars": ["Well-being", "Culture", "Retention & Exit"],
        "desc": "Recognizes companies supporting working parents with flexibility, inclusive leave policies, childcare access, and an empathetic culture that enables balancing family needs with career growth.",
    },
    {
        "id": 6,
        "name": "Best Diversity and Inclusion Program",
        "pillars": ["Culture", "Leadership & Strategy", "Attraction & Onboarding"],
        "desc": "Rewards workplaces creating diverse, equitable environments across age, gender, ethnicity, and nationality, ensuring all employees feel valued, included, and empowered.",
    },
    {
        "id": 7,
        "name": "Best Employee Reward & Recognition Strategy",
        "pillars": ["Culture", "Retention & Exit", "Well-being"],
        "desc": "Honours innovative, fair rewards tailored to multi-generational teams, addressing evolving motivators across Gen Z, Millennials, and beyond.",
    },
    {
        "id": 8,
        "name": "Best L&D Strategy",
        "pillars": ["Learning & Growth", "Leadership & Strategy"],
        "desc": "Recognizes organizations offering advanced learning programs that prepare employees for future business needs while supporting their long-term professional growth.",
    },
    {
        "id": 9,
        "name": "Best Internship Program",
        "pillars": ["Attraction & Onboarding", "Learning & Growth"],
        "desc": "Celebrates companies nurturing young talent through structured internships that offer real experience, mentorship, and future career pathways.",
    },
    {
        "id": 10,
        "name": "Best Leadership Succession Strategy",
        "pillars": ["Leadership & Strategy", "Learning & Growth", "Retention & Exit"],
        "desc": "Honours structured, forward-looking programs that identify and develop high-potential talent for future leadership roles internally, ensuring business continuity and growth.",
    },
    {
        "id": 11,
        "name": "Best ‘Women-in-Leadership’ Program",
        "pillars": ["Leadership & Strategy", "Culture", "Learning & Growth"],
        "desc": "Recognizes organizations advancing women leaders by creating inclusive cultures, equitable opportunities, and clear pathways for female career progression.",
    },
    {
        "id": 12,
        "name": "Talent Acquisition Strategy of the Year",
        "pillars": ["Attraction & Onboarding", "Culture"],
        "desc": "Celebrates recruitment teams using innovative hiring methods, strong employer branding, analytics, and digital platforms, including social media, to attract and secure top talent aligned with long-term business goals.",
    },
    {
        "id": 13,
        "name": "Best Employee Induction Program",
        "pillars": ["Attraction & Onboarding", "Culture", "Learning & Growth"],
        "desc": "Honours onboarding programs that integrate new employees quickly and smoothly, strengthening adaptation, cultural alignment, and early productivity.",
    },
    {
        "id": 14,
        "name": "Best Community Impact Initiative",
        "pillars": ["Culture", "Leadership & Strategy"],
        "desc": "Recognizes organizations embedding community engagement into their ethos and involving employees in creating meaningful, measurable social impact.",
    },
    {
        "id": 15,
        "name": "Best Retention Initiative",
        "pillars": ["Retention & Exit", "Culture", "Well-being"],
        "desc": "Celebrates companies achieving high retention through strategies that build loyalty, motivation, and long-term employee satisfaction.",
    },
    {
        "id": 16,
        "name": "Best Employee Driven Business Change",
        "pillars": ["Culture", "Leadership & Strategy", "Well-being"],
        "desc": "Honours workplaces where employee feedback and ideas directly inspire positive cultural or business transformation.",
    },
    {
        "id": 17,
        "name": "Best Use of Technology & AI in HR",
        "pillars": ["Leadership & Strategy", "Culture", "Attraction & Onboarding"],
        "desc": "Recognizes organizations transforming HR through AI, analytics, automation, and digital solutions to enhance employee experience and amplify business impact.",
    },
    {
        "id": 18,
        "name": "Best Use of Technology to Drive Learning Initiatives",
        "pillars": ["Learning & Growth", "Leadership & Strategy"],
        "desc": "Celebrates organizations offering tech-enabled, real-time learning solutions that build capability and deliver measurable performance impact.",
    },
    {
        "id": 19,
        "name": "Best Inclusion Strategy for People of Determination",
        "pillars": ["Culture", "Well-being", "Attraction & Onboarding"],
        "desc": "Honours organizations fostering inclusive, accessible environments through supportive infrastructure, policies, training, and equal opportunity practices.",
    },
    {
        "id": 20,
        "name": "Best Company to Work For – Large",
        "pillars": EHA_LIFECYCLE_PILLARS,
        "desc": "Recognizes companies with 250+ employees that maintain progressive, fair, and people-centric workplaces.",
    },
    {
        "id": 21,
        "name": "Best Company to Work For – Medium",
        "pillars": EHA_LIFECYCLE_PILLARS,
        "desc": "Honours organizations with 50–249 employees creating positive, supportive, and engaging workplaces.",
    },
    {
        "id": 22,
        "name": "Best Company to Work For – Small",
        "pillars": EHA_LIFECYCLE_PILLARS,
        "desc": "Celebrates companies under 50 employees that ensure a happy, fair, and growth-focused workplace culture.",
    },
    {
        "id": 23,
        "name": "HR Team of the Year",
        "pillars": EHA_LIFECYCLE_PILLARS,
        "desc": "Honours HR teams leading transformative, high-impact practices that elevate employee happiness and drive strong business performance.",
    },
    {
        "id": 24,
        "name": "Excellence in Emiratization (New Category)",
        "pillars": ["Attraction & Onboarding", "Learning & Growth", "Leadership & Strategy", "Culture"],
        "desc": "Recognizes companies committed to advancing Emirati talent through structured development pathways, leadership opportunities, and long-term national workforce investment.",
    },
    {
        "id": 25,
        "name": "Best Workplace for Gen Z (New Category)",
        "pillars": ["Culture", "Well-being", "Learning & Growth", "Attraction & Onboarding"],
        "desc": "Celebrates organizations aligned with Gen Z values, flexibility, inclusivity, authenticity, digital-first culture, and meaningful purpose at work.",
    },
]


def _normalize_category_key(text: str) -> str:
    """Normalize quotes, dashes, whitespace, and symbols for robust matching."""
    s = text.lower().strip()
    s = re.sub(r"[‘’'\"`]", "", s)
    s = re.sub(r"[–—−]", "-", s)
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)
    return s


# Build normalized lookup dictionary covering all 25 categories and common aliases
CATEGORY_PILLAR_MAPPING: dict[str, list[str]] = {}
for cat in EHA_CONFIRMED_CATEGORIES:
    norm_name = _normalize_category_key(cat["name"])
    CATEGORY_PILLAR_MAPPING[norm_name] = cat["pillars"]
    # Strip optional parenthetical qualifiers (e.g. "(new category)")
    clean_name = re.sub(r"\s*\(.*?\)", "", norm_name).strip()
    CATEGORY_PILLAR_MAPPING[clean_name] = cat["pillars"]

# Additional common aliases for presenter abbreviations
CATEGORY_PILLAR_MAPPING.update({
    "best company to work for": EHA_LIFECYCLE_PILLARS,
    "best ld strategy": ["Learning & Growth", "Leadership & Strategy"],
    "best landd strategy": ["Learning & Growth", "Leadership & Strategy"],
    "best learning and development strategy": ["Learning & Growth", "Leadership & Strategy"],
    "women in leadership": ["Leadership & Strategy", "Culture", "Learning & Growth"],
    "people of determination": ["Culture", "Well-being", "Attraction & Onboarding"],
    "emiratization": ["Attraction & Onboarding", "Learning & Growth", "Leadership & Strategy", "Culture"],
    "gen z": ["Culture", "Well-being", "Learning & Growth", "Attraction & Onboarding"],
    "return to work": ["Attraction & Onboarding", "Learning & Growth", "Well-being", "Culture"],
    "wellness initiative": ["Well-being", "Culture"],
    "flexible working": ["Well-being", "Culture", "Leadership & Strategy"],
    "workspace design": ["Well-being", "Culture"],
    "workplace for parents": ["Well-being", "Culture", "Retention & Exit"],
    "diversity and inclusion": ["Culture", "Leadership & Strategy", "Attraction & Onboarding"],
    "reward and recognition": ["Culture", "Retention & Exit", "Well-being"],
    "talent acquisition": ["Attraction & Onboarding", "Culture"],
    "employee induction": ["Attraction & Onboarding", "Culture", "Learning & Growth"],
    "community impact": ["Culture", "Leadership & Strategy"],
    "retention initiative": ["Retention & Exit", "Culture", "Well-being"],
    "employee driven business change": ["Culture", "Leadership & Strategy", "Well-being"],
    "ai in hr": ["Leadership & Strategy", "Culture", "Attraction & Onboarding"],
    "technology in hr": ["Leadership & Strategy", "Culture", "Attraction & Onboarding"],
    "technology to drive learning": ["Learning & Growth", "Leadership & Strategy"],
    "hr team": EHA_LIFECYCLE_PILLARS,
})


def get_applicable_pillars(category: str | None) -> list[str]:
    """Resolve applicable pillars based on category string, defaulting to all six pillars."""
    if not category:
        return list(EHA_LIFECYCLE_PILLARS)
    norm = _normalize_category_key(category)
    # 1. Exact match in normalized dictionary
    if norm in CATEGORY_PILLAR_MAPPING:
        return list(CATEGORY_PILLAR_MAPPING[norm])
    # 2. Substring match
    for cat_key, pillars in CATEGORY_PILLAR_MAPPING.items():
        if cat_key in norm or norm in cat_key:
            return list(pillars)
    # 3. Fallback: evaluate all 6 pillars
    return list(EHA_LIFECYCLE_PILLARS)


# --- Legacy compatibility questions (fallback) ------------------------------
QUESTIONS = [
    "Six Pillars of Wellbeing: What are the six pillars of employee wellbeing identified or referenced in the presentation, and what is the organisation's core philosophy on each?",
    "Initiatives Implemented: What specific programmes, initiatives, or workplace policies have been implemented to support employee wellbeing across these pillars?",
    "Key Findings & Impact: What measurable improvements, metrics, survey feedback, or notable findings resulted from the initiatives discussed?",
    "Growth & Professional Development: How does the organisation foster continuous learning, skill enhancement, and career growth within its employee wellbeing framework?",
    "Feedback & Long-term Sustainability: How is employee feedback gathered and evaluated, and how does leadership ensure these initiatives remain effective and sustainable over time?",
]
