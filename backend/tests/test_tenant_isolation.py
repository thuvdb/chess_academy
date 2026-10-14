"""
Integration & Security Tests for CAMS-0024: Tenant Isolation across Modules.
Validates:
1. Classes: Cross-center access returns 404; list queries are center-scoped.
2. Puzzles: Cross-center access returns 404; teacher can only modify own puzzles (403 for colleague's); center_admin can modify any puzzle in their center.
3. AI Scanner: Cross-center job inspection & deletion return 404; jobs list is center-scoped.
4. Assignments: Cross-center inspection & creation return 404; teacher can only modify own assignments; center_admin can modify center assignments.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role
from app.main import app
from app.models.user import User

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()

TEACHER_A1_ID = uuid.uuid4()
TEACHER_A2_ID = uuid.uuid4()
TEACHER_B_ID = uuid.uuid4()
ADMIN_A_ID = uuid.uuid4()
ADMIN_B_ID = uuid.uuid4()
SUPER_ADMIN_ID = uuid.uuid4()

USER_SUPER_ADMIN = User(
    id=SUPER_ADMIN_ID,
    email="super_admin@cams.vn",
    full_name="Super Admin",
    role=Role.SUPER_ADMIN.value,
    center_id=None,
    is_active=True,
    elo_rating=800,
)

USER_ADMIN_A = User(
    id=ADMIN_A_ID,
    email="admin_a@cams.vn",
    full_name="Center Admin A",
    role=Role.CENTER_ADMIN.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)

USER_TEACHER_A1 = User(
    id=TEACHER_A1_ID,
    email="teacher_a1@cams.vn",
    full_name="Teacher A1",
    role=Role.TEACHER.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)

USER_TEACHER_A2 = User(
    id=TEACHER_A2_ID,
    email="teacher_a2@cams.vn",
    full_name="Teacher A2",
    role=Role.TEACHER.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)

USER_TEACHER_B = User(
    id=TEACHER_B_ID,
    email="teacher_b@cams.vn",
    full_name="Teacher B",
    role=Role.TEACHER.value,
    center_id=CENTER_B,
    is_active=True,
    elo_rating=800,
)


@pytest_asyncio.fixture
async def api_client():
    state = {"current_user": USER_ADMIN_A}

    mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: state["current_user"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.state = state
        client.mock_db = mock_db
        yield client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. Classes Module Tenant Isolation
# ==============================================================================

@pytest.mark.asyncio
@patch("app.services.class_service.get_class_by_id")
async def test_get_class_cross_center_returns_404(mock_get_class, api_client):
    """Admin of Center A querying a Class belonging to Center B receives 404 Not Found."""
    class_b_id = uuid.uuid4()
    mock_get_class.return_value = {
        "id": class_b_id,
        "name": "Class B",
        "center_id": CENTER_B,
        "teacher_id": TEACHER_B_ID,
        "current_students": 5,
        "teacher_name": "Teacher B",
        "level": "beginner",
        "max_students": 20,
        "schedule_json": None,
        "is_active": True,
        "branch_id": None,
    }

    # Caller is Center Admin A
    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.get(f"/api/classes/{class_b_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"


@pytest.mark.asyncio
@patch("app.services.class_service.get_class_by_id")
async def test_get_class_super_admin_bypasses_center(mock_get_class, api_client):
    """Super Admin can access class of any center."""
    class_b_id = uuid.uuid4()
    mock_get_class.return_value = {
        "id": class_b_id,
        "name": "Class B",
        "center_id": CENTER_B,
        "teacher_id": TEACHER_B_ID,
        "current_students": 5,
        "teacher_name": "Teacher B",
        "level": "beginner",
        "max_students": 20,
        "schedule_json": None,
        "is_active": True,
        "branch_id": None,
        "created_at": datetime.now(timezone.utc),
    }

    api_client.state["current_user"] = USER_SUPER_ADMIN
    response = await api_client.get(f"/api/classes/{class_b_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Class B"


@pytest.mark.asyncio
@patch("app.services.class_service.get_classes")
async def test_list_classes_scoped_to_caller_center(mock_get_classes, api_client):
    """Non-super_admin callers have center_id filter automatically applied."""
    mock_get_classes.return_value = []

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.get("/api/classes/")
    assert response.status_code == 200

    # Ensure get_classes was invoked with center_id=CENTER_A
    mock_get_classes.assert_called_once()
    _, kwargs = mock_get_classes.call_args
    assert kwargs["center_id"] == CENTER_A


# ==============================================================================
# 2. Puzzles Module Tenant Isolation & Modification Rights
# ==============================================================================

@pytest.mark.asyncio
@patch("app.services.puzzle_service.get_puzzle")
async def test_get_puzzle_cross_center_returns_404(mock_get_puzzle, api_client):
    """Accessing a puzzle from another center returns 404."""
    puzzle_b_id = uuid.uuid4()
    mock_get_puzzle.return_value = SimpleNamespace(
        id=puzzle_b_id,
        center_id=CENTER_B,
        created_by=TEACHER_B_ID,
        title="Tactics B",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        solution_moves=[],
        puzzle_type="mate-in-1",
        difficulty="easy",
        solution_verified=True,
        solution_tree=None,
        created_at=None,
        updated_at=None,
    )

    api_client.state["current_user"] = USER_TEACHER_A1
    response = await api_client.get(f"/api/puzzles/{puzzle_b_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Puzzle not found"


@pytest.mark.asyncio
@patch("app.services.puzzle_service.get_puzzle")
async def test_teacher_cannot_modify_colleague_puzzle_same_center(mock_get_puzzle, api_client):
    """Teacher A1 cannot modify Teacher A2's puzzle in the same center (403 Forbidden)."""
    puzzle_a2_id = uuid.uuid4()
    mock_get_puzzle.return_value = SimpleNamespace(
        id=puzzle_a2_id,
        center_id=CENTER_A,
        created_by=TEACHER_A2_ID,  # Created by Teacher A2
        title="Teacher A2 Puzzle",
        fen="8/8/8/8/8/8/8/8 w - - 0 1",
    )

    api_client.state["current_user"] = USER_TEACHER_A1
    response = await api_client.put(f"/api/puzzles/{puzzle_a2_id}", json={"title": "Hacked Title"})
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only modify your own puzzles"


