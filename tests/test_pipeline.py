import json
from app.core.pipeline import PipelineRunner

def test_pipeline():
    pipeline = PipelineRunner()

    result = pipeline.run(
        "sample_data/csv/recruiter_data.csv",
        "sample_data/resumes/resume1.pdf"
    )

    assert "canonical_profile" in result
    canonical = result["canonical_profile"]
    assert "full_name" in canonical
    assert "emails" in canonical

def test_gold_profile():
    pipeline = PipelineRunner()

    result = pipeline.run(
        "sample_data/csv/recruiter_data.csv",
        "sample_data/resumes/resume1.pdf"
    )

    canonical = result["canonical_profile"]
    with open("tests/gold_profiles/gold_profile_1.json") as f:
        gold = json.load(f)

    assert canonical["full_name"] == gold["candidate_name"]["value"]
    assert canonical["emails"][0] == gold["candidate_email"]["value"]
