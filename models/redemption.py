import os
import csv
import uuid
from datetime import datetime
from .claim import load_vouchers_from_disk, save_vouchers_to_disk

# CSV header format for redemption records
CSV_HEADERS = [
    "Transaction_ID",
    "Household_ID",
    "Merchant_ID",
    "Transaction_Date_Time",
    "Voucher_Code",
    "Denomination_Used",
    "Amount_Redeemed",
    "Payment_Status",
    "Remarks"
]

def generate_qr_string(household_id, amount):
    """
    Household side
    User selects voucher amount ($2, $5, $10)
    QR string format: HouseholdID + VoucherCode
    """
    all_vouchers = load_vouchers_from_disk()
    user_vouchers = all_vouchers.get(household_id, [])

    target_voucher = None
    for v in user_vouchers:
        if v["amount"] == amount and v["status"] == "Active":
            target_voucher = v
            break

    if not target_voucher:
        return False, "No active vouchers found for this amount."

    qr_code_string = f"{household_id}+{target_voucher['voucher_code']}"

    return True, {
        "qr_string": qr_code_string,
        "voucher_info": target_voucher
    }

def process_redemption(merchant_id, code_input):
    """
    Merchant side
    Enter code -> verify -> deduct -> write CSV
    """

    # Step 1: Parse QR input
    try:
        if "+" not in code_input:
            return False, "Invalid format. Expected 'HouseholdID+VoucherCode'"
        h_id, v_code = code_input.split("+")
    except ValueError:
        return False, "Parsing error."

    # Step 2: Load voucher data
    all_vouchers = load_vouchers_from_disk()
    user_vouchers = all_vouchers.get(h_id)

    if not user_vouchers:
        return False, "Household not found."

    # Step 3: Find the voucher
    target_idx = -1
    for i, v in enumerate(user_vouchers):
        if v["voucher_code"] == v_code:
            target_idx = i
            break

    if target_idx == -1:
        return False, "Voucher not found."

    voucher = user_vouchers[target_idx]

    if voucher["status"] != "Active":
        return False, f"Voucher is {voucher['status']}, cannot redeem."

    # Step 4: Update voucher status
    current_time = datetime.now()
    timestamp_str = current_time.strftime("%Y%m%d%H%M%S")
    txn_id = f"TX{uuid.uuid4().hex[:6].upper()}"

    voucher["status"] = "Redeemed"
    voucher["redeemed_at"] = current_time.isoformat()
    voucher["redeemed_by"] = merchant_id

    user_vouchers[target_idx] = voucher
    all_vouchers[h_id] = user_vouchers
    save_vouchers_to_disk(all_vouchers)

    # Step 5: Write CSV file into redemption folder

    # Folder to store all redemption CSV files
    redemption_folder = "redemption"

    # Create folder if it does not exist
    if not os.path.exists(redemption_folder):
        os.makedirs(redemption_folder)

    # CSV filename grouped by hour
    csv_filename = f"Redeem{current_time.strftime('%Y%m%d%H')}.csv"

    # Full file path inside redemption folder
    csv_path = os.path.join(redemption_folder, csv_filename)

    file_exists = os.path.isfile(csv_path)

    with open(csv_path, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write header only once
        if not file_exists:
            writer.writerow(CSV_HEADERS)

        writer.writerow([
            txn_id,                       # Transaction_ID
            h_id,                          # Household_ID
            merchant_id,                  # Merchant_ID
            timestamp_str,                # Transaction_Date_Time
            v_code,                       # Voucher_Code
            f"${voucher['amount']:.2f}",   # Denomination_Used
            f"${voucher['amount']:.2f}",   # Amount_Redeemed
            "Completed",                  # Payment_Status
            "Final denomination used"     # Remarks
        ])

    return True, {
        "message": "Redemption Successful",
        "transaction_id": txn_id,
        "amount": voucher["amount"],
        "new_status": "Redeemed"
    }
