"""
API Client for Voucher Management System

This module provides data access and business logic functions for the voucher system.
All operations are performed on local JSON and CSV files, making the system fully offline.
"""

import json
import os
import datetime
import csv

# Set file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_redemptions.json")  # Used for cross-app communication

def get_balance(household_id):
    """
    Retrieve all active vouchers for a specific household.

    Args:
        household_id: The unique identifier of the household

    Returns:
        List of active voucher dictionaries, empty list if none found
    """
    if not os.path.exists(VOUCHER_FILE):
        return []

    with open(VOUCHER_FILE, "r") as file:
        voucher_data = json.load(file)

    # Get the household's data from the main structure
    household_info = voucher_data.get(household_id, {})

    # Extract vouchers list from household data
    all_vouchers = household_info.get("vouchers", [])

    # Filter for active vouchers only
    active_vouchers = [
        voucher for voucher in all_vouchers
        if voucher.get("status") == "Active"
    ]

    return active_vouchers

def get_redemption_history(household_id):
    """
    Get the complete redemption history for a household.

    Args:
        household_id: The unique identifier of the household

    Returns:
        List of redemption transaction records, empty list if no history exists
    """
    if not os.path.exists(VOUCHER_FILE):
        return []

    with open(VOUCHER_FILE, "r") as file:
        voucher_data = json.load(file)

    # Access household data
    household_info = voucher_data.get(household_id, {})

    # Check if data is in new dictionary format
    if isinstance(household_info, dict):
        return household_info.get("redemption_history", [])

    # Return empty list for old data formats (direct list)
    return []

def get_full_data(household_id):
    """
    Retrieve complete household data including vouchers and history.

    Args:
        household_id: The unique identifier of the household

    Returns:
        Complete household data dictionary, empty dict if not found
    """
    if not os.path.exists(VOUCHER_FILE):
        return {}

    with open(VOUCHER_FILE, "r") as file:
        voucher_data = json.load(file)

    return voucher_data.get(household_id, {})

# --- Cross-application temporary request management ---

def save_pending_request(code, data):
    """
    Save a redemption request to temporary storage for merchant processing.

    Args:
        code: 6-character redemption code
        data: Dictionary containing household_id, selections, and total amount
    """
    # Read existing requests or start with empty dictionary
    existing_requests = {}
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r") as file:
                existing_requests = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            # Use empty dict if file is corrupted or doesn't exist
            existing_requests = {}

    # Add or update the request
    existing_requests[code] = data

    # Save back to file
    with open(PENDING_FILE, "w") as file:
        json.dump(existing_requests, file, indent=4)

def get_pending_request(code):
    """
    Retrieve a pending redemption request by its code.

    Args:
        code: 6-character redemption code to look up

    Returns:
        Request data dictionary if found, None otherwise
    """
    if not os.path.exists(PENDING_FILE):
        return None

    try:
        with open(PENDING_FILE, "r") as file:
            all_requests = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    return all_requests.get(code)

def remove_pending_request(code):
    """
    Remove a completed or expired redemption request.

    Args:
        code: The redemption code to remove
    """
    if not os.path.exists(PENDING_FILE):
        return

    try:
        with open(PENDING_FILE, "r") as file:
            all_requests = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    # Remove the request if it exists
    if code in all_requests:
        del all_requests[code]

        # Save the updated list
        with open(PENDING_FILE, "w") as file:
            json.dump(all_requests, file, indent=4)

# --- Redemption processing logic ---

