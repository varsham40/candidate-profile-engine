import pytest
from app.core.validator import ValidatorService

def test_valid_output():
    validator = ValidatorService()

    output = {
        "candidate_name": {
            "value": "Varsha M",
            "confidence": 0.85
        },
        "candidate_email": {
            "value": "varsha@gmail.com",
            "confidence": 0.91
        }
    }

    assert validator.validate(output) is True

def test_invalid_email():
    validator = ValidatorService()

    output = {
        "candidate_name": {"value": "Varsha"},
        "candidate_email": {"value": "varsha@gmail"}
    }

    validator.validate(output)
    assert output["candidate_email"]["value"] is None
