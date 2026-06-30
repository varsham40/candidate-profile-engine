from app.parsers.csv_parser import CSVParser
from app.parsers.pdf_parser import PDFParser

def test_csv_parser():
    parser = CSVParser()
    result = parser.parse("sample_data/csv/recruiter_data.csv")

    assert result.source == "recruiter_csv"
    assert result.source_type == "structured"
    assert len(result.content) > 0

def test_pdf_parser():
    parser = PDFParser()
    result = parser.parse("sample_data/resumes/resume1.pdf")

    assert result.source == "resume_pdf"
    assert result.source_type == "unstructured"
    assert len(result.content) > 0
