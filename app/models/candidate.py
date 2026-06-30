from typing import Optional

from pydantic import BaseModel

from models.field import CandidateField


class CandidateProfile(BaseModel):
    name: Optional[CandidateField] = None
    email: Optional[CandidateField] = None
    phone: Optional[CandidateField] = None
    dob: Optional[CandidateField] = None

    current_company: Optional[CandidateField] = None
    designation: Optional[CandidateField] = None
    experience_years: Optional[CandidateField] = None

    skills: Optional[CandidateField] = None
    soft_skills: Optional[CandidateField] = None
    implicit_skills: Optional[CandidateField] = None
    certifications: Optional[CandidateField] = None
    projects: Optional[CandidateField] = None
    links: Optional[CandidateField] = None
    achievements: Optional[CandidateField] = None
    coding_profiles: Optional[CandidateField] = None

    education: Optional[CandidateField] = None
    experience: Optional[CandidateField] = None
    location: Optional[CandidateField] = None
    linkedin: Optional[CandidateField] = None
    github: Optional[CandidateField] = None

    def get_field(self, field_name: str):
        return getattr(self, field_name, None)
