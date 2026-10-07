"""
Phase 11 REST API Route Test Suite.
Tests endpoints for:
- Departments (/api/departments)
- Subjects (/api/subjects)
- Students (/api/students)
Verifies HTTP methods, payload validation, RBAC permissions, and standardized JSON envelopes.
"""

import pytest
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
# 1. DEPARTMENT ROUTES TESTS
# =============================================================================

def test_department_routes(client, app):
    """Verify department CRUD, semester roadmap, and RBAC."""
    with app.app_context():
        # Create Admin and Student users
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")
        AuthService.create_user("student_user", "student@poly.edu", "StudPass123!", role="STUDENT")

    # 1. Unauthenticated request to /api/departments -> 401
    resp = client.get("/api/departments")
    assert resp.status_code == 401

    # Log in as Student
    login_client(client, "student_user", "StudPass123!")

    # Student cannot create department -> 403 Forbidden
    post_resp = client.post("/api/departments", json={"code": "CO", "name": "Computer Engineering"})
    assert post_resp.status_code == 403

    # Log out student, log in as Admin
    client.post("/api/auth/logout")
    login_client(client, "admin_user", "AdminPass123!")

    # Admin creates department -> 201 Created
    create_resp = client.post("/api/departments", json={
        "code": "CO",
        "name": "Computer Engineering",
        "description": "Dept of Computer Engineering"
    })
    assert create_resp.status_code == 201
    dept_data = create_resp.get_json()
    assert dept_data["success"] is True
    dept_id = dept_data["data"]["id"]
    assert dept_data["data"]["code"] == "CO"

    # Get department list -> 200 OK
    list_resp = client.get("/api/departments")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()["data"]) == 1

    # Get Polytechnic semester structure -> 200 OK (Semesters 1 to 6)
    sem_resp = client.get("/api/departments/semesters")
    assert sem_resp.status_code == 200
    sems = sem_resp.get_json()["data"]
    assert len(sems) == 6
    assert sems[0]["semester"] == 1
    assert sems[5]["semester"] == 6

    # Update department -> 200 OK
    put_resp = client.put(f"/api/departments/{dept_id}", json={
        "name": "Computer Science & Engineering"
    })
    assert put_resp.status_code == 200
    assert put_resp.get_json()["data"]["name"] == "Computer Science & Engineering"

    # Delete department -> 200 OK
    del_resp = client.delete(f"/api/departments/{dept_id}")
    assert del_resp.status_code == 200


# =============================================================================
# 2. SUBJECT ROUTES TESTS
# =============================================================================

def test_subject_routes(client, app):
    """Verify subject CRUD, semester constraints (1-6), and filtering."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")

    login_client(client, "admin_user", "AdminPass123!")

    # Create department first
    dept_resp = client.post("/api/departments", json={"code": "ME", "name": "Mechanical Engineering"})
    dept_id = dept_resp.get_json()["data"]["id"]

    # Create valid subject (Semester 3) -> 201 Created
    subj_resp = client.post("/api/subjects", json={
        "code": "ME301",
        "name": "Thermal Engineering",
        "department_id": dept_id,
        "semester": 3,
        "credits": 4
    })
    assert subj_resp.status_code == 201
    subj_data = subj_resp.get_json()
    subj_id = subj_data["data"]["id"]
    assert subj_data["data"]["semester"] == 3

    # Attempt to create invalid subject (Semester 8 - Polytechnic is 1 to 6) -> 400
    invalid_resp = client.post("/api/subjects", json={
        "code": "ME801",
        "name": "Aerodynamics",
        "department_id": dept_id,
        "semester": 8,
    })
    assert invalid_resp.status_code in (400, 422)
    assert invalid_resp.get_json()["success"] is False

    # Query with filter ?semester=3
    filter_resp = client.get(f"/api/subjects?department_id={dept_id}&semester=3")
    assert filter_resp.status_code == 200
    assert len(filter_resp.get_json()["data"]) == 1

    # Update subject -> 200 OK
    update_resp = client.put(f"/api/subjects/{subj_id}", json={"name": "Advanced Thermal Engineering"})
    assert update_resp.status_code == 200
    assert update_resp.get_json()["data"]["name"] == "Advanced Thermal Engineering"

    # Delete subject -> 200 OK
    del_resp = client.delete(f"/api/subjects/{subj_id}")
    assert del_resp.status_code == 200


# =============================================================================
# 3. STUDENT ROUTES TESTS
# =============================================================================

def test_student_routes(client, app):
    """Verify student creation, pagination, status toggling, and self-access RBAC."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")

    login_client(client, "admin_user", "AdminPass123!")

    # Setup branch
    dept_resp = client.post("/api/departments", json={"code": "EE", "name": "Electrical Engineering"})
    dept_id = dept_resp.get_json()["data"]["id"]

    # Create Student via POST /api/students -> 201 Created
    create_resp = client.post("/api/students", json={
        "username": "stud_rahul",
        "email": "rahul@poly.edu",
        "password": "Password123!",
        "roll_number": "EE01",
        "enrollment_number": "ENR-EE-01",
        "first_name": "Rahul",
        "last_name": "Patil",
        "department_id": dept_id,
        "semester": 4,
        "academic_year": "2025-2026"
    })
    assert create_resp.status_code == 201
    stud_data = create_resp.get_json()
    student_id = stud_data["data"]["id"]
    assert stud_data["data"]["roll_number"] == "EE01"

    # Create a 2nd Student
    client.post("/api/students", json={
        "username": "stud_sneha",
        "email": "sneha@poly.edu",
        "password": "Password123!",
        "roll_number": "EE02",
        "enrollment_number": "ENR-EE-02",
        "first_name": "Sneha",
        "last_name": "Sharma",
        "department_id": dept_id,
        "semester": 4,
        "academic_year": "2025-2026"
    })

    # Paginated student list
    list_resp = client.get("/api/students?page=1&per_page=10&department_id=" + str(dept_id))
    assert list_resp.status_code == 200
    list_json = list_resp.get_json()
    assert len(list_json["data"]) == 2
    assert list_json["meta"]["pagination"]["total"] == 2

    # Toggle student active status via PATCH -> 200 OK
    patch_resp = client.patch(f"/api/students/{student_id}/status", json={"is_active": False})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["is_active"] is False

    # Update student record via PUT -> 200 OK
    put_resp = client.put(f"/api/students/{student_id}", json={"first_name": "Rahul Senior"})
    assert put_resp.status_code == 200
    assert put_resp.get_json()["data"]["first_name"] == "Rahul Senior"

    # Self-access RBAC test:
    # Log in as sneha, try to view rahul's profile -> 403 Forbidden
    client.post("/api/auth/logout")
    login_client(client, "stud_sneha", "Password123!")

    # Sneha cannot view Rahul -> 403
    forbidden_resp = client.get(f"/api/students/{student_id}")
    assert forbidden_resp.status_code == 403

    # Delete student as admin
    client.post("/api/auth/logout")
    login_client(client, "admin_user", "AdminPass123!")
    del_resp = client.delete(f"/api/students/{student_id}")
    assert del_resp.status_code == 200
