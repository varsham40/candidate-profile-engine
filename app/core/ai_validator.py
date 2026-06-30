"""
AI validation layer using spaCy.
Provides intelligent named entity recognition to distinguish between organizations, roles, and dates.
"""

from utils.logger import logger

from typing import Any
import spacy 

class AIValidator:
    def __init__(self):
        self.nlp: Any = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Successfully loaded spaCy AI model (en_core_web_sm)")
        except Exception as e:
            logger.error(f"Failed to load spaCy model. Ensure 'python -m spacy download en_core_web_sm' was run. Error: {e}")

    def _get_dominant_entity(self, text: str):
        if not self.nlp or not text.strip():
            return None
        doc = self.nlp(text.strip())
        if not doc.ents:
            return None
        
        # Count entity frequencies
        ent_counts = {}
        for ent in doc.ents:
            ent_counts[ent.label_] = ent_counts.get(ent.label_, 0) + 1
            
        # Return the most frequent entity type
        dominant = max(ent_counts.items(), key=lambda x: x[1])
        return dominant[0]

    def is_valid_organization(self, text: str) -> bool:
        """Returns True if the AI believes the text is an organization/institution."""
        # Fast fail for obvious job titles
        role_keywords = ["developer", "engineer", "manager", "lead", "intern", "analyst", "consultant", "scientist", "designer", "architect"]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in role_keywords):
            return False
            
        dominant = self._get_dominant_entity(text)
        # ORG = Companies, agencies, institutions, etc.
        if dominant in ["ORG"]:
            return True
        return False
        
    def is_valid_role(self, text: str) -> bool:
        """Returns True if text contains common job title keywords."""
        role_keywords = ["developer", "engineer", "manager", "lead", "intern", "analyst", "consultant", "scientist", "designer", "architect", "founder", "freelance", "president", "director"]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in role_keywords)

    def is_valid_date(self, text: str) -> bool:
        """Returns True if the AI believes the text is primarily a date/time period."""
        dominant = self._get_dominant_entity(text)
        # DATE = Absolute or relative dates or periods
        if dominant in ["DATE", "TIME"]:
            return True
        return False

    def is_technology_list(self, text: str) -> bool:
        """Heuristic combined with AI to detect if a line is just a list of technologies."""
        if not self.nlp or not text.strip():
            return False
            
        text_lower = text.lower()
        if any(h in text_lower for h in ["technologies:", "tech stack:", "skills:", "technologies used"]):
            return True

        tokens = [t.strip() for t in text.replace(",", " ").split() if len(t.strip()) > 2]
        doc = self.nlp(text.strip())
        verbs = [token for token in doc if token.pos_ == "VERB"]
        
        if "," in text and len(tokens) >= 4 and len(verbs) == 0:
            return True
        return False
