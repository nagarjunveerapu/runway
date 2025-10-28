#!/usr/bin/env python3
"""
Test salary sweep detection for test2@example.com
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

def test_salary_sweep_detection(token):
    """Test salary sweep detection"""
    headers = {"Authorization": f"Bearer {token}"}

    print("\n📊 Testing Salary Sweep Detection...")
    print("=" * 80)

    # Trigger detection
    print("\n1. Triggering salary pattern detection...")
    response = requests.post(
        f"{API_BASE}/api/v1/salary-sweep/detect",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Detection successful!")
        print(json.dumps(result, indent=2))
        return True
    else:
        print(f"❌ Detection failed: {response.status_code}")
        print(response.text)
        return False

def main():
    print("=" * 80)
    print("Testing Salary Sweep for test2@example.com")
    print("=" * 80)

    token = login()
    if not token:
        return

    success = test_salary_sweep_detection(token)

    if success:
        print("\n" + "=" * 80)
        print("✅ Salary sweep detection completed!")
        print("=" * 80)

if __name__ == "__main__":
    main()
