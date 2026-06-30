# Technical Design: Candidate Profile Engine

## 1. Pipeline Architecture (DAG)
The engine processes multi-modal data via a linear Directed Acyclic Graph (DAG) designed for fault tolerance and deterministic outputs:
**`Ingest & Parse` → `Extract (Regex + NLP)` → `Normalize` → `Merge & Score` → `Project` → `Validate`**

1. **Ingest & Parse:** Reads structured CSVs (`csv` module) and unstructured PDFs (`PyMuPDF/fitz`) into raw text blocks.
2. **Extract:** Uses fast regex heuristics for structured fields (emails, phones). Falls back to a local `spaCy` NLP model (Named Entity Recognition) to pull Organizations (`ORG`), Dates (`DATE`), and Names (`PERSON`) from complex text blocks.
3. **Normalize:** Standardizes formats to ensure 1:1 comparability.
4. **Merge & Score:** The core engine. Combines data from all sources, resolves conflicts, deduplicates using fuzzy matching, and calculates a dynamic confidence score.
5. **Project:** Maps the canonical profile into a customized output format based on a runtime `config.json`.
6. **Validate:** Final constraint check (e.g., email syntax, phone length). Appends non-fatal warnings to metadata instead of crashing.

---

## 2. Canonical Output Schema & Normalization
The system standardizes data into a strict internal Pydantic canonical schema before projection. 

**Core Schema:**
* `candidate_id` (UUID), `full_name`, `first_name`, `last_name`
* `emails` (List[str]), `phones` (List[str]), `location`
* `primary_skills` (List[str]), `secondary_skills` (List[str])
* `experience` & `education` (List of nested objects with titles, institutions, start/end dates)
* `metadata` (Tracking provenance, warnings, and source files)

**Normalization Formats:**
* **Dates:** Enforced to `YYYY-MM` (e.g., "Oct 2024" → `2024-10`).
* **Phones:** Stripped of non-numeric characters, preserving leading `+` for international codes.
* **Skills:** Title Cased and stripped of trailing punctuation.
* **Emails:** Lowercased.

---

## 3. Merge Strategy & Conflict Resolution
The merger handles contradictions across multiple files (e.g., Resume PDF vs. Recruiter CSV).

* **Resolution Policy (The Winner):** We apply a priority-based trust hierarchy. The structured Recruiter CSV inherently carries higher trust (`0.9` weight) than the highly unstructured PDF (`0.7` weight). If `RapidFuzz` detects a low-similarity conflict (e.g., CSV says "Lead Engineer", PDF says "Developer"), the higher-weight source wins. 
* **List Unioning:** For skills and links, we use a `Set` union to merge both sources, deduplicating fuzzy matches (e.g., "ReactJS" and "React.js" merge into one).
* **Confidence Scoring:** Calculated dynamically `[0.0 - 1.0]`. 
  * Base confidence = the origin source's reliability weight.
  * **Agreement Boost:** If both the CSV and PDF supply the same data point (Fuzzy Ratio > 85%), we apply a `+0.1` confidence boost, representing multi-source consensus.

---

## 4. Runtime Config (Projection)
The pipeline is decoupled from the final output shape. Before returning to the user, the `Projector` layer reads a runtime `config.json`.
* **Filtering:** Drops any fields not explicitly requested in the config (e.g., dropping `soft_skills` if omitted).
* **Mapping:** Remaps canonical keys to client-requested keys (e.g., internal `name` maps to output `candidate_name`).
* **Null Handling:** Instructs the engine whether to omit missing fields entirely or include them as `null`.

---

## 5. Edge Cases Handled

* **Aggressive PDF Word Splitting:** Resumes often render with arbitrary line breaks (e.g. "Software\nEngineer"). **Handling:** We utilize a local `spaCy` NLP Named Entity Recognition (NER) model to re-stitch tokens based on semantic context rather than relying on raw positional line breaks.
* **Corrupted / Empty PDFs:** Unparsable or encrypted PDF uploads normally crash pipelines. **Handling:** We catch all extraction faults and gracefully yield empty payload arrays. The system seamlessly falls back to relying 100% on the structured Recruiter CSV, logging a non-fatal warning in the output metadata.
* **Creative Skill Formatting & Evasion:** Candidates embed skills deep in job descriptions rather than neat lists. **Handling:** We bypass varied formatting entirely by tokenizing the raw document string and intersecting it against our static IT skills taxonomy to derive "Implicit Skills", merging them as secondary skills.
* **Contradictory Source Data:** A recruiter CSV says "Data Engineer", but the Resume PDF says "Data Scientist". **Handling:** We apply a priority-based trust hierarchy where the CSV base weight (`0.9`) overrides the PDF base weight (`0.7`). However, if `RapidFuzz` detects high similarity, we merge and grant a `+0.1` multi-source consensus boost.

### Left Out Under Time Pressure
We deliberately omitted advanced Optical Character Recognition (OCR) for image-based scanned PDFs, as well as complex graphical multi-column table preservation. These introduce massive extraction latency and unreliability outside the core scope of standard text-layer parsing.
