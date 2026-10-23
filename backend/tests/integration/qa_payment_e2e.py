import os
import requests
import uuid
import datetime
import asyncio

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.center import Center
from app.models.user import User
from app.core.security import hash_password
from tests.integration.test_cleanup_helper import (
    TestDataTracker,
    make_test_email,
    make_test_center_name,
)


async def setup_test_data(tracker: TestDataTracker):
    async with async_session_factory() as session:
        # Create Center
        center = Center(
            name=make_test_center_name("payment"),
            email=make_test_email("center_payment"),
        )
        session.add(center)
        await session.commit()
        await session.refresh(center)
        tracker.track_center(center.id)

        # Create Admin
        admin_email = make_test_email("admin_payment")
        admin_pass = "cams_secret"
        admin = User(
            email=admin_email,
            password_hash=hash_password(admin_pass),
            full_name="QA Admin",
            role="admin",
            center_id=center.id,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        tracker.track_user(admin.id)

        return admin_email, admin_pass, str(center.id)


BASE_URL = os.getenv("API_BASE_URL", f"{settings.API_PUBLIC_URL.rstrip('/')}/api")


def run_tests():
    print("Starting QA E2E Test for Payment & Invoices...")
    tracker = TestDataTracker()

    # 1. Setup Test Data (Center & Admin)
    try:
        ADMIN_EMAIL, ADMIN_PASS, CENTER_ID = asyncio.run(setup_test_data(tracker))

        # 2. Login to get token
        res = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if res.status_code not in (200, 201):
            print(f"FAILED: Login - {res.text}")
            return False
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("1. Login successful")

        # 3. Create Fee Plan
        fee_plan_data = {
            "name": f"QA Monthly Plan {uuid.uuid4().hex[:6]}",
            "fee_type": "monthly",
            "amount": 500000,
            "currency": "VND",
            "billing_cycle": "monthly",
            "center_id": CENTER_ID,
        }
        res = requests.post(f"{BASE_URL}/fee-plans/", json=fee_plan_data, headers=headers)
        if res.status_code not in (200, 201):
            print(f"FAILED: Create Fee Plan - {res.text}")
            return False
        fee_plan = res.json()
        fee_plan_id = fee_plan["id"]
        tracker.track_fee_plan(fee_plan_id)
        print(f"2. Created Fee Plan: {fee_plan_id}")

        # Fetch fee plans
        res = requests.get(f"{BASE_URL}/fee-plans/center/{CENTER_ID}", headers=headers)
        if res.status_code != 200:
            print(f"FAILED: Get Fee Plans - {res.text}")
            return False
        print("3. Fetched Fee Plans successfully")

        # 4. Create Class
        class_data = {
            "name": f"QA Payment Class {uuid.uuid4().hex[:6]}",
            "level": "beginner",
            "max_students": 10,
            "fee_plan_id": fee_plan_id,
        }
        res = requests.post(f"{BASE_URL}/classes/", json=class_data, headers=headers)
        if res.status_code not in (200, 201):
            print(f"FAILED: Create Class - {res.text}")
            return False
        cls = res.json()
        class_id = cls["id"]
        tracker.track_class(class_id)
        print(f"4. Created Class: {class_id}")

        # 5. Create Student & Enroll
        student_email = make_test_email("student")
        student_data = {
            "email": student_email,
            "password": "password123",
            "full_name": "QA Student",
            "role": "student",
            "center_id": CENTER_ID,
        }
        res = requests.post(f"{BASE_URL}/users", json=student_data, headers=headers)
        if res.status_code not in (200, 201):
            print(f"FAILED: Create Student - {res.text}")
            return False
        student_id = res.json()["id"]
        tracker.track_user(student_id)

        # Enroll student
        res = requests.post(f"{BASE_URL}/classes/{class_id}/students", json={"student_id": student_id}, headers=headers)
        if res.status_code not in (200, 201):
            print(f"FAILED: Enroll Student - {res.text}")
            return False
        print("5. Created and enrolled QA Student")

        # 6. Generate Invoice
        now = datetime.datetime.now(datetime.timezone.utc)
        future = now + datetime.timedelta(days=30)
        res = requests.post(f"{BASE_URL}/invoices/generate", json={
            "class_id": class_id,
            "fee_plan_id": fee_plan_id,
            "period_start": now.isoformat(),
            "period_end": future.isoformat(),
            "due_date": future.isoformat(),
        }, headers=headers)
        if res.status_code not in (200, 201):
            print(f"FAILED: Generate Invoice - {res.text}")
            return False
        invoices = res.json()
        if len(invoices) == 0:
            print("FAILED: No invoices generated")
            return False
        invoice_id = invoices[0]["id"]
        tracker.track_invoice(invoice_id)
        print(f"6. Generated Invoice: {invoice_id}")

        # Check Invoice status (should be sent)
        res = requests.get(f"{BASE_URL}/invoices/{invoice_id}", headers=headers)
        if res.json()["status"] != "sent":
            print(f"FAILED: Invoice status is {res.json()['status']}, expected sent")
            return False

        # 7. Confirm Payment
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

    finally:
        # Bắt buộc Teardown dọn dẹp
        asyncio.run(tracker.teardown())


if __name__ == "__main__":
    success = run_tests()
    import sys
    sys.exit(0 if success else 1)
