#!/usr/bin/env python3
"""
Test dynamic timeline API endpoint
"""

import requests
import json

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

def test_endpoints(token):
    """Test both static and dynamic endpoints"""
    headers = {"Authorization": f"Bearer {token}"}

    print("\n" + "=" * 80)
    print("Testing Static Timeline")
    print("=" * 80)

    response = requests.get(
        f"{API_BASE}/api/v1/net-worth/timeline?months=12",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: 200 OK")
        print(f"Timeline entries: {len(data.get('timeline', []))}")
        if data.get('timeline'):
            print("\nFirst 3 months:")
            for item in data['timeline'][:3]:
                print(f"  {item['month']}: Assets=₹{item['assets']:,.0f}, Net Worth=₹{item['net_worth']:,.0f}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

    print("\n" + "=" * 80)
    print("Testing Dynamic Timeline")
    print("=" * 80)

    response = requests.get(
        f"{API_BASE}/api/v1/net-worth/timeline/dynamic?months=12&projection=false",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: 200 OK")
        print(f"Timeline entries: {len(data.get('timeline', []))}")
        print(f"Has crossover point: {data.get('crossover_point') is not None}")
        if data.get('timeline'):
            print("\nFirst 3 months:")
            for item in data['timeline'][:3]:
                print(f"  {item['month']}: Assets=₹{item['assets']:,.0f}, Net Worth=₹{item['net_worth']:,.0f}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text[:500])

def main():
    token = login()
    if not token:
        return
    test_endpoints(token)

if __name__ == "__main__":
    main()
