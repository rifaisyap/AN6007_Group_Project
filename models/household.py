# models/household.py

class Household:
    def __init__(self, household_id, info=None, claims=None):
        self.household_id = household_id
        self.info = info if info is not None else {}
        
        if claims is None:
            self.claims = {
                "May_2025": False,
                "Jan_2026": False
            }
        else:
            self.claims = claims

    def can_claim(self, tranche):
        return self.claims.get(tranche) is False

    def mark_claimed(self, tranche):
        if tranche in self.claims:
            self.claims[tranche] = True

    def to_dict(self):
        return {
            "household_id": self.household_id,
            "info": self.info,
            "claims": self.claims
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(
            household_id=data.get("household_id"),
            info=data.get("info", {}),
            claims=data.get("claims")
        )
