#!/usr/bin/env python3
"""
Test Net Worth Timeline API endpoint
"""

import requests
import json

# Configuration
API_BASE = "http://localhost:8000"
EMAIL = "test2@example.com"
PASSWORD = "testpassword123"

def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": EMAIL, "password": PASSWORD}
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Logged in as {EMAIL}")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_timeline(token):
    """Test net worth timeline endpoint"""
    headers = {"Authorization": f"Bearer {token}"}

    print("\n📊 Testing Net Worth Timeline API...")
    print("=" * 80)

    # Test 1: Get 12-month timeline
    print("\n1. Testing GET /api/v1/net-worth/timeline?months=12")
    response = requests.get(
        f"{API_BASE}/api/v1/net-worth/timeline?months=12",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Timeline entries: {len(data.get('timeline', []))}")
        print(f"   Has historical data: {data.get('has_historical_data')}")
        print(f"   Months requested: {data.get('months_requested')}")
        print(f"   Months returned: {data.get('months_returned')}")

        if data.get('timeline'):
            print("\n   Sample data (first 3 months):")
            for entry in data['timeline'][:3]:
                print(f"   - {entry['month']}: Assets=₹{entry['assets']:,.0f}, Net Worth=₹{entry['net_worth']:,.0f}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

    # Test 2: Get current net worth
    print("\n2. Testing GET /api/v1/net-worth/current")
    response = requests.get(
        f"{API_BASE}/api/v1/net-worth/current",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Total Assets: ₹{data.get('total_assets', 0):,.0f}")
        print(f"   Total Liabilities: ₹{data.get('total_liabilities', 0):,.0f}")
        print(f"   Net Worth: ₹{data.get('net_worth', 0):,.0f}")
        print(f"   Liquid Assets: ₹{data.get('liquid_assets', 0):,.0f}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

    # Test 3: Get all snapshots
    print("\n3. Testing GET /api/v1/net-worth/snapshots")
    response = requests.get(
        f"{API_BASE}/api/v1/net-worth/snapshots",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Total snapshots: {data.get('total_snapshots', 0)}")
        if data.get('snapshots'):
            print(f"   Date range: {data['snapshots'][-1]['month']} to {data['snapshots'][0]['month']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

def main():
    print("=" * 80)
    print("Net Worth Timeline API Validation")
    print("=" * 80)

    token = login()
    if not token:
        return

    test_timeline(token)

    print("\n" + "=" * 80)
    print("✅ Validation complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
