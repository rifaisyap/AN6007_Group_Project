class Merchant:
    # This class represents a CDC merchant entity in the system
    # Designed based on the Merchant.csv specification in the project brief

    CSV_HEADERS = [
        "merchant_id",
        "merchant_name",
        "uen",
        "bank_name",
        "bank_code",
        "branch_code",
        "account_number",
        "account_holder_name",
        "registration_date",
        "status"
    ]

    def __init__(self, merchant_id, merchant_name, uen, bank_name,
                 bank_code, branch_code, account_number,
                 account_holder_name, registration_date, status):

        self.merchant_id = merchant_id
        self.merchant_name = merchant_name
        self.uen = uen
        self.bank_name = bank_name
        self.bank_code = bank_code
        self.branch_code = branch_code
        self.account_number = account_number
        self.account_holder_name = account_holder_name
        self.registration_date = registration_date
        self.status = status

    # Convert merchant object to dictionary
    def to_dict(self):
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "uen": self.uen,
            "bank_name": self.bank_name,
            "bank_code": self.bank_code,
            "branch_code": self.branch_code,
            "account_number": self.account_number,
            "account_holder_name": self.account_holder_name,
            "registration_date": self.registration_date,
            "status": self.status
        }

    # Convert merchant to CSV row (ORDER MATTERS)
    def to_csv_row(self):
        return [
            self.merchant_id,
            self.merchant_name,
            self.uen,
            self.bank_name,
            self.bank_code,
            self.branch_code,
            self.account_number,
            self.account_holder_name,
            self.registration_date,
            self.status
        ]
