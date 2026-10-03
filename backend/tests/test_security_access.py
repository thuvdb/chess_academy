"""
Security regression tests for CAMS-0009:
  - center-scoping (app.api.access)
  - local storage path traversal + HMAC signed URLs (app.services.storage_service)
"""

import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.access import ensure_puzzle_access, ensure_scan_job_access

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()


def _user(role, center_id=CENTER_A, uid=None):
    return SimpleNamespace(id=uid or uuid.uuid4(), role=role, center_id=center_id)


def _job(center_id=CENTER_A, uploaded_by=None):
    return SimpleNamespace(center_id=center_id, uploaded_by=uploaded_by or uuid.uuid4())


def _puzzle(center_id=CENTER_A):
    return SimpleNamespace(center_id=center_id)


# ── Scan job access ──────────────────────────────────────────

def test_scan_job_same_center_staff_allowed():
    for role in ("admin", "teacher"):
        ensure_scan_job_access(_job(), _user(role))


def test_scan_job_other_center_staff_denied_as_404():
    for role in ("admin", "teacher"):
        with pytest.raises(HTTPException) as exc:
            ensure_scan_job_access(_job(center_id=CENTER_B), _user(role))
        assert exc.value.status_code == 404


def test_scan_job_super_admin_allowed_any_center():
    ensure_scan_job_access(_job(center_id=CENTER_B), _user("super_admin"))


def test_scan_job_uploader_allowed_even_other_center():
    u = _user("teacher", center_id=CENTER_B)
    ensure_scan_job_access(_job(uploaded_by=u.id), u)


def test_scan_job_student_same_center_denied():
    with pytest.raises(HTTPException) as exc:
        ensure_scan_job_access(_job(), _user("student"))
    assert exc.value.status_code == 404


def test_scan_job_staff_without_center_denied():
    with pytest.raises(HTTPException):
        ensure_scan_job_access(_job(), _user("teacher", center_id=None))


# ── Puzzle access ────────────────────────────────────────────

def test_puzzle_read_global_and_own_center():
    ensure_puzzle_access(_puzzle(center_id=None), _user("student"))
    ensure_puzzle_access(_puzzle(), _user("student"))


def test_puzzle_read_other_center_denied():
    with pytest.raises(HTTPException) as exc:
        ensure_puzzle_access(_puzzle(center_id=CENTER_B), _user("teacher"))
    assert exc.value.status_code == 404


def test_puzzle_write_rules():
    ensure_puzzle_access(_puzzle(), _user("teacher"), write=True)
    ensure_puzzle_access(_puzzle(center_id=None), _user("super_admin"), write=True)
    # global puzzles: super_admin only
    with pytest.raises(HTTPException):
        ensure_puzzle_access(_puzzle(center_id=None), _user("admin"), write=True)
    # students never write
    with pytest.raises(HTTPException):
        ensure_puzzle_access(_puzzle(), _user("student"), write=True)
    # other center
    with pytest.raises(HTTPException):
        ensure_puzzle_access(_puzzle(center_id=CENTER_B), _user("admin"), write=True)


# ── Storage: traversal + signed URLs ─────────────────────────

def test_safe_local_path_blocks_traversal():
    from app.services import storage_service as ss

    for bad in ("../secret.txt", "a/../../secret.txt", "../../etc/passwd"):
        with pytest.raises(ValueError):
            ss._safe_local_path(bad)
        assert ss.read_local_file(bad) is None


def test_signed_url_roundtrip_and_tamper():
    from app.services import storage_service as ss

    rel = "job-1/pages/page_001.png"
    exp = int(time.time()) + 60
    sig = ss._local_signature(rel, exp)
    assert ss.verify_local_signature(rel, exp, sig)
    # wrong path / wrong expiry / wrong signature
    assert not ss.verify_local_signature("job-2/pages/page_001.png", exp, sig)
    assert not ss.verify_local_signature(rel, exp + 1, sig)
    assert not ss.verify_local_signature(rel, exp, "0" * 64)


def test_signed_url_expired_rejected():
    from app.services import storage_service as ss

    rel = "job-1/pages/page_001.png"
    exp = int(time.time()) - 1
    assert not ss.verify_local_signature(rel, exp, ss._local_signature(rel, exp))


def test_pdf_page_limit_constant():
    from app.services import pdf_service

    assert pdf_service.MAX_PAGES_PER_SCAN == 50
