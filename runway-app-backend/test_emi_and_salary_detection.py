#!/usr/bin/env python3
"""
Test EMI and Salary Detection

Tests the API endpoints for EMI and salary pattern detection.
"""

import requests
import sys
import os

# API base URL
BASE_URL = "http://localhost:8000"

def get_auth_token(username="testuser", password="test12345"):
    """Get authentication token"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    response = requests.post(login_url, json={"username": username, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def detect_emis_and_salary(token):
    """Call the salary sweep detect endpoint"""
    url = f"{BASE_URL}/api/v1/salary-sweep/detect"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(url, headers=headers)  # POST, not GET
    return response

def main():
    """Main test function"""
    print("=" * 80)
    print("Testing EMI and Salary Detection")
    print("=" * 80)
    print()
    
    # Step 1: Get auth token
    print("Step 1: Authenticating...")
    token = get_auth_token()
    if not token:
        print("❌ Authentication failed.")
        return
    print("✅ Authentication successful")
    print()
    
    # Step 2: Detect EMIs and Salary
    print("Step 2: Detecting EMIs and Salary patterns...")
    response = detect_emis_and_salary(token)
    
    if response.status_code != 200:
        print(f"❌ Detection failed: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    result = response.json()
    print(f"✅ Detection successful!")
    print()
    
    # Display EMI patterns
    emis = result.get('emis', [])
    print(f"📊 EMI Patterns Detected: {len(emis)}")
    for i, emi in enumerate(emis, 1):
        print(f"   {i}. {emi.get('merchant_source', 'N/A')} - ₹{emi.get('emi_amount', 0):,.2f}")
        print(f"      Category: {emi.get('category', 'N/A')}, Subcategory: {emi.get('subcategory', 'N/A')}")
        print(f"      Occurrences: {emi.get('occurrence_count', 0)}")
        print(f"      Confirmed: {emi.get('is_confirmed', False)}")
        if emi.get('user_label'):
            print(f"      Label: {emi.get('user_label')}")
        print()
    
    # Display Salary
    salary = result.get('salary')
    print(f"📊 Salary Detection:")
    if salary:
        print(f"   Source: {salary.get('source', 'N/A')}")
        print(f"   Amount: ₹{salary.get('amount', 0):,.2f}")
        print(f"   Count: {salary.get('count', 0)}")
        print(f"   Confirmed: {salary.get('is_confirmed', False)}")
    else:
        print(f"   ❌ No salary detected")
    print()
    
    print("=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

