import flet as ft
from api_client import (
    get_balance, 
    save_pending_request, 
    get_redemption_history, 
    reload_pending_requests
)

import random
import string


def main(page: ft.Page):
    # This ensures that generated codes persist even if the app process restarts
    reload_pending_requests() 

    page.title = "CDC Voucher Redemption"
    page.bgcolor = ft.Colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    state = {
        "total": 0,
        "remaining": 0,
        "denoms": {}
    }

    household_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        helper_text="Enter your unique Household ID to view balance"
    )

    error_text = ft.Text(color=ft.Colors.RED)

    # Login button to load household vouchers from SQLite database
    load_btn = ft.ElevatedButton("Login", height=45, width=float("inf"))

    # Container that will hold all dynamically generated voucher cards
    voucher_list = ft.Column(spacing=12)

    # Text elements for dynamic balance display
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.Colors.GREEN_700)

    # Button for redeeming selected vouchers (Disabled until vouchers are selected)
    redeem_btn = ft.ElevatedButton(
        text="Redeem Vouchers",
        height=48,
        disabled=True,
        width=float("inf")
    )

    # Button to open the persistent transaction history dialog
    history_btn = ft.OutlinedButton(
        text="View History",
        icon=ft.Icons.HISTORY,
        height=45,
        width=float("inf")
    )

    # Card that shows total and remaining balance after selection
    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column([
                ft.Text("Balance Summary", size=14, color=ft.Colors.GREY_600),
                total_text,
                remaining_text
            ])
        )
    )

    # Main content section that only appears after successful ID validation
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

    # Function to fetch household vouchers from SQLite database
    def load_household(e):
        error_text.value = ""
        hid = household_input.value.strip()

        if not hid:
            error_text.value = "Please enter a household ID"
            page.update()
            return

        # Calls the SQL-based get_balance function
        vouchers = get_balance(hid)

        if not vouchers:
            error_text.value = "No active vouchers found for this ID"
            content_section.visible = False
            page.update()
            return

        # Aggregates individual database rows into counts by denomination
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

        # Synchronize UI state with aggregated database data
        state["total"] = total
        state["remaining"] = total
        state["denoms"] = {k: {"available": v, "selected": 0} for k, v in grouped.items()}

        render_vouchers()
        refresh_balance()
        content_section.visible = True
        page.update()

    # Helper function to create button handlers for quantity changes
    def make_change_qty_handler(amount, delta):
        def handler(e):
            change_qty(amount, delta)
        return handler

    # Renders voucher cards based on the current state dictionary
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
                                            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                            on_click=make_change_qty_handler(amt, -1),
                                        ),
                                        ft.Text(
                                            str(d["selected"]),
                                            size=16,
                                            width=30,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                            on_click=make_change_qty_handler(amt, 1),
                                        ),]),],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),)))
        page.update()

    # Updates the balance UI and enables/disables the redeem button
    def refresh_balance():
        val = sum(k * v["selected"] for k, v in state["denoms"].items())
        state["remaining"] = state["total"] - val
        total_text.value = f"Total Available: ${state['total']}"
        remaining_text.value = f"Remaining after selection: ${state['remaining']}"
        redeem_btn.disabled = val == 0
        page.update()

    # Logic to increase or decrease voucher selection quantity
    def change_qty(amount, delta):
        d = state["denoms"][amount]
        if delta == 1 and (d["selected"] >= d["available"] or state["remaining"] < amount):
            return
        if delta == -1 and d["selected"] == 0:
            return
        d["selected"] += delta
        render_vouchers()
        refresh_balance()

    # Handles the generation of a redemption code and saving to the pending log
    def handle_user_redeem(e):
        selections = {amt: d["selected"] for amt, d in state["denoms"].items() if d["selected"] > 0}
        total = sum(k * v for k, v in selections.items())

        # Generate a random 6-character alphanumeric redemption code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Calls the optimized save_pending_request to update the .txt log
        save_pending_request(code, {
            "household_id": household_input.value.strip(),
            "selections": selections,
            "total": total
        })

        # Display the redemption code dialog to the resident
        redeem_dialog = ft.AlertDialog(
            title=ft.Text("Redemption Code Generated"),
            content=ft.Column([
                ft.Text("Show this code to the merchant to finish payment:"),
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
                        selectable=True
                    )
                ),
                ft.Text(f"Total Value: ${total}.00", weight="bold")
            ], tight=True, horizontal_alignment="center"),
            actions=[ft.TextButton("Finish", on_click=lambda _: page.close(redeem_dialog))]
        )
        page.open(redeem_dialog)
        page.update()

    # Fetches and displays the persistent transaction history from the SQL database
    def show_history(e):
        hid = household_input.value.strip()
        if not hid: return

        # Fetches history strictly from the SQL database to ensure confirmed records only
        history = get_redemption_history(hid)

        if not history:
            page.snack_bar = ft.SnackBar(ft.Text("No transaction history found for this household"))
            page.snack_bar.open = True
            page.update()
            return

        history_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, tight=True, width=400)

        # Display transactions in reverse chronological order (newest first)
        for item in reversed(history):
            history_list.controls.append(
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Merchant: {item['merchant_id']}", weight="bold", size=16),
                            ft.Text(f"${item['amount']}.00", color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD, size=16)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1),
                        ft.Text(f"Date: {item['date']}", size=12, color=ft.Colors.GREY_600)
                    ])
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Successful Transactions"),
            content=ft.Container(content=history_list, height=400),
            actions=[ft.TextButton("Close", on_click=lambda _: page.close(dialog))]
        )
        page.open(dialog)
        page.update()

    # Assign event handlers to UI buttons
    history_btn.on_click = show_history
    load_btn.on_click = load_household
    redeem_btn.on_click = handle_user_redeem

    # Refresh button to sync with the latest SQL database state
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.WHITE,
        tooltip="Sync with Server",
        on_click=load_household
    )

    # Top header bar UI
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
                        ft.Text("Select your vouchers and generate a code", size=14, color=ft.Colors.WHITE70)
                    ]
                ),
                refresh_btn
            ]
        )
    )

    # Add primary UI layers to the page
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

# Entry point for the Flet application
if __name__ == "__main__":
    ft.app(target=main)