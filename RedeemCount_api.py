from __future__ import annotations


import json

import os

from dataclasses import dataclass, asdict

from datetime import datetime

from typing import Dict, Optional


from fastapi import FastAPI, HTTPException

from pydantic import BaseModel, Field


# -----------------------------

# Persistence

# -----------------------------

DATA_FILE = "data_households.json"


def load_households() -> Dict[str, dict]:

    if not os.path.exists(DATA_FILE):

        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:

        return json.load(f)


def save_households(raw: Dict[str, dict]) -> None:

    tmp = DATA_FILE + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:

        json.dump(raw, f, ensure_ascii=False, indent=2)

    os.replace(tmp, DATA_FILE)


# -----------------------------

# In-memory Model

# -----------------------------


@dataclass
class VoucherWallet:

    # counts by denomination (e.g., {"2": 10, "5": 3, "10": 1})

    counts: Dict[str, int]

    def total_value(self) -> int:

        total = 0

        for k, v in self.counts.items():

            denom = int(k)

            total += denom * int(v)

        return total

    def can_spend_exact(self, required: Dict[str, int]) -> bool:

        for d, c in required.items():

            if self.counts.get(d, 0) < c:

                return False

        return True

    def spend(self, required: Dict[str, int]) -> None:
        """Deduct voucher counts (assumes validation already done)."""

        for d, c in required.items():

            self.counts[d] = self.counts.get(d, 0) - c

            if self.counts[d] < 0:

                # should never happen if validated

                raise ValueError("Negative voucher count after spend")


@dataclass
class HouseholdAccount:

    household_id: str

    # tranche -> wallet

    wallets: Dict[str, VoucherWallet]

    created_at: str


# -----------------------------

# App & bootstrap

# -----------------------------

app = FastAPI(title="CDC Voucher API - Remaining Vouchers")


# raw dict store for persistence simplicity

RAW_DB: Dict[str, dict] = load_households()


def get_account_or_404(household_id: str) -> HouseholdAccount:

    raw = RAW_DB.get(household_id)

    if not raw:

        raise HTTPException(status_code=404, detail="Household not found")

    wallets = {
        tranche: VoucherWallet(counts=w["counts"])
        for tranche, w in raw.get("wallets", {}).items()
    }

    return HouseholdAccount(
        household_id=raw["household_id"],
        wallets=wallets,
        created_at=raw["created_at"],
    )


def upsert_account(acc: HouseholdAccount) -> None:

    RAW_DB[acc.household_id] = {
        "household_id": acc.household_id,
        "created_at": acc.created_at,
        "wallets": {
            tranche: {"counts": wallet.counts}
            for tranche, wallet in acc.wallets.items()
        },
    }

    save_households(RAW_DB)


# -----------------------------

# Request/Response Schemas

# -----------------------------


class RegisterHouseholdReq(BaseModel):

    household_id: str = Field(..., examples=["H52298800781"])


class ClaimReq(BaseModel):

    tranche: str = Field(..., examples=["2025-05", "2026-01"])

    # simplest: claim creates counts directly (you can make it config-based)

    denomination_breakdown: Dict[str, int] = Field(
        ..., examples=[{"2": 50, "5": 40, "10": 20}]
    )


class RedeemReq(BaseModel):

    tranche: str = Field(..., examples=["2025-05"])

    merchant_id: str = Field(..., examples=["M001"])

    # how many vouchers to spend, by denomination

    spend_counts: Dict[str, int] = Field(..., examples=[{"2": 3, "5": 0, "10": 0}])


# -----------------------------

# APIs

# -----------------------------


@app.post("/api/v1/households")
def register_household(req: RegisterHouseholdReq):

    if req.household_id in RAW_DB:

        raise HTTPException(status_code=409, detail="Household already exists")

    acc = HouseholdAccount(
        household_id=req.household_id,
        wallets={},  # no tranche claimed yet
        created_at=datetime.now().isoformat(),
    )

    upsert_account(acc)

    return {"message": "Household registered", "household_id": req.household_id}


@app.post("/api/v1/households/{household_id}/claims")
def claim_vouchers(household_id: str, req: ClaimReq):

    acc = get_account_or_404(household_id)

    if req.tranche in acc.wallets:

        raise HTTPException(status_code=409, detail="Tranche already claimed")

    # store counts as strings keys: "2","5","10"

    normalized = {str(k): int(v) for k, v in req.denomination_breakdown.items()}

    acc.wallets[req.tranche] = VoucherWallet(counts=normalized)

    upsert_account(acc)

    return {
        "message": "Claim success",
        "household_id": household_id,
        "tranche": req.tranche,
        "remaining_counts": acc.wallets[req.tranche].counts,
        "remaining_total_value": acc.wallets[req.tranche].total_value(),
    }


@app.post("/api/v1/households/{household_id}/redeem")
def redeem_vouchers(household_id: str, req: RedeemReq):

    acc = get_account_or_404(household_id)

    wallet = acc.wallets.get(req.tranche)

    if not wallet:

        raise HTTPException(status_code=400, detail="Tranche not claimed")

    spend = {str(k): int(v) for k, v in req.spend_counts.items()}

    # basic validation: cannot spend negative; must have enough counts

    for d, c in spend.items():

        if c < 0:

            raise HTTPException(
                status_code=400, detail="Negative spend count is not allowed"
            )

    if not wallet.can_spend_exact(spend):

        raise HTTPException(status_code=400, detail="Insufficient voucher counts")

    # deduct

    wallet.spend(spend)

    acc.wallets[req.tranche] = wallet

    upsert_account(acc)

    spent_value = sum(int(d) * c for d, c in spend.items())

    return {
        "message": "Redeem success",
        "household_id": household_id,
        "merchant_id": req.merchant_id,
        "tranche": req.tranche,
        "spent_counts": spend,
        "spent_value": spent_value,
        # ✅ 你要的：消券后还剩多少张
        "remaining_counts": wallet.counts,
        "remaining_total_value": wallet.total_value(),
    }


@app.get("/api/v1/households/{household_id}/remaining")
def get_remaining_vouchers(household_id: str, tranche: Optional[str] = None):
    """

    ✅ 你要的 API：查询“消券后还剩多少张”

    - 不传 tranche：返回所有 tranche 的剩余张数与总金额

    - 传 tranche：只返回该 tranche

    """

    acc = get_account_or_404(household_id)

    if tranche:

        wallet = acc.wallets.get(tranche)

        if not wallet:

            raise HTTPException(
                status_code=404, detail="Tranche not found for this household"
            )

        return {
            "household_id": household_id,
            "tranche": tranche,
            "remaining_counts": wallet.counts,
            "remaining_total_value": wallet.total_value(),
        }

    # all tranches

    by_tranche = {}

    grand_total = 0

    for t, w in acc.wallets.items():

        total = w.total_value()

        by_tranche[t] = {
            "remaining_counts": w.counts,
            "remaining_total_value": total,
        }

        grand_total += total

    return {
        "household_id": household_id,
        "by_tranche": by_tranche,
        "grand_total_value": grand_total,
    }
