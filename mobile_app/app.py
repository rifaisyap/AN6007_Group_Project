"""
Household Voucher Management Application

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
from api_client import (
    get_active_vouchers,
    save_pending_redemption_request,
    get_redemption_history
)


def create_household_application(page):
    """
    Build and configure the household voucher management interface.

    This function creates all UI components and connects them to the
    voucher management logic for household users.
    """
    # Application configuration
    page.title = "CDC Household Voucher Portal"
    page.bgcolor = ft.Colors.GREY_100
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # Application State

    # Track the current household's voucher state
    application_state = {
        "total_balance": 0,  # Total available voucher value
        "remaining_balance": 0,  # Balance after current selections
        "voucher_denominations": {}  # Available vouchers by amount
    }

    # UI Component Definitions

    # Refresh button for reloading household data
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.WHITE,
        tooltip="Refresh voucher data",
        on_click=handle_household_login
    )

    # Application header
    application_header = ft.Container(
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
                            "CDC Voucher Redemption Portal",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE
                        ),
                        ft.Text(
                            "Select vouchers to redeem at participating merchants",
                            size=14,
                            color=ft.Colors.WHITE70
                        )
                    ]
                ),
                refresh_button
            ]
        )
    )

    # Household identification input
    household_id_input = ft.TextField(
        label="Household ID",
        filled=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=12
    )

    # Error message display
    error_message_display = ft.Text(color=ft.Colors.RED)

    # Login button
    login_button = ft.ElevatedButton(
        text="Login to Household Account",
        height=45,
        width=float("inf")
    )

    # Transaction History Components

    def display_transaction_history(event):
        """
        Show the household's redemption transaction history.

        This function retrieves and displays all previous redemption
        transactions in a modal dialog for the household to review.
        """
        household_id = household_id_input.value.strip()

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
        for transaction in reversed(transaction_history):
            transaction_card = create_transaction_card(transaction)
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
                    text="Close",
                    on_click=create_dialog_closer(history_dialog)
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
                    create_itemized_description(transaction_data['items']),
                    size=12
                )
            ])
        )

    def create_itemized_description(items_dict):
        """
        Create a human-readable description of redeemed items.

        Args:
            items_dict: Dictionary mapping amounts to quantities

        Returns:
            Formatted string describing the items
        """
        item_descriptions = []
        for amount, quantity in items_dict.items():
            item_descriptions.append(f"${amount}x{quantity}")

        return "Items: " + ", ".join(item_descriptions)

    def create_dialog_closer(dialog):
        """
        Create a function to close a specific dialog.

        Args:
            dialog: The dialog to close

        Returns:
            A function that closes the dialog when called
        """

        def close_handler(event):
            page.close(dialog)

        return close_handler

    # History button
    history_button = ft.OutlinedButton(
        text="View Transaction History",
        icon=ft.Icons.HISTORY,
        on_click=display_transaction_history,
        height=45,
        width=float("inf")
    )

    # Balance and Voucher Display Components

    # Balance display texts
    total_balance_display = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    remaining_balance_display = ft.Text(size=16, color=ft.Colors.GREEN_700)

    # Balance summary card
    balance_card = ft.Card(
        elevation=4,
        content=ft.Container(
            width=float("inf"),
            padding=20,
            content=ft.Column([
                ft.Text("Voucher Balance", size=14, color=ft.Colors.GREY_600),
                total_balance_display,
                remaining_balance_display
            ])
        )
    )

    # Voucher selection list
    voucher_selection_list = ft.Column(spacing=12)

    # Redemption button
    redemption_button = ft.ElevatedButton(
        text="Generate Redemption Code",
        height=48,
        disabled=True,
        width=float("inf")
    )

    # Main Content Section (initially hidden)

    main_content_section = ft.Container(
        visible=False,
        padding=20,
        content=ft.Column(
            spacing=20,
            controls=[
                balance_card,
                history_button,
                ft.Text(
                    "Available Vouchers",
                    size=16,
                    weight=ft.FontWeight.BOLD
                ),
                voucher_selection_list,
                redemption_button
            ]
        )
    )

    # Core Business Logic Functions

    def handle_household_login(event):
        """
        Load household data and available vouchers.

        This function validates the household ID, retrieves voucher data,
        and updates the UI to show available vouchers for selection.
        """
        # Clear previous errors
        error_message_display.value = ""

        # Get and validate household ID
        household_id = household_id_input.value.strip()

        if not household_id:
            error_message_display.value = "Please enter a household ID"
            page.update()
            return

        # Retrieve active vouchers for this household
        active_vouchers = get_active_vouchers(household_id)

        if not active_vouchers:
            error_message_display.value = "No active vouchers found for this household"
            main_content_section.visible = False
            page.update()
            return

        # Process and organize voucher data
        total_value, organized_vouchers = organize_vouchers_by_denomination(active_vouchers)

        # Update application state
        application_state["total_balance"] = total_value
        application_state["remaining_balance"] = total_value
        application_state["voucher_denominations"] = organized_vouchers

        # Refresh the UI
        update_voucher_display()
        update_balance_display()

        # Show the main content section
        main_content_section.visible = True
        page.update()

    def organize_vouchers_by_denomination(voucher_list):
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

        # Convert counts to structured format with selection tracking
        organized_data = {}
        for amount, count in denomination_counts.items():
            organized_data[amount] = {
                "available": count,
                "selected": 0
            }

        return total_value, organized_data

    def update_voucher_display():
        """Update the voucher selection interface based on current state."""
        voucher_selection_list.controls.clear()

        # Sort denominations for consistent display
        sorted_denominations = sorted(application_state["voucher_denominations"].keys())

        for amount in sorted_denominations:
            voucher_data = application_state["voucher_denominations"][amount]

            # Create voucher selection card
            voucher_card = create_voucher_selection_card(amount, voucher_data)
            voucher_selection_list.controls.append(voucher_card)

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
                            on_click=create_quantity_changer(amount, -1)
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
                            on_click=create_quantity_changer(amount, 1)
                        )
                    ])
                ], alignment="spaceBetween")
            )
        )

    def create_quantity_changer(amount, change_amount):
        """
        Create a function to change selected quantity for a specific denomination.

        Args:
            amount: The voucher denomination amount
            change_amount: +1 to increase, -1 to decrease

        Returns:
            A function that updates the quantity when called
        """

        def quantity_change_handler(event):
            update_selected_quantity(amount, change_amount)

        return quantity_change_handler

    def update_selected_quantity(amount, change_amount):
        """Update the selected quantity for a voucher denomination."""
        voucher_data = application_state["voucher_denominations"][amount]

        # Check if we can increase
        if change_amount == 1:
            cannot_increase = (
                    voucher_data["selected"] >= voucher_data["available"] or
                    application_state["remaining_balance"] < amount
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
        for amount, voucher_data in application_state["voucher_denominations"].items():
            selected_value += amount * voucher_data["selected"]

        # Update remaining balance
        application_state["remaining_balance"] = (
                application_state["total_balance"] - selected_value
        )

        # Update display texts
        total_balance_display.value = f"Total Available: ${application_state['total_balance']}"
        remaining_balance_display.value = f"Remaining Balance: ${application_state['remaining_balance']}"

        # Enable/disable redemption button
        redemption_button.disabled = (selected_value == 0)

        page.update()

    def handle_redemption_request(event):
        """
        Generate a redemption code and save the pending request.

        This function:
        1. Validates current selections
        2. Generates a unique redemption code
        3. Saves the request for merchant processing
        4. Shows the code to the household user
        """
        # Gather selected vouchers
        selected_vouchers = {}
        total_amount = 0

        for amount, voucher_data in application_state["voucher_denominations"].items():
            if voucher_data["selected"] > 0:
                selected_vouchers[str(amount)] = voucher_data["selected"]
                total_amount += amount * voucher_data["selected"]

        # Generate unique redemption code
        redemption_code = generate_redemption_code()

        # Save the pending request
        save_pending_redemption_request(
            redemption_code=redemption_code,
            request_data={
                "household_id": household_id_input.value.strip(),
                "selections": selected_vouchers,
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
            title=ft.Text("Your Redemption Code"),
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
                ft.Text(f"Total Amount: ${total_amount}.00", weight="bold")
            ],
                tight=True,
                horizontal_alignment="center"),

            actions