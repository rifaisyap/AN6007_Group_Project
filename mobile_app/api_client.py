import requests

BASE_URL = "http://127.0.0.1:8000"


def get_balance(household_id):
    r = requests.get(f"{BASE_URL}/api/household/{household_id}/balance")
    if r.status_code != 200:
        return {}
    return r.json()


def redeem(household_id, merchant_id, amount, tranche):
    payload = {
        "household_id": household_id,
        "merchant_id": merchant_id,
        "amount": amount,
        "tranche": tranche
    }
    r = requests.post(f"{BASE_URL}/api/household/redeem", json=payload)
    return r.json()
