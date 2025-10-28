#!/usr/bin/env python3
"""
Upload Aarish.pdf for test2@example.com user
"""

import requests
import json

# Configuration
API_BASE = "http://localhost:8000"
EMAIL = "test2@example.com"
PASSWORD = "testpassword123"
PDF_FILE = "Aarish.pdf"

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

def upload_pdf(token):
    """Upload PDF file"""
    headers = {"Authorization": f"Bearer {token}"}

    with open(PDF_FILE, "rb") as f:
        files = {"file": (PDF_FILE, f, "application/pdf")}

        print(f"\n📤 Uploading {PDF_FILE}...")
        response = requests.post(
            f"{API_BASE}/api/v1/upload/pdf",
            headers=headers,
            files=files
        )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Upload successful!")
        print(json.dumps(result, indent=2))
        return True
    else:
        print(f"\n❌ Upload failed: {response.status_code}")
        print(response.text)
        return False

def main():
    print("=" * 80)
    print("Uploading Aarish.pdf for test2@example.com")
    print("=" * 80)

    token = login()
    if not token:
        return

    success = upload_pdf(token)

    if success:
        print("\n" + "=" * 80)
        print("✅ PDF uploaded successfully! Check database for transactions.")
        print("=" * 80)

if __name__ == "__main__":
    main()