@pytest.mark.asyncio
@patch("app.services.puzzle_service.update_puzzle")
@patch("app.services.puzzle_service.get_puzzle")
async def test_center_admin_can_modify_any_puzzle_in_own_center(mock_get_puzzle, mock_update, api_client):
    """Center Admin can modify any puzzle belonging to their center."""
    puzzle_a2_id = uuid.uuid4()
    mock_puzzle = SimpleNamespace(
        id=puzzle_a2_id,
        center_id=CENTER_A,
        created_by=TEACHER_A2_ID,
        title="Teacher A2 Puzzle",
        fen="8/8/8/8/8/8/8/8 w - - 0 1",
        solution_moves=[],
        puzzle_type="tactic",
        difficulty="medium",
        solution_verified=True,
        solution_tree=None,
        created_at=None,
        updated_at=None,
    )
    mock_get_puzzle.return_value = mock_puzzle
    mock_update.return_value = mock_puzzle

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(f"/api/puzzles/{puzzle_a2_id}", json={"title": "Admin Updated Title"})
    assert response.status_code == 200


@pytest.mark.asyncio
@patch("app.services.puzzle_service.get_puzzle")
async def test_center_admin_cannot_modify_puzzle_diff_center(mock_get_puzzle, api_client):
    """Center Admin A cannot modify puzzle from Center B (returns 404)."""
    puzzle_b_id = uuid.uuid4()
    mock_get_puzzle.return_value = SimpleNamespace(
        id=puzzle_b_id,
        center_id=CENTER_B,
        created_by=TEACHER_B_ID,
        title="Puzzle B",
    )

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(f"/api/puzzles/{puzzle_b_id}", json={"title": "Attack Title"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Puzzle not found"


# ==============================================================================
# 3. AI Scanner Module Tenant Isolation
# ==============================================================================

@pytest.mark.asyncio
@patch("app.services.scan_service.get_scan_job")
async def test_scan_job_cross_center_returns_404(mock_get_job, api_client):
    """Accessing scan job from another center returns 404."""
    job_b_id = uuid.uuid4()
    mock_get_job.return_value = SimpleNamespace(
        id=job_b_id,
        center_id=CENTER_B,
        uploaded_by=TEACHER_B_ID,
        file_name="book_b.pdf",
    )

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.get(f"/api/scan/jobs/{job_b_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Scan job not found"


@pytest.mark.asyncio
@patch("app.services.scan_service.get_scan_job")
async def test_delete_scan_job_cross_center_returns_404(mock_get_job, api_client):
    """Deleting scan job from another center returns 404."""
    job_b_id = uuid.uuid4()
    mock_get_job.return_value = SimpleNamespace(
        id=job_b_id,
        center_id=CENTER_B,
        uploaded_by=TEACHER_B_ID,
    )

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.delete(f"/api/scan/jobs/{job_b_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Scan job not found"


@pytest.mark.asyncio
@patch("app.services.scan_service.list_scan_jobs")
async def test_list_scan_jobs_scoped_to_caller_center(mock_list_jobs, api_client):
    """list_jobs filters strictly by caller's center_id."""
    mock_list_jobs.return_value = []

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.get("/api/scan/jobs")
    assert response.status_code == 200

    mock_list_jobs.assert_called_once()
    _, kwargs = mock_list_jobs.call_args
    assert kwargs["center_id"] == CENTER_A


# ==============================================================================
# 4. Assignments Module Tenant Isolation
# ==============================================================================

@pytest.mark.asyncio
@patch("app.services.assignment_service.get_assignment")
async def test_get_assignment_cross_center_returns_404(mock_get_assignment, api_client):
    """Accessing assignment of a class in Center B by Center A user returns 404."""
    assignment_id = uuid.uuid4()
    mock_class = SimpleNamespace(id=uuid.uuid4(), center_id=CENTER_B)
    mock_get_assignment.return_value = SimpleNamespace(
        id=assignment_id,
        class_id=mock_class.id,
        class_=mock_class,
        teacher_id=TEACHER_B_ID,
        title="Homework Center B",
    )

    api_client.state["current_user"] = USER_TEACHER_A1
    response = await api_client.get(f"/api/assignments/{assignment_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Assignment not found"


@pytest.mark.asyncio
@patch("app.services.assignment_service.create_assignment")
async def test_create_assignment_cross_center_rejected(mock_create, api_client):
    """Teacher in Center A cannot create assignment for a Class in Center B."""
    class_b_id = uuid.uuid4()
    mock_target_class = SimpleNamespace(id=class_b_id, center_id=CENTER_B)

    # Mock db.get(Class, data.class_id)
    api_client.mock_db.get = AsyncMock(return_value=mock_target_class)

    api_client.state["current_user"] = USER_TEACHER_A1
    payload = {
        "class_id": str(class_b_id),
        "title": "Malicious Assignment",
        "puzzle_ids": [],
    }
    response = await api_client.post("/api/assignments", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"


@pytest.mark.asyncio
@patch("app.services.assignment_service.get_assignment")
async def test_teacher_cannot_modify_colleague_assignment_same_center(mock_get_assignment, api_client):
    """Teacher A1 cannot modify Teacher A2's assignment in the same center (403 Forbidden)."""
    assignment_id = uuid.uuid4()
    mock_class = SimpleNamespace(id=uuid.uuid4(), center_id=CENTER_A)
    mock_get_assignment.return_value = SimpleNamespace(
        id=assignment_id,
        class_id=mock_class.id,
        class_=mock_class,
        teacher_id=TEACHER_A2_ID,  # Owned by Teacher A2
        title="Teacher A2 HW",
    )

    api_client.state["current_user"] = USER_TEACHER_A1
    response = await api_client.put(f"/api/assignments/{assignment_id}", json={"title": "Hacked Title"})
    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to modify this assignment"


@pytest.mark.asyncio
@patch("app.services.assignment_service.update_assignment")
@patch("app.services.assignment_service.get_assignment")
async def test_center_admin_can_modify_any_assignment_in_center(mock_get_assignment, mock_update, api_client):
    """Center Admin can modify any assignment within their center."""
    assignment_id = uuid.uuid4()
    mock_class = SimpleNamespace(id=uuid.uuid4(), name="Class A", center_id=CENTER_A)
    mock_assignment = SimpleNamespace(
        id=assignment_id,
        class_id=mock_class.id,
        class_=mock_class,
        teacher_id=TEACHER_A2_ID,
        title="Teacher A2 HW",
        description="Description",
        puzzle_ids=[],
        due_date=None,
        max_attempts=3,
        created_at=None,
        updated_at=None,
    )
    mock_get_assignment.return_value = mock_assignment
    mock_update.return_value = mock_assignment

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(f"/api/assignments/{assignment_id}", json={"title": "Admin Adjusted HW"})
    assert response.status_code == 200
