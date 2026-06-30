"""
Data normalization pipeline.
Standardizes text fields, validates dates, and ensures all extracted data conforms to expected formats.
"""
from utils.logger import logger
from utils.helpers import (
    normalize_phone,
    normalize_email,
    normalize_skills,
    normalize_date,
    normalize_name,
    normalize_education_entries,
    normalize_experience_entries,
)

class NormalizerService:

    def normalize(self, extracted_data):
        logger.info("Starting normalization")

        normalized = {}

        for field, value in extracted_data.items():
            # Drop explicitly missing values, empty strings, and pandas NaNs
            if value is None or value == "" or str(value).lower() == "nan":
                continue

            if field == "email":
                normalized[field] = normalize_email(value)
            elif field == "name":
                normalized[field] = normalize_name(value)
            elif field == "phone":
                result = normalize_phone(value)
                if result:
                    normalized[field] = result
            elif field in ["skills", "implicit_skills"]:
                categorized = normalize_skills(value)
                normalized[field] = categorized["technical"]
                if categorized["soft"]:
                    if "soft_skills" not in normalized:
                        normalized["soft_skills"] = []
                    normalized["soft_skills"].extend(categorized["soft"])
            elif field == "dob":
                normalized[field] = normalize_date(value)
            elif field == "education":
                if isinstance(value, list):
                    normalized[field] = normalize_education_entries(value)
            elif field == "experience":
                if isinstance(value, list):
                    normalized[field] = normalize_experience_entries(value)
            else:
                normalized[field] = value

        return normalized