def merchant_confirm_redemption(household_id, merchant_id, selections):
    """
    Process a redemption request from a merchant.

    This function:
    1. Updates voucher statuses in the JSON database
    2. Adds transaction to redemption history
    3. Generates CSV audit log for accounting
    4. Returns success/failure status

    Args:
        household_id: ID of the household redeeming vouchers
        merchant_id: ID of the merchant processing the redemption
        selections: Dictionary mapping denomination amounts to quantities

    Returns:
        True if redemption successful, False otherwise
    """
    # Check if voucher data file exists
    if not os.path.exists(VOUCHER_FILE):
        return False

    try:
        with open(VOUCHER_FILE, "r") as file:
            all_voucher_data = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

    # Verify household exists
    if household_id not in all_voucher_data:
        return False

    # Access household's data
    household_record = all_voucher_data[household_id]
    household_vouchers = household_record.get("vouchers", [])

    # Track redeemed vouchers
    redemption_details = []
    total_redemption_amount = 0

    # Process each denomination requested
    for amount_str, quantity_str in selections.items():
        target_amount = int(amount_str)
        quantity_needed = int(quantity_str)
        redeemed_count = 0

        # Find and redeem matching vouchers
        for voucher in household_vouchers:
            if voucher["amount"] == target_amount and voucher["status"] == "Active":
                # Mark voucher as redeemed
                voucher["status"] = "Redeemed"

                # Record redemption details
                redemption_details.append({
                    "code": voucher["voucher_code"],
                    "amt": target_amount
                })

                total_redemption_amount += target_amount
                redeemed_count += 1

                # Stop if we've redeemed enough of this denomination
                if redeemed_count >= quantity_needed:
                    break

    # Check if any vouchers were actually redeemed
    if not redemption_details:
        return False

    # Create transaction record
    current_time = datetime.datetime.now()
    transaction_id = f"TX{int(current_time.timestamp())}"

    transaction_record = {
        "transaction_id": transaction_id,
        "date": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "merchant_id": merchant_id,
        "amount": total_redemption_amount,
        "items": selections
    }

    # Ensure history array exists
    if "redemption_history" not in household_record:
        household_record["redemption_history"] = []

    # Add to history
    household_record["redemption_history"].append(transaction_record)

    # Save updated data
    try:
        with open(VOUCHER_FILE, "w") as file:
            json.dump(all_voucher_data, file, indent=4)
    except Exception:
        return False

    # Generate CSV audit log
    generate_audit_csv(
        transaction_id=transaction_id,
        household_id=household_id,
        merchant_id=merchant_id,
        transaction_time=current_time,
        redemption_details=redemption_details,
        total_amount=total_redemption_amount
    )

    return True

def generate_audit_csv(transaction_id, household_id, merchant_id,
                      transaction_time, redemption_details, total_amount):
    """
    Generate CSV audit log for accounting and settlement purposes.

    Each redemption creates one row per voucher in a timestamped CSV file.
    Files are organized by hour for easy merchant settlement processing.

    Args:
        transaction_id: Unique transaction identifier
        household_id: ID of redeeming household
        merchant_id: ID of processing merchant
        transaction_time: When the transaction occurred
        redemption_details: List of voucher details
        total_amount: Total amount redeemed
    """
    # Create filename based on transaction hour
    hour_timestamp = transaction_time.strftime('%Y%m%d%H')
    file_name = f"Redeem{hour_timestamp}.csv"

    # CSV column headers
    csv_headers = [
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

    # Check if file exists to determine if we need headers
    file_exists = os.path.isfile(file_name)

    try:
        with open(file_name, "a", newline="") as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=csv_headers)

            # Write header only for new files
            if not file_exists:
                csv_writer.writeheader()

            # Create one row per redeemed voucher
            for index, detail in enumerate(redemption_details):
                is_last_voucher = (index == len(redemption_details) - 1)

                # Create remark: "Final denomination used" for last voucher
                remark_text = "Final denomination used" if is_last_voucher else str(index + 1)

                csv_writer.writerow({
                    "Transaction_ID": transaction_id,
                    "Household_ID": household_id,
                    "Merchant_ID": merchant_id,
                    "Transaction_Date_Time": transaction_time.strftime("%Y-%m-%d-%H%M%S"),
                    "Voucher_Code": detail["code"],
                    "Denomination_Used": f"${detail['amt']}.00",
                    "Amount_Redeemed": f"${total_amount}.00",
                    "Payment_Status": "Completed",
                    "Remarks": remark_text
                })
    except Exception as error:
        # Log error but don't fail the main operation
        print(f"Error generating CSV log: {error}")