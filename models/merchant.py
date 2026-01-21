class Merchant:
    # This class represents a CDC merchant entity in the system
    # It was designed based on the Merchant.csv specification provided in the project brief
    def __init__(self, merchant_id, merchant_name, uen, bank_name,
                 bank_code, branch_code, account_number,
                 account_holder_name, registration_date, status):

        self.merchant_id = merchant_id

        # Basic merchant information provided during registration
        self.merchant_name = merchant_name
        self.uen = uen

        # Bank and account details used for reimbursement
        self.bank_name = bank_name
        self.bank_code = bank_code
        self.branch_code = branch_code
        self.account_number = account_number
        self.account_holder_name = account_holder_name

        self.registration_date = registration_date
        self.status = status

    # Converts the Merchant object into a dictionary.
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

    # Converts the Merchant object into a readable text format
    def to_txt(self):
        lines = [
            "----- Merchant Registration -----",
            f"merchant_id: {self.merchant_id}",
            f"merchant_name: {self.merchant_name}",
            f"uen: {self.uen}",
            f"bank_name: {self.bank_name}",
            f"bank_code: {self.bank_code}",
            f"branch_code: {self.branch_code}",
            f"account_number: {self.account_number}",
            f"account_holder_name: {self.account_holder_name}",
            f"registration_date: {self.registration_date}",
            f"status: {self.status}",
        ]
        return "\n".join(lines)
