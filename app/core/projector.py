class ProjectorService:

    def project(self, candidate_profile, config):
        projected = {}

        profile_dict = candidate_profile.model_dump()

        for field in config.fields:
            if field == "skills":
                # Special handling for skills: combine explicit and implicit skills
                p_data = profile_dict.get("skills") or {"value": [], "confidence": 0.0, "provenance": []}
                i_data = profile_dict.get("implicit_skills") or {"value": [], "confidence": 0.0, "provenance": []}
                
                if not p_data.get("value") and not i_data.get("value") and config.null_handling == "include":
                    projected[field] = None
                    continue
                elif not p_data.get("value") and not i_data.get("value"):
                    continue
                    
                union_val = list(dict.fromkeys(p_data.get("value", []) + i_data.get("value", [])))
                prov = p_data.get("provenance", []) + i_data.get("provenance", [])
                
                field_data = {
                    "value": union_val,
                    "confidence": p_data.get("confidence") or i_data.get("confidence") or 0.0,
                    "provenance": prov
                }
            else:
                field_data = profile_dict.get(field)
                if field_data is None:
                    if config.null_handling == "include":
                        projected[field] = None
                    continue

            output_key = field

            if config.field_mapping and field in config.field_mapping:
                output_key = config.field_mapping[field]

            projected[output_key] = self._format_field(field_data, config)

        return projected

    def _format_field(self, field_data, config):
        result = {
            "value": field_data["value"]
        }

        if config.include_confidence:
            result["confidence"] = field_data["confidence"]

        if config.include_provenance:
            result["provenance"] = field_data["provenance"]

        return result

    def build_semantic_profile(self, candidate_profile, file_path=None):
        from datetime import datetime, timezone
        import os
        profile_dict = candidate_profile.model_dump()

        def _val(field_name):
            f = profile_dict.get(field_name)
            return f["value"] if f and f.get("value") else None

        def _full(field_name):
            f = profile_dict.get(field_name)
            if not f or not f.get("value"):
                return None
            return {
                "value": f.get("value"),
                "confidence": f.get("confidence", 0.0),
                "provenance": f.get("provenance", [])
            }

        full_name = _val("name") or ""
        first_name = full_name.split()[0] if full_name else None
        last_name = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else None
        
        name_full = _full("name")
        if name_full:
            name_full["value"] = full_name
            first_name_full = {**name_full, "value": first_name}
            last_name_full = {**name_full, "value": last_name}
        else:
            name_full = first_name_full = last_name_full = None

        email = _val("email")
        phone = _val("phone")
        emails = [email] if email else []
        phones = [phone] if phone else []
        
        email_full = _full("email")
        if email_full:
            email_full["value"] = emails
        phone_full = _full("phone")
        if phone_full:
            phone_full["value"] = phones

        # ── Skills split ──────────────────────────────────────────────────────
        primary = _val("skills") or []
        if isinstance(primary, str):
            primary = [s.strip() for s in primary.split(",") if s.strip()]
        primary = list(dict.fromkeys(primary))

        implicit = _val("implicit_skills") or []
        if isinstance(implicit, str):
            implicit = [s.strip() for s in implicit.split(",") if s.strip()]
        primary_set = set(s.lower() for s in primary)
        secondary = [s for s in implicit if s.lower() not in primary_set]
        secondary = list(dict.fromkeys(secondary))

        skills_union = list(dict.fromkeys(primary + secondary))

        # We construct wrapper objects for the skills based on original provenance
        skills_base = _full("skills") or {"confidence": 0.0, "provenance": []}
        implicit_base = _full("implicit_skills") or {"confidence": 0.0, "provenance": []}
        
        skills_union_full = {
            "value": skills_union,
            "confidence": max(skills_base.get("confidence", 0), implicit_base.get("confidence", 0)),
            "provenance": skills_base.get("provenance", []) + implicit_base.get("provenance", [])
        }
        
        primary_full = {
            "value": primary,
            "confidence": skills_base.get("confidence", 0.0),
            "provenance": skills_base.get("provenance", [])
        }
        
        secondary_full = {
            "value": secondary,
            "confidence": implicit_base.get("confidence", 0.0),
            "provenance": implicit_base.get("provenance", [])
        }

        # ── Links ─────────────────────────────────────────────────────────────
        extracted_links = _val("links") or []
        links = list(extracted_links)
        li = _val("linkedin")
        gh = _val("github")
        if li and li not in links: links.append(li)
        if gh and gh not in links: links.append(gh)
        
        links_base = _full("links") or {"confidence": 0.8, "provenance": []}
        links_full = {
            "value": links,
            "confidence": links_base.get("confidence", 0.8),
            "provenance": links_base.get("provenance", [])
        }

        # ── Metadata ──────────────────────────────────────────────────────────
        import re
        file_name = file_path or "candidate_resume.txt"
        raw_source_id = os.path.basename(file_name)
        
        # Clean UUID prefix if present
        clean_file_name = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_', '', raw_source_id)

        metadata = {
            "source_type": "resume",
            "file_name": clean_file_name,
            "parse_status": "SUCCESS",
            "warnings": [],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "raw_source_id": raw_source_id
        }

        return {
            "candidate_id": None,
            "full_name": name_full,
            "first_name": first_name_full,
            "last_name": last_name_full,
            "emails": email_full,
            "phones": phone_full,
            "skills": skills_union_full,
            "primary_skills": primary_full,
            "secondary_skills": secondary_full,
            "current_company": _full("current_company"),
            "title": _full("designation"),
            "education": _full("education"),
            "experience": _full("experience"),
            "years_experience": _full("experience_years"),
            "location": _full("location"),
            "links": links_full,
            "achievements": _full("achievements"),
            "coding_profiles": _full("coding_profiles"),
            "certifications": _full("certifications"),
            "metadata": metadata
        }
