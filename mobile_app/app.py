import flet as ft
from api_client import get_balance


def main(page: ft.Page):
    page.title = "CDC Voucher Redemption"
    page.bgcolor = ft.colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # Initiate state
    state = {
        "total": 0,
        "remaining": 0,
        "denoms": {}
    }

    # Set header
    header = ft.Container(
        width=float("inf"),
        padding=20,
        bgcolor=ft.colors.BLUE_600,
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(
                    "CDC Voucher Redemption",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.WHITE
                ),
                ft.Text(
                    "Select vouchers to redeem",
                    size=14,
                    color=ft.colors.WHITE70
                )
            ]
        )
    )

    # Input section
    household_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.colors.WHITE,
        border_radius=12
    )

    error_text = ft.Text(color=ft.colors.RED)

    load_btn = ft.ElevatedButton("Load Household")

    # Balance card
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.colors.GREEN_700)

    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Balance", size=14, color=ft.colors.GREY_600),
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
                                        color=ft.colors.GREY_600)
                            ]
                        ),
                        ft.Row(
                            spacing=0,
                            controls=[
                                ft.IconButton(
                                    icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
                                    on_click=lambda e: change_qty(amount, -1)
                                ),
                                ft.Text(str(selected),
                                        size=16,
                                        width=30,
                                        text_align=ft.TextAlign.CENTER),
                                ft.IconButton(
                                    icon=ft.icons.ADD_CIRCLE_OUTLINE,
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

    load_btn.on_click = load_household
    redeem_btn.on_click = lambda e: print("Redeem handled by teammate")

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
