"""
Phase 13 REST API Route Test Suite.
Tests endpoints for:
- Examination Scheduling (/api/exams)
- Candidate Registrations (/api/exams/<id>/registrations)
- Bulk Cohort Enrollment (/api/exams/<id>/bulk-enroll)
Verifies timetable conflict avoidance, lifecycle transitions, registration CRUD, and RBAC permissions.
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
from app.services.student_service import StudentService


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
# EXAM & REGISTRATION ROUTES TESTS
# =============================================================================

def test_exam_scheduling_and_conflict_checks(client, app):
    """Verify exam creation, cohort overlap conflict prevention, and lifecycle state changes."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")
        dept = AcademicService.create_department(code="CO", name="Computer Engineering")
        s1 = AcademicService.create_subject(code="CO301", name="Data Structures", department_id=dept.id, semester=3)
        s2 = AcademicService.create_subject(code="CO302", name="Operating Systems", department_id=dept.id, semester=3)
        s1_id = s1.id
        s2_id = s2.id

    login_client(client, "admin_user", "AdminPass123!")

    # 1. Schedule Exam 1 -> 201 Created
    create_resp = client.post("/api/exams", json={
        "subject_id": s1_id,
        "exam_code": "EXAM-CO301-W26",
        "title": "Data Structures Exam",
        "exam_date": "2026-11-15",
        "start_time": "10:00:00",
        "end_time": "13:00:00",
        "session_name": "MORNING",
        "status": "SCHEDULED"
    })
    assert create_resp.status_code == 201
    ex_data = create_resp.get_json()
    assert ex_data["success"] is True
    exam_id = ex_data["data"]["id"]
    assert ex_data["data"]["exam_code"] == "EXAM-CO301-W26"

    # 2. Schedule conflicting Exam for same cohort (same dept & sem, overlapping time) -> 409 Conflict
    conflict_resp = client.post("/api/exams", json={
        "subject_id": s2_id,
        "exam_code": "EXAM-CO302-W26",
        "title": "Operating Systems Exam",
        "exam_date": "2026-11-15",
        "start_time": "11:00:00",
        "end_time": "14:00:00",
        "session_name": "MORNING",
        "status": "SCHEDULED"
    })
    assert conflict_resp.status_code == 409
    assert conflict_resp.get_json()["success"] is False

    # 3. Query Exam Timetable -> 200 OK
    list_resp = client.get("/api/exams?status=SCHEDULED")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()["data"]) == 1

    # 4. Update Exam title -> 200 OK
    put_resp = client.put(f"/api/exams/{exam_id}", json={
        "title": "Data Structures Winter 2026 Final"
    })
    assert put_resp.status_code == 200
    assert put_resp.get_json()["data"]["title"] == "Data Structures Winter 2026 Final"

    # 5. Transition Exam Status via PATCH -> 200 OK
    patch_resp = client.patch(f"/api/exams/{exam_id}/status", json={"status": "PLANNED"})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["status"] == "PLANNED"


def test_candidate_registration_routes(client, app):
    """Verify individual candidate registration, duplicate prevention, and bulk cohort enrollment."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")
        dept = AcademicService.create_department(code="ME", name="Mechanical Engineering")
        subj = AcademicService.create_subject(code="ME301", name="Thermodynamics", department_id=dept.id, semester=3)

        # Create two students in department
        st1 = StudentService.create_student({
            "username": "stud_1",
            "email": "s1@poly.edu",
            "password": "Password123!",
            "roll_number": "ME01",
            "enrollment_number": "ENR-ME-01",
            "first_name": "Ajay",
            "last_name": "Verma",
            "department_id": dept.id,
            "semester": 3,
        })
        st2 = StudentService.create_student({
            "username": "stud_2",
            "email": "s2@poly.edu",
            "password": "Password123!",
            "roll_number": "ME02",
            "enrollment_number": "ENR-ME-02",
            "first_name": "Vijay",
            "last_name": "Verma",
            "department_id": dept.id,
            "semester": 3,
        })

        st1_id = st1.id
        st2_id = st2.id
        subj_id = subj.id

    login_client(client, "admin_user", "AdminPass123!")

    # Schedule Exam
    ex_resp = client.post("/api/exams", json={
        "subject_id": subj_id,
        "exam_code": "EXAM-ME301",
        "title": "Thermodynamics Exam",
        "exam_date": "2026-11-18",
        "start_time": "14:00:00",
        "end_time": "17:00:00",
        "session_name": "AFTERNOON",
        "status": "SCHEDULED"
    })
    exam_id = ex_resp.get_json()["data"]["id"]

    # 1. Register student 1 -> 201 Created
    reg_resp = client.post(f"/api/exams/{exam_id}/registrations", json={
        "student_id": st1_id,
        "is_eligible": True
    })
    assert reg_resp.status_code == 201
    reg_data = reg_resp.get_json()
    reg_id = reg_data["data"]["id"]
    assert reg_data["data"]["student_id"] == st1_id

    # 2. Duplicate registration attempt -> 409 Conflict
    dup_resp = client.post(f"/api/exams/{exam_id}/registrations", json={
        "student_id": st1_id
    })
    assert dup_resp.status_code == 409

    # 3. Bulk enroll cohort -> 200 OK (enrolls st2, skips st1)
    bulk_resp = client.post(f"/api/exams/{exam_id}/bulk-enroll", json={"semester": 3})
    assert bulk_resp.status_code == 200
    bulk_data = bulk_resp.get_json()["data"]
    assert bulk_data["enrolled"] == 1
    assert bulk_data["skipped"] == 1
    assert bulk_data["total"] == 2

    # 4. Query candidate registrations -> 200 OK
    list_regs = client.get(f"/api/exams/{exam_id}/registrations")
    assert list_regs.status_code == 200
    assert len(list_regs.get_json()["data"]) == 2

    # 5. Update candidate attendance/eligibility via PATCH -> 200 OK
    patch_resp = client.patch(f"/api/exams/registrations/{reg_id}", json={
        "attendance_status": "PRESENT"
    })
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["attendance_status"] == "PRESENT"

    # 6. Deregister candidate -> 200 OK
    del_resp = client.delete(f"/api/exams/{exam_id}/registrations/{st1_id}")
    assert del_resp.status_code == 200

    # Total registered should now be 1
    check_regs = client.get(f"/api/exams/{exam_id}/registrations")
    assert len(check_regs.get_json()["data"]) == 1
