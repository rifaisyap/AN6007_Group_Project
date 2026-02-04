import json
import os
import datetime
import csv
import sqlite3
from datetime import datetime, timedelta

# --- Directory and File Path Configurations ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "vouchers.db")
MERCHANT_FILE = os.path.join(BASE_DIR, "merchants.csv")

# --- Memory Cache and Temporary Log Settings ---
PENDING_CACHE = {}
PENDING_LOG = os.path.join(BASE_DIR, "pending_log.txt")

def reload_pending_requests(expiry_seconds=3600): 
    """
    Restores data from the flat file into memory and filters out:
    1. Transactions marked as 'REMOVED'.
    2. Expired transactions (defaults to 1 hour).
    """
    global PENDING_CACHE
    if not os.path.exists(PENDING_LOG): return

    temp_cache = {}
    try:
        with open(PENDING_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                entry = json.loads(line)
                for code, data in entry.items():
                    if data == "REMOVED":
                        # Remove from temporary cache if a tombstone record is found
                        if code in temp_cache: del temp_cache[code]
                    else:
                        # Check if the redemption code has expired
                        t_str = data.get("timestamp")
                        if t_str:
                            req_time = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S.%f")
                            # Only reinstate if the request is within the validity window
                            if datetime.now() - req_time < timedelta(seconds=expiry_seconds):
                                temp_cache[code] = data
        
        PENDING_CACHE = temp_cache
        # Execute log compaction to wipe expired or deleted entries from the physical file
        compact_log() 
        print(f"Successfully re-instated {len(PENDING_CACHE)} active requests.")
    except Exception as e:
        print(f"Error re-instating data: {e}")

def save_pending_request(code, data):
    """
    Efficiently saves request: Adds a timestamp, updates memory cache, 
    and appends to the log file.
    """
    # Record the exact time of code generation for TTL (Time-to-Live) checks
    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # Update local memory cache for O(1) retrieval speed
    PENDING_CACHE[code] = data
    
    # Append to log file (Append-only mode ensures high performance)
    with open(PENDING_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({code: data}) + "\n")

def get_pending_request(code):
    """Retrieves a pending request directly from memory cache."""
    return PENDING_CACHE.get(code)

def remove_pending_request(code):
    """
    Appends a 'REMOVED' tombstone to the log and removes it from memory.
    This signifies the code has been successfully used or cancelled.
    """
    if code in PENDING_CACHE:
        del PENDING_CACHE[code]
        with open(PENDING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({code: "REMOVED"}) + "\n")

def compact_log():
    """
    Log Compaction: Overwrites the physical log file with only the valid 
    data currently in memory, permanently removing expired or 'REMOVED' lines.
    """
    try:
        with open(PENDING_LOG, "w", encoding="utf-8") as f:
            for code, data in PENDING_CACHE.items():
                f.write(json.dumps({code: data}) + "\n")
    except Exception as e:
        print(f"Log compaction failed: {e}")

# --- Database Connection and Balance Logic ---

def get_db_connection():
    """Establishes connection to SQLite with WAL mode enabled for better concurrency."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def get_balance(household_id):
    """Returns a list of active vouchers for a specific household from SQL."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM vouchers WHERE household_id = ? AND status = 'Active'",
            (household_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_redemption_history(household_id):
    """
    Reads confirmed redemption records from vouchers.db.
    This strictly excludes pending or failed attempts.
    """
    conn = get_db_connection()
    try:
        # Query only the history table, which is updated only after merchant confirmation
        cursor = conn.execute("""
            SELECT amount, merchant_id, date, items_json 
            FROM redemption_history 
            WHERE household_id = ? 
            ORDER BY date DESC
        """, (household_id,))
        
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            # Parse the JSON string representing voucher denominations (e.g., {"2": 5})
            if d.get('items_json'):
                try:
                    d['items'] = json.loads(d['items_json'])
                except:
                    d['items'] = {}
            else:
                d['items'] = {}
            results.append(d)
        return results
    except Exception as e:
        print(f"Error fetching redemption history: {e}")
        return []
    finally:
        conn.close()

# --- Merchant Verification and Redemption Logic ---

def is_valid_merchant(merchant_id):
    """Checks if the Merchant ID exists and is currently 'Active' in the CSV."""
    if not os.path.exists(MERCHANT_FILE):
        return False
    with open(MERCHANT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Merchant_ID", "").strip() == merchant_id:
                return row.get("Status", "").strip().lower() == "active"
    return False

def merchant_confirm_redemption(household_id, merchant_id, selections):
    """
    Finalizes the transaction: 
    1. Updates SQL voucher status.
    2. Inserts into SQL history table.
    3. Triggers CSV audit log generation.
    """
    if not is_valid_merchant(merchant_id):
        return False, "INVALID_MERCHANT"

    conn = get_db_connection()
    now = datetime.now()
    txn_id = f"TX{int(now.timestamp())}"
    redeemed_details = []
    total_amount = 0

    try:
        with conn:
            # Ensure the history table exists before insertion
            conn.execute('''
                CREATE TABLE IF NOT EXISTS redemption_history (
                    transaction_id TEXT PRIMARY KEY,
                    household_id TEXT,
                    merchant_id TEXT,
                    amount INTEGER,
                    items_json TEXT,
                    date TEXT
                )
            ''')

            for amt_str, qty in selections.items():
                amt = int(amt_str)
                cursor = conn.execute("""
                    SELECT voucher_code FROM vouchers 
                    WHERE household_id = ? AND amount = ? AND status = 'Active' 
                    LIMIT ?
                """, (household_id, amt, int(qty)))
                
                rows = cursor.fetchall()
                if len(rows) < int(qty): return False, "VOUCHER_NOT_AVAILABLE"

                for row in rows:
                    v_code = row['voucher_code']
                    # Update status in the main voucher ledger
                    conn.execute("UPDATE vouchers SET status = 'Redeemed' WHERE voucher_code = ?", (v_code,))
                    redeemed_details.append({"code": v_code, "amt": amt})
                    total_amount += amt

            # Record successfully completed transaction in SQL
            conn.execute("""
                INSERT INTO redemption_history (transaction_id, household_id, merchant_id, amount, items_json, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (txn_id, household_id, merchant_id, total_amount, json.dumps(selections), now.strftime("%Y-%m-%d %H:%M:%S")))

        # Generate the physical CSV audit file for government/merchant reimbursement
        _write_audit_csv(txn_id, household_id, merchant_id, total_amount, redeemed_details, now)
        return True, "SUCCESS"
    except Exception as e:
        print(f"Redemption error: {e}")
        return False, str(e)
    finally:
        conn.close()

def _write_audit_csv(txn_id, household_id, merchant_id, total_amount, redeemed_details, now):
    """Generates an audit-ready CSV file following the RedeemYYYYMMDDHH.csv format."""
    folder = os.path.join(BASE_DIR, "redemption")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"Redeem{now.strftime('%Y%m%d%H')}.csv")
    
    headers = ["Transaction_ID", "Household_ID", "Merchant_ID", "Transaction_Date_Time", "Voucher_Code", "Denomination_Used", "Amount_Redeemed", "Payment_Status", "Remarks"]
    file_exists = os.path.isfile(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists: writer.writeheader()
        for i, d in enumerate(redeemed_details):
            remark = "Final denomination used" if i == len(redeemed_details)-1 else str(i+1)
            writer.writerow({
                "Transaction_ID": txn_id, "Household_ID": household_id, "Merchant_ID": merchant_id,
                "Transaction_Date_Time": now.strftime("%Y-%m-%d %H:%M:%S"), "Voucher_Code": d["code"],
                "Denomination_Used": f"${d['amt']}.00", "Amount_Redeemed": f"${total_amount}.00",
                "Payment_Status": "Completed", "Remarks": remark
            })

if __name__ == "__main__":
    # For development and testing purposes only
    reload_pending_requests()