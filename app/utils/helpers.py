"""
Utility functions for date parsing, string cleaning, and data formatting used throughout the application.
"""
import re
from dateutil import parser as dateutil_parser
from utils.constants import SUPPORTED_SKILL_ALIASES, VALID_SKILLS

def clean_text(text: str) -> str:
    return text.strip()

def clean_resume_text(text: str) -> str:
    return text.replace("\n", " ").strip()

def normalize_name(name: str) -> str | None:
    if not name:
        return name
    # Remove any characters that aren't letters, spaces, or periods (for initials)
    cleaned = re.sub(r'[^a-zA-Z\s\.]', '', str(name)).strip()
    if not cleaned or cleaned.lower() in ["unknown", "na", "n/a", "none", "null"]:
        return None
    return cleaned.title()

def normalize_phone(phone: str) -> str | None:
    # Remove all characters except digits
    digits_only = re.sub(r"\D", "", str(phone))
    if len(digits_only) < 10:
        return None
    # Return last 10 digits (strips country codes like +91, +1)
    return digits_only[-10:]

def normalize_email(email: str) -> str:
    return email.strip().lower()

def normalize_skills(skills):
    from utils.constants import SUPPORTED_SKILL_ALIASES, VALID_SKILLS, VALID_SOFT_SKILLS
    if not skills:
        return {"technical": [], "soft": []}
    if isinstance(skills, str):
        skills = [s.strip(" -*") for s in re.split(r'[,|•;]|\s+-\s+', skills) if s.strip(" -*")]

    tech = []
    soft = []
    for skill in skills:
        cleaned = skill.strip(" -*").lower()
        if not cleaned:
            continue
        if cleaned in SUPPORTED_SKILL_ALIASES:
            canonical = SUPPORTED_SKILL_ALIASES[cleaned]
            if canonical in VALID_SKILLS:
                tech.append(canonical)
            elif canonical in VALID_SOFT_SKILLS:
                soft.append(canonical)

    return {"technical": list(set(tech)), "soft": list(set(soft))}

def normalize_date(date_string: str | None) -> str | None:
    """Normalize any date string to YYYY-MM format. Returns None if unparseable."""
    if not date_string:
        return None
    s = str(date_string).strip()
    if s.lower() in ("present", "current", "ongoing", "till date", "now"):
        return "present"
    try:
        # dateutil handles "Aug 2023", "August 2023", "2023", "2023-08" etc.
        parsed = dateutil_parser.parse(s, default=dateutil_parser.parse("2000-01-01"))
        # If input was year-only (e.g. "2023"), don't emit a month
        if re.fullmatch(r'\d{4}', s):
            return parsed.strftime("%Y")
        return parsed.strftime("%Y-%m")
    except Exception:
        return s  # return as-is if we can't parse

def normalize_education_entries(entries: list) -> list:
    """Normalize each education dict: standardize dates and clean degree/institution strings."""
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        norm = dict(entry)
        norm["start_date"] = normalize_date(entry.get("start_date"))
        norm["end_date"] = normalize_date(entry.get("end_date"))
        # Clean up space-collapsed degree/institution strings
        if norm.get("degree"):
            norm["degree"] = _clean_collapsed_text(norm["degree"])
        if norm.get("institution"):
            norm["institution"] = _clean_collapsed_text(norm["institution"])
        # Validate CGPA: must be 0-10 or a percentage 0-100
        cgpa = norm.get("cgpa")
        norm["cgpa"] = _validate_cgpa(cgpa)
        normalized.append(norm)
    return normalized

def normalize_experience_entries(entries: list) -> list:
    """Normalize each experience dict: standardize dates and clean text."""
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        norm = dict(entry)
        norm["start_date"] = normalize_date(entry.get("start_date"))
        norm["end_date"] = normalize_date(entry.get("end_date"))
        if norm.get("title"):
            norm["title"] = _clean_collapsed_text(norm["title"])
        if norm.get("company"):
            norm["company"] = _clean_collapsed_text(norm["company"])
        # Clean bullet responsibilities
        if isinstance(norm.get("responsibilities"), list):
            norm["responsibilities"] = [
                _clean_collapsed_text(r) for r in norm["responsibilities"] if r and r.strip()
            ]
        normalized.append(norm)
    return normalized

def _clean_collapsed_text(text: str) -> str:
    """Fix PDF space-collapsed text by inserting spaces before uppercase letters
    that follow a lowercase letter with no space, e.g. 'FreelanceFull' -> 'Freelance Full'."""
    if not text:
        return text
    # Insert space before a capital letter that follows a lowercase letter
    fixed = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Collapse multiple spaces
    fixed = re.sub(r' {2,}', ' ', fixed)
    return fixed.strip()

def _validate_cgpa(cgpa) -> str | None:
    """Return the cgpa string if it looks valid (0-10 scale or % 0-100), else None."""
    if not cgpa:
        return None
    s = str(cgpa).strip()
    # e.g. "8.5/10"
    frac = re.fullmatch(r'([\d.]+)\s*/\s*([\d.]+)', s)
    if frac:
        try:
            val = float(frac.group(1))
            scale = float(frac.group(2))
            if 0 <= val <= scale:
                return s
        except ValueError:
            pass
        return None
    # e.g. "99.0" or "99.0%"
    pct = re.fullmatch(r'([\d.]+)%?', s)
    if pct:
        try:
            val = float(pct.group(1))
            # If <= 10, it's likely a GPA; if <= 100 it's a percentage
            if 0 <= val <= 100:
                return s
        except ValueError:
            pass
    return None
