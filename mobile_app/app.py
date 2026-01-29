import flet as ft
from api_client import get_balance, save_pending_request, get_redemption_history
import random
import string

def main(page: ft.Page):
    page.title = "CDC Voucher Redemption"
    page.bgcolor = ft.Colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # Initiate state
    state = {
        "total": 0,
        "remaining": 0,
        "denoms": {}
    }
    
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.WHITE,
        tooltip="Refresh data",
        on_click=lambda e: load_household(e)
    )

    # Set header
    header = ft.Container(
        width=float("inf"),
        padding=20,
        bgcolor=ft.Colors.BLUE_600,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text("CDC Voucher Redemption", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("Select vouchers to redeem", size=14, color=ft.Colors.WHITE70)
                    ]
                ),
                refresh_btn
            ]
        )
    )

    # Input section
    household_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=12
    )

    error_text = ft.Text(color=ft.Colors.RED)
    load_btn = ft.ElevatedButton("Login", height=45, width=float("inf"))

    # --- 歷史紀錄邏輯 ---
    def show_history(e):
        hid = household_input.value.strip()
        if not hid: return
        
        history = get_redemption_history(hid)
        if not history:
            page.snack_bar = ft.SnackBar(ft.Text("尚未有任何交易紀錄"))
            page.snack_bar.open = True
            page.update()
            return

        history_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, tight=True, width=400)
        for item in reversed(history):
            history_list.controls.append(
                ft.Container(
                    padding=15, bgcolor=ft.Colors.WHITE, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Merchant: {item['merchant_id']}", weight="bold", size=16),
                            ft.Text(f"${item['amount']}.00", color="blue", weight="bold", size=16)
                        ], alignment="spaceBetween"),
                        ft.Divider(height=1),
                        ft.Text(f"Date: {item['date']}", size=12, color="grey600"),
                        ft.Text(f"Items: " + ", ".join([f"${k}x{v}" for k, v in item['items'].items()]), size=12)
                    ])
                )
            )

        history_dialog = ft.AlertDialog(
            title=ft.Text("Transaction History", weight="bold"),
            content=ft.Container(content=history_list, height=400),
            actions=[ft.TextButton("Close", on_click=lambda _: page.close(history_dialog))]
        )
        page.open(history_dialog)
        page.update()

    # --- 歷史按鈕物件 ---
    history_btn = ft.OutlinedButton(
        text="View History",
        icon=ft.Icons.HISTORY,
        on_click=show_history,
        height=45,
        width=float("inf")
    )

    # Balance card
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.Colors.GREEN_700)
    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"), padding=20,
            content=ft.Column([
                ft.Text("Balance", size=14, color=ft.Colors.GREY_600),
                total_text,
                remaining_text
            ])
        )
    )

    voucher_list = ft.Column(spacing=12)
    redeem_btn = ft.ElevatedButton(text="Redeem Vouchers", height=48, disabled=True, width=float("inf"))

    # --- 關鍵修正：將 history_btn 放入 content_section ---
    content_section = ft.Container(
        visible=False,
        padding=20,
        content=ft.Column(
            spacing=20,
            controls=[
                balance_card,
                history_btn, # <--- 只有登入成功後才會顯示在餘額下方
                ft.Text("Available Vouchers", size=16, weight=ft.FontWeight.BOLD),
                voucher_list,
                redeem_btn
            ]
        )
    )

    # Business Logic
    def load_household(e):
        error_text.value = ""
        hid = household_input.value.strip()
        if not hid:
            error_text.value = "Please enter a household ID"
            page.update()
            return

        vouchers = get_balance(hid)
        if not vouchers:
            error_text.value = "No active vouchers found"
            content_section.visible = False
            page.update()
            return

            # (數據聚合邏輯)
        def aggregate(vouchers):
            total = 0
            result = {}
            for v in vouchers:
                if v["status"] == "Active":
                    amount = v["amount"]
                    total += amount
                    result[amount] = result.get(amount, 0) + 1
            return total, result

        total, grouped = aggregate(vouchers)
        state["total"] = total
        state["remaining"] = total
        state["denoms"] = {k: {"available": v, "selected": 0} for k, v in grouped.items()}

        render_vouchers()
        refresh_balance()
        content_section.visible = True # 成功登入，顯示內容區塊
        page.update()

    # (其他輔助函數保持原樣: render_vouchers, refresh_balance, change_qty, handle_user_redeem)
    def render_vouchers():
        voucher_list.controls.clear()
        for amt in sorted(state["denoms"]):
            d = state["denoms"][amt]
            voucher_list.controls.append(
                ft.Card(content=ft.Container(padding=16, content=ft.Row([
                    ft.Column([ft.Text(f"${amt}", size=18, weight="bold"), ft.Text(f"{d['available']} available", size=12)]),
                    ft.Row([
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e, a=amt: change_qty(a, -1)),
                        ft.Text(str(d["selected"]), size=16, width=30, text_align="center"),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e, a=amt: change_qty(a, 1))
                    ])
                ], alignment="spaceBetween")))
            )
        page.update()

    def refresh_balance():
        val = sum(k * v["selected"] for k, v in state["denoms"].items())
        state["remaining"] = state["total"] - val
        total_text.value = f"Total Available: ${state['total']}"
        remaining_text.value = f"Remaining: ${state['remaining']}"
        redeem_btn.disabled = val == 0
        page.update()

    def change_qty(amount, delta):
        d = state["denoms"][amount]
        if delta == 1 and (d["selected"] >= d["available"] or state["remaining"] < amount): return
        if delta == -1 and d["selected"] == 0: return
        d["selected"] += delta
        render_vouchers()
        refresh_balance()

    def handle_user_redeem(e):
        selections = {amt: d["selected"] for amt, d in state["denoms"].items() if d["selected"] > 0}
        total = sum(k * v for k, v in selections.items())
        
        # 產生 6 位核銷碼
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # 儲存暫存請求
        save_pending_request(code, {
            "household_id": household_input.value.strip(), 
            "selections": selections, 
            "total": total
        })

        # 建立彈出對話框
        redeem_dialog = ft.AlertDialog(
            title=ft.Text("Redemption Code"),
            content=ft.Column([
                ft.Text("Show this code to the merchant:"),
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    content=ft.Text(
                        code, 
                        size=44, 
                        weight="bold", 
                        color="blue", 
                        text_align="center",
                        selectable=True  # <--- 加入這行，讓代碼可以被選取並複製
                    )
                ),
                ft.Text(f"Total: ${total}.00", weight="bold")
            ], tight=True, horizontal_alignment="center"),
            actions=[
                ft.TextButton("Finish", on_click=lambda _: page.close(redeem_dialog))
            ]
        )
        
        page.open(redeem_dialog)
        page.update()

    load_btn.on_click = load_household
    redeem_btn.on_click = handle_user_redeem

    page.add(
        header,
        ft.Container(
            padding=20,
            content=ft.Column([
                household_input,
                load_btn,
                error_text
            ], spacing=16)
        ),
        content_section
    )

ft.app(target=main)