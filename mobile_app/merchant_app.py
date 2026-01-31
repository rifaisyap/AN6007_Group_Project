"""
Merchant Redemption Application

This application provides merchants with an interface to:
1. Verify redemption codes from households
2. Process voucher redemptions
3. Generate transaction records

The app communicates with the API client to update voucher statuses
and create audit logs through local file operations.
"""

import flet as ft
from api_client import get_pending_request, merchant_confirm_redemption, remove_pending_request

def main(page: ft.Page):
    """
    Main function for the merchant redemption application.

    Args:
        page: Flet page object for the application
    """
    # Configure the page
    page.title = "CDC Merchant App"
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- UI Component Definitions ---

    # Status display for user feedback
    status_text = ft.Text(
        value="",
        size=16,
        weight=ft.FontWeight.BOLD
    )

    # Merchant identification input
    m_id = ft.TextField(
        label="Merchant ID",
        value="",
        hint_text="Enter your merchant identification"
    )

    # Redemption code input from household
    code_input = ft.TextField(
        label="Enter Household Redemption Code",
        hint_text="e.g.: AB1234 (6 characters)"
    )

    # Container for redemption details (hidden until verification)
    result_card = ft.Container(visible=False)

    # Confirmation button for processing redemption
    confirm_btn = ft.ElevatedButton(
        "Confirm Deduction",
        bgcolor="green",
        color="white",
        height=48
    )

    # --- Event Handler Functions ---

    def handle_code_verification(event):
        """
        Verify a redemption code entered by the merchant.

        This function checks if the code corresponds to a valid pending
        request and displays the redemption details if found.

        Args:
            event: The button click event
        """
        # Get and normalize the input code
        entered_code = code_input.value.strip().upper()

        if not entered_code:
            update_status("Please enter a redemption code", is_error=True)
            return

        # Look up the redemption request
        redemption_request = get_pending_request(entered_code)

        if redemption_request:
            # Enable confirmation button
            confirm_btn.disabled = False

            # Create confirmation handler with specific data
            def create_confirmation_handler(code, request_data):
                def handler(event):
                    process_redemption_confirmation(code, request_data)
                return handler

            confirm_btn.on_click = create_confirmation_handler(
                entered_code,
                redemption_request
            )

            # Build redemption details display
            result_card.content = create_redemption_card(
                household_id=redemption_request['household_id'],
                total_amount=redemption_request['total']
            )

            # Update status display
            update_status(
                f"✅ Found request for household {redemption_request['household_id']}",
                is_success=True
            )

            # Show redemption details
            result_card.visible = True

        else:
            # Invalid or expired code
            update_status("❌ Invalid redemption code", is_error=True)
            result_card.visible = False

        # Refresh the UI
        page.update()

    def create_redemption_card(household_id, total_amount):
        """
        Create a card displaying redemption details.

        Args:
            household_id: ID of the household
            total_amount: Total redemption amount

        Returns:
            A Card widget with redemption information
        """
        return ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text(f"Household ID: {household_id}"),
                    ft.Text(
                        f"Redemption Amount: ${total_amount}.00",
                        size=24,
                        weight="bold"
                    ),
                    confirm_btn
                ])
            )
        )

    def process_redemption_confirmation(redemption_code, request_data):
        """
        Process the actual redemption when merchant confirms.

        This function:
        1. Disables the button to prevent duplicate submissions
        2. Calls the redemption API
        3. Shows success/failure feedback
        4. Cleans up the UI for next transaction

        Args:
            redemption_code: The redemption code to process
            request_data: The redemption request data
        """
        # Disable button immediately to prevent duplicate processing
        confirm_btn.disabled = True
        page.update()

        try:
            # Process the redemption through the API
            redemption_successful = merchant_confirm_redemption(
                household_id=request_data['household_id'],
                merchant_id=m_id.value,
                selections=request_data['selections']
            )

            if redemption_successful:
                # Clean up the pending request
                remove_pending_request(redemption_code)

                # Show success message
                show_snackbar_message(
                    "Redemption successful! CSV audit log generated."
                )

                # Reset UI for next transaction
                result_card.visible = False
                code_input.value = ""
                update_status("Transaction completed successfully", is_success=True)

            else:
                # Show failure message
                show_snackbar_message("Redemption failed. Please try again.")

        except Exception as error:
            # Handle unexpected errors
            show_snackbar_message(f"Error: {str(error)}")

        finally:
            # Always re-enable the button for next attempt
            confirm_btn.disabled = False
            page.update()

    def update_status(message, is_success=False, is_error=False):
        """
        Update the status display with appropriate styling.

        Args:
            message: Status message to display
            is_success: Whether this is a success message
            is_error: Whether this is an error message
        """
        status_text.value = message

        if is_success:
            status_text.color = ft.Colors.GREEN
        elif is_error:
            status_text.color = ft.Colors.RED
        else:
            status_text.color = ft.Colors.BLACK

    def show_snackbar_message(message):
        """
        Show a temporary notification message at the bottom of the screen.

        Args:
            message: The message to display
        """
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True

    # --- UI Layout Assembly ---

    # Create the verification button
    verify_button = ft.ElevatedButton(
        "Verify Code",
        on_click=handle_code_verification,
        height=48
    )

    # Assemble the complete UI
    page.add(
        # Application title
        ft.Text(
            "Merchant Redemption Terminal",
            size=24,
            weight=ft.FontWeight.BOLD
        ),

        # Merchant identification
        m_id,

        # Redemption code input
        code_input,

        # Verification button
        verify_button,

        # Status display area
        status_text,

        # Redemption details container
        result_card
    )

# Application entry point
ft.app(target=main)