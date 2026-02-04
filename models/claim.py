import uuid
import sqlite3
import os
import json
from datetime import datetime

# 引用連線與讀取函數
from storage.household_storage import (
    get_db_connection, 
    load_single_household
)

# 根據專案文件第 3 頁定義的精確面額分配 [cite: 90, 92]
TRANCHE_CONFIG = {
    "May_2025": {
        "total_value": 500,
        "breakdown": [
            {"amount": 2, "count": 50},  # $100
            {"amount": 5, "count": 20},  # $100
            {"amount": 10, "count": 30}  # $300, 總計 $500 
        ]
    },
    "Jan_2026": {
        "total_value": 300,
        "breakdown": [
            {"amount": 2, "count": 30},  # $60
            {"amount": 5, "count": 12},  # $60
            {"amount": 10, "count": 18}  # 修正為 18 張以湊足專案要求的 $300 總額 [cite: 88, 92]
        ]
    }
}

def generate_vouchers(household_id, tranche):
    """
    實作 Requirement 2c: 根據不同輪次生成券 [cite: 84, 85]
    使用單一 SQL 事務處理，防止資料庫鎖定並確保狀態同步。
    """
    # 1. 讀取住戶最新狀態
    household = load_single_household(household_id)
    if not household:
        return False, "Household not found"

    # 2. 檢查是否領取過 (由 household.py 內的字典狀態判定)
    if not household.can_claim(tranche):
        return False, f"Tranche {tranche} already claimed."

    config = TRANCHE_CONFIG.get(tranche)
    if not config:
        return False, "Invalid tranche type"

    # 3. 開始單一資料庫連線
    conn = get_db_connection()
    try:
        with conn: # 開啟事務 (Transaction)
            # 建立券資料表，使用專案要求的元數據欄位 [cite: 107, 111, 112]
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
            # 建立索引以支援快速檢索餘額 [cite: 53]
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_hid ON vouchers(household_id);")

            new_vouchers = []
            now_str = datetime.now().isoformat()
            
            # 批量生成券
            for item in config['breakdown']:
                amt = item['amount']
                for _ in range(item['count']):
                    # 唯一代碼：V-住戶ID-輪次-隨機碼 [cite: 111]
                    unique_suffix = uuid.uuid4().hex[:8].upper()
                    code = f"V-{household_id}-{tranche[:3].upper()}-{unique_suffix}"
                    
                    conn.execute("""
                        INSERT INTO vouchers (voucher_code, household_id, amount, tranche, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, household_id, amt, tranche, "Active", now_str))
                    
                    new_vouchers.append({"voucher_code": code, "amount": amt})

            # 4. 同步更新住戶領取狀態 (標記為 True)
            # 直接在同一個連線執行 UPDATE，避免 database is locked
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