import json
import os

SOURCE_TYPES = [
    "recruiter_csv",
    "ats_json",
    "resume_pdf",
    "linkedin",
    "recruiter_notes"
]

# Load taxonomy
taxonomy_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'skills_taxonomy.json')
SUPPORTED_SKILL_ALIASES = {}
VALID_SKILLS = set()
VALID_SOFT_SKILLS = set()

if os.path.exists(taxonomy_path):
    with open(taxonomy_path, 'r') as f:
        taxonomy = json.load(f)
        for item in taxonomy.get("technical", []):
            canonical = item["canonical"]
            VALID_SKILLS.add(canonical)
            for alias in item["aliases"]:
                SUPPORTED_SKILL_ALIASES[alias.lower()] = canonical
        for item in taxonomy.get("non_technical", []):
            canonical = item["canonical"]
            VALID_SOFT_SKILLS.add(canonical)
            for alias in item["aliases"]:
                SUPPORTED_SKILL_ALIASES[alias.lower()] = canonical

EXACT_FIELDS = [
    "email",
    "phone",
    "dob"
]

FUZZY_FIELDS = [
    "name",
    "current_company",
    "designation"
]

MULTI_VALUE_FIELDS = [
    "skills",
    "soft_skills",
    "implicit_skills",
    "certifications",
    "links",
    "achievements",
    "coding_profiles"
]

SOURCE_PRIORITY = {
    "recruiter_csv": 0.85,
    "resume_pdf": 0.80
}

REQUIRED_FIELDS = ["candidate_name", "candidate_email"]
