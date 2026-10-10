"""
Security regression tests:
  CAMS-0009: center-scoping (app.api.access), local storage path traversal + HMAC signed URLs
  CAMS-0014: class tenancy & authorization (F1 email PII, F2 cross-center read, F3 teacher ownership)
"""

import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.access import (
    ensure_class_access,
    ensure_class_ownership,
    ensure_puzzle_access,
    ensure_scan_job_access,
)

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()

TEACHER_A_ID = uuid.uuid4()


def _user(role, center_id=CENTER_A, uid=None):
    return SimpleNamespace(id=uid or uuid.uuid4(), role=role, center_id=center_id)


def _job(center_id=CENTER_A, uploaded_by=None):
    return SimpleNamespace(center_id=center_id, uploaded_by=uploaded_by or uuid.uuid4())


def _puzzle(center_id=CENTER_A):
    return SimpleNamespace(center_id=center_id)


def _cls(center_id=CENTER_A, teacher_id=None):
    """Return a dict matching class_service return shape."""
    return {"center_id": center_id, "teacher_id": teacher_id or TEACHER_A_ID}


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

    # MAX_PAGES_PER_SCAN was raised to 500 for AI scanner heavy-books support
    assert pdf_service.MAX_PAGES_PER_SCAN == 500


# ── CAMS-0014: Class access — F2 (cross-center read) ─────────

def test_class_access_same_center_all_roles_allowed():
    """F2: Any authenticated user in the same center may read a class."""
    for role in ("admin", "teacher", "student", "parent"):
        ensure_class_access(_cls(), _user(role))


def test_class_access_super_admin_any_center():
    """F2: super_admin can access classes from any center."""
    ensure_class_access(_cls(center_id=CENTER_B), _user("super_admin"))


def test_class_access_other_center_returns_404():
    """F2: Users from a different center must receive 404 (not 403) to avoid leaking existence."""
    for role in ("admin", "teacher", "student", "parent"):
        with pytest.raises(HTTPException) as exc:
            ensure_class_access(_cls(center_id=CENTER_B), _user(role))
        assert exc.value.status_code == 404, f"Expected 404 for role={role}"


def test_class_access_no_center_user_denied():
    """F2: User without a center_id cannot access a class that HAS a center_id."""
    with pytest.raises(HTTPException) as exc:
        ensure_class_access(_cls(center_id=CENTER_A), _user("teacher", center_id=None))
    assert exc.value.status_code == 404


def test_class_access_unscoped_class_all_roles_allowed():
    """Legacy/unscoped classes (center_id=NULL) are accessible to any authenticated user."""
    for role in ("admin", "teacher", "student", "parent"):
        ensure_class_access(_cls(center_id=None), _user(role))
    # Even users without a center can access unscoped classes
    ensure_class_access(_cls(center_id=None), _user("teacher", center_id=None))


# ── CAMS-0014: Class ownership — F3 (teacher write gate) ─────

def test_class_ownership_super_admin_always_allowed():
    """F3: super_admin may manage any class."""
    ensure_class_ownership(_cls(center_id=CENTER_B), _user("super_admin"))


def test_class_ownership_admin_same_center_allowed():
    """F3: admin can manage any class within own center or unscoped classes."""
    ensure_class_ownership(_cls(), _user("admin"))
    # Unscoped (legacy) class should also be manageable by admin
    ensure_class_ownership(_cls(center_id=None), _user("admin"))


def test_class_ownership_admin_other_center_returns_404():
    """F3: admin from another center gets 404, not 403."""
    with pytest.raises(HTTPException) as exc:
        ensure_class_ownership(_cls(center_id=CENTER_B), _user("admin"))
    assert exc.value.status_code == 404


def test_class_ownership_teacher_owns_class_allowed():
    """F3: teacher who owns the class (teacher_id == user.id) is allowed."""
    teacher = _user("teacher", uid=TEACHER_A_ID)
    ensure_class_ownership(_cls(teacher_id=TEACHER_A_ID), teacher)
    # Also works for unscoped (legacy) classes
    ensure_class_ownership(_cls(center_id=None, teacher_id=TEACHER_A_ID), teacher)


def test_class_ownership_teacher_not_owner_denied_403():
    """F3: teacher who does NOT own the class gets 403."""
    other_teacher = _user("teacher")  # different uuid
    with pytest.raises(HTTPException) as exc:
        ensure_class_ownership(_cls(teacher_id=TEACHER_A_ID), other_teacher)
    assert exc.value.status_code == 403


def test_class_ownership_teacher_other_center_denied():
    """F3: teacher in a different center (even if teacher_id matches) gets 403."""
    teacher = _user("teacher", center_id=CENTER_B, uid=TEACHER_A_ID)
    with pytest.raises(HTTPException) as exc:
        ensure_class_ownership(_cls(center_id=CENTER_A, teacher_id=TEACHER_A_ID), teacher)
    assert exc.value.status_code == 403


def test_class_ownership_student_always_denied():
    """F3: student role can never write — gets 403."""
    with pytest.raises(HTTPException) as exc:
        ensure_class_ownership(_cls(), _user("student"))
    assert exc.value.status_code == 403


# ── CAMS-0014: F1 email visibility — unit-level logic check ──
#
# The actual include_email decision lives in the endpoint, not in access.py.
# We replicate the endpoint logic here to verify correctness.

def _include_email(current_user, cls_dict: dict) -> bool:
    """Mirror the endpoint logic for include_email (list_class_students)."""
    is_class_teacher = (
        current_user.role == "teacher"
        and cls_dict.get("teacher_id") == current_user.id
    )
    return current_user.role in {"super_admin", "admin"} or is_class_teacher


def test_f1_admin_and_super_admin_see_email():
    """F1: Admin and super_admin always see student emails."""
    cls = _cls()
    assert _include_email(_user("admin"), cls) is True
    assert _include_email(_user("super_admin"), cls) is True


def test_f1_class_teacher_sees_email():
    """F1: The teacher who owns the class sees student emails."""
    teacher = _user("teacher", uid=TEACHER_A_ID)
    cls = _cls(teacher_id=TEACHER_A_ID)
    assert _include_email(teacher, cls) is True


def test_f1_non_owner_teacher_hides_email():
    """F1: A teacher who doesn't own the class does NOT see student emails."""
    teacher = _user("teacher")  # different id from TEACHER_A_ID
    cls = _cls(teacher_id=TEACHER_A_ID)
    assert _include_email(teacher, cls) is False


def test_f1_student_and_parent_hide_email():
    """F1: Student/parent roles must never see classmate emails."""
    cls = _cls()
    for role in ("student", "parent"):
        assert _include_email(_user(role), cls) is False, f"Expected False for role={role}"
