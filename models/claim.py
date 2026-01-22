import uuid
import json
import os
from datetime import datetime

from storage.household_storage import household_db, save_household_json

VOUCHER_FILE = "vouchers.json"

TRANCHE_CONFIG = {
    "May_2025": {
        "total_value": 500,
        "breakdown": [
            {"amount": 2, "count": 50},  # $2 x 50 = $100
            {"amount": 5, "count": 20},  # $5 x 20 = $100
            {"amount": 10, "count": 30}  # $10 x 30 = $300
        ]
    },
    "Jan_2026": {
        "total_value": 300,
        "breakdown": [
            {"amount": 2, "count": 30},
            {"amount": 5, "count": 12},
            {"amount": 10, "count": 15}
        ]
    }
}

def load_vouchers_from_disk():
    """load already generated Vouchers"""
    if os.path.exists(VOUCHER_FILE):
        try:
            with open(VOUCHER_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_vouchers_to_disk(data):
    with open(VOUCHER_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def generate_vouchers(household_id, tranche):
    #verify status
    # 1. check household id 
    if household_id not in household_db:
        return False, "Household not found"

    household = household_db[household_id]

    # 2. check if claimed
    if not household.can_claim(tranche):
        return False, f"Tranche {tranche} already claimed or invalid."

    # 3. 
    config = TRANCHE_CONFIG.get(tranche)
    if not config:
        return False, "Invalid tranche type"

    # 4. 
    new_vouchers = []
    
    for item in config['breakdown']:
        amount = item['amount']
        count = item['count']
        
        for _ in range(count):
            unique_suffix = uuid.uuid4().hex[:6].upper()
            code = f"V-{household_id}-{tranche[:3].upper()}-{unique_suffix}"
            
            new_vouchers.append({
                "voucher_code": code,
                "amount": amount,
                "tranche": tranche,
                "status": "Active",
                "household_id": household_id,
                "created_at": datetime.now().isoformat()
            })

    all_vouchers = load_vouchers_from_disk()
    
    if household_id not in all_vouchers:
        all_vouchers[household_id] = []
    all_vouchers[household_id].extend(new_vouchers)
    
    save_vouchers_to_disk(all_vouchers)

    household.mark_claimed(tranche)
    save_household_json()

    return True, {
        "message": "Vouchers generated successfully",
        "tranche": tranche,
        "count": len(new_vouchers),
        "vouchers": new_vouchers  # 回傳給前端顯示用
    }
