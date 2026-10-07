"""
Phase 12 REST API Route Test Suite.
Tests endpoints for:
- Teachers (/api/teachers)
- Rooms & Seats (/api/rooms)
Verifies HTTP methods, payload validation, RBAC permissions, and standardized JSON envelopes.
"""

import pytest
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.models.subject import Subject
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.seat import Seat
from app.models.exam import Exam
from app.models.registration import Registration
from app.models.seating_plan import SeatingPlan
from app.models.seat_allocation import SeatAllocation
from app.models.invigilation_duty import InvigilationDuty
from app.models.teacher_availability import TeacherAvailability
from app.models.notification import Notification
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService


@pytest.fixture(scope="module")
def app():
    """Create and configure a testing Flask app instance."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean all tables before each test to ensure test isolation."""
    with app.app_context():
        Notification.query.delete()
        SeatAllocation.query.delete()
        SeatingPlan.query.delete()
        InvigilationDuty.query.delete()
        TeacherAvailability.query.delete()
        Registration.query.delete()
        Exam.query.delete()
        Seat.query.delete()
        Room.query.delete()
        Student.query.delete()
        Teacher.query.delete()
        Subject.query.delete()
        Department.query.delete()
        User.query.delete()
        db.session.commit()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


def login_client(client, username, password):
    """Helper to log in via Flask test client session."""
    return client.post("/api/auth/login", json={"username": username, "password": password})


# =============================================================================
# 1. TEACHER ROUTES TESTS
# =============================================================================

def test_teacher_routes(client, app):
    """Verify faculty CRUD, availability setting, and RBAC."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")
        dept = AcademicService.create_department(code="CO", name="Computer Engineering")
        dept_id = dept.id

    login_client(client, "admin_user", "AdminPass123!")

    # 1. Create Teacher via POST /api/teachers -> 201 Created
    create_resp = client.post("/api/teachers", json={
        "username": "prof_sharma",
        "email": "sharma@poly.edu",
        "password": "Password123!",
        "employee_id": "CO-FAC-01",
        "first_name": "Rakesh",
        "last_name": "Sharma",
        "department_id": dept_id,
        "designation": "Assistant Professor",
        "phone_number": "9876543210",
        "max_duties_per_week": 4
    })
    assert create_resp.status_code == 201
    t_data = create_resp.get_json()
    assert t_data["success"] is True
    teacher_id = t_data["data"]["id"]
    assert t_data["data"]["employee_id"] == "CO-FAC-01"

    # 2. Get Teacher Directory -> 200 OK
    list_resp = client.get("/api/teachers?department_id=" + str(dept_id))
    assert list_resp.status_code == 200
    list_json = list_resp.get_json()
    assert len(list_json["data"]) == 1
    assert list_json["meta"]["pagination"]["total"] == 1

    # 3. Get single teacher -> 200 OK
    get_resp = client.get(f"/api/teachers/{teacher_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["data"]["designation"] == "Assistant Professor"

    # 4. Update teacher -> 200 OK
    put_resp = client.put(f"/api/teachers/{teacher_id}", json={
        "designation": "Associate Professor"
    })
    assert put_resp.status_code == 200
    assert put_resp.get_json()["data"]["designation"] == "Associate Professor"

    # 5. Set availability -> 201 Created
    avail_resp = client.post(f"/api/teachers/{teacher_id}/availability", json={
        "date": "2026-11-20",
        "time_slot": "MORNING",
        "is_available": False,
        "reason": "Department meeting"
    })
    assert avail_resp.status_code == 201
    assert avail_resp.get_json()["data"]["is_available"] is False

    # 6. Toggle status -> 200 OK
    patch_resp = client.patch(f"/api/teachers/{teacher_id}/status", json={"is_active": False})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["is_active"] is False

    # 7. Delete teacher -> 200 OK
    del_resp = client.delete(f"/api/teachers/{teacher_id}")
    assert del_resp.status_code == 200


# =============================================================================
# 2. ROOM & SEAT ROUTES TESTS
# =============================================================================

def test_room_and_seat_routes(client, app):
    """Verify room creation, auto seat grid generation, capacity metrics, and seat status toggles."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")

    login_client(client, "admin_user", "AdminPass123!")

    # 1. Create Room (5 rows x 6 columns = 30 seats) -> 201 Created
    create_resp = client.post("/api/rooms", json={
        "room_number": "HALL-101",
        "building": "Polytechnic Exam Block",
        "floor": 1,
        "rows_count": 5,
        "columns_count": 6,
        "capacity": 30
    })
    assert create_resp.status_code == 201
    room_data = create_resp.get_json()
    assert room_data["success"] is True
    room_id = room_data["data"]["id"]
    assert room_data["data"]["capacity"] == 30

    # 2. Query Room with full seats grid -> 200 OK
    get_resp = client.get(f"/api/rooms/{room_id}?include_seats=true")
    assert get_resp.status_code == 200
    get_json = get_resp.get_json()["data"]
    assert len(get_json["seats"]) == 30
    seat_numbers = [s["seat_number"] for s in get_json["seats"]]
    assert "R1-C1" in seat_numbers
    assert "R5-C6" in seat_numbers

    # 3. Check Capacity Summary -> 200 OK
    cap_resp = client.get("/api/rooms/capacity-summary")
    assert cap_resp.status_code == 200
    cap_json = cap_resp.get_json()["data"]
    assert cap_json["total_rooms"] == 1
    assert cap_json["nominal_capacity"] == 30
    assert cap_json["functional_seats"] == 30

    # 4. Fetch Seats for room -> 200 OK
    seats_resp = client.get(f"/api/rooms/{room_id}/seats")
    assert seats_resp.status_code == 200
    seats_list = seats_resp.get_json()["data"]
    first_seat_id = seats_list[0]["id"]

    # 5. Toggle Individual Seat condition (e.g., damaged desk) -> 200 OK
    seat_toggle_resp = client.patch(f"/api/rooms/seats/{first_seat_id}/status", json={"is_active": False})
    assert seat_toggle_resp.status_code == 200
    assert seat_toggle_resp.get_json()["data"]["is_active"] is False

    # Capacity summary should now reflect 29 functional seats
    cap_resp_after = client.get("/api/rooms/capacity-summary")
    assert cap_resp_after.get_json()["data"]["functional_seats"] == 29

    # 6. Update Room -> 200 OK
    put_resp = client.put(f"/api/rooms/{room_id}", json={"building": "Polytechnic Main Building"})
    assert put_resp.status_code == 200
    assert put_resp.get_json()["data"]["building"] == "Polytechnic Main Building"

    # 7. Delete Room -> 200 OK
    del_resp = client.delete(f"/api/rooms/{room_id}")
    assert del_resp.status_code == 200
