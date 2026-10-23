import asyncio
import os
import websockets
import json
import requests
import uuid

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

BASE_URL = os.getenv("API_BASE_URL", f"{settings.API_PUBLIC_URL.rstrip('/')}/api")
_ws_proto = "wss" if BASE_URL.startswith("https") else "ws"
_ws_host = BASE_URL.replace("http://", "").replace("https://", "").replace("/api", "").rstrip("/")
WS_URL = os.getenv("WS_URL", f"{_ws_proto}://{_ws_host}/ws/game")


async def setup_test_data(tracker: TestDataTracker):
    async with async_session_factory() as session:
        center = Center(
            name=make_test_center_name("live_game"),
            email=make_test_email("center_live"),
        )
        session.add(center)
        await session.commit()
        await session.refresh(center)
        tracker.track_center(center.id)

        admin_email = make_test_email("admin_live")
        admin_pass = "cams_secret"
        admin = User(
            email=admin_email,
            password_hash=hash_password(admin_pass),
            full_name="QA Admin Live",
            role="admin",
            center_id=center.id,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        tracker.track_user(admin.id)

        return admin_email, admin_pass, str(center.id)


async def test_live_game():
    tracker = TestDataTracker()
    print("1. Creating dummy users and tournament...")

    try:
        admin_email, admin_pass, center_id = await setup_test_data(tracker)

        # 1. Login as Admin
        login_data = {"username": admin_email, "password": admin_pass}
        resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        admin_token = resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Create 2 Students
        students = []
        tokens = []
        for i in range(2):
            email = make_test_email(f"player{i}")
            resp = requests.post(f"{BASE_URL}/users", json={
                "email": email,
                "password": "password123",
                "full_name": f"Test Player {i}",
                "role": "student",
                "center_id": center_id,
            }, headers=admin_headers)
            if resp.status_code not in (200, 201):
                print(f"Failed to create student: {resp.text}")
            student_id = resp.json()["id"]
            tracker.track_user(student_id)
            students.append(student_id)

            # Login student
            resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": "password123"})
            tokens.append(resp.json()["access_token"])

        print(f"Created players: {students[0]} and {students[1]}")

        # 3. Create Tournament
        resp = requests.post(f"{BASE_URL}/tournaments/", json={
            "name": f"Live Game Test Tournament {uuid.uuid4().hex[:6]}",
            "format": "swiss",
            "max_rounds": 1,
            "time_control": "5+0",
        }, headers=admin_headers)
        t_id = resp.json()["id"]
        tracker.track_tournament(t_id)

        # 4. Register players
        for s_id, tk in zip(students, tokens):
            r = requests.post(f"{BASE_URL}/tournaments/{t_id}/register", json={"student_id": s_id}, headers={"Authorization": f"Bearer {tk}"})
            if r.status_code != 200:
                print(f"Register failed: {r.text}")

        # 5. Start tournament (creates games)
        r = requests.post(f"{BASE_URL}/tournaments/{t_id}/start", headers=admin_headers)
        if r.status_code != 200:
            print(f"Start failed: {r.text}")

        # 6. Fetch games
        resp = requests.get(f"{BASE_URL}/tournaments/{t_id}/games", headers=admin_headers)
        games = resp.json()
        game_id = games[0]["id"]
        print(f"2. Tournament started. Game ID: {game_id}")

        print("3. Connecting WebSockets for both players...")

        async def player_session(player_name, token, moves_to_play=None, wait_before_move=0):
            url = f"{WS_URL}/{game_id}?token={token}"
            async with websockets.connect(url) as ws:
                # Receive initial state
                msg = await ws.recv()
                print(f"[{player_name}] Connected: {msg}")

                if moves_to_play:
                    for move in moves_to_play:
                        await asyncio.sleep(wait_before_move)
                        print(f"[{player_name}] Playing move: {move}")
                        await ws.send(json.dumps({"type": "move", "san": move}))

                # Keep listening for a bit
                try:
                    for _ in range(4):
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        print(f"[{player_name}] Received: {msg}")
                except asyncio.TimeoutError:
                    pass
                print(f"[{player_name}] Disconnecting.")

        # White plays e4, Black plays e5
        white_task = player_session("WHITE", tokens[0], moves_to_play=["e4", "Nf3"], wait_before_move=0.5)
        black_task = player_session("BLACK", tokens[1], moves_to_play=["e5", "Nc6"], wait_before_move=1.0)

        await asyncio.gather(white_task, black_task)
        print("4. Live game test complete.")

    finally:
        # Bắt buộc Teardown dọn dẹp
        await tracker.teardown()


if __name__ == "__main__":
    asyncio.run(test_live_game())
