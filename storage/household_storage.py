import json
import os
# 注意：這裡路徑要確保正確
from models.household import Household

# 定義全域變數
household_db = {} 
FILE_PATH = "household_data.json"

# [FIX] 函數名稱必須與 main.py 的 import 一致
def save_household_json():
    """將記憶體資料存入硬碟"""
    data_to_save = {k: v.to_dict() for k, v in household_db.items()}
    with open(FILE_PATH, 'w') as f:
        json.dump(data_to_save, f, indent=4)
    # print(f"[System] Data saved to {FILE_PATH}") # Debug 用

# [FIX] 函數名稱必須與 main.py 的 import 一致
def load_household_data():
    """伺服器啟動時載入資料"""
    if not os.path.exists(FILE_PATH):
        return

    try:
        with open(FILE_PATH, 'r') as f:
            data = json.load(f)
            for h_id, h_data in data.items():
                # 使用 from_dict 重建對象
                household_db[h_id] = Household.from_dict(h_data)
        print(f"[System] Loaded {len(household_db)} households from storage.")
    except Exception as e:
        print(f"[Error] Failed to load data: {e}")
