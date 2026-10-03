"""
HTTP-level authorization tests for CAMS-0009 (no real DB: get_db / services are faked).

Verifies the access helpers are actually wired into the endpoints:
  - cross-center users get 404 on scan jobs, results, review/approve/reject
  - same-center staff are allowed
  - puzzle get/update/delete are center-scoped; puzzle create cannot target another center
  - /api/files rejects tampered / expired signatures
"""

import time
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_db
from app.main import app
from app.services import puzzle_service, scan_service, storage_service

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()
UPLOADER = uuid.uuid4()


class FakeDB:
    async def commit(self): ...
    async def rollback(self): ...
    async def refresh(self, _obj): ...


def _user(role="teacher", center_id=CENTER_A):
    return SimpleNamespace(id=uuid.uuid4(), role=role, center_id=center_id)


def _job(center_id=CENTER_A):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(), center_id=center_id, uploaded_by=UPLOADER,
        file_name="x.pdf", file_url="http://other-host/x.pdf", file_size=1,
        total_pages=1, boards_found=1, boards_approved=0, status="completed",
        error_message=None, processing_time_ms=1, created_at=now, updated_at=now,
    )


def _result(job_id):
    return SimpleNamespace(
        id=uuid.uuid4(), job_id=job_id, page_number=1, board_index=0,
        board_image_url=None, bounding_box=None, confidence_board=0.9,
        fen_candidate="8/8/8/8/8/8/8/8 w - - 0 1", fen_final=None,
        side_to_move="w", castling_rights="-", en_passant="-",
        cell_confidence=None, review_status="pending", reviewed_by=None,
        reviewed_at=None, puzzle_id=None,
    )


@pytest.fixture
def client(monkeypatch):
    state = {"user": _user(), "job": _job(), "calls": []}
    state["result"] = _result(state["job"].id)

    async def _get_job(db, job_id):
        return state["job"]

    async def _get_result(db, result_id):
        return state["result"]

    async def _get_results(db, job_id):
        return [state["result"]]

    async def _update_review(**kwargs):
        state["calls"].append("update_result_review")

    monkeypatch.setattr(scan_service, "get_scan_job", _get_job)
    monkeypatch.setattr(scan_service, "get_scan_result", _get_result)
    monkeypatch.setattr(scan_service, "get_job_results", _get_results)
    monkeypatch.setattr(scan_service, "update_result_review", _update_review)

    async def _db():
        yield FakeDB()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    c = TestClient(app, raise_server_exceptions=False)
    c.state = state
    yield c
    app.dependency_overrides.clear()


# ── Scan jobs / results ──────────────────────────────────────

def test_get_job_same_center_ok(client):
    r = client.get(f"/api/scan/jobs/{client.state['job'].id}")
    assert r.status_code == 200


def test_get_job_other_center_404(client):
    client.state["user"] = _user("teacher", CENTER_B)
    r = client.get(f"/api/scan/jobs/{client.state['job'].id}")
    assert r.status_code == 404


def test_get_job_results_other_center_404(client):
    client.state["user"] = _user("admin", CENTER_B)
    r = client.get(f"/api/scan/jobs/{client.state['job'].id}/results")
    assert r.status_code == 404


def test_get_job_results_student_404(client):
    client.state["user"] = _user("student", CENTER_A)
    r = client.get(f"/api/scan/jobs/{client.state['job'].id}/results")
    assert r.status_code == 404


@pytest.mark.parametrize("method,suffix,body", [
    ("put", "review", {"fen_final": "8/8/8/8/8/8/8/8 w - - 0 1"}),
    ("post", "approve", None),
    ("post", "reject", None),
])
def test_review_actions_other_center_404_and_no_write(client, method, suffix, body):
    client.state["user"] = _user("teacher", CENTER_B)
    url = f"/api/scan/results/{client.state['result'].id}/{suffix}"
    r = getattr(client, method)(url, json=body) if body else getattr(client, method)(url)
    assert r.status_code == 404
    assert client.state["calls"] == []  # review must NOT have been applied


@pytest.mark.parametrize("method,suffix,body", [
    ("put", "review", {"fen_final": "8/8/8/8/8/8/8/8 w - - 0 1"}),
    ("post", "approve", None),
    ("post", "reject", None),
])
def test_review_actions_same_center_ok(client, method, suffix, body):
    url = f"/api/scan/results/{client.state['result'].id}/{suffix}"
    r = getattr(client, method)(url, json=body) if body else getattr(client, method)(url)
    assert r.status_code == 200, r.text
    assert client.state["calls"] == ["update_result_review"]


