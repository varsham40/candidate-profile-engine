"""
Core extraction engine for parsing resumes.
Handles layout complexities, text slicing, and data extraction using heuristics and AI validation.
"""
import re
from typing import Dict, Any
from utils.exceptions import ExtractionError
from utils.helpers import clean_resume_text
from core.ai_validator import AIValidator

class ExtractorService:
    def __init__(self):
        self.ai_validator = AIValidator()

    def extract(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        source_type = raw_data.get("source_type")
        content = raw_data.get("content")
        
        if not content:
            raise ExtractionError("Empty resume text")
            
        metadata = raw_data.get("metadata", {})
            
        if source_type == "unstructured":
            return self._extract_from_text(content, metadata)
        elif source_type == "structured":
            record = content[0] if isinstance(content, list) and content else content
            skills_val = record.get("skills", [])
            if isinstance(skills_val, str):
                skills_val = [s.strip() for s in skills_val.split(",") if s.strip()]
            return {
                "name": record.get("name"),
                "email": record.get("email"),
                "phone": record.get("phone"),
                "skills": skills_val,
                "implicit_skills": [],
                "current_company": record.get("current_company"),
                "designation": record.get("designation"),
                "experience_years": record.get("experience_years"),
                "location": record.get("location"),
                "linkedin": record.get("linkedin"),
                "github": record.get("github"),
                "education": None,
                "experience": None,
                "projects": None,
                "certifications": None,
                "links": None,
                "achievements": None,
                "coding_profiles": None
            }
        else:
            raise ExtractionError(f"Unsupported source type: {source_type}")

    def _extract_from_text(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cleaned_text = clean_resume_text(text)
        geometric_links = metadata.get("geometric_links", [])
        
        sections = self._segment_sections(text)
        
        explicit_skills = self._extract_skills(text)
        implicit_skills = self._extract_implicit_skills(text, explicit_skills)
        
        # If the segmenter found an experience section, use it; otherwise fall back
        # to scanning ALL lines for date-range entries (handles missing/misread headers)
        exp_lines = sections.get("experience", [])
        if not exp_lines:
            exp_lines = sections.get("general", []) + [
                line.strip() for line in text.split('\n') if line.strip()
            ]

        parsed_exp = self._parse_experience(exp_lines)
        parsed_edu = self._parse_education(sections.get("education", []))

        # Same fallback for projects
        proj_lines = sections.get("projects", [])
        if not proj_lines:
            proj_lines = sections.get("general", [])
        parsed_proj = self._parse_projects(proj_lines)

        years_exp = self._calculate_years_experience(parsed_exp)
        
        designation = None
        current_company = None
        if parsed_exp:
            designation = parsed_exp[0].get("title")
            current_company = parsed_exp[0].get("company")
            
        # Combine text-based links and geometric links
        text_links = self._extract_links(text)
        all_links = list(set(text_links + [link.get("url") for link in geometric_links if link.get("url")]))
        
        linkedin = next((l for l in all_links if "linkedin.com" in l), None)
        github = next((l for l in all_links if "github.com" in l), None)
        
        def _clean_bullets(lines):
            result = []
            for line in lines:
                if line.startswith(("•", "-", "*")):
                    result.append(line.strip("•-* ").strip())
                else:
                    if result:
                        result[-1] += " " + line
                    else:
                        result.append(line)
            return result
        
        # New sections
        achievements = _clean_bullets(sections.get("achievements", []))
        coding_profiles = sections.get("codingprofiles", [])
        certifications = _clean_bullets(sections.get("certifications", []))

        return {
            "name": self._extract_name(text),
            "email": self._extract_email(cleaned_text),
            "phone": self._extract_phone(cleaned_text),
            "skills": explicit_skills,
            "implicit_skills": implicit_skills,
            "current_company": current_company,
            "designation": designation,
            "experience_years": years_exp,
            "location": self._extract_location(text),
            "linkedin": linkedin,
            "github": github,
            "education": parsed_edu,
            "experience": parsed_exp,
            "projects": parsed_proj,
            "certifications": certifications,
            "links": all_links,
            "achievements": achievements,
            "coding_profiles": coding_profiles
        }

    def _segment_sections(self, text: str) -> Dict[str, list]:
        lines = text.split('\n')
        sections = {
            "summary": [],
            "experience": [],
            "education": [],
            "projects": [],
            "skills": [],
            "achievements": [],
            "certifications": [],
            "codingprofiles": [],
            "general": []
        }
        
        current_section = "general"
        
        # Keys here have all spaces removed to support zero-space PDFs
        header_mapping = {
            "workexperience": "experience",
            "professionalexperience": "experience",
            "experience": "experience",
            "employmenthistory": "experience",
            "workhistory": "experience",
            "internships": "experience",
            "internship": "experience",
            "education": "education",
            "academic": "education",
            "academicprofile": "education",
            "academicbackground": "education",
            "projects": "projects",
            "keyprojects": "projects",
            "personalprojects": "projects",
            "academicprojects": "projects",
            "majorprojects": "projects",
            "minorprojects": "projects",
            "technicalskills": "skills",
            "skills": "skills",
            "expertise": "skills",
            "summary": "summary",
            "professionalsummary": "summary",
            "aboutme": "summary",
            "achievements": "achievements",
            "certifications": "certifications",
            "certifications&courses": "certifications",
            "certificationsandcourses": "certifications",
            "codingprofiles": "codingprofiles",
            "profiles": "codingprofiles"
        }
        
        for line in lines:
            line_clean = line.strip()
            line_lower = line_clean.lower().replace(":", "").replace("•", "").strip()
            if not line_clean:
                continue
                
            clean_line_lower = re.sub(r'\s+', '', line_lower)
            is_header = False
            
            # Header heuristic: short word count OR short char length
            if len(line_clean.split()) <= 4 or len(clean_line_lower) <= 25:
                for h, s in header_mapping.items():
                    if h == clean_line_lower or clean_line_lower.startswith(h):
                        current_section = s
                        is_header = True
                        break
                        
            if is_header:
                continue
                
            sections[current_section].append(line_clean)
            
        return sections

    def _extract_name(self, text: str) -> str | None:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Look at first line, remove non-alpha chars except space/dots
            first_line = lines[0]
            clean_first = re.sub(r'[^a-zA-Z\s\.]', '', first_line).strip()
            if clean_first and len(clean_first.split()) <= 4:
                return clean_first
        return None

    def _extract_email(self, text: str) -> str | None:
        pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        # Match 10 digits or digits with separators
        pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        match = re.search(pattern, text)
        if match:
            return re.sub(r"\D", "", match.group(0))
        # Fallback if spaces are collapsed: e.g. "+916304371409"
        pattern_collapsed = r"\+?\d{10,12}"
        match_c = re.search(pattern_collapsed, text)
        if match_c:
            return match_c.group(0)
        return None

    def _extract_skills(self, text: str) -> list[str]:
        from utils.constants import SUPPORTED_SKILL_ALIASES

        skills: list[str] = []
        inside_skill_section = False

        # These headers end the skills section
        section_stoppers = {
            "workexperience", "experience", "projects", "education",
            "certifications", "achievements", "professionalexperience",
            "internship", "internships"
        }

        skill_section_text = []

        lines = text.split('\n')
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()
            clean_for_match = re.sub(r'\s+', '', line_lower)

            if ("skills" in clean_for_match or "technicalskills" in clean_for_match) and len(line_clean.split()) <= 8:
                inside_skill_section = True
                # If it's just the header, we can still include it
                skill_section_text.append(line_clean)
                continue

            if not inside_skill_section:
                continue

            if clean_for_match in section_stoppers:
                inside_skill_section = False
                continue
                
            skill_section_text.append(line_clean)

        full_skill_text = " ".join(skill_section_text).lower()
        
        for alias, canonical in SUPPORTED_SKILL_ALIASES.items():
            # For very short aliases like 'c' or 'r', ensure strict word boundaries
            if len(alias) <= 2:
                # Python's \b works well, but we can also handle punctuation boundaries natively
                if re.search(r'\b' + re.escape(alias) + r'\b', full_skill_text):
                    skills.append(canonical)
            else:
                if re.search(r'\b' + re.escape(alias) + r'\b', full_skill_text):
                    skills.append(canonical)

        return list(set(skills))

    def _extract_implicit_skills(self, text: str, explicit_skills: list[str]) -> list[str]:
        from utils.constants import SUPPORTED_SKILL_ALIASES
        implicit = []

        # Only scan sections that are NOT the skills section itself.
        # This avoids double-counting and prevents the skills section text from
        # polluting implicit results.
        non_skill_text = self._get_non_skill_text(text)
        text_lower = non_skill_text.lower()
        
        explicit_lower = [s.strip().lower() for s in explicit_skills]
        explicit_mapped = set(SUPPORTED_SKILL_ALIASES.get(s, s) for s in explicit_lower)
        # Also add canonical forms of explicit skills directly
        explicit_mapped.update(explicit_skills)

        for alias, canonical in SUPPORTED_SKILL_ALIASES.items():
            if canonical in explicit_mapped:
                continue
            # Only use strict word-boundary matching — no compressed space tricks
            # Skip very short aliases (<=2 chars) that cause false positives
            if len(alias) <= 2:
                continue
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                implicit.append(canonical)
                    
        return list(set(implicit))

    def _get_non_skill_text(self, text: str) -> str:
        """Returns only the lines of the resume that are NOT under the skills section.
        This prevents skill-section keywords from polluting implicit skill detection."""
        lines = text.split('\n')
        result = []
        in_skills_section = False

        skill_headers = {"technicalskills", "skills", "expertise", "coretechnologies"}
        end_headers = {"workexperience", "experience", "projects", "education",
                       "certifications", "achievements", "professionalexperience"}

        for line in lines:
            line_clean = line.strip()
            clean_key = re.sub(r'\s+', '', line_clean.lower())

            if clean_key in skill_headers:
                in_skills_section = True
                continue
            if in_skills_section and clean_key in end_headers:
                in_skills_section = False

            if not in_skills_section:
                result.append(line_clean)

        return '\n'.join(result)

    def _parse_experience(self, lines: list[str]) -> list[Dict[str, Any]]:
        entries = []
        current_entry: Dict[str, Any] | None = None
        pending_header_lines = []
        
        # date_pattern: space-insensitive (\s*) month-year matching
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4})\s*[\-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4}|Present|present)'

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            match = re.search(date_pattern, line_clean, re.IGNORECASE)
            if match:
                if current_entry:
                    entries.append(current_entry)
                    
                start, end = match.group(1), match.group(2)
                date_str = match.group(0)
                remaining = line_clean.replace(date_str, "").strip(" -–—|,").strip()
                if remaining:
                    pending_header_lines.append(remaining)
                
                title = None
                company = None
                location = None
                
                if pending_header_lines:
                    # Parse title, company, location
                    split_done = False
                    hl = pending_header_lines[0]
                    # First try spaced delimiters
                    for delimiter in [" at ", " @ ", " - ", " – ", " — ", " | ", ", ", ": "]:
                        if delimiter in hl:
                            parts = hl.split(delimiter, 1)
                            title = parts[0].strip()
                            company = parts[1].strip()
                            split_done = True
                            break
                    # Try space-less delimiters if failed. Omit plain '-' to avoid breaking titles like "Full-Stack"
                    if not split_done:
                        for delimiter in ["@", "–", "—", "|", ",", ":"]:
                            if delimiter in hl:
                                parts = hl.split(delimiter, 1)
                                title = parts[0].strip()
                                company = parts[1].strip()
                                split_done = True
                                break
                    if not split_done:
                        title = hl
                        
                    if len(pending_header_lines) == 2:
                        company = pending_header_lines[1]
                    elif len(pending_header_lines) >= 3:
                        company = pending_header_lines[1]
                        location = pending_header_lines[2]
                        
                    if company and title:
                        swap_needed = False
                        
                        if self.ai_validator.is_valid_organization(title) and not self.ai_validator.is_valid_organization(company):
                            swap_needed = True
                            
                        if self.ai_validator.is_valid_role(company) and not self.ai_validator.is_valid_role(title):
                            swap_needed = True
                            
                        if swap_needed:
                            temp = company
                            company = title
                            title = temp
                
                
                current_entry = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "start_date": start,
                    "end_date": end,
                    "responsibilities": []
                }
                pending_header_lines = []
            else:
                if current_entry is None:
                    pending_header_lines.append(line_clean)
                else:
                    res = current_entry["responsibilities"]
                    if isinstance(res, list):
                        if line_clean.startswith(("•", "-", "*")):
                            res.append(line_clean.strip("•-* ").strip())
                        else:
                            # Heuristic: if it's short, capitalized, doesn't end with a period, and isn't a tech stack list, it's likely a new header
                            looks_like_header = (
                                len(line_clean.split()) <= 12 and
                                line_clean[0].isupper() and
                                not line_clean.endswith('.') and
                                not self.ai_validator.is_technology_list(line_clean) and
                                not any(k in line_clean.lower() for k in ['technologies used', 'tech stack', 'skills:', 'environment:'])
                            )
                            if looks_like_header:
                                entries.append(current_entry)
                                current_entry = None
                                pending_header_lines.append(line_clean)
                            else:
                                if len(res) > 0:
                                    res[-1] += " " + line_clean
                                else:
                                    res.append(line_clean)
                        
        if current_entry:
            entries.append(current_entry)
        elif not entries and pending_header_lines:
            # Fallback for experience block without any dates
            hl = pending_header_lines[0]
            title = None
            company = None
            split_done = False
            
            for delimiter in [" at ", " @ ", " - ", " – ", " — ", " | ", ", ", ": "]:
                if delimiter in hl:
                    parts = hl.split(delimiter, 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                    split_done = True
                    break
            if not split_done:
                for delimiter in ["@", "–", "—", "|", ",", ":"]:
                    if delimiter in hl:
                        parts = hl.split(delimiter, 1)
                        title = parts[0].strip()
                        company = parts[1].strip()
                        split_done = True
                        break
            if not split_done:
                title = hl
                if len(pending_header_lines) > 1 and len(pending_header_lines[1].split()) <= 6:
                    company = pending_header_lines[1]
                    pending_header_lines.pop(1)
            
            if company and title:
                swap_needed = False
                if self.ai_validator.is_valid_organization(title) and not self.ai_validator.is_valid_organization(company):
                    swap_needed = True
                if self.ai_validator.is_valid_role(company) and not self.ai_validator.is_valid_role(title):
                    swap_needed = True
                if swap_needed:
                    temp = company
                    company = title
                    title = temp
                    
            entries.append({
                "title": title,
                "company": company,
                "location": None,
                "start_date": None,
                "end_date": None,
                "responsibilities": pending_header_lines[1:]
            })
            
        return entries

    def _parse_education(self, lines: list[str]) -> list[Dict[str, Any]]:
        entries = []
        current_entry: Dict[str, Any] | None = None
        pending_lines = []
        
        # Degree and Institution regex patterns with word boundaries
        degree_pattern = r'\b(bachelor|master|phd|b\.?tech|m\.?tech|b\.?sc|m\.?sc|b\.?e|m\.?e|m\.?s|mba|degree|intermediate|high\s*school|secondary|12th|10th|diploma|ssc|hsc)\b'
        inst_pattern = r'\b(university|college|institute|school|academy|vidyalaya|kalasala|technology)\b'
        
        # Date pattern for range (e.g. 2020 - 2024)
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4})\s*[\-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4}|Present|present)'
        # Date pattern for single year or expected year
        single_date_pattern = r'\b(?:Expected\s+|Graduation\s+|Class of\s+)?((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-zA-Z]*\s*(?:19|20)\d{2})\b'
        # CGPA pattern
        cgpa_pattern = r'(?:cgpa|gpa|percentage|marks|score)\s*:?\s*([\d]+(?:[\.,]\d+)?(?:\s*/\s*[\d]+(?:[\.,]\d+)?)?|[\d]+(?:[\.,]\d+)?%)'

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            match_date = re.search(date_pattern, line_clean, re.IGNORECASE)
            match_single = None if match_date else re.search(single_date_pattern, line_clean, re.IGNORECASE)
            match_cgpa = re.search(cgpa_pattern, line_clean, re.IGNORECASE)
            
            if match_date or match_single:
                if current_entry and (current_entry.get("start_date") or current_entry.get("end_date")):
                    entries.append(current_entry)
                    current_entry = None
                
                if not current_entry:
                    current_entry = {
                        "degree": None,
                        "institution": None,
                        "location": None,
                        "start_date": None,
                        "end_date": None,
                        "cgpa": None
                    }
                    
                    if pending_lines:
                        for pl in pending_lines:
                            pl_lower = pl.lower()
                            if re.search(degree_pattern, pl_lower):
                                current_entry["degree"] = pl
                            elif re.search(inst_pattern, pl_lower):
                                current_entry["institution"] = pl
                            else:
                                if pl.count(",") > 1 or len(pl.split()) > 10:
                                    continue
                                if not current_entry["degree"]:
                                    current_entry["degree"] = pl
                                elif not current_entry["institution"]:
                                    current_entry["institution"] = pl
                        pending_lines = []
                
                date_str = match_date.group(0) if match_date else (match_single.group(0) if match_single else "")
                remaining = line_clean.replace(date_str, "").strip(" -–—|,").strip()
                
                if match_date:
                    current_entry["start_date"] = match_date.group(1)
                    current_entry["end_date"] = match_date.group(2)
                else:
                    if match_single:
                        current_entry["end_date"] = match_single.group(1)
                    
                if remaining:
                    rem_lower = remaining.lower()
                    if re.search(degree_pattern, rem_lower):
                        current_entry["degree"] = remaining
                    else:
                        current_entry["institution"] = remaining

                if current_entry.get("institution") and self.ai_validator.is_valid_date(current_entry["institution"]):
                    current_entry["start_date"] = current_entry["institution"]
                    current_entry["institution"] = None
                elif current_entry.get("degree") and self.ai_validator.is_valid_organization(current_entry["degree"]):
                    deg_lower = current_entry["degree"].lower()
                    if not re.search(degree_pattern, deg_lower):
                        temp = current_entry["institution"]
                        current_entry["institution"] = current_entry["degree"]
                        current_entry["degree"] = temp

            elif match_cgpa:
                if not current_entry:
                    current_entry = {
                        "degree": None,
                        "institution": None,
                        "location": None,
                        "start_date": None,
                        "end_date": None,
                        "cgpa": None
                    }
                    if pending_lines:
                        current_entry["degree"] = pending_lines[0]
                        if len(pending_lines) > 1:
                            current_entry["institution"] = pending_lines[1]
                        pending_lines = []
                current_entry["cgpa"] = match_cgpa.group(1)
            else:
                pl_lower = line_clean.lower()
                is_degree = bool(re.search(degree_pattern, pl_lower))
                is_inst = bool(re.search(inst_pattern, pl_lower))
                
                if current_entry:
                    if (is_degree and current_entry.get("degree")) or (is_inst and current_entry.get("institution")):
                        entries.append(current_entry)
                        current_entry = {
                            "degree": line_clean if is_degree else None,
                            "institution": line_clean if is_inst and not is_degree else None,
                            "location": None,
                            "start_date": None,
                            "end_date": None,
                            "cgpa": None
                        }
                        continue

                    if not current_entry["degree"] and is_degree:
                        current_entry["degree"] = line_clean
                    elif not current_entry["institution"] and is_inst:
                        current_entry["institution"] = line_clean
                    elif not current_entry["location"] and re.search(r'\b(hyderabad|mumbai|california|london|delhi|bangalore)\b', pl_lower):
                        current_entry["location"] = line_clean
                else:
                    if is_degree or is_inst:
                        current_entry = {
                            "degree": line_clean if is_degree else None,
                            "institution": line_clean if is_inst and not is_degree else None,
                            "location": None,
                            "start_date": None,
                            "end_date": None,
                            "cgpa": None
                        }
                    else:
                        pending_lines.append(line_clean)
                        
        if current_entry:
            entries.append(current_entry)
            
        if not entries and pending_lines:
            degree = None
            institution = None
            for pl in pending_lines:
                pl_lower = pl.lower()
                clean_pl = re.sub(r'\s+', '', pl_lower)
                if any(k in clean_pl for k in ["bachelor", "master", "phd", "b.tech", "m.tech", "b.sc", "m.sc", "b.e", "m.s", "be", "me", "mba", "degree", "btech", "mtech"]):
                    degree = pl
                elif any(k in clean_pl for k in ["university", "college", "institute", "school"]):
                    institution = pl
            if degree or institution:
                entries.append({
                    "degree": degree,
                    "institution": institution,
                    "location": None,
                    "start_date": None,
                    "end_date": None,
                    "cgpa": None
                })
                
        return entries

    def _parse_projects(self, lines: list[str]) -> list[Dict[str, Any]]:
        entries = []
        current_entry = None
        state = 0
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4})\s*[\-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{4}|\d{4}|Present|present)'

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            line_lower = line_clean.lower()
            if re.search(date_pattern, line_clean, re.IGNORECASE):
                continue
                
            is_bullet = line_clean.startswith(('•', '-', '*'))
            
            if is_bullet:
                if current_entry:
                    desc = line_clean.strip('•-* ').strip()
                    if current_entry['description']:
                        current_entry['description'] += ' ' + desc
                    else:
                        current_entry['description'] = desc
                state = 2
                continue

            clean_for_match = re.sub(r'\s+', '', line_lower)
            
            # Stop processing if we hit another section header bleeding in
            if any(h in clean_for_match for h in ['certifications', 'achievements', 'skills', 'codingprofiles', 'education', 'experience']):
                break
                
            if 'technologiesused' in clean_for_match or 'techstack' in clean_for_match or 'technologies' in clean_for_match:
                if current_entry:
                    if ':' in line_clean:
                        current_entry['technologies'] = line_clean.split(':', 1)[-1].strip()
                    else:
                        current_entry['technologies'] = line_clean
                state = 2
                continue
                
            if state == 2:
                # If it doesn't look like a new project title, it's probably a wrapped bullet
                looks_like_title = (line_clean[0].isupper() and not line_clean.endswith('.') 
                                    and len(line_clean.split()) <= 12)
                    
                if not looks_like_title:
                    if current_entry:
                        current_entry['description'] += ' ' + line_clean
                    continue
                else:
                    state = 0

            if state == 0:
                if self.ai_validator.is_technology_list(line_clean):
                    if current_entry:
                        current_entry['description'] += ' ' + line_clean
                    elif entries:
                        entries[-1]['description'] += ' ' + line_clean
                    state = 2
                    continue
                    
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    'name': line_clean,
                    'description': '',
                    'technologies': ''
                }
                state = 1
            elif state == 1 and current_entry is not None:
                if ',' in line_clean and len(re.split(r'[,|]', line_clean)) > 1 and len(line_clean.split()) <= 8:
                    current_entry['technologies'] = line_clean
                else:
                    current_entry['description'] = line_clean
                state = 2

        if current_entry:
            entries.append(current_entry)
        return entries

    def _calculate_years_experience(self, experience_blocks) -> float | None:
        from datetime import datetime
        total_months = 0
        for exp in experience_blocks:
            start_str = exp.get("start_date")
            end_str = exp.get("end_date")
            if not start_str or not end_str:
                continue
            
            def parse_date(d_str):
                d_str = d_str.strip().lower()
                if "present" in d_str or "current" in d_str:
                    return datetime.now()
                for fmt in ("%B %Y", "%b %Y", "%Y", "%m-%Y", "%m/%Y", "%B%Y", "%b%Y"):
                    try:
                        return datetime.strptime(d_str, fmt)
                    except ValueError:
                        pass
                return None
                
            start = parse_date(start_str)
            end = parse_date(end_str)
            if start and end:
                diff = end - start
                total_months += diff.days / 30.44
                
        if total_months > 0:
            return round(total_months / 12.0, 1)
        return None

    def _extract_location(self, text: str) -> str | None:
        lines = [line.strip() for line in text.split('\n') if line.strip()][:15]
        for line in lines:
            line_lower = line.lower()
            if any(k in line_lower for k in ["linkedin", "github", "email", "phone", "profile"]):
                continue
            match = re.search(r'([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)', line)
            if match:
                return match.group(1).strip()
            # Collapsed spacing location match: e.g. "Hyderabad,Telangana" or "SanJose,California"
            match_collapsed = re.search(r'([A-Z][a-zA-Z]+,\s*[A-Z][a-zA-Z]+)', line)
            if match_collapsed:
                return match_collapsed.group(1).strip()
        return None

    def _extract_links(self, text: str) -> list[str]:
        links = []
        pattern = r'\b(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com|portfolio\.com)/[a-zA-Z0-9_\-\./]+'
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            links.append(m.strip())
        # Space-less fallback (e.g. "linkedin.com/in/dhanushp")
        pattern_collapsed = r'\b(?:linkedin\.com|github\.com)/in/[a-zA-Z0-9_-]+'
        matches_c = re.findall(pattern_collapsed, text, re.IGNORECASE)
        for mc in matches_c:
            links.append(mc.strip())
        return list(set(links))
