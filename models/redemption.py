import os
import csv
import uuid
from datetime import datetime
from .claim import load_vouchers_from_disk, save_vouchers_to_disk

# 根據專案文檔定義 CSV 表頭 [cite: 108-114]
CSV_HEADERS = [
    "Transaction_ID", "Household_ID", "Merchant_ID", 
    "Transaction_Date_Time", "Voucher_Code", "Denomination_Used", 
    "Amount_Redeemed", "Payment_Status", "Remarks"
]

def generate_qr_string(household_id, amount):
    """
    [Household Side]
    使用者選擇面額 ($2, $5, $10)，系統找出一張可用的 Voucher。
    回傳格式: "HouseholdID+VoucherCode"
    """
    # 1. 讀取所有 Voucher
    all_vouchers = load_vouchers_from_disk()
    user_vouchers = all_vouchers.get(household_id, [])

    # 2. 尋找第一張符合面額且狀態為 "Active" 的券
    target_voucher = None
    for v in user_vouchers:
        if v['amount'] == amount and v['status'] == "Active":
            target_voucher = v
            break
    
    if not target_voucher:
        return False, "No active vouchers found for this amount."

    # 3. 組合字串 (這是商家掃描槍讀到的內容)
    # 格式要求: household_id + voucher_code
    qr_code_string = f"{household_id}+{target_voucher['voucher_code']}"
    
    return True, {
        "qr_string": qr_code_string,
        "voucher_info": target_voucher
    }

def process_redemption(merchant_id, code_input):
    """
    [Merchant Side]
    商家輸入代碼 -> 驗證 -> 扣款 -> 寫入 CSV 日誌
    """
    # 1. 解析代碼 (Split household_id and voucher_code)
    try:
        if '+' not in code_input:
             return False, "Invalid format. Expected 'HouseholdID+VoucherCode'"
        h_id, v_code = code_input.split('+')
    except ValueError:
        return False, "Parsing error."

    # 2. 讀取資料庫
    all_vouchers = load_vouchers_from_disk()
    user_vouchers = all_vouchers.get(h_id)

    if not user_vouchers:
        return False, "Household not found."

    # 3. 尋找並驗證 Voucher
    target_idx = -1
    for i, v in enumerate(user_vouchers):
        if v['voucher_code'] == v_code:
            target_idx = i
            break
    
    if target_idx == -1:
        return False, "Voucher not found."
    
    voucher = user_vouchers[target_idx]
    
    if voucher['status'] != "Active":
        return False, f"Voucher is {voucher['status']}, cannot redeem."

    # 4. 執行兌換 (更新狀態)
    current_time = datetime.now()
    timestamp_str = current_time.strftime("%Y%m%d%H%M%S") # YYYYMMDDhhmmss
    txn_id = f"TX{uuid.uuid4().hex[:6].upper()}" # 模擬 Transaction ID

    # 更新記憶體物件
    voucher['status'] = "Redeemed"
    voucher['redeemed_at'] = current_time.isoformat()
    voucher['redeemed_by'] = merchant_id
    
    # 寫回 JSON (更新狀態)
    user_vouchers[target_idx] = voucher
    all_vouchers[h_id] = user_vouchers
    save_vouchers_to_disk(all_vouchers)

    # 5. [關鍵需求] 寫入 CSV 日誌 (以小時為單位命名) 
    # 檔名格式: RedeemYYYYMMDDHH.csv
    csv_filename = f"Redeem{current_time.strftime('%Y%m%d%H')}.csv"
    
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # 如果是新檔案，先寫入 Header
        if not file_exists:
            writer.writerow(CSV_HEADERS)
            
        # 寫入交易紀錄 [cite: 115]
        writer.writerow([
            txn_id,                 # Transaction_ID
            h_id,                   # Household_ID
            merchant_id,            # Merchant_ID
            timestamp_str,          # Transaction_Date_Time
            v_code,                 # Voucher_Code
            f"${voucher['amount']:.2f}", # Denomination_Used (e.g., $2.00)
            f"${voucher['amount']:.2f}", # Amount_Redeemed
            "Completed",            # Payment_Status
            "Final denomination used" # Remarks (簡化版)
        ])

    return True, {
        "message": "Redemption Successful",
        "transaction_id": txn_id,
        "amount": voucher['amount'],
        "new_status": "Redeemed"
    }