def test_review_student_forbidden(client):
    client.state["user"] = _user("student", CENTER_A)
    r = client.post(f"/api/scan/results/{client.state['result'].id}/approve")
    assert r.status_code == 403


def test_review_super_admin_other_center_ok(client):
    client.state["user"] = _user("super_admin", CENTER_B)
    r = client.post(f"/api/scan/results/{client.state['result'].id}/approve")
    assert r.status_code == 200


# ── Puzzles ──────────────────────────────────────────────────

def _fake_puzzle(center_id):
    return SimpleNamespace(id=uuid.uuid4(), center_id=center_id)


def test_puzzle_other_center_get_update_delete_404(client, monkeypatch):
    p = _fake_puzzle(CENTER_B)
    deleted = []

    async def _get(db, pid):
        return p

    async def _delete(db, puzzle):
        deleted.append(puzzle)

    monkeypatch.setattr(puzzle_service, "get_puzzle", _get)
    monkeypatch.setattr(puzzle_service, "delete_puzzle", _delete)

    assert client.get(f"/api/puzzles/{p.id}").status_code == 404
    assert client.put(f"/api/puzzles/{p.id}", json={"title": "x"}).status_code == 404
    assert client.delete(f"/api/puzzles/{p.id}").status_code == 404
    assert deleted == []


def test_puzzle_same_center_delete_ok(client, monkeypatch):
    p = _fake_puzzle(CENTER_A)

    async def _get(db, pid):
        return p

    async def _delete(db, puzzle):
        return None

    monkeypatch.setattr(puzzle_service, "get_puzzle", _get)
    monkeypatch.setattr(puzzle_service, "delete_puzzle", _delete)
    assert client.delete(f"/api/puzzles/{p.id}").status_code == 204


def test_puzzle_global_delete_denied_for_admin(client, monkeypatch):
    p = _fake_puzzle(None)

    async def _get(db, pid):
        return p

    monkeypatch.setattr(puzzle_service, "get_puzzle", _get)
    client.state["user"] = _user("admin", CENTER_A)
    assert client.delete(f"/api/puzzles/{p.id}").status_code == 404


def test_puzzle_create_cannot_target_other_center(client, monkeypatch):
    seen = {}

    async def _create(db, created_by, data):
        seen["center_id"] = data.center_id
        raise ValueError("stop-after-capture")

    monkeypatch.setattr(puzzle_service, "create_puzzle", _create)
    r = client.post("/api/puzzles", json={
        "title": "t", "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
        "difficulty": "easy", "puzzle_type": "tactic",
        "center_id": str(CENTER_B),
    })
    assert r.status_code == 400, r.text  # reached create_puzzle (schema accepted)
    assert seen["center_id"] == CENTER_A  # forced to caller's own center


def test_puzzle_from_scan_other_center_404(client, monkeypatch):
    client.state["user"] = _user("teacher", CENTER_B)
    called = []

    async def _create(**kw):
        called.append(1)

    monkeypatch.setattr(puzzle_service, "create_puzzle_from_scan", _create)
    r = client.post("/api/puzzles/from-scan", json={
        "scan_result_id": str(client.state["result"].id),
        "title": "t", "difficulty": "easy", "puzzle_type": "tactic",
    })
    assert r.status_code == 404, r.text
    assert called == []


# ── Signed file endpoint ─────────────────────────────────────

def test_files_bad_signature_403(client):
    exp = int(time.time()) + 60
    r = client.get(f"/api/files/{exp}/{'0' * 64}/x/pages/page_001.png")
    assert r.status_code == 403


def test_files_expired_403(client):
    rel = "x/pages/page_001.png"
    exp = int(time.time()) - 5
    sig = storage_service._local_signature(rel, exp)
    assert client.get(f"/api/files/{exp}/{sig}/{rel}").status_code == 403


def test_files_valid_signature_traversal_not_served():
    # HTTP clients normalize '..' before sending, so call the endpoint directly with a
    # *validly signed* traversal path: the signature check passes, path guard must refuse.
    import asyncio

    from fastapi import HTTPException

    from app.api.endpoints.files import get_signed_file

    rel = "../../app/core/config.py"
    exp = int(time.time()) + 60
    sig = storage_service._local_signature(rel, exp)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_signed_file(exp, sig, rel))
    assert exc.value.status_code == 404


def test_scan_static_mount_removed(client):
    # Old public /scans mount must be gone
    assert client.get("/scans/anything.png").status_code == 404
