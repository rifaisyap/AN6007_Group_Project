import flet as ft
from api_client import get_pending_request, merchant_confirm_redemption, remove_pending_request

def main(page: ft.Page):
    page.title = "CDC Merchant App"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 1. Initialize all controls
    status_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD)
    m_id = ft.TextField(label="Merchant ID", value="")
    code_input = ft.TextField(label="Enter Household Redemption Code", hint_text="e.g.: AB1234")
    result_card = ft.Container(visible=False)

    # 2. Pre-define the confirmation button so on_confirm can control it correctly
    confirm_btn = ft.ElevatedButton(
        "Confirm Deduction", 
        bgcolor="green", 
        color="white"
    )

    def on_verify(e):
        code = code_input.value.strip().upper()
        data = get_pending_request(code)
        
        if data:
            # --- Fix 1: Ensure button state is reset on every successful verification ---
            confirm_btn.disabled = False 
            confirm_btn.on_click = lambda _: on_confirm(code, data)
            
            result_card.content = ft.Card(
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text(f"Household ID: {data['household_id']}"),
                        ft.Text(f"Redemption Amount: ${data['total']}.00", size=24, weight="bold"),
                        confirm_btn 
                    ])
                )
            )
            status_text.value = f"✅ Found request for household {data['household_id']}"
            status_text.color = ft.Colors.GREEN
            result_card.visible = True
        else:
            status_text.value = "❌ Error: Invalid Code"
            status_text.color = ft.Colors.RED
            result_card.visible = False
        page.update()

    def on_confirm(code, data):
        # Disable button to prevent double-clicking resulting in duplicate records
        confirm_btn.disabled = True
        page.update()

        try:
            # Call API to execute redemption and write to CSV
            if merchant_confirm_redemption(data['household_id'], m_id.value, data['selections']):
                remove_pending_request(code)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Deduction successful, CSV record generated"))
                page.snack_bar.open = True
                result_card.visible = False
                code_input.value = ""
                status_text.value = "✅ Transaction Completed"
            else:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Redemption Failed"))
                page.snack_bar.open = True
        finally:
            # --- Fix 2: Always unlock the button regardless of success or failure to prevent locking up the next attempt ---
            confirm_btn.disabled = False
            page.update()

    # 3. Ensure all controls (especially status_text) are added to the page
    page.add(
        ft.Text("Merchant Redemption Terminal", size=24, weight="bold"),
        m_id,
        code_input,
        ft.ElevatedButton("Verify Code", on_click=on_verify),
        status_text, # <--- Fix: Must include this line to see feedback
        result_card
    )

ft.app(target=main)