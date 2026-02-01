import flet as ft
from api_client import (
    get_pending_request,
    merchant_confirm_redemption,
    remove_pending_request,
    is_valid_merchant
)

def main(page: ft.Page):
    # Page basic setup
    page.title = "CDC Merchant Redemption"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO   
    # State
    logged_in_merchant_id = {"value": None}

    # Common UI elements
    status_text = ft.Text(size=14, weight=ft.FontWeight.BOLD)

    # Header
    header = ft.Column(
        spacing=6,
        controls=[
            ft.Text(
                "CDC Merchant Redemption",
                size=28,
                weight=ft.FontWeight.BOLD
            ),
            ft.Text(
                "Secure voucher verification for registered merchants",
                size=14,
                color=ft.colors.GREY_600
            ),
            ft.Divider()
        ]
    )

    # Merchant Login Section
    merchant_input = ft.TextField(
        label="Merchant ID",
        helper_text="Example: M-C8BBA95FE6"
    )

    login_btn = ft.ElevatedButton(
        text="Login as Merchant",
        icon=ft.icons.LOGIN
    )

    def handle_login(e):
        merchant_id = merchant_input.value.strip()

        if not merchant_id:
            status_text.value = "❌ Please enter Merchant ID"
            status_text.color = ft.colors.RED
            page.update()
            return

        if not is_valid_merchant(merchant_id):
            status_text.value = "❌ Merchant ID not found or inactive"
            status_text.color = ft.colors.RED
            page.update()
            return

        # Login success
        logged_in_merchant_id["value"] = merchant_id
        status_text.value = f"✅ Logged in as {merchant_id}"
        status_text.color = ft.colors.GREEN

        # Unlock next step (voucher verification / confirmation)
        voucher_section.visible = True
        merchant_input.disabled = True
        login_btn.disabled = True

        page.update()

    login_btn.on_click = handle_login

    login_card = ft.Card(
        content=ft.Container(
            padding=20,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Text("Merchant Login", size=20, weight=ft.FontWeight.BOLD),
                    merchant_input,
                    login_btn
                ]
            )
        )
    )

    # Voucher Redemption Section
    code_input = ft.TextField(
        label="Redemption Code",
        helper_text="Example: GP3R8V"
    )

    verify_btn = ft.ElevatedButton(
        text="Verify Voucher",
        icon=ft.icons.SEARCH
    )

    confirm_btn = ft.ElevatedButton(
        text="Confirm Deduction",
        bgcolor=ft.colors.GREEN,
        color=ft.colors.WHITE,
        disabled=True
    )

    result_container = ft.Container(visible=False)

    voucher_section = ft.Card(
        visible=False,
        content=ft.Container(
            padding=20,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Text("Voucher Redemption", size=20, weight=ft.FontWeight.BOLD),
                    code_input,
                    verify_btn,
                    result_container
                ]
            )
        )
    )

    # Verify voucher code
    def verify_voucher(e):
        status_text.value = ""
        result_container.visible = False
        confirm_btn.disabled = True
        page.update()

        # Normalize input
        code = code_input.value.strip().upper()

        # Lookup pending request associated with the redeem code
        if not code:
            status_text.value = "❌ Please enter redemption code"
            status_text.color = ft.colors.RED
            page.update()
            return

        data = get_pending_request(code)

        if not data:
            status_text.value = "❌ Invalid or expired redemption code"
            status_text.color = ft.colors.RED
            page.update()
            return

        confirm_btn.disabled = False
        confirm_btn.on_click = lambda _: confirm_redemption(code, data)

        result_container.content = ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(f"Household ID: {data['household_id']}"),
                        ft.Text(
                            f"Total Amount: ${data['total']}.00",
                            size=22,
                            weight=ft.FontWeight.BOLD
                        ),
                        confirm_btn
                    ]
                )
            )
        )

        result_container.visible = True
        status_text.value = "✅ Voucher found"
        status_text.color = ft.colors.GREEN
        page.update()

    verify_btn.on_click = verify_voucher

    # Confirm redemption
    def confirm_redemption(code, data):
        merchant_id = logged_in_merchant_id["value"]

        confirm_btn.disabled = True
        page.update()

        success, reason = merchant_confirm_redemption(
            data["household_id"],
            merchant_id,
            data["selections"]
        )

        # User feedback
        if success:
            remove_pending_request(code)

            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Redemption successful")
            )
            page.snack_bar.open = True

            # Reset UI
            status_text.value = "✅ Transaction completed"
            status_text.color = ft.colors.GREEN

            code_input.value = ""
            result_container.visible = False

        else:
            error_map = {
                "INVALID_MERCHANT": "❌ Merchant not authorised",
                "HOUSEHOLD_NOT_FOUND": "❌ Household not found",
                "VOUCHER_NOT_AVAILABLE": "❌ Voucher already redeemed",
                "VOUCHER_FILE_NOT_FOUND": "❌ System error"
            }

            status_text.value = error_map.get(reason, "❌ Redemption failed")
            status_text.color = ft.colors.RED

        confirm_btn.disabled = False
        page.update()

    # Page Layout 
    page.add(
        ft.Column(
            expand=True,
            spacing=24,
            controls=[
                header,
                login_card,
                voucher_section,
                status_text
            ]
        )
    )

# Run app
ft.app(target=main)
