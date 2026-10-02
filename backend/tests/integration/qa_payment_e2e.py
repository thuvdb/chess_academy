import requests
import uuid
import datetime

import asyncio
from app.core.database import async_session_factory
from app.models.center import Center
from app.models.user import User
from app.core.security import hash_password

async def setup_test_data():
    async with async_session_factory() as session:
        # Create Center
        center = Center(name="QA Test Center", email="center@example.com")
        session.add(center)
        await session.commit()
        await session.refresh(center)
        
        # Create Admin
        admin_email = f"admin_qa_{uuid.uuid4().hex[:8]}@example.com"
        admin_pass = "cams_secret"
        admin = User(
            email=admin_email,
            password_hash=hash_password(admin_pass),
            full_name="QA Admin",
            role="admin",
            center_id=center.id
        )
        session.add(admin)
        await session.commit()
        
        return admin_email, admin_pass, str(center.id)

BASE_URL = "http://localhost:8000/api"

def run_tests():
    print("Starting QA E2E Test for Payment & Invoices...")
    
    # 1. Setup Test Data (Center & Admin)
    try:
        ADMIN_EMAIL, ADMIN_PASS, CENTER_ID = asyncio.run(setup_test_data())
    except Exception as e:
        print(f"FAILED: Setup Test Data - {e}")
        return False
        
    # 2. Login to get token
    res = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if res.status_code not in (200, 201):
        print(f"FAILED: Login - {res.text}")
        return False
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("1. Login successful")
    
    # 2. Get Center ID from /auth/me
    res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Get Profile - {res.text}")
        return False
    center_id = res.json().get("center_id")
    if not center_id:
        print("FAILED: Admin has no center_id")
        return False
    print("2. Got user profile & center_id")
    
    # 3. Create a Fee Plan
    plan_data = {
        "center_id": center_id,
        "name": "QA Test Fee Plan",
        "amount": 500000.0,
        "currency": "VND",
        "billing_cycle": "monthly",
        "description": "QA integration test plan",
        "is_active": True
    }
    res = requests.post(f"{BASE_URL}/fee-plans/", json=plan_data, headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Create Fee Plan - {res.text}")
        return False
    fee_plan_id = res.json()["id"]
    print(f"3. Created Fee Plan: {fee_plan_id}")
    
    # 4. Generate Invoice (requires a dummy class_id - let's create a class and enroll a student first)
    class_data = {
        "center_id": center_id,
        "name": "QA Test Class",
        "level": "beginner",
        "max_students": 10
    }
    res = requests.post(f"{BASE_URL}/classes/", json=class_data, headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Create Class - {res.text}")
        return False
    class_id = res.json()["id"]
    print(f"4. Created Class: {class_id}")
    
    # Create a student
    student_data = {
        "center_id": center_id,
        "full_name": "QA Student",
        "email": f"qa_{uuid.uuid4().hex[:8]}@example.com",
        "password": "qa_password",
        "role": "student"
    }
    # We might not have a direct endpoint to create students as admin in tests easily if it's protected or not implemented.
    # Let's try registering them.
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": student_data["email"],
        "password": student_data["password"],
        "full_name": student_data["full_name"],
        "role": "student",
        "center_id": center_id
    })
    if res.status_code not in (200, 201):
        print(f"FAILED: Create Student - {res.text}")
        return False
    student_id = res.json()["id"]
    
    # Enroll student
    res = requests.post(f"{BASE_URL}/classes/{class_id}/students", json={"student_id": student_id}, headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Enroll Student - {res.text}")
        return False
    print("5. Created and enrolled QA Student")
    
    # Generate Invoice
    now = datetime.datetime.utcnow()
    future = now + datetime.timedelta(days=30)
    res = requests.post(f"{BASE_URL}/invoices/generate", json={
        "class_id": class_id,
        "fee_plan_id": fee_plan_id,
        "period_start": now.isoformat() + "Z",
        "period_end": future.isoformat() + "Z",
        "due_date": future.isoformat() + "Z"
    }, headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Generate Invoice - {res.text}")
        return False
    invoices = res.json()
    if len(invoices) == 0:
        print("FAILED: No invoices generated")
        return False
    invoice_id = invoices[0]["id"]
    print(f"6. Generated Invoice: {invoice_id}")
    
    # Check Invoice status (should be sent)
    res = requests.get(f"{BASE_URL}/invoices/{invoice_id}", headers=headers)
    if res.json()["status"] != "sent":
        print(f"FAILED: Invoice status is {res.json()['status']}, expected sent")
        return False
    
    # Confirm Payment
    res = requests.post(f"{BASE_URL}/payments/confirm", json={"invoice_id": invoice_id, "notes": "QA Test"}, headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Confirm Payment - {res.text}")
        return False
    print("7. Confirmed Payment")
    
    # Check Invoice status again (should be paid)
    res = requests.get(f"{BASE_URL}/invoices/{invoice_id}", headers=headers)
    if res.json()["status"] != "paid":
        print(f"FAILED: Invoice status is {res.json()['status']}, expected paid")
        return False
    print("8. Verified Invoice Status is PAID")
    
    # Get QR Code (VietQR)
    res = requests.get(f"{BASE_URL}/invoices/{invoice_id}/qr", headers=headers)
    if res.status_code not in (200, 201):
        print(f"FAILED: Get QR Code - {res.text}")
        return False
    if "vietqr.io" not in res.json()["qr_url"]:
        print(f"FAILED: QR Code URL not valid - {res.json()['qr_url']}")
        return False
    print("9. Verified QR Code Generation")
    
    print("ALL TESTS PASSED!")
    return True

if __name__ == "__main__":
    success = run_tests()
    import sys
    sys.exit(0 if success else 1)
