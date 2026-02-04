import uuid
import sqlite3
import os
import json
from datetime import datetime

from storage.household_storage import (
    get_db_connection, 
    load_single_household
)
TRANCHE_CONFIG = {
    "May_2025": {
        "total_value": 500,
        "breakdown": [
            {"amount": 2, "count": 50},  # $100
            {"amount": 5, "count": 20},  # $100
            {"amount": 10, "count": 30}  # $300
        ]
    },
    "Jan_2026": {
        "total_value": 300,
        "breakdown": [
            {"amount": 2, "count": 30},  # $60
            {"amount": 5, "count": 12},  # $60
            {"amount": 10, "count": 15}  # $150
        ]
    }
}

def generate_vouchers(household_id, tranche):
    # 1. 
    household = load_single_household(household_id)
    if not household:
        return False, "Household not found"

    # 2. 
    if not household.can_claim(tranche):
        return False, f"Tranche {tranche} already claimed."

    config = TRANCHE_CONFIG.get(tranche)
    if not config:
        return False, "Invalid tranche type"

    # 3.
    conn = get_db_connection()
    try:
        with conn: 
            conn.execute('''
                CREATE TABLE IF NOT EXISTS vouchers (
                    voucher_code TEXT PRIMARY KEY,
                    household_id TEXT,
                    amount INTEGER,
                    tranche TEXT,
                    status TEXT,
                    created_at TEXT
                )
            ''')
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_hid ON vouchers(household_id);")

            new_vouchers = []
            now_str = datetime.now().isoformat()
            
            # 批量生成券
            for item in config['breakdown']:
                amt = item['amount']
                for _ in range(item['count']):
                    unique_suffix = uuid.uuid4().hex[:8].upper()
                    code = f"V-{household_id}-{tranche[:3].upper()}-{unique_suffix}"
                    
                    conn.execute("""
                        INSERT INTO vouchers (voucher_code, household_id, amount, tranche, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, household_id, amt, tranche, "Active", now_str))
                    
                    new_vouchers.append({"voucher_code": code, "amount": amt})

            household.mark_claimed(tranche)
            conn.execute("""
                UPDATE households 
                SET data_json = ? 
                WHERE household_id = ?
            """, (json.dumps(household.to_dict()), household_id))

        return True, {
            "message": f"Successfully generated {len(new_vouchers)} vouchers",
            "tranche": tranche,
            "vouchers": new_vouchers  
        }

    except Exception as e:
        print(f"[SQL Transaction Error] {e}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()
