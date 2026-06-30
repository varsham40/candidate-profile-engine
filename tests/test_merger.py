from app.core.merger import MergeService

def test_merge_exact():
    merger = MergeService()
    sources = [
        {"source": "recruiter_csv", "data": {"email": "varsha@gmail.com"}},
        {"source": "resume_pdf", "data": {"email": "varsham@gmail.com"}}
    ]
    result = merger.merge(sources)
    assert result.email is not None
    assert result.email.value == "varsha@gmail.com"

def test_merge_fuzzy():
    merger = MergeService()
    sources = [
        {"source": "recruiter_csv", "data": {"name": "Varsha M"}},
        {"source": "resume_pdf", "data": {"name": "Varsha"}}
    ]
    result = merger.merge(sources)
    assert result.name is not None
    assert result.name.value == "Varsha M"

def test_merge_multi():
    merger = MergeService()
    sources = [
        {"source": "recruiter_csv", "data": {"skills": ["Python", "React"]}},
        {"source": "resume_pdf", "data": {"skills": ["Python", "SQL"]}}
    ]
    result = merger.merge(sources)
    assert result.skills is not None
    assert "Python" in result.skills.value
    assert "React" in result.skills.value
    assert "SQL" in result.skills.value
