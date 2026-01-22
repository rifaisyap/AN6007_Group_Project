import json
import os
from models.household import Household

household_db = {} 
FILE_PATH = "household_data.json"

    data_to_save = {k: v.to_dict() for k, v in household_db.items()}
    with open(FILE_PATH, 'w') as f:
        json.dump(data_to_save, f, indent=4)

def load_household_data():
    if not os.path.exists(FILE_PATH):
        return

    try:
        with open(FILE_PATH, 'r') as f:
            data = json.load(f)
            for h_id, h_data in data.items():
                household_db[h_id] = Household.from_dict(h_data)
        print(f"[System] Loaded {len(household_db)} households from storage.")
    except Exception as e:
        print(f"[Error] Failed to load data: {e}")
