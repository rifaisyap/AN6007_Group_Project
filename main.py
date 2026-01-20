from flask import Flask, jsonify, request, render_template
from datetime import datetime
import uuid
from models import Household
from storage import household_db, save_to_file as save_household_json, load_from_file as load_household_data
app = Flask(__name__)

# =====================================================
# HARD-CODED BANK & BRANCH REFERENCE DATA
# =====================================================
BANK_DATA = [
    {
        "bank_code": "7171",
        "bank_name": "DBS Bank Ltd",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "DBSSSGSG"
    },
    {
        "bank_code": "7339",
        "bank_name": "OCBC Bank",
        "branch_code": "501",
        "branch_name": "Tampines Branch",
        "swift_code": "OCBCSGSG"
    },
    {
        "bank_code": "7761",
        "bank_name": "UOB Bank",
        "branch_code": "001",
        "branch_name": "Raffles Place",
        "swift_code": "UOVBSGSG"
    },
    {
        "bank_code": "7091",
        "bank_name": "Maybank Singapore",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "MBBESGSG"
    },
    {
        "bank_code": "7302",
        "bank_name": "Standard Chartered Bank",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "SCBLSGSG"
    },
    {
        "bank_code": "7375",
        "bank_name": "HSBC Singapore",
        "branch_code": "146",
        "branch_name": "Orchard Branch",
        "swift_code": "HSBCSGSG"
    },
    {
        "bank_code": "7171",
        "bank_name": "POSB Bank",
        "branch_code": "081",
        "branch_name": "Toa Payoh Branch",
        "swift_code": "DBSSSGSG"
    },
    {
        "bank_code": "9465",
        "bank_name": "Citibank Singapore",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "CITISGSG"
    },
    {
        "bank_code": "7083",
        "bank_name": "RHB Bank Berhad",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "RHBBSGSG"
    },
    {
        "bank_code": "7012",
        "bank_name": "Bank of China Singapore",
        "branch_code": "001",
        "branch_name": "Main Branch",
        "swift_code": "BKCHSGSG"
    }
]

OUTPUT_FILE = "merchants.txt"

# =====================================================
# REQUIRED PAYLOAD FIELDS
# =====================================================
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

# =====================================================
# VALIDATION HELPERS
# =====================================================
def is_numeric(value):
    """Check if value contains digits only"""
    return value.isdigit()

def validate_bank_details(bank_name, bank_code, branch_code):
    """Validate bank name, bank code, and branch code"""
    banks = [b for b in BANK_DATA if b["bank_name"] == bank_name]
    if not banks:
        return False, "INVALID_BANK_NAME", None

    if bank_code not in {b["bank_code"] for b in banks}:
        return False, "INVALID_BANK_CODE", None

    for bank in banks:
        if bank["branch_code"] == branch_code:
            return True, None, bank["branch_name"]

    return False, "INVALID_BRANCH_CODE", None

def save_to_txt(data, branch_name):
    """Save merchant registration to text file (demo persistence)"""
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write("----- Merchant Registration -----\n")
        for k, v in data.items():
            f.write(f"{k}: {v}\n")
        f.write(f"branch_name: {branch_name}\n")
        f.write(f"saved_at: {datetime.utcnow().isoformat()}\n\n")

# =====================================================
# MERCHANT REGISTRATION API
# =====================================================
@app.route("/merchant/registration", methods=["POST"])
def merchant_register():
    payload = request.get_json() if request.is_json else request.form.to_dict()

    if not payload:
        return jsonify({"error": "Invalid or missing request body"}), 400

    # Required fields
    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        return jsonify({"error": "Missing required fields", "missing_fields": missing}), 400

    # Status validation
    status = payload["status"].lower()
    if status not in ALLOWED_STATUS:
        return jsonify({
            "error": "Invalid status",
            "allowed_status": list(ALLOWED_STATUS)
        }), 400

    # Account number numeric validation
    if not is_numeric(payload["account_number"]):
        return jsonify({
            "error": "Invalid account number",
            "message": "account_number must contain digits only"
        }), 400

    # Optional realistic length check
    if not (6 <= len(payload["account_number"]) <= 20):
        return jsonify({
            "error": "Invalid account number length",
            "message": "account_number must be between 6 and 20 digits"
        }), 400

    # Bank validation
    is_valid, error_code, branch_name = validate_bank_details(
        payload["bank_name"],
        payload["bank_code"],
        payload["branch_code"]
    )

    if not is_valid:
        messages = {
            "INVALID_BANK_NAME": "bank_name does not exist",
            "INVALID_BANK_CODE": "bank_code does not match bank_name",
            "INVALID_BRANCH_CODE": "branch_code does not match bank_name and bank_code"
        }
        return jsonify({
            "error": "Invalid bank details",
            "error_code": error_code,
            "message": messages[error_code]
        }), 400

    # System-generated fields
    merchant_id = f"M-{uuid.uuid4().hex[:10].upper()}"
    registration_date = datetime.utcnow().isoformat()

    full_payload = {
        "merchant_id": merchant_id,
        "registration_date": registration_date,
        **payload,
        "status": status
    }

    save_to_txt(full_payload, branch_name)

    if not request.is_json:
        return render_template(
            "merchant_register/result.html",
            merchant_id=merchant_id,
            registration_date=registration_date,
            branch_name=branch_name,
            status=status
        )

    return jsonify({
        "message": "Merchant registered successfully",
        "merchant_id": merchant_id,
        "registration_date": registration_date,
        "branch_name": branch_name,
        "status": status
    }), 201

# =====================================================
# TEMPLATE ENGINE (FORM PAGE)
# =====================================================
@app.route("/merchant/register", methods=["GET"])
def merchant_register_page():
    banks = {}

    for b in BANK_DATA:
        banks[b["bank_name"]] = {
            "bank_code": b["bank_code"],
            "branch_code": b["branch_code"]
        }

    return render_template(
        "merchant_register/merchant_register.html",
        banks=banks
    )
# =====================================================
# [UPDATED] HOUSEHOLD REGISTRATION API
# =====================================================
@app.route("/household/registration", methods=["POST"])
def household_register():
    # 1. 
    payload = request.get_json() if request.is_json else request.form.to_dict()
    if not payload:
        return jsonify({"error": "Invalid or missing request body"}), 400

    h_id = payload.get("household_id")
    
    # verify id
    if not h_id:
        return jsonify({"error": "Missing household_id"}), 400

    # 3. 驗證: 檢查是否已存在 (O(1) 快速查找)
    if h_id in household_db:
        return jsonify({
            "error": "Household already registered",
            "household_id": h_id
        }), 409 # Conflict

    # 4. 
    try:
        new_household = Household(h_id, payload)
    except Exception as e:
        return jsonify({"error": f"Creation failed: {str(e)}"}), 500

    # 5. 
    household_db[h_id] = new_household

    # write household_data.json
    save_household_json()

    #status
    return jsonify({
        "status": "success",
        "message": "Household registered successfully.",
        "household_id": h_id,
        "eligibility": {
            "total_value": 800,
            "May_2025_Status": "Unclaimed", # 
            "Jan_2026_Status": "Unclaimed"
        },
        "next_step": "Please use /claim API to redeem your vouchers."
    }), 201
# test
# APP ENTRY
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
