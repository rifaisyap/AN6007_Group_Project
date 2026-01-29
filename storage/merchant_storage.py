import csv
from datetime import datetime
from models.merchant import Merchant

OUTPUT_FILE = "merchants.csv"

# In-memory data structure
MERCHANTS = {} 

# Bank reference data
BANK_DATA = [
    {"bank_code": "7171", "bank_name": "DBS Bank Ltd", "branch_code": "001", "branch_name": "Main Branch"},
    {"bank_code": "7339", "bank_name": "OCBC Bank", "branch_code": "501", "branch_name": "Tampines Branch"},
    {"bank_code": "7761", "bank_name": "UOB Bank", "branch_code": "001", "branch_name": "Raffles Place"},
    {"bank_code": "7091", "bank_name": "Maybank Singapore", "branch_code": "001", "branch_name": "Main Branch"},
    {"bank_code": "7302", "bank_name": "Standard Chartered Bank", "branch_code": "001", "branch_name": "Main Branch"},
    {"bank_code": "7375", "bank_name": "HSBC Singapore", "branch_code": "146", "branch_name": "Orchard Branch"},
    {"bank_code": "7171", "bank_name": "POSB Bank", "branch_code": "081", "branch_name": "Toa Payoh Branch"},
    {"bank_code": "9465", "bank_name": "Citibank Singapore", "branch_code": "001", "branch_name": "Main Branch"},
    {"bank_code": "7083", "bank_name": "RHB Bank Berhad", "branch_code": "001", "branch_name": "Main Branch"},
    {"bank_code": "7012", "bank_name": "Bank of China Singapore", "branch_code": "001", "branch_name": "Main Branch"}
]

# Required fields
REQUIRED_FIELDS = [
    "merchant_name",
    "uen",
    "bank_name",
    "bank_code",
    "branch_code",
    "account_number",
    "account_holder_name",
    "status"
]

ALLOWED_STATUS = {"active", "pending", "suspended"}


def is_numeric(value: str) -> bool:
    return value.isdigit()


# Validate bank details
def validate_bank_details(bank_name, bank_code, branch_code):
    banks = []
    for bank in BANK_DATA:
        if bank["bank_name"] == bank_name:
            banks.append(bank)

    if len(banks) == 0:
        return False, "INVALID_BANK_NAME", None

    valid_bank_codes = []
    for bank in banks:
        valid_bank_codes.append(bank["bank_code"])

    if bank_code not in valid_bank_codes:
        return False, "INVALID_BANK_CODE", None

    for bank in banks:
        if bank["branch_code"] == branch_code:
            return True, None, bank["branch_name"]

    return False, "INVALID_BRANCH_CODE", None


# Save merchant to CSV file
def save_merchant_to_csv(merchant: Merchant, branch_name: str):
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write header (simple beginner approach)
        writer.writerow([
            "merchant_id",
            "merchant_name",
            "uen",
            "bank_name",
            "bank_code",
            "branch_code",
            "branch_name",
            "account_number",
            "account_holder_name",
            "status",
            "saved_at"
        ])

        # Write merchant data
        writer.writerow([
            merchant.merchant_id,
            merchant.merchant_name,
            merchant.uen,
            merchant.bank_name,
            merchant.bank_code,
            merchant.branch_code,
            branch_name,
            merchant.account_number,
            merchant.account_holder_name,
            merchant.status,
            datetime.utcnow().isoformat()
        ])


# Validate incoming payload
def validate_payload(payload):
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in payload:
            return "Missing required fields"

    # Validate status
    status = payload["status"].lower()
    if status not in ALLOWED_STATUS:
        return "Invalid status"

    # Validate account number
    account_number = payload["account_number"]

    if not is_numeric(account_number):
        return "Invalid account number"

    if len(account_number) < 5:
        return "Invalid account number length"

    return None