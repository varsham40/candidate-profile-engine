"""
Main execution pipeline.
Orchestrates the end-to-end process of parsing, extracting, normalizing, and merging candidate data.
"""
from parsers.csv_parser import CSVParser
from parsers.pdf_parser import PDFParser
from core.extractor import ExtractorService
from core.normalizer import NormalizerService
from core.merger import MergeService
from core.projector import ProjectorService
from core.validator import ValidatorService
from utils.config_loader import load_projection_config
import os

class PipelineRunner:

    def __init__(self):
        self.csv_parser = CSVParser()
        self.pdf_parser = PDFParser()

        self.extractor = ExtractorService()
        self.normalizer = NormalizerService()
        self.merger = MergeService()
        self.projector = ProjectorService()
        self.validator = ValidatorService()

    def run(self, csv_path, pdf_path, custom_config_path=None):
        parsed_csv = self.csv_parser.parse(csv_path)
        parsed_pdf = self.pdf_parser.parse(pdf_path)

        extracted_csv = self.extractor.extract(parsed_csv.model_dump())
        extracted_pdf = self.extractor.extract(parsed_pdf.model_dump())

        normalized_csv = self.normalizer.normalize(extracted_csv)
        normalized_pdf = self.normalizer.normalize(extracted_pdf)

        source_records = [
            {
                "source": "recruiter_csv",
                "filename": os.path.basename(csv_path),
                "data": normalized_csv,
                "raw_data": extracted_csv
            },
            {
                "source": "resume_pdf",
                "filename": os.path.basename(pdf_path),
                "data": normalized_pdf,
                "raw_data": extracted_pdf
            }
        ]

        merged = self.merger.merge(source_records)
        
        # Output the new nested semantic profile instead of a flat dump
        canonical_profile = self.projector.build_semantic_profile(merged, pdf_path)

        # Validate the canonical profile — adds warnings, normalizes phones/emails
        canonical_profile = self.validator.validate_canonical(canonical_profile)

        result = {
            "canonical_profile": canonical_profile
        }

        if custom_config_path and os.path.exists(custom_config_path):
            config = load_projection_config(custom_config_path)
            projected = self.projector.project(merged, config)
            self.validator.validate(projected)
            return projected

        return result
