import json
import os
from models import Household

FILE_PATH = "household_data.json"
household_db = {} 

def save_to_file():
    data_to_save = {k: v.to_dict() for k, v in household_db.items()}
    with open(FILE_PATH, 'w') as f:
        json.dump(data_to_save, f, indent=4)

def load_from_file():
    if not os.path.exists(FILE_PATH):
        return

    try:
        with open(FILE_PATH, 'r') as f:
            data = json.load(f)
            for h_id, h_data in data.items():
                household_db[h_id] = Household.from_dict(h_data)
        print(f"[System] Loaded {len(household_db)} households.")
    except Exception as e:
        print(f"[Error] Failed to load data: {e}")
