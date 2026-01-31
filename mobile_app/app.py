# Import the main UI library
import flet as ft

# Import helper functions to talk to backend / API
from api_client import get_balance, save_pending_request, get_redemption_history

# Import libraries for random redemption code
import random
import string


def main(page: ft.Page):
    # Set basic page configuration
    page.title = "CDC Voucher Redemption"
    page.bgcolor = ft.colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # This dictionary keeps the current voucher state
    state = {
        "total": 0,
        "remaining": 0,
        "denoms": {}
    }

    # Input field for household ID
    household_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.colors.WHITE,
        border_radius=12
    )

    # Text to show error messages
    error_text = ft.Text(color=ft.colors.RED)

    # Login button to load household vouchers
    load_btn = ft.ElevatedButton("Login", height=45, width=float("inf"))

    # Container that will hold all voucher cards
    voucher_list = ft.Column(spacing=12)

    # Text elements for balance display
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.colors.GREEN_700)

    # Button for redeeming selected vouchers
    redeem_btn = ft.ElevatedButton(
        text="Redeem Vouchers",
        height=48,
        disabled=True,
        width=float("inf")
    )

    # Button to open transaction history
    history_btn = ft.OutlinedButton(
        text="View History",
        icon=ft.icons.HISTORY,
        height=45,
        width=float("inf")
    )

    # Card that shows total and remaining balance
    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column([
                ft.Text("Balance", size=14, color=ft.colors.GREY_600),
                total_text,
                remaining_text
            ])
        )
    )

    # Section that only appears after successful login
    content_section = ft.Container(
        visible=False,
        padding=20,
        content=ft.Column(
            spacing=20,
            controls=[
                balance_card,
                history_btn,
                ft.Text("Available Vouchers", size=16, weight=ft.FontWeight.BOLD),
                voucher_list,
                redeem_btn
            ]
        )
    )

    # Function to load household vouchers
    def load_household(e):
        error_text.value = ""
        hid = household_input.value.strip()

        # Check if household ID is empty
        if not hid:
            error_text.value = "Please enter a household ID"
            page.update()
            return

        # Call API to get voucher data
        vouchers = get_balance(hid)

        # Handle case when no vouchers are found
        if not vouchers:
            error_text.value = "No active vouchers found"
            content_section.visible = False
            page.update()
            return

        # Combine vouchers by amount
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

        # Save aggregated data into state
        state["total"] = total
        state["remaining"] = total
        state["denoms"] = {k: {"available": v, "selected": 0} for k, v in grouped.items()}

        render_vouchers()
        refresh_balance()
        content_section.visible = True
        page.update()

    # Helper function to create button handlers without lambda
    def make_change_qty_handler(amount, delta):
        def handler(e):
            change_qty(amount, delta)
        return handler

    # Render voucher cards based on state
    def render_vouchers():
        voucher_list.controls.clear()

        for amt in sorted(state["denoms"]):
            d = state["denoms"][amt]

            voucher_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(f"${amt}", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{d['available']} available", size=12),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
                                            on_click=make_change_qty_handler(amt, -1),
                                        ),
                                        ft.Text(
                                            str(d["selected"]),
                                            size=16,
                                            width=30,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.IconButton(
                                            icon=ft.icons.ADD_CIRCLE_OUTLINE,
                                            on_click=make_change_qty_handler(amt, 1),
                                        ),]),],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),)))

        page.update()

    # Update balance text and redeem button status
    def refresh_balance():
        val = sum(k * v["selected"] for k, v in state["denoms"].items())
        state["remaining"] = state["total"] - val
        total_text.value = f"Total Available: ${state['total']}"
        remaining_text.value = f"Remaining: ${state['remaining']}"
        redeem_btn.disabled = val == 0
        page.update()

    # Increase or decrease voucher quantity
    def change_qty(amount, delta):
        d = state["denoms"][amount]

        if delta == 1 and (d["selected"] >= d["available"] or state["remaining"] < amount):
            return
        if delta == -1 and d["selected"] == 0:
            return

        d["selected"] += delta
        render_vouchers()
        refresh_balance()

    # Handle redeem button click
    def handle_user_redeem(e):
        selections = {amt: d["selected"] for amt, d in state["denoms"].items() if d["selected"] > 0}
        total = sum(k * v for k, v in selections.items())

        # Generate random 6 character redemption code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Save redemption request temporarily
        save_pending_request(code, {
            "household_id": household_input.value.strip(),
            "selections": selections,
            "total": total
        })

        # Show redemption code to user
        redeem_dialog = ft.AlertDialog(
            title=ft.Text("Redemption Code"),
            content=ft.Column([
                ft.Text("Show this code to the merchant"),
                ft.Container(
                    padding=10,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8,
                    content=ft.Text(
                        code,
                        size=44,
                        weight="bold",
                        color="blue",
                        text_align="center",
                        selectable=True
                    )
                ),
                ft.Text(f"Total: ${total}.00", weight="bold")
            ], tight=True, horizontal_alignment="center"),
            actions=[ft.TextButton("Finish", on_click=lambda _: page.close(redeem_dialog))]
        )

        page.open(redeem_dialog)
        page.update()

    # Show transaction history dialog
    def show_history(e):
        hid = household_input.value.strip()
        if not hid:
            return

        history = get_redemption_history(hid)

        if not history:
            page.snack_bar = ft.SnackBar(ft.Text("No transaction history found"))
            page.snack_bar.open = True
            page.update()
            return

        history_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, tight=True, width=400)

        for item in reversed(history):
            history_list.controls.append(
                ft.Container(
                    padding=15,
                    bgcolor=ft.colors.WHITE,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Merchant: {item['merchant_id']}", weight="bold", size=16),
                            ft.Text(f"${item['amount']}.00", color=ft.colors.BLUE, weight=ft.FontWeight.BOLD, size=16)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1),
                        ft.Text(f"Date: {item['date']}", size=12, color=ft.colors.GREY_600),
                        ft.Text("Items: " + ", ".join([f"${k}x{v}" for k, v in item['items'].items()]), size=12)
                    ])
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Transaction History"),
            content=ft.Container(content=history_list, height=400),
            actions=[ft.TextButton("Close", on_click=lambda _: page.close(dialog))]
        )

        page.open(dialog)
        page.update()

    # Connect buttons to their functions
    history_btn.on_click = show_history
    load_btn.on_click = load_household
    redeem_btn.on_click = handle_user_redeem

    # Refresh button to reload household data
    refresh_btn = ft.IconButton(
        icon=ft.icons.REFRESH,
        icon_color=ft.colors.WHITE,
        tooltip="Refresh data",
        on_click=load_household
    )

    # Top header bar
    header = ft.Container(
        width=float("inf"),
        padding=20,
        bgcolor=ft.colors.BLUE_600,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text("CDC Voucher Redemption", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        ft.Text("Select vouchers to redeem", size=14, color=ft.colors.WHITE70)
                    ]
                ),
                refresh_btn
            ]
        )
    )

    # Add all UI components to the page
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


# Start the Flet application
ft.app(target=main)
