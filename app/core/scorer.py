"""
Candidate scoring engine.
Evaluates profiles based on configured skill weights, experience, and educational background to generate a match score.
"""
class ScorerService:

    def calculate_confidence(self, source_score, agreement_score):
        confidence = (
            0.6 * source_score +
            0.4 * agreement_score
        )

        return round(confidence, 2)
