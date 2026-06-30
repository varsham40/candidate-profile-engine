import pytest
from core.extractor import ExtractorService
from core.validator import ValidatorService
from core.merger import MergeService
from utils.exceptions import ExtractionError, ValidationError

def test_empty_resume():
    extractor = ExtractorService()
    parsed_data = {
        "source": "resume_pdf",
        "source_type": "unstructured",
        "content": ""
    }
    with pytest.raises(ExtractionError):
        extractor.extract(parsed_data)

def test_missing_required_email():
    validator = ValidatorService()
    output = {
        "candidate_name": {"value": "Varsha"}
    }
    validator.validate(output)
    assert output.get("candidate_email") is None

def test_missing_required_name():
    validator = ValidatorService()
    output = {
        "candidate_email": {"value": "varsha@gmail.com"}
    }
    validator.validate(output)
    assert output.get("candidate_name") is None

def test_invalid_phone():
    validator = ValidatorService()
    output = {
        "candidate_name": {"value": "Varsha"},
        "candidate_email": {"value": "varsha@gmail.com"},
        "phone": {"value": "12345"}
    }
    validator.validate(output)
    assert output["phone"]["value"] is None

def test_conflicting_emails():
    merger = MergeService()
    sources = [
        {"source": "resume_pdf", "data": {"email": "abc@gmail.com"}},
        {"source": "recruiter_csv", "data": {"email": "xyz@gmail.com"}}
    ]
    result = merger.merge(sources)
    assert result.email is not None
    assert result.email.value == "xyz@gmail.com"
