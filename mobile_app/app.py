"""
Voucher Management Application

This application allows households to:
1. View available vouchers and balances
2. Select vouchers for redemption
3. Generate redemption codes for merchants
4. View transaction history

The app provides a user-friendly interface for managing digital vouchers
and preparing them for merchant redemption.
"""

import flet as ft
import random
import string
from api_client import get_balance, save_pending_request, get_redemption_history

def main(page: ft.Page):
    """
    Main function for the household voucher application.

    Args:
        page: Flet page object for the application
    """
    # Configure the page
    page.title = "CDC Voucher Redemption"
    page.bgcolor = ft.Colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # --- Application State ---

    # Track the current household's voucher state
    state = {
        "total": 0,           # Total available voucher value
        "remaining": 0,       # Balance after current selections
        "denoms": {}          # Available vouchers by denomination
    }

    # --- UI Component Definitions ---

    # Refresh button for reloading household data
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.WHITE,
        tooltip="Refresh data"
    )

    # Application header
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
                refresh_btn
            ]
        )
    )

    # Household identification input
    household_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=12
    )

    # Error message display
    error_text = ft.Text(color=ft.Colors.RED)

    # Login button
    load_btn = ft.ElevatedButton(
        "Login",
        height=45,
        width=float("inf")
    )

    # --- Transaction History Components ---

    def handle_history_click(event):
        """
        Show the household's redemption transaction history.

        Args:
            event: The button click event
        """
        household_id = household_input.value.strip()

        if not household_id:
            return  # No household ID entered

        # Retrieve transaction history
        transaction_history = get_redemption_history(household_id)

        if not transaction_history:
            show_notification("No transaction history found for this household")
            return

        # Create history list display
        history_display = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            tight=True,
            width=400
        )

        # Add each transaction (most recent first)
        for record in reversed(transaction_history):
            transaction_card = create_transaction_card(record)
            history_display.controls.append(transaction_card)

        # Create history dialog
        history_dialog = ft.AlertDialog(
            title=ft.Text("Transaction History", weight="bold"),
            content=ft.Container(
                content=history_display,
                height=400
            ),
            actions=[
                ft.TextButton(
                    "Close",
                    on_click=lambda e: close_dialog(history_dialog)
                )
            ]
        )

        # Show the dialog
        page.open(history_dialog)
        page.update()

    def create_transaction_card(transaction_data):
        """
        Create a visual card for a transaction record.

        Args:
            transaction_data: Dictionary containing transaction details

        Returns:
            A Container widget displaying the transaction
        """
        # Create itemized description
        items_description = ", ".join([
            f"${amount}x{quantity}"
            for amount, quantity in transaction_data['items'].items()
        ])

        return ft.Container(
            padding=15,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            content=ft.Column([
                # Merchant and amount header
                ft.Row([
                    ft.Text(
                        f"Merchant: {transaction_data['merchant_id']}",
                        weight="bold",
                        size=16
                    ),
                    ft.Text(
                        f"${transaction_data['amount']}.00",
                        color="blue",
                        weight="bold",
                        size=16
                    )
                ], alignment="spaceBetween"),

                # Separator
                ft.Divider(height=1),

                # Transaction details
                ft.Text(
                    f"Date: {transaction_data['date']}",
                    size=12,
                    color="grey600"
                ),

                # Itemized voucher breakdown
                ft.Text(
                    f"Items: {items_description}",
                    size=12
                )
            ])
        )

    # History button
    history_btn = ft.OutlinedButton(
        text="View History",
        icon=ft.Icons.HISTORY,
        on_click=handle_history_click,
        height=45,
        width=float("inf")
    )

    # --- Balance and Voucher Display Components ---

    # Balance display texts
    total_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_text = ft.Text(size=16, color=ft.Colors.GREEN_700)

    # Balance summary card
    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column([
                ft.Text("Balance", size=14, color=ft.Colors.GREY_600),
                total_text,
                remaining_text
            ])
        )
    )

    # Voucher selection list
    voucher_list = ft.Column(spacing=12)

    # Redemption button
    redeem_btn = ft.ElevatedButton(
        text="Redeem Vouchers",
        height=48,
        disabled=True,
        width=float("inf")
    )

    # --- Main Content Section (initially hidden) ---

    content_section = ft.Container(
        visible=False,
        padding=20,
        content=ft.Column(
            spacing=20,
            controls=[
                balance_card,
                history_btn,
                ft.Text(
                    "Available Vouchers",
                    size=16,
                    weight=ft.FontWeight.BOLD
                ),
                voucher_list,
                redeem_btn
            ]
        )
    )

    # --- Core Business Logic Functions ---

    def handle_login(event):
        """
        Load household data and available vouchers.

        Args:
            event: The button click event
        """
        # Clear previous errors
        error_text.value = ""

        # Get and validate household ID
        household_id = household_input.value.strip()

        if not household_id:
            error_text.value = "Please enter a household ID"
            page.update()
            return

        # Retrieve active vouchers for this household
        active_vouchers = get_balance(household_id)

        if not active_vouchers:
            error_text.value = "No active vouchers found for this household"
            content_section.visible = False
            page.update()
            return

        # Process and organize voucher data
        def aggregate_vouchers(voucher_list):
            """
            Group vouchers by denomination and count available quantities.

            Args:
                voucher_list: List of active voucher dictionaries

            Returns:
                Tuple of (total_value, organized_dictionary)
            """
            total_value = 0
            denomination_counts = {}

            for voucher in voucher_list:
                if voucher["status"] == "Active":
                    amount = voucher["amount"]
                    total_value += amount
                    denomination_counts[amount] = denomination_counts.get(amount, 0) + 1

            return total_value, denomination_counts

        total_value, organized_data = aggregate_vouchers(active_vouchers)

        # Update application state
        state["total"] = total_value
        state["remaining"] = total_value

        # Convert to structured format with selection tracking
        for amount, count in organized_data.items():
            state["denoms"][amount] = {
                "available": count,
                "selected": 0
            }

        # Refresh the UI
        update_voucher_display()
        update_balance_display()

        # Show the main content section
        content_section.visible = True
        page.update()

    def update_voucher_display():
        """Update the voucher selection interface based on current state."""
        voucher_list.controls.clear()

        # Sort denominations for consistent display
        sorted_denominations = sorted(state["denoms"].keys())

        for amount in sorted_denominations:
            voucher_data = state["denoms"][amount]

            # Create voucher selection card
            voucher_card = create_voucher_selection_card(amount, voucher_data)
            voucher_list.controls.append(voucher_card)

        page.update()

    def create_voucher_selection_card(amount, voucher_data):
        """
        Create an interactive card for selecting voucher quantities.

        Args:
            amount: Voucher denomination amount
            voucher_data: Dictionary with available and selected counts

        Returns:
            A Card widget with quantity controls
        """
        # Create decrease handler
        def handle_decrease(event):
            update_selected_quantity(amount, -1)

        # Create increase handler
        def handle_increase(event):
            update_selected_quantity(amount, 1)

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Row([
                    # Voucher information
                    ft.Column([
                        ft.Text(f"${amount}", size=18, weight="bold"),
                        ft.Text(f"{voucher_data['available']} available", size=12)
                    ]),

                    # Quantity selection controls
                    ft.Row([
                        # Decrease button
                        ft.IconButton(
                            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                            on_click=handle_decrease
                        ),

                        # Current quantity display
                        ft.Text(
                            str(voucher_data["selected"]),
                            size=16,
                            width=30,
                            text_align="center"
                        ),

                        # Increase button
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                            on_click=handle_increase
                        )
                    ])
                ], alignment="spaceBetween")
            )
        )

    def update_selected_quantity(amount, change_amount):
        """Update the selected quantity for a voucher denomination."""
        voucher_data = state["denoms"][amount]

        # Check if we can increase
        if change_amount == 1:
            cannot_increase = (
                voucher_data["selected"] >= voucher_data["available"] or
                state["remaining"] < amount
            )
            if cannot_increase:
                return

        # Check if we can decrease
        if change_amount == -1 and voucher_data["selected"] == 0:
            return

        # Update the quantity
        voucher_data["selected"] += change_amount

        # Refresh the display
        update_voucher_display()
        update_balance_display()

    def update_balance_display():
        """Update all balance-related displays."""
        # Calculate current selected value
        selected_value = 0
        for amount, voucher_data in state["denoms"].items():
            selected_value += amount * voucher_data["selected"]

        # Update remaining balance
        state["remaining"] = state["total"] - selected_value

        # Update display texts
        total_text.value = f"Total Available: ${state['total']}"
        remaining_text.value = f"Remaining: ${state['remaining']}"

        # Enable/disable redemption button
        redeem_btn.disabled = (selected_value == 0)

        page.update()

    def handle_redemption(event):
        """
        Generate a redemption code and save the pending request.

        Args:
            event: The button click event
        """
        # Gather selected vouchers
        selected_items = {}
        total_amount = 0

        for amount, voucher_data in state["denoms"].items():
            if voucher_data["selected"] > 0:
                selected_items[str(amount)] = voucher_data["selected"]
                total_amount += amount * voucher_data["selected"]

        # Generate unique redemption code
        redemption_code = generate_redemption_code()

        # Save the pending request
        save_pending_request(
            code=redemption_code,
            data={
                "household_id": household_input.value.strip(),
                "selections": selected_items,
                "total": total_amount
            }
        )

        # Show redemption code dialog
        show_redemption_code_dialog(redemption_code, total_amount)

    def generate_redemption_code():
        """Generate a random 6-character alphanumeric redemption code."""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=6))

    def show_redemption_code_dialog(redemption_code, total_amount):
        """
        Display the generated redemption code in a dialog.

        Args:
            redemption_code: The 6-character code to display
            total_amount: Total redemption amount
        """
        redemption_dialog = ft.AlertDialog(
            title=ft.Text("Redemption Code"),
            content=ft.Column([
                ft.Text("Show this code to the merchant:"),

                # Code display with selectable text
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    content=ft.Text(
                        redemption_code,
                        size=44,
                        weight="bold",
                        color="blue",
                        text_align="center",
                        selectable=True  # Allows copying the code
                    )
                ),

                # Total amount display
                ft.Text(f"Total: ${total_amount}.00", weight="bold")
            ],
            tight=True,
            horizontal_alignment="center"),

            actions=[
                ft.TextButton(
                    "Finish",
                    on_click=lambda e: close_dialog(redemption_dialog)
                )
            ]
        )

        page.open(redemption_dialog)
        page.update()

    def show_notification(message):
        """
        Show a temporary notification message.

        Args:
            message: The message to display
        """
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True

    def close_dialog(dialog):
        """
        Close a dialog window.

        Args:
            dialog: The dialog to close
        """
        page.close(dialog)
        page.update()

    # --- Connect Event Handlers ---

    refresh_btn.on_click = handle_login
    load_btn.on_click = handle_login
    redeem_btn.on_click = handle_redemption

    # --- Build the Page Layout ---

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

# Start the application
ft.app(target=main)