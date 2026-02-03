# CDC Voucher Redemption System

## Overview

This project implements a CDC Voucher Redemption System that simulates the lifecycle of digital vouchers, from household and merchant registration to voucher claiming, balance enquiry, and redemption. The system demonstrates core software engineering concepts such as API design, data persistence, state management, and basic protection against duplicate redemption.

The application uses Python-based backend APIs, in-memory data structures for fast access, and file-based persistence to ensure recoverability after server restarts. A Python-based mobile application is provided to simulate real-world interactions by households and merchants.

---

## Features

- Household registration
- Merchant registration
- Tranche-based voucher claiming (one claim per tranche)
- Voucher balance enquiry with denomination breakdown
- Redemption initiation with one-time redeem code generation
- Merchant verification and confirmation of redemption
- Voucher state transition control (Active → Redeemed)
- Persistent storage for recovery after server downtime
- Hourly redemption audit log generation

---

# CDC Voucher Redemption System

## Overview

This project implements a CDC Voucher Redemption System that simulates the complete lifecycle of digital vouchers—from household and merchant registration to voucher claiming, balance enquiry, and redemption. The system demonstrates core software engineering concepts including API design, data persistence, state management, and duplicate redemption prevention.

The application uses a Python-based backend with REST APIs, in-memory data structures for performance, and file-based persistence for reliability. A Python mobile application simulates real-world interactions between households and merchants.

---

## Features

- **Household registration** with unique account management
- **Merchant registration** with bank detail validation
- **Tranche-based voucher claiming** (one claim per tranche per household)
- **Voucher balance enquiry** with denomination breakdown
- **Redemption initiation** with one-time redeem code generation
- **Merchant verification** and redemption confirmation
- **Voucher state management** (Active → Redeemed)
- **Persistent storage** for recovery after server downtime
- **Hourly audit logs** for redemption tracking and compliance

---

## System Actors

### Household
Registers an account, claims vouchers by tranche, checks voucher balance, and initiates redemption by generating a one-time redeem code.

### Merchant
Registers with valid business and bank details, logs in using a merchant ID, verifies redeem codes, and confirms voucher redemption.

The backend system manages business logic, enforces validation rules, persists critical data, and generates audit logs for accountability.

---

## Data Persistence

The system uses file-based persistence to ensure durability and recovery:

- **household_data.json** - Household registration and tranche claim status
- **vouchers.json** - Voucher records and status (Active/Redeemed)
- **pending_redemptions.json** - Pending redemption requests
- **merchants.csv** - Merchant registration records
- **RedeemYYYYMMDDHH.csv** - Hourly audit logs for confirmed redemptions

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/household/registration` | POST | Register a new household |
| `/merchant/registration` | POST | Register a new merchant |
| `/household/claim` | POST | Claim vouchers by tranche |
| `/voucher/balance` | GET | Retrieve voucher balance |
| `/redeem/initiate` | POST | Generate one-time redeem code |
| `/redeem/confirm` | POST | Confirm redemption |

---

## Voucher Redemption Flow

## Voucher Redemption Flow

1. **Household** registers an account with household ID and personal details
2. **Merchant** registers with business details and bank account information
3. **Household** claims vouchers for a specific tranche (e.g., Tranche 1, Tranche 2)
4. **System** generates vouchers with unique IDs and assigns them to the household
5. **Household** checks voucher balance and available denominations
6. **Household** selects a valid denomination mix and initiates redemption
7. **System** generates a one-time redeem code and stores a pending redemption record
8. **Merchant** logs in using merchant ID and verifies the redeem code
9. **Merchant** confirms the redemption transaction
10. **System** marks vouchers as Redeemed, persists state, and generates an audit log
11. **Redeem code** is invalidated to prevent reuse

---

## Voucher State Management

Vouchers follow a strict one-way lifecycle:
```
Active → Redeemed
```

Once a voucher is marked as **Redeemed** and persisted, it cannot revert to **Active**, even after server restart. This prevents duplicate redemption and ensures accounting correctness.

---

## Mobile Application

A Python-based mobile application simulates real-world user interactions.

### Household Features
- Voucher balance enquiry
- Denomination breakdown
- Initiate redemption and generate redeem code
- View transaction history

### Merchant Features
- Merchant login using merchant ID
- Redeem code verification
- Redemption confirmation

The mobile app communicates with backend APIs to demonstrate end-to-end voucher redemption.

---

## How to Run the Program

### 1. Prerequisites

- Python 3.0 or above
- pip (Python package manager)
- Virtual environment (recommended)

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
```

**Activate the virtual environment:**

- **macOS/Linux:**
```bash
  source venv/bin/activate
```

- **Windows:**
```bash
  venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the Backend Server
```bash
python3 main.py
```

The backend server will start and expose APIs for household registration, merchant registration, voucher claiming, balance enquiry, and voucher redemption.

### 5. Run the Mobile Application

Open a new terminal (keep the backend running), then run:
```bash
python mobile_app/app.py
```

```bash
python mobile_app/merchant_app.py
```

The mobile application allows you to:
- Check household voucher balance
- Initiate redemption and generate redeem codes
- Log in as a merchant
- Verify and confirm voucher redemption

### 6. Persistent Data and Logs

During execution, the system automatically creates or updates the following files:

- `household_data.json`
- `vouchers.json`
- `pending_redemptions.json`
- `merchants.csv`
- `RedeemYYYYMMDDHH.csv` (hourly audit logs)


### 7. Stop the Program

To stop the backend server or mobile app, press:
```
Ctrl + C
```
