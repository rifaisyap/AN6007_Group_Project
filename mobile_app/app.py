import flet as ft
from api_client import get_balance, save_pending_request
import random
import string
# 模擬記憶體內的暫存請求 (In-memory structure)
pending_requests = {}

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
        icon_color=ft.Colors.WHITE, # 讓圖示變白色，配背景
        tooltip="刷新數據",
        on_click=lambda e: load_household(e) # 加上 lambda 確保正確觸發
    )
    # Set header
    header = ft.Container(
        width=float("inf"),
        padding=20,
        bgcolor=ft.Colors.BLUE_600,
        content=ft.Row( # 改用 Row 讓文字和按鈕左右並排
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, # 讓文字靠左，按鈕靠右
            controls=[
                # 這裡放你原本的 Column 文字區塊
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(
                            "CDC Voucher Redemption",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE
                        ),
                        ft.Text(
                            "Select vouchers to redeem",
                            size=14,
                            color=ft.Colors.WHITE70
                        )
                    ]
                ),
                # 這裡放新加的按鈕
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

    load_btn = ft.ElevatedButton("Load Household")

    # Balance card
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.Colors.GREEN_700)

    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Balance", size=14, color=ft.Colors.GREY_600),
                    total_text,
                    remaining_text
                ]
            )
        )
    )

    # Voucher setting
    voucher_list = ft.Column(spacing=12)

    redeem_btn = ft.ElevatedButton(
        text="Redeem Vouchers",
        height=48,
        disabled=True
    )

    # Content section
    content_section = ft.Container(
        visible=False,
        padding=20,
        content=ft.Column(
            spacing=20,
            controls=[
                balance_card,
                ft.Text("Available Vouchers",
                        size=16,
                        weight=ft.FontWeight.BOLD),
                voucher_list,
                redeem_btn
            ]
        )
    )

    # Voucher logic
    def aggregate(vouchers):
        total = 0
        result = {}

        for v in vouchers:
            if v["status"] != "Active":
                continue
            amount = v["amount"]
            total += amount
            result[amount] = result.get(amount, 0) + 1

        return total, result

    def selected_value():
        return sum(k * v["selected"] for k, v in state["denoms"].items())

    def refresh_balance():
        state["remaining"] = state["total"] - selected_value()
        total_text.value = f"Total Available: ${state['total']}"
        remaining_text.value = f"Remaining: ${state['remaining']}"
        redeem_btn.disabled = selected_value() == 0
        page.update()

    def change_qty(amount, delta):
        d = state["denoms"][amount]

        if delta == 1:
            if d["selected"] >= d["available"]:
                return
            if state["remaining"] < amount:
                return

        if delta == -1 and d["selected"] == 0:
            return

        d["selected"] += delta
        render_vouchers()
        refresh_balance()

    def voucher_card(amount, available, selected):
        return ft.Card(
            content=ft.Container(
                width=float("inf"),
                padding=16,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(f"${amount}",
                                        size=18,
                                        weight=ft.FontWeight.BOLD),
                                ft.Text(f"{available} available",
                                        size=12,
                                        color=ft.Colors.GREY_600)
                            ]
                        ),
                        ft.Row(
                            spacing=0,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                    on_click=lambda e: change_qty(amount, -1)
                                ),
                                ft.Text(str(selected),
                                        size=16,
                                        width=30,
                                        text_align=ft.TextAlign.CENTER),
                                ft.IconButton(
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                    on_click=lambda e: change_qty(amount, 1)
                                )
                            ]
                        )
                    ]
                )
            )
        )

    def render_vouchers():
        voucher_list.controls.clear()
        for amt in sorted(state["denoms"]):
            d = state["denoms"][amt]
            voucher_list.controls.append(
                voucher_card(amt, d["available"], d["selected"])
            )
        page.update()

    def load_household(e):
        error_text.value = ""
        content_section.visible = False
        voucher_list.controls.clear()

        hid = household_input.value.strip()
        if not hid:
            error_text.value = "Please enter a household ID"
            page.update()
            return

        vouchers = get_balance(hid)
        if not vouchers:
            error_text.value = "No vouchers found for this household"
            page.update()
            return

        total, grouped = aggregate(vouchers)

        state["total"] = total
        state["remaining"] = total
        state["denoms"] = {
            k: {"available": v, "selected": 0}
            for k, v in grouped.items()
        }

        render_vouchers()
        refresh_balance()
        content_section.visible = True
        page.update()


    def handle_user_redeem(e):
        # 在 app.py 的 handle_user_redeem 函數中修改：

        hid = household_input.value.strip()
        selections = {amt: d["selected"] for amt, d in state["denoms"].items() if d["selected"] > 0}
        
        if not selections: return

        # 1. 產生 6 位核銷代碼
        redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # 2. 呼叫 API 存入 JSON 檔案 (這讓另一個 App 讀得到資料)
        save_pending_request(redeem_code, {
            "household_id": hid,
            "selections": selections,
            "total": selected_value()
        })

        # 3. 僅顯示代碼與成功提示
        code_dialog = ft.AlertDialog(
            title=ft.Text("您的核銷碼"),
            content=ft.Column([
                ft.Text("請將此代碼出示給商家："),
                ft.Container(
                    content=ft.Text(
                        redeem_code, # 第 240 行引用處
                        size=44, 
                        weight="bold", 
                        color="blue",
                        selectable=True # 讓 code 可以複製
                    ),
                    padding=10, bgcolor=ft.Colors.BLUE_50, border_radius=8
                ),
                ft.Text(f"總金額: ${selected_value()}.00", weight="bold")
            ], tight=True, horizontal_alignment="center"),
            actions=[
                ft.TextButton("完成", on_click=lambda _: page.close(code_dialog))
            ]
        )
        page.open(code_dialog)
        page.update()

    # 綁定按鈕
    redeem_btn.on_click = handle_user_redeem
    # ... (其餘 page.add 保持不變) ...

    load_btn.on_click = load_household
    redeem_btn.on_click = handle_user_redeem
    
    

    # Page
    page.add(
        header,
        ft.Container(
            padding=20,
            content=ft.Column(
                spacing=16,
                controls=[
                    household_input,
                    load_btn,
                    error_text
                ]
            )
        ),
        content_section
    )


ft.app(target=main)
