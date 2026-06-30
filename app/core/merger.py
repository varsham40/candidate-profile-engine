"""
Profile merger module.
Responsible for reconciling and merging candidate data extracted from multiple sources (e.g., CSV, PDF) into a single canonical profile.
"""
from rapidfuzz import fuzz

from models.candidate import CandidateProfile
from models.field import CandidateField
from models.source import Provenance, SourceMetadata
from core.scorer import ScorerService
from utils.constants import (
    EXACT_FIELDS,
    FUZZY_FIELDS,
    MULTI_VALUE_FIELDS,
    SOURCE_PRIORITY
)

class MergeService:

    def __init__(self):
        self.scorer = ScorerService()

    def merge(self, source_records):
        merged = {}
        all_fields = set()

        for source in source_records:
            all_fields.update(source["data"].keys())

        for field in all_fields:
            merged[field] = self._merge_field(field, source_records)

        if "implicit_skills" in merged and "skills" in merged:
            if merged["implicit_skills"] and merged["skills"]:
                explicit_vals = set(merged["skills"].value)
                implicit_vals = set(merged["implicit_skills"].value)
                filtered_implicit = list(implicit_vals - explicit_vals)
                merged["implicit_skills"].value = filtered_implicit

        return CandidateProfile(**merged)

    def _merge_field(self, field, source_records):
        values = []

        for source in source_records:
                values.append({
                    "value": source["data"].get(field),
                    "raw_value": source.get("raw_data", {}).get(field),
                    "source": source["source"],
                    "filename": source.get("filename")
                })

        if not values:
            return None

        if field in EXACT_FIELDS:
            return self._merge_exact(field, values)
        elif field in FUZZY_FIELDS:
            return self._merge_fuzzy(field, values)
        elif field in ["education", "experience", "projects"]:
            return self._merge_list_of_dicts(field, values)
        elif field in MULTI_VALUE_FIELDS:
            return self._merge_multi(field, values)
        else:
            return None

    def _merge_list_of_dicts(self, field, values):
        merged_list = []
        provenance = []
        seen = []
        contributing_sources = 0

        for item in values:
            provenance.append(self._create_provenance(item["source"], item.get("raw_value", item["value"]), item["value"], item.get("filename")))

            val_list = item["value"]
            if not isinstance(val_list, list) or len(val_list) == 0:
                continue
            contributing_sources += 1
            for entry in val_list:
                if entry not in seen:
                    seen.append(entry)
                    merged_list.append(entry)

        # Confidence scales with source reliability and agreement:
        # - Single source: base confidence from that source's priority
        # - Multiple sources: boost confidence for agreement
        if contributing_sources == 0:
            base_score = 0.5
        elif contributing_sources == 1:
            src = next((v["source"] for v in values if isinstance(v["value"], list) and len(v["value"]) > 0), "resume_pdf")
            base_score = SOURCE_PRIORITY.get(src, 0.5)
        else:
            # Both sources have data — treat as strong agreement
            base_score = max(SOURCE_PRIORITY.get(v["source"], 0.5) for v in values)

        confidence = self.scorer.calculate_confidence(base_score, 0.9)

        return CandidateField(
            value=merged_list,
            confidence=confidence,
            field_type="list_of_dicts",
            provenance=provenance,
            is_verified=True
        )

    def _create_provenance(self, source_name, raw_value, normalized_value, filename=None):
        import re
        score = SOURCE_PRIORITY.get(source_name, 0.5)
        source_type = "structured" if "csv" in source_name or "json" in source_name else "unstructured"
        
        display_name = source_name
        if filename:
            clean_filename = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_', '', filename)
            suffix = "csv" if "csv" in source_name else "resume"
            display_name = f"{clean_filename} ({suffix})"

        return Provenance(
            source_metadata=SourceMetadata(
                source_name=display_name,
                source_type=source_type,
                reliability_score=score
            ),
            raw_value=str(raw_value),
            normalized_value=str(normalized_value)
        )

    def _merge_exact(self, field, values):
        valid = [v for v in values if v["value"] is not None]
        if not valid:
            valid = values

        chosen = max(valid, key=lambda x: SOURCE_PRIORITY.get(x["source"], 0.0))

        confidence = self.scorer.calculate_confidence(
            SOURCE_PRIORITY.get(chosen["source"], 0.5),
            1.0
        )

        all_provenance = [
            self._create_provenance(v["source"], v.get("raw_value", v["value"]), v["value"], v.get("filename"))
            for v in values
        ]

        return CandidateField(
            value=chosen["value"],
            confidence=confidence,
            field_type="exact",
            provenance=all_provenance,
            is_verified=True
        )

    def _merge_fuzzy(self, field, values):
        # Filter out None values first
        valid = [v for v in values if v["value"] is not None]
        if not valid:
            valid = values

        if field == "name":
            # For names, prefer the longest value — resumes have full names
            # while CSVs often have initials like "P Dhanush"
            chosen = max(valid, key=lambda x: len(str(x["value"])))
        else:
            # For other fuzzy fields (company, designation), prefer higher-priority source
            chosen = max(valid, key=lambda x: SOURCE_PRIORITY.get(x["source"], 0.0))

        confidence = self.scorer.calculate_confidence(
            SOURCE_PRIORITY.get(chosen["source"], 0.5),
            0.85
        )

        all_provenance = [
            self._create_provenance(v["source"], v.get("raw_value", v["value"]), v["value"], v.get("filename"))
            for v in values
        ]

        return CandidateField(
            value=chosen["value"],
            confidence=confidence,
            field_type="fuzzy",
            provenance=all_provenance,
            is_verified=True
        )

    def _merge_multi(self, field, values):
        merged_values = []
        provenance = []

        for item in values:
            provenance.append(self._create_provenance(item["source"], item.get("raw_value", item["value"]), item["value"], item.get("filename")))
            
            if isinstance(item["value"], list):
                for value in item["value"]:
                    if value not in merged_values:
                        merged_values.append(value)

        confidence = self.scorer.calculate_confidence(0.9, 0.9)

        return CandidateField(
            value=list(merged_values),
            confidence=confidence,
            field_type="multi_value",
            provenance=provenance,
            is_verified=True
        )
