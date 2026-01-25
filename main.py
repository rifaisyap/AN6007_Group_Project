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
import os
import csv

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
    

@app.route("/api/household/redeem", methods=["POST"])
def api_household_redeem():
    data = request.get_json()

    h_id = data.get("household_id")
    m_id = data.get("merchant_id")
    amount = data.get("amount")
    tranche = data.get("tranche")

    if not h_id or not m_id or not amount or not tranche:
        return jsonify({"error": "Missing required fields"}), 400

    # Reuse existing logic
    normalized_tranche = f"{tranche[:3]}_{tranche[3:]}"

    success, qr_result = generate_qr_string(h_id, int(amount), tranche)


    if not success:
        return jsonify({"error": qr_result}), 400

    return jsonify({
        "status": "ready_for_redemption",
        "qr_string": qr_result["qr_string"],
        "denominations": qr_result.get("denominations", [])
    }), 200


# Merchant scan
@app.route("/household/register", methods=["GET"])
def household_register_page():
    return render_template("household_register.html")
@app.route("/household/claim_page")
def household_claim_page():
    return render_template("household_claim.html")
@app.route("/household/redeem")
def household_redeem_page():
    return render_template("household_redeem.html")

#balance check
@app.route("/household/balance_page")
def household_balance_page():
    return render_template("household_balance.html")

@app.route("/household/api/balance_history/<household_id>")
def get_balance_and_history(household_id):
    try:
        from models.claim import load_vouchers_from_disk #
        all_data = load_vouchers_from_disk() #
        
        # 你的資料格式是字典，ID 為 Key
        user_vouchers = all_data.get(household_id, [])
        
        active_vouchers = [v for v in user_vouchers if v.get("status") == "Active"] #
        balance = sum(v.get("amount", 0) for v in active_vouchers) #
        
        history_vouchers = [v for v in user_vouchers if v.get("status") == "Redeemed"] #
        recent_history = history_vouchers[-5:] #
        
        return jsonify({
            "total_balance": balance,
            "history": recent_history
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Household Balance API 
@app.route("/api/household/<household_id>/balance", methods=["GET"])
def api_household_balance(household_id):
    from models.claim import load_vouchers_from_disk

    all_data = load_vouchers_from_disk()
    user_vouchers = all_data.get(household_id, [])

    balance = {
        "May_2025": {2: 0, 5: 0, 10: 0},
        "Jan_2026": {2: 0, 5: 0, 10: 0}
    }

    for v in user_vouchers:
        if v.get("status") == "Active":
            tranche = v.get("tranche")
            amount = v.get("amount")

            if tranche in balance and amount in balance[tranche]:
                balance[tranche][amount] += 1

    return jsonify(balance), 200



@app.route("/merchant/redeem", methods=["GET"])
def merchant_redeem_page():
    return render_template("merchant_redeem.html")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/merchant/redeem", methods=["POST"])
def api_merchant_redeem():
    data = request.get_json()
    merchant_id = data.get("merchant_id")
    qr_string = data.get("qr_string")

    if not merchant_id or not qr_string:
        return jsonify({"error": "Missing merchant_id or qr_string"}), 400

    success, result = process_redemption(merchant_id, qr_string)

    if not success:
        return jsonify({"error": result}), 400

    # CSV file per hour (matches assignment)
    filename = f"Redeem{datetime.now().strftime('%Y%m%d%H')}.csv"
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Transaction_ID",
                "Household_ID",
                "Merchant_ID",
                "Transaction_Date_Time",
                "Voucher_Code",
                "Denomination_Used",
                "Amount_Redeemed",
                "Payment_Status",
                "Remarks"
            ])

        for row in result["records"]:
            writer.writerow(row)

    return jsonify({
        "status": "success",
        "records_written": len(result["records"])
    }), 200


# ------------------------------------------------------------
# App Entry
# ------------------------------------------------------------

if __name__ == "__main__":
    from storage.household_storage import load_household_data
    
    # 2.
    print("🔄 System Starting... Loading data from disk...")
    load_household_data()
    
    # 3. 
    app.run(port=8000, debug=True)
