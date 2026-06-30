import re
from utils.logger import logger
from utils.exceptions import ValidationError

class ValidatorService:

    def validate(self, projected_output):
        self._validate_required_fields(projected_output)
        self._validate_email(projected_output)
        self._validate_phone(projected_output)
        self._validate_confidence(projected_output)
        return True

    def validate_canonical(self, canonical: dict) -> dict:
        """
        Validate the final canonical profile dict and attach a warnings list.
        Does NOT raise — adds to warnings so the caller can still return data.
        """
        warnings = canonical.get("metadata", {}).get("warnings", [])
        
        def _val(field):
            obj = canonical.get(field)
            return obj.get("value") if isinstance(obj, dict) else obj

        # Required fields
        if not _val("full_name"):
            warnings.append("MISSING_NAME: full_name could not be extracted")
        if not _val("emails"):
            warnings.append("MISSING_EMAIL: no valid email found")

        # Phone
        phone_obj = canonical.get("phones")
        if isinstance(phone_obj, dict):
            phones = phone_obj.get("value") or []
            validated_phones = []
            for p in phones:
                digits = re.sub(r"\D", "", str(p))
                if len(digits) >= 10:
                    validated_phones.append(p)
                else:
                    warnings.append(f"INVALID_PHONE: '{p}' is not a valid phone number — removed")
            canonical["phones"]["value"] = validated_phones

        # Email format
        email_obj = canonical.get("emails")
        if isinstance(email_obj, dict):
            emails = email_obj.get("value") or []
            validated_emails = []
            for e in emails:
                if re.match(r'^[\w\.\+\-]+@[\w\.-]+\.\w+$', str(e)):
                    validated_emails.append(e)
                else:
                    warnings.append(f"INVALID_EMAIL: '{e}' does not look like a valid email — removed")
            canonical["emails"]["value"] = validated_emails

        # Education: validate each entry
        edu_obj = canonical.get("education")
        if isinstance(edu_obj, dict):
            edu_list = edu_obj.get("value") or []
            for edu in edu_list:
                if not edu.get("degree") and not edu.get("institution"):
                    warnings.append("EDUCATION_ENTRY: entry has no degree or institution — possible parse error")
                if edu.get("start_date") and edu.get("end_date") and edu["end_date"] != "present":
                    try:
                        if edu["start_date"] > edu["end_date"]:
                            warnings.append(f"EDUCATION_DATE: start_date '{edu['start_date']}' is after end_date '{edu['end_date']}'")
                    except TypeError:
                        pass

        # Experience: validate each entry
        exp_obj = canonical.get("experience")
        if isinstance(exp_obj, dict):
            exp_list = exp_obj.get("value") or []
            for exp in exp_list:
                if not exp.get("title") and not exp.get("company"):
                    warnings.append("EXPERIENCE_ENTRY: entry has no title or company — possible parse error")
                if exp.get("start_date") and exp.get("end_date") and exp["end_date"] != "present":
                    try:
                        if exp["start_date"] > exp["end_date"]:
                            warnings.append(f"EXPERIENCE_DATE: start_date '{exp['start_date']}' is after end_date '{exp['end_date']}'")
                    except TypeError:
                        pass

        # Skills
        if not _val("skills"):
            warnings.append("MISSING_SKILLS: no skills could be extracted")

        if canonical.get("metadata"):
            canonical["metadata"]["warnings"] = warnings

        return canonical

    # ── Legacy methods used by the projected profile path ──────────────────────

    def _validate_required_fields(self, output):
        for field in ["candidate_name", "candidate_email"]:
            field_data = output.get(field)
            if field_data is None or field_data.get("value") is None:
                logger.warning(f"Required field '{field}' is missing or null in projected output")

    def _validate_email(self, output):
        email_field = output.get("candidate_email")
        if email_field and email_field.get("value"):
            email = email_field["value"]
            pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
            if not re.match(pattern, email):
                output["candidate_email"]["value"] = None

    def _validate_phone(self, output):
        phone_field = output.get("phone")
        if phone_field and phone_field.get("value"):
            phone = str(phone_field["value"])
            if not re.fullmatch(r"\d{10}", phone):
                output["phone"]["value"] = None

    def _validate_confidence(self, output):
        for field_data in output.values():
            if isinstance(field_data, dict):
                confidence = field_data.get("confidence")
                if confidence is not None:
                    if confidence < 0 or confidence > 1:
                        raise ValidationError("Confidence must be between 0 and 1")
