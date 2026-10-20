import os
import requests
import time
import uuid
import asyncio

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.center import Center
from app.models.user import User
from app.core.security import hash_password

async def setup_test_data():
    async with async_session_factory() as session:
        # Create Center
        center = Center(name="QA Test Center", email="center_tournament@example.com")
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

BASE_URL = os.getenv("API_BASE_URL", f"{settings.API_PUBLIC_URL.rstrip('/')}/api")

def run_tests():
    print("Starting QA E2E Test for Tournaments...")
    
    try:
        ADMIN_EMAIL, ADMIN_PASS, CENTER_ID = asyncio.run(setup_test_data())
    except Exception as e:
        print(f"FAILED: Setup Test Data - {e}")
        return False

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
    
    print("1. Successfully logged in as admin.")

    # Create a new tournament
    tournament_data = {
        "name": "Winter E2E Championship",
        "description": "Integration Test Tournament",
        "format": "swiss",
        "max_rounds": 3,
        "time_control": "10+5"
    }

    resp = requests.post(f"{BASE_URL}/tournaments/", json=tournament_data, headers=headers)
    resp.raise_for_status()
    tournament = resp.json()
    tournament_id = tournament["id"]

    print(f"2. Created tournament {tournament_id}.")

    # Fetch tournaments
    resp = requests.get(f"{BASE_URL}/tournaments/", headers=headers)
    resp.raise_for_status()
    assert len(resp.json()) > 0
    print("3. Fetched tournaments successfully.")

    # Get specific tournament
    resp = requests.get(f"{BASE_URL}/tournaments/{tournament_id}", headers=headers)
    resp.raise_for_status()
    assert resp.json()["name"] == "Winter E2E Championship"
    print("4. Fetched specific tournament successfully.")

    print("✅ TOURNAMENT E2E QA PASS")
    return True

if __name__ == "__main__":
    success = run_tests()
    import sys
    sys.exit(0 if success else 1)
