"""
Resource-level authorization helpers (center scoping).

Rules:
  - super_admin: everything
  - the uploader / creator of a resource
  - admin & teacher: resources of their own center only
  - everyone else: no access
Denials are reported as 404 so resource existence is not leaked.
"""

import uuid

from fastapi import HTTPException

from app.models.user import User

STAFF_ROLES = ("super_admin", "admin", "teacher")


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def same_center(user: User, center_id: uuid.UUID | None) -> bool:
    return (
        center_id is not None
        and user.center_id is not None
        and user.center_id == center_id
    )


def ensure_scan_job_access(job, user: User) -> None:
    """Allow super_admin, the uploader, or staff of the job's center."""
    if user.role == "super_admin" or job.uploaded_by == user.id:
        return
    if is_staff(user) and same_center(user, job.center_id):
        return
    raise HTTPException(404, detail="Scan job not found")


def ensure_puzzle_access(puzzle, user: User, write: bool = False) -> None:
    """
    Read: super_admin, global puzzles (center_id is NULL), or same center.
    Write: super_admin, or staff of the puzzle's own center (global puzzles are super_admin only).
    """
    if user.role == "super_admin":
        return
    if write:
        if getattr(puzzle, "created_by", None) == user.id:
            return
        if is_staff(user) and same_center(user, puzzle.center_id):
            return
    else:
        if puzzle.center_id is None or same_center(user, puzzle.center_id):
            return
    raise HTTPException(404, detail="Puzzle not found")


def ensure_class_access(cls_dict: dict, user: User) -> None:
    """Check that user can access a class (read-level).

    Rules (CAMS-0014):
      - super_admin: cross-center access.
      - Classes with center_id = NULL are treated as "unscoped" (legacy/global) and
        accessible to any authenticated user — prevents regression for classes created
        before CAMS-0014 deployed center scoping.
      - admin: own center only (when class has a center_id).
      - teacher / student / parent: own center only (when class has a center_id).
    Returns 404 (not 403) to avoid leaking class existence across centers.
    """
    if user.role == "super_admin":
        return
    class_center = cls_dict.get("center_id")
    # Legacy / unscoped classes (no center_id) are visible to all authenticated users.
    if class_center is None:
        return
    if same_center(user, class_center):
        return
    raise HTTPException(404, detail="Class not found")


def ensure_class_ownership(cls_dict: dict, user: User) -> None:
    """Check that a teacher is the owner of the class before modifying enrollments.

    Rules (CAMS-0014 F3):
      - super_admin: always allowed.
      - admin: allowed for classes within own center (or unscoped classes).
      - teacher: only own classes (teacher_id == user.id).
        Center check is skipped for unscoped (center_id = NULL) classes to avoid
        blocking teachers on legacy data.
    """
    if user.role == "super_admin":
        return
    class_center = cls_dict.get("center_id")
    if user.role == "admin":
        # Allow admin to manage unscoped (legacy) classes or own-center classes.
        if class_center is None or same_center(user, class_center):
            return
        raise HTTPException(404, detail="Class not found")
    # teacher — must be the assigned teacher; center check only when class has a center_id
    if user.role == "teacher":
        is_owner = cls_dict.get("teacher_id") == user.id
        center_ok = class_center is None or same_center(user, class_center)
        if is_owner and center_ok:
            return
        raise HTTPException(403, detail="You can only manage your own classes")
    raise HTTPException(403, detail="Insufficient permissions")

