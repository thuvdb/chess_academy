"""
CAMS RBAC & Tenant Isolation Core Permissions.
Provides centralized role-checking dependencies and multi-center data isolation helpers.

Rules:
1. super_admin has global access across all centers.
2. center_admin / admin, teacher, student, parent are strictly bounded to their assigned center_id.
3. Accessing resources from another center returns 404 Not Found (NEVER 403) to prevent tenant enumeration and data leakage.
4. Legacy 'admin' role is transparently treated as 'center_admin' for backward compatibility.
"""

import enum
import uuid
from typing import Any, Callable, Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.sql import Select

from app.api.deps import get_current_user
from app.models.base import UserRole
from app.models.user import User


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    CENTER_ADMIN = "center_admin"
    ADMIN = "admin"  # Backward compatibility
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


ADMIN_ROLES = {Role.SUPER_ADMIN, Role.CENTER_ADMIN, Role.ADMIN}
CENTER_ADMIN_ROLES = {Role.CENTER_ADMIN, Role.ADMIN}


def is_super_admin(user: User) -> bool:
    """Return True if user has super_admin role."""
    return user.role == Role.SUPER_ADMIN.value


def is_center_admin(user: User) -> bool:
    """Return True if user has center_admin (or legacy admin) role."""
    return user.role in {Role.CENTER_ADMIN.value, Role.ADMIN.value}


def is_admin(user: User) -> bool:
    """Return True if user is either super_admin or center_admin."""
    return is_super_admin(user) or is_center_admin(user)


def require_roles(*allowed_roles: str | Role) -> Callable[[User], User]:
    """
    FastAPI dependency that enforces user role membership.
    Automatically treats CENTER_ADMIN and legacy ADMIN as interchangeable.
    """
    expanded_roles = set()
    for r in allowed_roles:
        val = r.value if isinstance(r, Role) else str(r)
        expanded_roles.add(val)
        if val in {Role.CENTER_ADMIN.value, Role.ADMIN.value}:
            expanded_roles.add(Role.CENTER_ADMIN.value)
            expanded_roles.add(Role.ADMIN.value)

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in expanded_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privileges to perform this action",
            )
        return current_user

    return role_checker


def assert_same_center(
    current_user: User,
    resource_center_id: uuid.UUID | str | None,
    detail: str = "Resource not found",
) -> None:
    """
    Assert that the current user belongs to the same center as the requested resource.
    super_admin bypasses this check.
    For all other roles, if centers do not match, raises 404 NOT FOUND (not 403)
    to prevent information disclosure across tenants.
    """
    if is_super_admin(current_user):
        return

    if resource_center_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    # Normalize to string for reliable comparison
    user_cid = str(current_user.center_id) if current_user.center_id else None
    res_cid = str(resource_center_id)

    if user_cid != res_cid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


def assert_owner_or_admin(
    current_user: User,
    resource_owner_id: uuid.UUID | str | None,
    resource_center_id: uuid.UUID | str | None = None,
    detail_not_found: str = "Resource not found",
    detail_forbidden: str = "You do not have permission to modify this resource",
) -> None:
    """
    Assert that current_user is:
    1. super_admin (allowed globally), OR
    2. The owner of the resource (and within their center), OR
    3. center_admin of the same center.
    Cross-center access raises 404. Same center but unauthorized raises 403.
    """
    if is_super_admin(current_user):
        return

    # Check center boundary first — cross-center must be 404
    if resource_center_id is not None:
        assert_same_center(current_user, resource_center_id, detail=detail_not_found)

    # Owner check
    user_uid = str(current_user.id)
    owner_uid = str(resource_owner_id) if resource_owner_id else None
    if owner_uid and user_uid == owner_uid:
        return

    # Center admin check (can manage resources of their center)
    if is_center_admin(current_user):
        return

    # Within same center, but neither owner nor center admin -> 403 Forbidden
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail_forbidden,
    )


def scope_query_to_center(
    query: Select,
    current_user: User,
    center_id_column: Any,
    filter_center_id: uuid.UUID | str | None = None,
) -> Select:
    """
    Scope a SQLAlchemy query to the user's center.
    - If super_admin: applies optional filter_center_id if provided.
    - If non-super_admin: strictly forces query WHERE center_id = current_user.center_id.
    """
    if is_super_admin(current_user):
        if filter_center_id:
            target_cid = uuid.UUID(str(filter_center_id)) if not isinstance(filter_center_id, uuid.UUID) else filter_center_id
            return query.where(center_id_column == target_cid)
        return query

    # Non-super_admin must be strictly scoped
    return query.where(center_id_column == current_user.center_id)
