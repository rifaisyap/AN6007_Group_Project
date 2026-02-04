import sqlite3
import os
import json
from models.household import Household

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vouchers.db")

def get_db_connection():
    """connects to database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def save_household_sql(household_obj):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS households (
                    household_id TEXT PRIMARY KEY,
                    data_json TEXT
                )
            ''')
            conn.execute("""
                INSERT OR REPLACE INTO households (household_id, data_json)
                VALUES (?, ?)
            """, (household_obj.household_id, json.dumps(household_obj.to_dict())))
        return True
    except Exception as e:
        print(f"[Error] Failed to save household: {e}")
        return False
    finally:
        conn.close()

def load_single_household(household_id):
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS households (
                household_id TEXT PRIMARY KEY,
                data_json TEXT
            )
        ''')
        
        row = conn.execute(
            "SELECT data_json FROM households WHERE household_id = ?", 
            (household_id,)
        ).fetchone()
        
        if row:
            h_data = json.loads(row['data_json'])
            return Household.from_dict(h_data)
        return None
    except Exception as e:
        print(f"[Error] Load household failed: {e}")
        return None
    finally:
        conn.close()

household_db = {}