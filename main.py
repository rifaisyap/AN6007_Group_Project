from flask import Flask, jsonify, request, render_template
from datetime import datetime
import uuid
from models.household import Household 
from storage.household_storage import (
    household_db, 
    save_household_json, 
    load_household_data
)
from models.merchant import Merchant 
from storage.merchant_storage import validate_bank_details, save_merchant_to_txt, validate_payload, MERCHANTS, BANK_DATA
from models.claim import generate_vouchers
from models.redemption import generate_qr_string, process_redemption

app = Flask(__name__)

# ------------------------------------------------------------
# Merchant Registration API
# ------------------------------------------------------------

@app.route("/merchant/registration", methods=["POST"])
def merchant_register():
    payload = request.get_json() if request.is_json else request.form.to_dict()

    if not payload:
        return jsonify({"error": "Invalid or missing request body"}), 400

    er = validate_payload(payload)

    if er is not None:
        return jsonify({"error": er}), 400

    # Bank validation
    is_valid, error_code, branch_name = validate_bank_details(
        payload["bank_name"],
        payload["bank_code"],
        payload["branch_code"]
    )

    if not is_valid:
        messages = {
            "INVALID_BANK_NAME": "Bank name does not exist",
            "INVALID_BANK_CODE": "Bank code does not match bank",
            "INVALID_BRANCH_CODE": "Branch code does not match bank"
        }
        return jsonify({"error": messages[error_code]}), 400


    # System-generated fields
    merchant_id = f"M-{uuid.uuid4().hex[:10].upper()}"
    registration_date = datetime.utcnow().isoformat()

    # Create Merchant object (OOP)
    merchant = Merchant(
        merchant_id=merchant_id,
        merchant_name=payload["merchant_name"],
        uen=payload["uen"],
        bank_name=payload["bank_name"],
        bank_code=payload["bank_code"],
        branch_code=payload["branch_code"],
        account_number=payload["account_number"],
        account_holder_name=payload["account_holder_name"],
        registration_date=registration_date,
        status=payload["status"].lower()
    )

    # Store in memory
    MERCHANTS[merchant.merchant_id] = merchant

    # Persist to file
    save_merchant_to_txt(merchant, branch_name)

    # HTML or JSON response
    if not request.is_json:
        return render_template(
            "merchant_register/result.html",
            merchant_id=merchant.merchant_id,
            registration_date=merchant.registration_date,
            branch_name=branch_name,
            status=merchant.status
        )

    return jsonify({
        "message": "Merchant registered successfully",
        "merchant_id": merchant.merchant_id,
        "registration_date": merchant.registration_date,
        "branch_name": branch_name,
        "status": merchant.status
    }), 201

# MERCHANT REGISTRATION FORM PAGE
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
# Household Registration API
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

    # 3. 
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
# ------------------------------------------------------------
# Voucher Claim
# ------------------------------------------------------------
@app.route("/household/claim", methods=["POST"])
def claim_api():
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "Missing JSON body"}), 400

    h_id = payload.get("household_id")
    tranche = payload.get("tranche")
    if not h_id or not tranche:
        return jsonify({"error": "Missing household_id or tranche"}), 400

    success, result = generate_vouchers(h_id, tranche)

    if success:
        return jsonify(result), 200
    else:
        return jsonify({"error": result}), 400

# -----------------------------------------------------------
#Voucher Use
# -----------------------------------------------------------
@app.route("/household/use_voucher", methods=["POST"])
def use_voucher_api():
    data = request.get_json()
    h_id = data.get("household_id")
    amount = data.get("amount")

    if not h_id or not amount:
        return jsonify({"error": "Missing household_id or amount"}), 400

    success, result = generate_qr_string(h_id, int(amount))

    if success:
        return jsonify(result), 200
    else:
        return jsonify({"error": result}), 400

# 2. Merchant scan
@app.route("/merchant/redeem", methods=["POST"])
def redeem_api():
    data = request.get_json()
    m_id = data.get("merchant_id")
    code = data.get("qr_string") #HouseholdID+VoucherID

    if not m_id or not code:
        return jsonify({"error": "Missing merchant_id or code"}), 400

    success, result = process_redemption(m_id, code)

    if success:
        return jsonify(result), 200
    else:
        return jsonify({"error": result}), 400

@app.route("/household/register", methods=["GET"])
def household_register_page():
    return render_template("household_register.html")
@app.route("/household/claim_page")
def household_claim_page():
    """顯示領券頁面"""
    return render_template("household_claim.html")
@app.route("/household/redeem")
def household_redeem_page():
    return render_template("household_redeem.html") # 確保檔名一致

#balance check
# main.py

@app.route("/household/balance_page")
def household_balance_page():
    return render_template("household_balance.html")

@app.route("/household/api/balance_history/<household_id>")
def get_balance_and_history(household_id):
    """API: get balance and transcation record"""
    try:
        vouchers = load_vouchers_from_disk() #
        
        # 1. count
        active = [v for v in vouchers if v["household_id"] == household_id and v["status"] == "Active"]
        balance = sum(v["amount"] for v in active)
        
        # 2. latest 5 record
        history = [v for v in vouchers if v["household_id"] == household_id and v["status"] == "Redeemed"]
        recent_history = history[-5:] 
        
        return jsonify({
            "total_balance": balance,
            "history": recent_history
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/merchant/redeem")
def merchant_redeem_page():
    return render_template("merchant_redeem.html") # 確保檔名一致
@app.route("/")
def index():
    return render_template("index.html")

#Redemption Record
import csv
from datetime import datetime

@app.route("/merchant/redeem", methods=["POST"])
def redeem_voucher():
    data = request.json
    merchant_id = data.get("merchant_id")
    qr_string = data.get("qr_string") 
    success, result = process_redemption(merchant_id, qr_string) 

    if success:
        filename = f"Redeem_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Transaction_ID", "Timestamp", "Merchant_ID", "Household_ID", "Voucher_ID", "Amount"])
            
            writer.writerow([
                f"TXN{datetime.now().strftime('%H%M%S%f')[:10]}",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                merchant_id,
                result['household_id'],
                result['voucher_id'],
                result['amount']
            ])

        return jsonify({"status": "success", "transaction_id": "TXN...", "amount": result['amount']}), 200
    else:
        return jsonify({"error": result}), 400
# ------------------------------------------------------------
# App Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
