import json
import os
import datetime
import csv

# Set file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_redemptions.json") # Used for cross-app communication

def get_balance(household_id):
    if not os.path.exists(VOUCHER_FILE): return []
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    # 從 vouchers 鍵中取得列表
    user_data = data.get(household_id, {})
    vouchers = user_data.get("vouchers", [])
    return [v for v in vouchers if v.get("status") == "Active"]

def get_redemption_history(household_id):
    if not os.path.exists(VOUCHER_FILE): return []
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    # 從新格式 user_data[household_id]["redemption_history"] 讀取
    user_data = data.get(household_id, {})
    if isinstance(user_data, dict):
        return user_data.get("redemption_history", [])
    return [] # 防止讀到舊格式的 list
def get_full_data(household_id):
    """取得住戶完整物件，包含 vouchers 與 redemption_history"""
    if not os.path.exists(VOUCHER_FILE): return {}
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    return data.get(household_id, {})
# --- Added: Management of temporary requests across apps ---

def save_pending_request(code, data):
    """Save the generated code and data to JSON from the user client"""
    requests = {}
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            try: requests = json.load(f)
            except: requests = {}
    requests[code] = data
    with open(PENDING_FILE, "w") as f:
        json.dump(requests, f, indent=4)

def get_pending_request(code):
    """Read the temporary request from the merchant side"""
    if not os.path.exists(PENDING_FILE): return None
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    return requests.get(code)

def remove_pending_request(code):
    """Remove temporary request after successful redemption"""
    if not os.path.exists(PENDING_FILE): return
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    if code in requests:
        del requests[code]
        with open(PENDING_FILE, "w") as f:
            json.dump(requests, f, indent=4)

# --- Fixed: Official redemption logic (Addresses JSON updates and CSV denomination issues) ---

def merchant_confirm_redemption(household_id, merchant_id, selections):
    if not os.path.exists(VOUCHER_FILE): return False

    # 1. 讀取新的 JSON 格式
    with open(VOUCHER_FILE, "r") as f:
        all_data = json.load(f)

    # 判斷住戶是否存在
    if household_id not in all_data: return False

    # 取得該住戶的資料容器
    user_container = all_data[household_id]
    vouchers = user_container.get("vouchers", [])
    
    redeemed_details = []
    total_amount = 0

    # 2. 核銷邏輯：遍歷 selections 並修改 vouchers 列表中的狀態
    for amt_str, qty in selections.items():
        count = 0
        target_amt = int(amt_str)
        for v in vouchers:
            if v["amount"] == target_amt and v["status"] == "Active":
                v["status"] = "Redeemed"
                redeemed_details.append({"code": v["voucher_code"], "amt": target_amt})
                total_amount += target_amt
                count += 1
                if count >= int(qty): break

    if not redeemed_details: return False

    # 3. 新增交易紀錄到 redemption_history (用於 App 內查看)
    now = datetime.datetime.now()
    txn_id = f"TX{int(now.timestamp())}"
    
    new_history_entry = {
        "transaction_id": txn_id,
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "merchant_id": merchant_id,
        "amount": total_amount,
        "items": selections
    }
    
    # 確保 history 鍵存在並寫入
    if "redemption_history" not in user_container:
        user_container["redemption_history"] = []
    user_container["redemption_history"].append(new_history_entry)

    # 4. 寫回 JSON 檔案 (持久化保存)
    with open(VOUCHER_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

    # 5. 同步產生符合專案規範的每小時 CSV 紀錄 (用於商家結算)
    file_name = f"Redeem{now.strftime('%Y%m%d%H')}.csv"
    headers = ["Transaction_ID", "Household_ID", "Merchant_ID", "Transaction_Date_Time", 
               "Voucher_Code", "Denomination_Used", "Amount_Redeemed", "Payment_Status", "Remarks"]

    file_exists = os.path.isfile(file_name)
    with open(file_name, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists: writer.writeheader()
        
        for i, detail in enumerate(redeemed_details):
            is_last = (i == len(redeemed_details) - 1)
            remark = "Final denomination used" if is_last else str(i + 1)
            
            writer.writerow({
                "Transaction_ID": txn_id,
                "Household_ID": household_id,
                "Merchant_ID": merchant_id,
                "Transaction_Date_Time": now.strftime("%Y-%m-%d-%H%M%S"),
                "Voucher_Code": detail["code"],
                "Denomination_Used": f"${detail['amt']}.00",
                "Amount_Redeemed": f"${total_amount}.00",
                "Payment_Status": "Completed",
                "Remarks": remark
            })
    return True