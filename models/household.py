# models/household.py

class Household:
    def __init__(self, household_id, info=None, claims=None):
        self.household_id = household_id
        # 儲存住戶額外資訊 (例如地址等)
        self.info = info if info is not None else {}
        
        # 使用字典儲存領取狀態，確保邏輯清晰且易於擴展
        # 預設狀態皆為 False (尚未領取)
        if claims is None:
            self.claims = {
                "May_2025": False,
                "Jan_2026": False
            }
        else:
            self.claims = claims

    def can_claim(self, tranche):
        """檢查特定輪次是否可以領取。如果該輪次不存在或已領取，則回傳 False。"""
        # 只有當該輪次在字典中且值為 False 時，才允許領取
        return self.claims.get(tranche) is False

    def mark_claimed(self, tranche):
        """標記該輪次為已領取 (True)。"""
        if tranche in self.claims:
            self.claims[tranche] = True

    def to_dict(self):
        """轉換為字典，以便透過 JSON 存入資料庫的 data_json 欄位。"""
        return {
            "household_id": self.household_id,
            "info": self.info,
            "claims": self.claims
        }

    @classmethod
    def from_dict(cls, data):
        """從資料庫讀取的資料重建 Household 物件。"""
        if not data:
            return None
        return cls(
            household_id=data.get("household_id"),
            info=data.get("info", {}),
            claims=data.get("claims")
        )