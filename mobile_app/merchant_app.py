"""
Merchant Redemption Terminal

This application provides merchants with an interface to:
1. Verify redemption codes from households
2. Process voucher redemptions
3. Generate transaction records

The app communicates with the API client to update voucher statuses
and create audit logs, all while maintaining a simple, intuitive interface.
"""

import flet as ft
from api_client import (
    get_pending_redemption_request,
    process_merchant_redemption,
    remove_pending_redemption_request
)


def create_merchant_application(page):
    """
    Build and configure the merchant redemption terminal interface.

    This function sets up all UI components and connects them to the
    business logic for processing redemption requests.
    """
    page.title = "CDC Merchant Redemption Terminal"
    page.theme_mode = ft.ThemeMode.LIGHT

    # UI Component Definitions

    # Status display for user feedback
    status_display = ft.Text(
        value="",
        size=16,
        weight=ft.FontWeight.BOLD
    )

    # Merchant identification input
    merchant_id_input = ft.TextField(
        label="Merchant ID",
        value="",
        hint_text="Enter your merchant identification"
    )

    # Redemption code input from household
    redemption_code_input = ft.TextField(
        label="Household Redemption Code",
        hint_text="e.g.: AB1234 (6 characters)",
        autocorrect=False,
        capitalization=ft.TextCapitalization.CHARACTERS
    )

    # Container for redemption details (hidden until verification)
    redemption_details_container = ft.Container(visible=False)

    # Confirmation button (initially disabled)
    confirmation_button = ft.ElevatedButton(
        text="Confirm Redemption",
        bgcolor="green",
        color="white",
        height=45
    )

    # Event Handler Functions

    def handle_code_verification(event):
        """
        Verify a redemption code entered by the merchant.

        This function checks if the code corresponds to a valid pending
        request and displays the redemption details if found.
        """
        # Get and normalize the input code
        entered_code = redemption_code_input.value.strip().upper()

        if not entered_code:
            update_status("Please enter a redemption code", is_error=True)
            return

        # Look up the redemption request
        redemption_request = get_pending_redemption_request(entered_code)

        if redemption_request:
            # Enable confirmation button and set up handler
            confirmation_button.disabled = False

            # Create a proper handler function with the specific data
            def create_confirmation_handler(code, request_data):
                def handler(event):
                    process_redemption_confirmation(code, request_data)

                return handler

            confirmation_button.on_click = create_confirmation_handler(
                entered_code,
                redemption_request
            )

            # Build redemption details display
            redemption_details_container.content = create_redemption_card(
                household_id=redemption_request['household_id'],
                total_amount=redemption_request['total']
            )

            # Update status
            update_status(
                f"✅ Found redemption request for household {redemption_request['household_id']}",
                is_success=True
            )

            # Show redemption details
            redemption_details_container.visible = True

        else:
            # Invalid or expired code
            update_status("❌ Invalid redemption code", is_error=True)
            redemption_details_container.visible = False

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
                    confirmation_button
                ])
            )
        )

    def process_redemption_confirmation(redemption_code, request_data):
        """
        Process the actual redemption when merchant confirms.

        This function:
        1. Disables the button to prevent double submissions
        2. Calls the redemption API
        3. Shows success/failure feedback
        4. Cleans up the UI for next transaction
        """
        # Disable button immediately to prevent duplicate processing
        confirmation_button.disabled = True
        page.update()

        try:
            # Process the redemption through the API
            redemption_successful = process_merchant_redemption(
                household_id=request_data['household_id'],
                merchant_id=merchant_id_input.value,
                voucher_selections=request_data['selections']
            )

            if redemption_successful:
                # Clean up the pending request
                remove_pending_redemption_request(redemption_code)

                # Show success message
                show_snackbar_message(
                    "✅ Redemption successful! CSV audit log generated."
                )

                # Reset UI for next transaction
                redemption_details_container.visible = False
                redemption_code_input.value = ""
                update_status("✅ Transaction completed successfully", is_success=True)

            else:
                # Show failure message
                show_snackbar_message("❌ Redemption failed. Please try again.")

        except Exception as error:
            # Handle unexpected errors
            show_snackbar_message(f"❌ Error: {str(error)}")

        finally:
            # Always re-enable the button for next attempt
            confirmation_button.disabled = False
            page.update()

    def update_status(message, is_success=False, is_error=False):
        """
        Update the status display with appropriate styling.

        Args:
            message: Status message to display
            is_success: Whether this is a success message
            is_error: Whether this is an error message
        """
        status_display.value = message

        if is_success:
            status_display.color = ft.Colors.GREEN
        elif is_error:
            status_display.color = ft.Colors.RED
        else:
            status_display.color = ft.Colors.BLACK

    def show_snackbar_message(message):
        """
        Show a temporary notification message at the bottom of the screen.

        Args:
            message: The message to display
        """
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True

    # UI Layout Assembly

    # Create the verification button with explicit handler
    verify_button = ft.ElevatedButton(
        text="Verify Redemption Code",
        on_click=handle_code_verification,
        height=45
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
        merchant_id_input,

        # Redemption code input
        redemption_code_input,

        # Verification button
        verify_button,

        # Status display area
        status_display,

        # Redemption details (shown after verification)
        redemption_details_container
    )


# Application entry point
def launch_merchant_app():
    """Launch the merchant redemption application."""
    ft.app(target=create_merchant_application)


# Allow running as standalone script
if __name__ == "__main__":
    launch_merchant_app()