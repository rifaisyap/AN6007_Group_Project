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
from storage.merchant_storage import validate_bank_details, save_merchant_to_csv, validate_payload, MERCHANTS, BANK_DATA
from models.claim import generate_vouchers
import os

app = Flask(__name__)

# ------------------------------------------------------------
# 1. Merchant Registration (商家註冊)
# ------------------------------------------------------------

@app.route("/merchant/register", methods=["GET"])
def merchant_register_page():
    """顯示商家註冊表單頁面"""
    banks = {b["bank_name"]: {"bank_code": b["bank_code"], "branch_code": b["branch_code"]} for b in BANK_DATA}
    return render_template("merchant_register/merchant_register.html", banks=banks)

@app.route("/merchant/registration", methods=["POST"])
def merchant_register():
    """處理商家註冊邏輯"""
    payload = request.get_json() if request.is_json else request.form.to_dict()
    if not payload:
        return jsonify({"error": "Invalid or missing request body"}), 400

    er = validate_payload(payload)
    if er:
        return jsonify({"error": er}), 400

    # 銀行細節驗證
    is_valid, error_code, branch_name = validate_bank_details(
        payload["bank_name"], payload["bank_code"], payload["branch_code"]
    )

    if not is_valid:
        return jsonify({"error": f"Bank validation failed: {error_code}"}), 400

    # 產生系統欄位
    merchant_id = f"M-{uuid.uuid4().hex[:10].upper()}"
    registration_date = datetime.utcnow().isoformat()

    # 使用 OOP 建立商家物件
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
    save_merchant_to_csv(merchant, branch_name) # 持久化至 CSV

    if not request.is_json:
        return render_template("merchant_register/result.html", 
                               merchant_id=merchant.merchant_id, 
                               status=merchant.status)

    return jsonify({"message": "Merchant registered", "merchant_id": merchant.merchant_id}), 201

# ------------------------------------------------------------
# 2. Household Registration (住戶註冊)
# ------------------------------------------------------------

@app.route("/household/register", methods=["GET"])
def household_register_page():
    """顯示住戶註冊頁面"""
    return render_template("household_register.html")

@app.route("/household/registration", methods=["POST"])
def household_register():
    """處理住戶註冊與持久化"""
    payload = request.get_json() if request.is_json else request.form.to_dict()
    h_id = payload.get("household_id")
    
    if not h_id:
        return jsonify({"error": "Missing household_id"}), 400

    if h_id in household_db:
        return jsonify({"error": "Already registered"}), 409

    # 建立住戶物件並儲存
    new_household = Household(h_id, payload)
    household_db[h_id] = new_household
    save_household_json() # 持久化至 JSON

    return jsonify({"status": "success", "household_id": h_id}), 201

# ------------------------------------------------------------
# 3. Household Claim (住戶領取券)
# ------------------------------------------------------------

@app.route("/household/claim_page")
def household_claim_page():
    """顯示領取券頁面"""
    return render_template("household_claim.html")

@app.route("/household/claim", methods=["POST"])
def claim_api():
    """執行領取邏輯並產生券數據"""
    payload = request.get_json()
    h_id = payload.get("household_id")
    tranche = payload.get("tranche")

    if not h_id or not tranche:
        return jsonify({"error": "Missing household_id or tranche"}), 400

    # 呼叫 claim 邏輯產生券
    success, result = generate_vouchers(h_id, tranche)

    if success:
        return jsonify(result), 200
    return jsonify({"error": result}), 400

# ------------------------------------------------------------
# 系統入口
# ------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    print("🔄 System Starting... Loading data from disk...")
    load_household_data() # 啟動時從磁碟載入數據以支援重啟恢復
    app.run(port=8000, debug=True)