# models.py

class Household:
    def __init__(self, household_id, info, claims=None):
        self.household_id = household_id
        self.info = info
        
        if claims:
            self.claims = claims
        else:
            self.claims = {
                "May_2025": False,
                "Jan_2026": False
            }

    def to_dict(self):
        return {
            "household_id": self.household_id,
            "info": self.info,
            "claims": self.claims
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['household_id'], data['info'], data.get('claims'))

    # Helper function to check eligibility
    def can_claim(self, tranche):
        if tranche == "May_2025":
            return not self.claims["May_2025"]
        elif tranche == "Jan_2026":
            return not self.claims["Jan_2026"]
        return False

    def mark_claimed(self, tranche):
        if tranche in self.claims:
            self.claims[tranche] = True
