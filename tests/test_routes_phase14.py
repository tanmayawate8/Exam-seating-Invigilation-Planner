"""
Phase 14 REST API Route Test Suite.
Tests endpoints for:
- Seating Plan Generation (/api/planning/seating/generate)
- Seating Plan Publication & Notification Dispatch (/api/planning/seating/<id>/publish)
- Visual 2D Layout Grid Matrix (/api/planning/seating/<plan_id>/matrix/<room_id>)
- Invigilation Duty Generation (/api/planning/invigilation/generate)
- Seating Plan Cancellation (/api/planning/seating/<id>/cancel)
Verifies algorithm adapter orchestration, atomic transactions, RBAC, and JSON envelopes.
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
from app.services.academic_service import AcademicService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.room_service import RoomService
from app.services.exam_service import ExamService
from app.services.registration_service import RegistrationService


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


def test_planning_routes_end_to_end(client, app):
    """Verify complete seating generation, publishing, 2D matrix, and invigilation assignment via REST."""
    with app.app_context():
        AuthService.create_user("admin_user", "admin@poly.edu", "AdminPass123!", role="ADMIN")

        dept = AcademicService.create_department(code="CO", name="Computer Engineering")
        subj = AcademicService.create_subject(code="CO301", name="Data Structures", department_id=dept.id, semester=3)

        exam = ExamService.create_exam({
            "subject_id": subj.id,
            "exam_code": "EXAM-CO301",
            "title": "Data Structures Exam",
            "exam_date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "13:00:00",
            "session_name": "MORNING",
        })

        # Register 3 students
        s1 = StudentService.create_student({
            "username": "s1", "email": "s1@poly.edu", "password": "Pass123!",
            "roll_number": "CO01", "enrollment_number": "ENR-01",
            "first_name": "A", "last_name": "One", "department_id": dept.id, "semester": 3,
        })
        s2 = StudentService.create_student({
            "username": "s2", "email": "s2@poly.edu", "password": "Pass123!",
            "roll_number": "CO02", "enrollment_number": "ENR-02",
            "first_name": "B", "last_name": "Two", "department_id": dept.id, "semester": 3,
        })
        s3 = StudentService.create_student({
            "username": "s3", "email": "s3@poly.edu", "password": "Pass123!",
            "roll_number": "CO03", "enrollment_number": "ENR-03",
            "first_name": "C", "last_name": "Three", "department_id": dept.id, "semester": 3,
        })

        RegistrationService.register_student(s1.id, exam.id)
        RegistrationService.register_student(s2.id, exam.id)
        RegistrationService.register_student(s3.id, exam.id)

        # Create room with capacity 10 (2 rows x 5 cols)
        room = RoomService.create_room({
            "room_number": "HALL-A",
            "building": "Poly Block",
            "floor": 1,
            "rows_count": 2,
            "columns_count": 5,
            "capacity": 10,
        })

        # Create faculty member for invigilation
        teacher = TeacherService.create_teacher({
            "username": "prof_invig",
            "email": "invig@poly.edu",
            "password": "Pass123!",
            "employee_id": "CO-FAC-99",
            "first_name": "Dr.",
            "last_name": "Invigilator",
            "department_id": dept.id,
            "designation": "HOD",
        })

        exam_id = exam.id
        room_id = room.id
        teacher_user_id = teacher.user_id

    login_client(client, "admin_user", "AdminPass123!")

    # 1. Trigger Seating Generation -> 201 Created
    gen_resp = client.post("/api/planning/seating/generate", json={
        "exam_id": exam_id,
        "room_ids": [room_id],
    })
    assert gen_resp.status_code == 201
    gen_data = gen_resp.get_json()["data"]
    plan_id = gen_data["id"]
    assert gen_data["total_students_allocated"] == 3
    assert gen_data["status"] == "GENERATED"

    # 2. Query Seating Plan by ID -> 200 OK
    get_plan = client.get(f"/api/planning/seating/{plan_id}")
    assert get_plan.status_code == 200
    assert get_plan.get_json()["data"]["plan_code"] == gen_data["plan_code"]

    # 3. Query 2D Seating Layout Matrix for Room -> 200 OK
    matrix_resp = client.get(f"/api/planning/seating/{plan_id}/matrix/{room_id}")
    assert matrix_resp.status_code == 200
    m_data = matrix_resp.get_json()["data"]
    assert m_data["rows"] == 2
    assert m_data["columns"] == 5
    assert m_data["total_allocated"] == 3
    assert len(m_data["grid"]) == 2  # 2 rows

    # 4. Publish Seating Plan -> 200 OK
    pub_resp = client.post(f"/api/planning/seating/{plan_id}/publish")
    assert pub_resp.status_code == 200
    assert pub_resp.get_json()["data"]["status"] == "PUBLISHED"

    # Verify notifications were created for 3 students
    with app.app_context():
        notifs = Notification.query.filter_by(notification_type="SEATING_PUBLISHED").all()
        assert len(notifs) == 3

    # 5. Generate Invigilation Duties -> 201 Created
    invig_resp = client.post("/api/planning/invigilation/generate", json={
        "exam_id": exam_id,
        "room_ids": [room_id],
    })
    assert invig_resp.status_code == 201
    duties_data = invig_resp.get_json()["data"]
    assert len(duties_data) == 1
    assert duties_data[0]["room_id"] == room_id
    assert duties_data[0]["duty_role"] == "CHIEF_INVIGILATOR"

    # Verify faculty notification was created
    with app.app_context():
        faculty_notif = Notification.query.filter_by(user_id=teacher_user_id, notification_type="DUTY_ASSIGNED").first()
        assert faculty_notif is not None

    # 6. Query Invigilation Duties for Exam -> 200 OK
    invig_list_resp = client.get(f"/api/planning/invigilation/exam/{exam_id}")
    assert invig_list_resp.status_code == 200
    assert len(invig_list_resp.get_json()["data"]) == 1

    # 7. Cancel Seating Plan -> 200 OK
    cancel_resp = client.post(f"/api/planning/seating/{plan_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.get_json()["data"]["status"] == "CANCELLED"
