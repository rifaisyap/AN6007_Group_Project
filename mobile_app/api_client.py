import json
import os
import datetime
import csv

# 設定檔案路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_redemptions.json") # 用於跨 App 通訊 [cite: 14]

def get_balance(household_id):
    """取得住戶所有 Active 的券 [cite: 53]"""
    if not os.path.exists(HOUSEHOLD_FILE) or not os.path.exists(VOUCHER_FILE):
        return None
    with open(VOUCHER_FILE, "r") as f:
        data = json.load(f)
    vouchers = data.get(household_id, [])
    return [v for v in vouchers if v.get("status") == "Active"]

# --- 新增：跨 App 暫存請求管理 ---

def save_pending_request(code, data):
    """住戶端產生代碼後存入 JSON [cite: 51]"""
    requests = {}
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            try: requests = json.load(f)
            except: requests = {}
    requests[code] = data
    with open(PENDING_FILE, "w") as f:
        json.dump(requests, f, indent=4)

def get_pending_request(code):
    """商家端讀取暫存請求"""
    if not os.path.exists(PENDING_FILE): return None
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    return requests.get(code)

def remove_pending_request(code):
    """核銷後移除暫存"""
    if not os.path.exists(PENDING_FILE): return
    with open(PENDING_FILE, "r") as f:
        requests = json.load(f)
    if code in requests:
        del requests[code]
        with open(PENDING_FILE, "w") as f:
            json.dump(requests, f, indent=4)

# --- 修正：正式核銷邏輯 (解決 JSON 更新與 CSV 面額問題) ---

def merchant_confirm_redemption(household_id, merchant_id, selections):
    if not os.path.exists(VOUCHER_FILE): return False

    # 1. 讀取並修改 JSON 狀態
    with open(VOUCHER_FILE, "r") as f:
        all_data = json.load(f)

    if household_id not in all_data: return False

    vouchers = all_data[household_id]
    redeemed_details = []
    total_amount = 0

    # 根據 selections (例如 {"2": 1, "5": 1}) 尋找對應面額的券 [cite: 112]
    for amt_str, qty in selections.items():
        count = 0
        target_amt = int(amt_str)
        for v in vouchers:
            if v["amount"] == target_amt and v["status"] == "Active":
                v["status"] = "Redeemed" # 修改為已兌換
                redeemed_details.append({"code": v["voucher_code"], "amt": target_amt})
                total_amount += target_amt
                count += 1
                if count >= int(qty): break

    if not redeemed_details: return False

    # 2. 寫回 JSON 確保狀態更新
    with open(VOUCHER_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

    # 3. 產生符合規範的每小時 CSV 紀錄 [cite: 107, 261]
    now = datetime.datetime.now()
    file_name = f"Redeem{now.strftime('%Y%m%d%H')}.csv"
    txn_id = f"TX{int(now.timestamp())}"
    
    headers = ["Transaction_ID", "Household_ID", "Merchant_ID", "Transaction_Date_Time", 
               "Voucher_Code", "Denomination_Used", "Amount_Redeemed", "Payment_Status", "Remarks"]

    file_exists = os.path.isfile(file_name)
    with open(file_name, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists: writer.writeheader()
        
        for i, detail in enumerate(redeemed_details):
            is_last = (i == len(redeemed_details) - 1)
            remark = "Final denomination used" if is_last else str(i + 1) # [cite: 114, 270]
            
            writer.writerow({
                "Transaction_ID": txn_id,
                "Household_ID": household_id,
                "Merchant_ID": merchant_id,
                "Transaction_Date_Time": now.strftime("%Y-%m-%d-%H%M%S"),
                "Voucher_Code": detail["code"],
                "Denomination_Used": f"${detail['amt']}.00", # 修正為實際使用的面額 [cite: 112]
                "Amount_Redeemed": f"${total_amount}.00",
                "Payment_Status": "Completed",
                "Remarks": remark
            })
    return True