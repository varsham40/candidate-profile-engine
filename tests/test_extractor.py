from app.core.extractor import ExtractorService

def test_resume_extraction():
    extractor = ExtractorService()

    parsed_data = {
        "source": "resume_pdf",
        "source_type": "unstructured",
        "content": """
        Varsha M
        varsha@gmail.com
        9876543210
        Skills: Python3, ReactJS
        """
    }

    result = extractor.extract(parsed_data)

    assert result["email"] == "varsha@gmail.com"
    assert result["phone"] == "9876543210"
    assert "Python" in result["skills"]  # Taxonomy normalizes Python3 -> Python
