import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_data.json")
VOUCHER_FILE = os.path.join(BASE_DIR, "vouchers.json")


def get_balance(household_id):
    """
    Return ALL ACTIVE vouchers for a household_id
    Aggregation is handled by the UI
    """

    if not os.path.exists(HOUSEHOLD_FILE) or not os.path.exists(VOUCHER_FILE):
        return None

    # Load households
    with open(HOUSEHOLD_FILE, "r") as f:
        households = json.load(f)

    if household_id not in households:
        return None

    # Load vouchers
    with open(VOUCHER_FILE, "r") as f:
        voucher_data = json.load(f)

    # voucher_data structure:
    # { household_id: [ {voucher}, {voucher}, ... ] }

    vouchers = voucher_data.get(household_id, [])

    # Only return ACTIVE vouchers
    active_vouchers = [
        v for v in vouchers if v.get("status") == "Active"
    ]

    return active_vouchers
