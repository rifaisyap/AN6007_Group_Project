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
from storage.merchant_storage import (
    validate_bank_details,
    save_merchant_to_csv,
    validate_payload,
    MERCHANTS,
    BANK_DATA
)
from models.claim import generate_vouchers
import os

app = Flask(__name__)

# Merchant registration pages and logic

@app.route("/merchant/register", methods=["GET"])
def merchant_register_page():
    # Show merchant registration form page
    banks = BANK_DATA
    return render_template("merchant_register/merchant_register.html", banks=banks)

@app.route("/merchant/registration", methods=["POST"])
def merchant_register():
    # Handle merchant registration submission
    payload = request.get_json() if request.is_json else request.form.to_dict()

    if not payload:
        return jsonify({"error": "Invalid or missing request body"}), 400

    error = validate_payload(payload)
    if error:
        return jsonify({"error": error}), 400

    # Validate bank details provided by merchant
    is_valid, error_code, branch_name = validate_bank_details(
        payload["bank_name"],
        payload["bank_code"],
        payload["branch_code"]
    )

    if not is_valid:
        return jsonify({"error": f"Bank validation failed: {error_code}"}), 400

    # Generate system-managed fields
    merchant_id = f"M-{uuid.uuid4().hex[:10].upper()}"
    registration_date = datetime.utcnow().isoformat()

    # Create merchant object using OOP
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

    MERCHANTS[merchant.merchant_id] = merchant
    save_merchant_to_csv(merchant)

    # If request comes from HTML form, return result page
    if not request.is_json:
        return render_template(
            "merchant_register/result.html",
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            bank_name=merchant.bank_name,
            account_holder_name=merchant.account_holder_name,
            account_number=merchant.account_number
        )

    return jsonify({
        "message": "Merchant registered",
        "merchant_id": merchant.merchant_id
    }), 201


# Household registration

@app.route("/household/register", methods=["GET"])
def household_register_page():
    # Show household registration page
    return render_template("household_register.html")

@app.route("/household/registration", methods=["POST"])
def household_register():
    # Handle household registration and save data
    payload = request.get_json() if request.is_json else request.form.to_dict()
    household_id = payload.get("household_id")

    if not household_id:
        return jsonify({"error": "Missing household_id"}), 400

    if household_id in household_db:
        return jsonify({"error": "Already registered"}), 409

    # Create household object and store it
    new_household = Household(household_id, payload)
    household_db[household_id] = new_household
    save_household_json()

    return jsonify({
        "status": "success",
        "household_id": household_id
    }), 201


# Household voucher claiming

@app.route("/household/claim_page")
def household_claim_page():
    # Show voucher claim page
    return render_template("household_claim.html")

@app.route("/household/claim", methods=["POST"])
def claim_api():
    # Run voucher claim logic and generate vouchers
    payload = request.get_json()
    household_id = payload.get("household_id")
    tranche = payload.get("tranche")

    if not household_id or not tranche:
        return jsonify({"error": "Missing household_id or tranche"}), 400

    success, result = generate_vouchers(household_id, tranche)

    if success:
        return jsonify(result), 200

    return jsonify({"error": result}), 400


# System entry point

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print("System starting, loading data from disk...")
    load_household_data()
    app.run(port=8000, debug=True)
