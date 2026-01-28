import flet as ft
from api_client import get_pending_request, merchant_confirm_redemption, remove_pending_request

def main(page: ft.Page):
    page.title = "CDC Merchant App"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 1. 初始化所有控制項
    status_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD)
    m_id = ft.TextField(label="Merchant ID", value="M001")
    code_input = ft.TextField(label="輸入住戶核銷碼", hint_text="例如: AB1234")
    result_card = ft.Container(visible=False)

    # 2. 預先定義確認按鈕，這樣 on_confirm 才能正確控制它
    confirm_btn = ft.ElevatedButton(
        "確認扣款", 
        bgcolor="green", 
        color="white"
    )

    def on_verify(e):
        code = code_input.value.strip().upper()
        data = get_pending_request(code)
        
        if data:
            # --- 修正 1：確保每次驗證成功都重置按鈕狀態 ---
            confirm_btn.disabled = False 
            confirm_btn.on_click = lambda _: on_confirm(code, data)
            
            result_card.content = ft.Card(
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text(f"住戶 ID: {data['household_id']}"),
                        ft.Text(f"核銷金額: ${data['total']}.00", size=24, weight="bold"),
                        confirm_btn 
                    ])
                )
            )
            status_text.value = f"✅ 找到住戶 {data['household_id']} 的請求"
            status_text.color = ft.Colors.GREEN
            result_card.visible = True
        else:
            status_text.value = "❌ 錯誤：代碼無效"
            status_text.color = ft.Colors.RED
            result_card.visible = False
        page.update()

    def on_confirm(code, data):
        # 禁用按鈕防止連續點擊導致重複紀錄 [cite: 105, 107]
        confirm_btn.disabled = True
        page.update()

        try:
            # 呼叫 API 執行核銷與寫入 CSV [cite: 105, 115]
            if merchant_confirm_redemption(data['household_id'], m_id.value, data['selections']):
                remove_pending_request(code)
                page.snack_bar = ft.SnackBar(ft.Text("✅ 扣款成功，已產生 CSV 紀錄"))
                page.snack_bar.open = True
                result_card.visible = False
                code_input.value = ""
                status_text.value = "✅ 交易完成"
            else:
                page.snack_bar = ft.SnackBar(ft.Text("❌ 核銷失敗"))
                page.snack_bar.open = True
        finally:
            # --- 修正 2：不論成功或失敗，一定要解鎖按鈕，否則第二次會卡住 ---
            confirm_btn.disabled = False
            page.update()

    # 3. 確保所有控制項（尤其是 status_text）都有加入頁面
    page.add(
        ft.Text("商家核銷終端", size=24, weight="bold"),
        m_id,
        code_input,
        ft.ElevatedButton("驗證代碼", on_click=on_verify),
        status_text, # <--- 修正點：一定要加入這行，你才看得到反饋
        result_card
    )

ft.app(target=main)