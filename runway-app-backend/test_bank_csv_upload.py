#!/usr/bin/env python3
"""
Test Bank CSV Upload API

Tests the CSV upload endpoint to verify transactions are stored in bank_transactions table.
"""

import requests
import sys
import os
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000"
CSV_FILE = "Nagarjun Transactions.csv"

def get_auth_token(username="testuser", password="test12345"):
    """Get authentication token"""
    # First try to register if user doesn't exist
    register_url = f"{BASE_URL}/api/v1/auth/register"
    try:
        register_response = requests.post(register_url, json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password
        })
        if register_response.status_code == 201:
            print(f"✅ Registered new user: {username}")
        elif register_response.status_code == 400:
            print(f"✅ User {username} already exists")
    except Exception as e:
        pass  # Continue to login attempt
    
    # Now login
    login_url = f"{BASE_URL}/api/v1/auth/login"
    response = requests.post(login_url, json={"username": username, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def upload_csv(file_path, token):
    """Upload CSV file"""
    url = f"{BASE_URL}/api/v1/upload/csv-smart"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'text/csv')}
        data = {}  # No account_id - let it auto-create
        
        response = requests.post(url, headers=headers, files=files, data=data)
        return response

def get_bank_transactions(token, account_id=None):
    """Get bank transactions"""
    url = f"{BASE_URL}/api/v1/bank-transactions/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page": 1, "page_size": 10}
    if account_id:
        params["account_id"] = account_id
    
    response = requests.get(url, headers=headers, params=params)
    return response

def get_credit_card_transactions(token):
    """Get credit card transactions"""
    url = f"{BASE_URL}/api/v1/credit-card-transactions/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page": 1, "page_size": 10}
    
    response = requests.get(url, headers=headers, params=params)
    return response

def get_unified_transactions(token, transaction_type='all'):
    """Get unified transactions"""
    url = f"{BASE_URL}/api/v1/transactions/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page": 1, "page_size": 10, "transaction_type": transaction_type}
    
    response = requests.get(url, headers=headers, params=params)
    return response

def get_bank_statistics(token, account_id=None):
    """Get bank transaction statistics"""
    url = f"{BASE_URL}/api/v1/bank-transactions/statistics/summary"
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    if account_id:
        params["account_id"] = account_id
    
    response = requests.get(url, headers=headers, params=params)
    return response

def main():
    """Main test function"""
    print("=" * 80)
    print("Testing Bank CSV Upload API")
    print("=" * 80)
    print()
    
    # Check if CSV file exists
    csv_path = Path(CSV_FILE)
    if not csv_path.exists():
        csv_path = Path("runway-app-backend") / CSV_FILE
        if not csv_path.exists():
            print(f"❌ CSV file not found: {CSV_FILE}")
            return
    
    print(f"✅ Found CSV file: {csv_path}")
    print()
    
    # Step 1: Get auth token
    print("Step 1: Authenticating...")
    token = get_auth_token()
    if not token:
        print("❌ Authentication failed. Please create a test user first.")
        print("   Or update credentials in the script.")
        return
    print("✅ Authentication successful")
    print()
    
    # Step 2: Upload CSV
    print("Step 2: Uploading CSV file...")
    upload_response = upload_csv(csv_path, token)
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed: {upload_response.status_code}")
        print(f"Response: {upload_response.text}")
        return
    
    upload_result = upload_response.json()
    print(f"✅ Upload successful!")
    print(f"   Transactions found: {upload_result.get('transactions_found', 0)}")
    print(f"   Transactions imported: {upload_result.get('transactions_created', 0)}")
    print(f"   Account ID: {upload_result.get('account_id', 'N/A')}")
    print()
    
    account_id = upload_result.get('account_id')
    
    # Step 3: Verify bank transactions
    print("Step 3: Verifying bank transactions...")
    bank_response = get_bank_transactions(token, account_id)
    
    if bank_response.status_code == 200:
        bank_txns = bank_response.json()
        print(f"✅ Found {len(bank_txns)} bank transactions")
        if len(bank_txns) > 0:
            print(f"   Sample transaction: {bank_txns[0].get('date')} - {bank_txns[0].get('description_raw', '')[:50]}")
    else:
        print(f"❌ Failed to get bank transactions: {bank_response.status_code}")
        print(f"Response: {bank_response.text}")
    print()
    
    # Step 4: Verify credit card transactions (should be empty)
    print("Step 4: Verifying credit card transactions (should be empty for bank CSV)...")
    cc_response = get_credit_card_transactions(token)
    
    if cc_response.status_code == 200:
        cc_txns = cc_response.json()
        print(f"✅ Found {len(cc_txns)} credit card transactions (expected: 0)")
        if len(cc_txns) > 0:
            print("   ⚠️  WARNING: Credit card transactions found! This shouldn't happen for bank CSV.")
    else:
        print(f"✅ No credit card transactions (or endpoint not accessible)")
    print()
    
    # Step 5: Get bank statistics
    print("Step 5: Getting bank transaction statistics...")
    stats_response = get_bank_statistics(token, account_id)
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✅ Statistics retrieved:")
        print(f"   Total count: {stats.get('total_count', 0)}")
        print(f"   Debit count: {stats.get('debit_count', 0)}")
        print(f"   Credit count: {stats.get('credit_count', 0)}")
        print(f"   Total debit: ₹{stats.get('total_debit', 0):,.2f}")
        print(f"   Total credit: ₹{stats.get('total_credit', 0):,.2f}")
        print(f"   Net amount: ₹{stats.get('net_amount', 0):,.2f}")
    else:
        print(f"❌ Failed to get statistics: {stats_response.status_code}")
    print()
    
    # Step 6: Test unified endpoint
    print("Step 6: Testing unified transactions endpoint...")
    unified_response = get_unified_transactions(token, 'bank')
    
    if unified_response.status_code == 200:
        result = unified_response.json()
        txns = result.get('transactions', [])
        print(f"✅ Found {len(txns)} bank transactions via unified endpoint")
    else:
        print(f"⚠️  Unified endpoint returned: {unified_response.status_code}")
    print()
    
    print("=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

