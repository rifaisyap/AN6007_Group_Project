from datetime import datetime
from models.merchant import Merchant

OUTPUT_FILE = "merchants.txt"
# In-memory data structure
MERCHANTS = {}  # merchant_id -> Merchant object

# Bank and brand reference data
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

# Required payload fields
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


# Function for validation 
def validate_bank_details(bank_name, bank_code, branch_code):
    banks = [b for b in BANK_DATA if b["bank_name"] == bank_name]
    if not banks:
        return False, "INVALID_BANK_NAME", None

    if bank_code not in {b["bank_code"] for b in banks}:
        return False, "INVALID_BANK_CODE", None

    for bank in banks:
        if bank["branch_code"] == branch_code:
            return True, None, bank["branch_name"]

    return False, "INVALID_BRANCH_CODE", None

# Save merchant to txt file
def save_merchant_to_txt(merchant: Merchant, branch_name: str):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(merchant.to_txt() + "\n")
        f.write(f"branch_name: {branch_name}\n")
        f.write(f"saved_at: {datetime.utcnow().isoformat()}\n\n")

def validate_payload(payload):
    # Required fields check
    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        return "Missing required fields"

    # Status validation
    status = payload["status"].lower()
    if status not in ALLOWED_STATUS:
        return "Invalid status"

    # Account number validation
    if not is_numeric(payload["account_number"]):
        return "Invalid account number"

    if not (5 <= len(payload["account_number"])):
        return "Invalid account number length"

    return None
    