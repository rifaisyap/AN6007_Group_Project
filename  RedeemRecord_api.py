# redeem_api.py
import os
import re
import csv
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Union

import pandas as pd


###############################################################################
# Utilities
###############################################################################

_DT_INPUT_FORMATS = [
    "%Y-%m-%d-%H%M%S",  # sample: 2025-11-02-081532
    "%Y%m%d%H%M%S",  # strict: 20251102081532
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]


def parse_txn_datetime(dt: Union[str, datetime]) -> datetime:
    """Parse Transaction_Date_Time into a datetime object."""
    if isinstance(dt, datetime):
        return dt

    s = str(dt).strip()
    # common cleanup: remove extra spaces
    s = re.sub(r"\s+", "", s)

    # Try known formats
    for fmt in _DT_INPUT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    # Last resort: try to extract digits and parse as YYYYMMDDhhmmss
    digits = re.sub(r"\D", "", s)
    if len(digits) == 14:
        return datetime.strptime(digits, "%Y%m%d%H%M%S")

    raise ValueError(f"Unrecognized Transaction_Date_Time format: {dt!r}")


def hour_key(dt: datetime) -> str:
    """Return YYYYMMDDHH for hourly file naming."""
    return dt.strftime("%Y%m%d%H")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def money_to_float(x: Union[str, float, int]) -> float:
    """Convert '$2.00' or '2.00' to float 2.00."""
    if x is None:
        raise ValueError("Money value cannot be None")
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "")
    s = s.replace("$", "")
    if s == "":
        raise ValueError(f"Empty money string: {x!r}")
    return float(s)


def float_to_money_str(v: float) -> str:
    """Format float as $X.XX string."""
    return f"${v:.2f}"


def normalize_id(x: str) -> str:
    """Trim and remove accidental spaces around IDs (TX/Household/Merchant/Voucher)."""
    if x is None:
        raise ValueError("ID cannot be None")
    return re.sub(r"\s+", "", str(x).strip())


