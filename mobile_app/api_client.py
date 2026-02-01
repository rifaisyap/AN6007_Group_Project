import json
import os
import datetime
import csv

# Base directory (project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_redemptions.json")
MERCHANT_FILE = os.path.join(BASE_DIR, "merchants.csv")


# Household helpers
def get_balance(household_id):
    if not os.path.exists(VOUCHER_FILE):
        return []
    # Load voucher store from disk (file-based persistence)
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    # Per-household container stores: vouchers and recordsredemption_history
    user_data = data.get(household_id, {})
    vouchers = user_data.get("vouchers", [])

    return [v for v in vouchers if v.get("status") == "Active"]


def get_redemption_history(household_id):
    if not os.path.exists(VOUCHER_FILE):
        return []

    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)

    user_data = data.get(household_id, {})
    return user_data.get("redemption_history", [])


# Pending redemption helpers
def save_pending_request(code, data):
    requests = {}

    # Load existing pending requests if file exists
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            try:
                requests = json.load(f)
            except:
                requests = {}

    # Store the pending request under the redeem code
    requests[code] = data

    with open(PENDING_FILE, "w") as f:
        json.dump(requests, f, indent=4)


def get_pending_request(code):
    if not os.path.exists(PENDING_FILE):
        return None

    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)

    return requests.get(code)


def remove_pending_request(code):
    if not os.path.exists(PENDING_FILE):
        return

    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)

    if code in requests:
        del requests[code]

        with open(PENDING_FILE, "w") as f:
            json.dump(requests, f, indent=4)


# Merchant validation helper

def is_valid_merchant(merchant_id):
    # Merchant file must exist
    if not os.path.exists(MERCHANT_FILE):
        return False

    merchant_id = merchant_id.strip()

    # Scan CSV to find matching merchant_id and check status
    with open(MERCHANT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_merchant_id = row.get("Merchant_ID", "").strip()
            status = row.get("Status", "").strip().lower()

            if csv_merchant_id == merchant_id:
                return status == "active"

    return False


# Merchant redemption logic

def merchant_confirm_redemption(household_id, merchant_id, selections):
    # Step 1: Validate merchant FIRST
    if not is_valid_merchant(merchant_id):
        return False, "INVALID_MERCHANT"

    if not os.path.exists(VOUCHER_FILE):
        return False, "VOUCHER_FILE_NOT_FOUND"

    # Step 2: Load voucher data
    with open(VOUCHER_FILE, "r") as f:
        all_data = json.load(f)

    # Step 3: Validate household
    if household_id not in all_data:
        return False, "HOUSEHOLD_NOT_FOUND"

    user_container = all_data[household_id]
    vouchers = user_container.get("vouchers", [])

    redeemed_details = []
    total_amount = 0

    # Step 4: Redeem vouchers
    for amt_str, qty in selections.items():
        count = 0
        target_amt = int(amt_str)

        for v in vouchers:
            if v["amount"] == target_amt and v["status"] == "Active":
                v["status"] = "Redeemed"
                redeemed_details.append({
                    "code": v["voucher_code"],
                    "amt": target_amt
                })
                total_amount += target_amt
                count += 1

                if count >= int(qty):
                    break

    if not redeemed_details:
        return False, "VOUCHER_NOT_AVAILABLE"

    # Step 5: Add redemption history
    now = datetime.datetime.now()
    txn_id = f"TX{int(now.timestamp())}"

    history_entry = {
        "transaction_id": txn_id,
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "merchant_id": merchant_id,
        "amount": total_amount,
        "items": selections
    }

    if "redemption_history" not in user_container:
        user_container["redemption_history"] = []

    user_container["redemption_history"].append(history_entry)

    # Step 6: Save voucher JSON
    with open(VOUCHER_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

    # Step 7: Write CSV record to redemption folder
    csv_folder = os.path.join(BASE_DIR, "redemption")
    os.makedirs(csv_folder, exist_ok=True)

    csv_name = f"Redeem{now.strftime('%Y%m%d%H')}.csv"
    csv_path = os.path.join(csv_folder, csv_name)

    headers = [
        "Transaction_ID", "Household_ID", "Merchant_ID",
        "Transaction_Date_Time", "Voucher_Code",
        "Denomination_Used", "Amount_Redeemed",
        "Payment_Status", "Remarks"
    ]

    file_exists = os.path.isfile(csv_path)
    
    # Append to the hourly CSV
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)

        if not file_exists:
            writer.writeheader()
        
        # Write one row per redeemed voucher 
        # Mark the final row for easier readability in CSV
        for i, detail in enumerate(redeemed_details):
            remark = "Final denomination used" if i == len(redeemed_details) - 1 else str(i + 1)

            writer.writerow({
                "Transaction_ID": txn_id,
                "Household_ID": household_id,
                "Merchant_ID": merchant_id,
                "Transaction_Date_Time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "Voucher_Code": detail["code"],
                "Denomination_Used": f"${detail['amt']}.00",
                "Amount_Redeemed": f"${total_amount}.00",
                "Payment_Status": "Completed",
                "Remarks": remark
            })

    return True, "SUCCESS"
