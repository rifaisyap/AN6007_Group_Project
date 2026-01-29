import json
import os
import datetime
import csv

# Set file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_redemptions.json") # Used for cross-app communication

def get_balance(household_id):
    """Retrieve all 'Active' vouchers for a household"""
    if not os.path.exists(HOUSEHOLD_FILE) or not os.path.exists(VOUCHER_FILE):
        return None
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    vouchers = data.get(household_id, [])
    return [v for v in vouchers if v.get("status") == "Active"]

# --- Added: Management of temporary requests across apps ---

def save_pending_request(code, data):
    """Save the generated code and data to JSON from the user client"""
    requests = {}
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            try: requests = json.load(f)
            except: requests = {}
    requests[code] = data
    with open(PENDING_FILE, "w") as f:
        json.dump(requests, f, indent=4)

def get_pending_request(code):
    """Read the temporary request from the merchant side"""
    if not os.path.exists(PENDING_FILE): return None
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    return requests.get(code)

def remove_pending_request(code):
    """Remove temporary request after successful redemption"""
    if not os.path.exists(PENDING_FILE): return
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    if code in requests:
        del requests[code]
        with open(PENDING_FILE, "w") as f:
            json.dump(requests, f, indent=4)

# --- Fixed: Official redemption logic (Addresses JSON updates and CSV denomination issues) ---

def merchant_confirm_redemption(household_id, merchant_id, selections):
    if not os.path.exists(VOUCHER_FILE): return False

    # 1. Read and modify JSON status
    with open(VOUCHER_FILE, "r") as f:
        all_data = json.load(f)

    if household_id not in all_data: return False

    vouchers = all_data[household_id]
    redeemed_details = []
    total_amount = 0

    # Find vouchers corresponding to the selected denominations (e.g., {"2": 1, "5": 1})
    for amt_str, qty in selections.items():
        count = 0
        target_amt = int(amt_str)
        for v in vouchers:
            if v["amount"] == target_amt and v["status"] == "Active":
                v["status"] = "Redeemed" # Change status to Redeemed
                redeemed_details.append({"code": v["voucher_code"], "amt": target_amt})
                total_amount += target_amt
                count += 1
                if count >= int(qty): break

    if not redeemed_details: return False

    # 2. Write back to JSON to ensure status is updated
    with open(VOUCHER_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

    # 3. Generate hourly CSV records following the specification
    now = datetime.datetime.now()
    file_name = f"Redeem{now.strftime('%Y%m%d%H')}.csv"
    txn_id = f"TX{int(now.timestamp())}"
    
    headers = ["Transaction_ID", "Household_ID", "Merchant_ID", "Transaction_Date_Time", 
               "Voucher_Code", "Denomination_Used", "Amount_Redeemed", "Payment_Status", "Remarks"]

    file_exists = os.path.isfile(file_name)
    with open(file_name, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists: writer.writeheader()
        
        for i, detail in enumerate(redeemed_details):
            is_last = (i == len(redeemed_details) - 1)
            remark = "Final denomination used" if is_last else str(i + 1)
            
            writer.writerow({
                "Transaction_ID": txn_id,
                "Household_ID": household_id,
                "Merchant_ID": merchant_id,
                "Transaction_Date_Time": now.strftime("%Y-%m-%d-%H%M%S"),
                "Voucher_Code": detail["code"],
                "Denomination_Used": f"${detail['amt']}.00", # Fixed to reflect actual denomination used
                "Amount_Redeemed": f"${total_amount}.00",
                "Payment_Status": "Completed",
                "Remarks": remark
            })
    return True