def validate_columns(df: pd.DataFrame, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def append_df_to_csv(df: pd.DataFrame, path: str) -> None:
    """Append df to csv (create if not exists), keep header only on create."""
    ensure_dir(os.path.dirname(path))
    file_exists = os.path.exists(path)
    df.to_csv(path, mode="a", index=False, header=not file_exists)


def append_rows_to_txt(
    rows: List[Dict[str, str]], txt_path: str, delimiter: str = "|"
) -> None:
    """
    Append records to a .txt file for payment processing.
    Format is delimiter-separated, with a header line only if file doesn't exist.
    """
    ensure_dir(os.path.dirname(txt_path))
    file_exists = os.path.exists(txt_path)

    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(txt_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=delimiter,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        if not file_exists:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)


###############################################################################
# API Data Structures
###############################################################################

REQUIRED_FIELDS = [
    "Transaction_ID",
    "Household_ID",
    "Merchant_ID",
    "Transaction_Date_Time",
    "Voucher_Code",
    "Denomination_Used",
    "Amount_Redeemed",
    "Payment_Status",
    "Remarks",
]


@dataclass
class RedeemConfig:
    data_dir: str = "./data"
    redeem_dirname: str = "redeem"  # hourly csv folder: ./data/redeem/
    settlement_dirname: str = "settlement"  # txt folder: ./data/settlement/
    settlement_txt_name: str = "Redeemed_All.txt"  # total txt file name
    txt_delimiter: str = "|"  # can change to "," or "\t"

    @property
    def redeem_dir(self) -> str:
        return os.path.join(self.data_dir, self.redeem_dirname)

    @property
    def settlement_dir(self) -> str:
        return os.path.join(self.data_dir, self.settlement_dirname)

    @property
    def settlement_txt_path(self) -> str:
        return os.path.join(self.settlement_dir, self.settlement_txt_name)


###############################################################################
# Core Redeem API
###############################################################################


class RedeemAPI:
    """
    Redeem API for voucher redemption recording:
    - record_redemption(): write one txn's voucher lines (one or multiple) into hourly CSV
    - settle_hour(): move/append that hour's CSV lines into the total .txt file
    """

    def __init__(self, config: Optional[RedeemConfig] = None):
        self.cfg = config or RedeemConfig()
        ensure_dir(self.cfg.redeem_dir)
        ensure_dir(self.cfg.settlement_dir)

    def _hourly_csv_path(self, dt: datetime) -> str:
        return os.path.join(self.cfg.redeem_dir, f"Redeem{hour_key(dt)}.csv")

    def _clean_and_standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        "Redemption - Update any data you think is appropriate to ensure data accuracy":
        - trim IDs
        - normalize datetime to canonical string
        - ensure money formats and numeric consistency
        - standardize Payment_Status
        - enforce required columns
        """
        # Ensure columns exist
        validate_columns(df, REQUIRED_FIELDS)

        # Clean IDs
        for c in ["Transaction_ID", "Household_ID", "Merchant_ID", "Voucher_Code"]:
            df[c] = df[c].apply(normalize_id)

        # Datetime normalization -> keep as original spec string "YYYY-MM-DD-HHMMSS"
        dts = df["Transaction_Date_Time"].apply(parse_txn_datetime)
        df["Transaction_Date_Time"] = dts.apply(lambda x: x.strftime("%Y-%m-%d-%H%M%S"))

        # Money normalization
        denom = df["Denomination_Used"].apply(money_to_float)
        amt = df["Amount_Redeemed"].apply(money_to_float)
        df["Denomination_Used"] = denom.apply(float_to_money_str)
        df["Amount_Redeemed"] = amt.apply(float_to_money_str)

        # Payment status normalization (example rule)
        df["Payment_Status"] = df["Payment_Status"].astype(str).str.strip().str.title()

        # Remarks normalization: collapse whitespace
        df["Remarks"] = (
            df["Remarks"].astype(str).apply(lambda s: re.sub(r"\s+", " ", s.strip()))
        )

        return df

    def record_redemption(
        self,
        transaction_id: str,
        household_id: str,
        merchant_id: str,
        transaction_dt: Union[str, datetime],
        voucher_codes: List[str],
        denomination_used: Union[str, float, int],
        amount_redeemed: Union[str, float, int],
        payment_status: str = "Pending",
        auto_remarks: bool = True,
    ) -> pd.DataFrame:
        """
        Record ONE transaction that may consume MULTIPLE voucher codes.
        This will generate multiple rows with Remarks = 1,2,...,Final denomination used

        Returns the DataFrame that was appended.
        """
        if not voucher_codes or len(voucher_codes) == 0:
            raise ValueError("voucher_codes cannot be empty")

        dt_obj = parse_txn_datetime(transaction_dt)

        txid = normalize_id(transaction_id)
        hid = normalize_id(household_id)
        mid = normalize_id(merchant_id)
        denom_f = money_to_float(denomination_used)
        amt_f = money_to_float(amount_redeemed)

        # Build rows
        rows = []
        n = len(voucher_codes)
        for i, vc in enumerate(voucher_codes, start=1):
            remark = str(i) if (auto_remarks and i < n) else "Final denomination used"
            rows.append(
                {
                    "Transaction_ID": txid,
                    "Household_ID": hid,
                    "Merchant_ID": mid,
                    "Transaction_Date_Time": dt_obj.strftime("%Y-%m-%d-%H%M%S"),
                    "Voucher_Code": normalize_id(vc),
                    "Denomination_Used": float_to_money_str(denom_f),
                    "Amount_Redeemed": float_to_money_str(amt_f),
                    "Payment_Status": payment_status,
                    "Remarks": remark,
                }
            )

        df = pd.DataFrame(rows, columns=REQUIRED_FIELDS)
        df = self._clean_and_standardize(df)

        # Append to hourly CSV
        hourly_path = self._hourly_csv_path(dt_obj)
        append_df_to_csv(df, hourly_path)

        return df

    def record_redemption_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Alternative API: user supplies a DataFrame already in REQUIRED_FIELDS schema
        (could be one row or many). We'll clean/standardize then write into the proper
        hourly CSV *per row's timestamp* (rows may span multiple hours).

        Returns standardized DataFrame.
        """
        df = df.copy()
        df = self._clean_and_standardize(df)

        # group by hour file
        dt_objs = df["Transaction_Date_Time"].apply(parse_txn_datetime)
        df["_dt_obj"] = dt_objs

        for hk, g in df.groupby(df["_dt_obj"].apply(hour_key)):
            # Use first row dt to pick file path
            dt0 = g["_dt_obj"].iloc[0]
            path = self._hourly_csv_path(dt0)
            out = g.drop(columns=["_dt_obj"])
            append_df_to_csv(out, path)

        return df.drop(columns=["_dt_obj"])

    def settle_hour(self, dt_hour: Union[str, datetime]) -> int:
        """
        "Every hour record completed then added to a total .txt file"
        - read RedeemYYYYMMDDHH.csv
        - append all rows into total txt file
        Returns number of rows appended.
        """
        dt_obj = parse_txn_datetime(dt_hour)
        # Force dt_obj to exact hour (if user passes a minute/second time)
        dt_obj = dt_obj.replace(minute=0, second=0, microsecond=0)

        hourly_csv = self._hourly_csv_path(dt_obj)
        if not os.path.exists(hourly_csv):
            return 0

        df = safe_read_csv(hourly_csv)
        if df.empty:
            return 0

        # Ensure schema order + basic cleanup for output
        for c in REQUIRED_FIELDS:
            if c not in df.columns:
                df[c] = ""
        df = df[REQUIRED_FIELDS].fillna("")

        rows = df.to_dict(orient="records")
        append_rows_to_txt(
            rows, self.cfg.settlement_txt_path, delimiter=self.cfg.txt_delimiter
        )
        return len(rows)

    def load_hour(self, dt_hour: Union[str, datetime]) -> pd.DataFrame:
        """Convenience: read the hourly CSV file."""
        dt_obj = parse_txn_datetime(dt_hour).replace(minute=0, second=0, microsecond=0)
        hourly_csv = self._hourly_csv_path(dt_obj)
        df = safe_read_csv(hourly_csv)
        return df if not df.empty else pd.DataFrame(columns=REQUIRED_FIELDS)


###############################################################################
# Example usage (run this file directly to test)
###############################################################################

if __name__ == "__main__":
    api = RedeemAPI(RedeemConfig(data_dir="./data"))

    # Example: one transaction uses 3 vouchers in the same transaction
    df_written = api.record_redemption(
        transaction_id="TX1001",
        household_id="H52298800781",
        merchant_id="M001",
        transaction_dt="2025-11-02-081532",
        voucher_codes=["V0000001", "V0000002", "V0000003"],
        denomination_used="$2.00",
        amount_redeemed="$6.00",
        payment_status="Completed",
    )
    print(df_written)

    # Hourly settlement (append that hour into total txt)
    appended = api.settle_hour("2025-11-02-080000")
    print("Rows appended to total txt:", appended)


"""
# Redeem multiple vouchers in one transaction

from redeem_api import RedeemAPI, RedeemConfig

api = RedeemAPI(RedeemConfig(data_dir="./data"))

api.record_redemption(
    transaction_id="TX2001",
    household_id="H12345678901",
    merchant_id="M010",
    transaction_dt="2025-11-02-235908",
    voucher_codes=["V0000101", "V0000102"],
    denomination_used=2,
    amount_redeemed=4,
    payment_status="Pending"
)
"""

"""
# Settle an hour's redemption records into total txt file

api.settle_hour("2025-11-02-230000")
"""
