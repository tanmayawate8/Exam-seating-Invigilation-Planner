"""
Phase 15 REST API Route Test Suite.
Tests dedicated portal endpoints for Member 2 Frontend Integration:
- Student Portal:
  * GET /api/student/profile
  * GET /api/student/timetable
  * GET /api/student/my-seat (and /api/student/seating)
  * GET /api/student/seat-search (Public / Kiosk lookup)
  * GET /api/student/notifications
- Teacher Portal:
  * GET /api/teacher/profile
  * GET /api/teacher/duties
  * POST /api/teacher/availability
  * POST /api/teacher/duty-swap
  * GET /api/teacher/duty-swaps
  * GET /api/teacher/colleagues
  * GET /api/teacher/notifications
- RBAC Security Isolation:
  * Unauthenticated access rejected (401)
  * Cross-role portal access rejected (403: Student accessing Teacher portal, Teacher accessing Student portal)
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
from app.models.duty_swap import DutySwap
from app.models.teacher_availability import TeacherAvailability
from app.models.notification import Notification
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.room_service import RoomService
from app.services.exam_service import ExamService
from app.services.registration_service import RegistrationService
from app.services.planning_service import PlanningService


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
    """Clean all tables before each test to ensure complete test isolation."""
    with app.app_context():
        Notification.query.delete()
        DutySwap.query.delete()
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


def test_student_portal_endpoints_end_to_end(client, app):
    """
    Verify complete student portal functionality:
    - Profile retrieval
    - Registered examination timetable
    - Allocated seating after publishing
    - Kiosk roll number search
    - Student notifications
    """
    with app.app_context():
        # Setup Academic Data
        dept = AcademicService.create_department(code="CO", name="Computer Engineering")
        subj = AcademicService.create_subject(code="CO301", name="Data Structures", department_id=dept.id, semester=3)

        # Create Exam
        exam = ExamService.create_exam({
            "subject_id": subj.id,
            "exam_code": "EXAM-CO301",
            "title": "Data Structures Exam",
            "exam_date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "13:00:00",
            "session_name": "MORNING",
        })

        # Create Room
        room = RoomService.create_room({
            "room_number": "101",
            "building": "Main",
            "floor": 1,
            "rows_count": 2,
            "columns_count": 2,
            "actual_capacity": 4,
        })

        # Create Student
        student = StudentService.create_student({
            "first_name": "Rahul",
            "last_name": "Sharma",
            "email": "rahul.sharma@poly.edu",
            "username": "rahul_s",
            "password": "Password123!",
            "department_id": dept.id,
            "roll_number": "CO301",
            "enrollment_number": "ENR-CO-301",
            "semester": 3,
            "division": "A",
            "academic_year": "2026-2027",
        })

        # Register Student for Exam
        RegistrationService.register_student(student_id=student.id, exam_id=exam.id)

        # Generate Seating Plan and Publish it
        plan = PlanningService.generate_seating_plan(exam.id, [room.id])
        PlanningService.publish_seating_plan(plan.id, operator_user_id=1)

    # 1. Login as Student
    login_res = login_client(client, "rahul_s", "Password123!")
    assert login_res.status_code == 200

    # 2. GET /api/student/profile
    profile_res = client.get("/api/student/profile")
    assert profile_res.status_code == 200
    p_data = profile_res.get_json()["data"]
    assert p_data["roll_number"] == "CO301"
    assert p_data["first_name"] == "Rahul"
    assert p_data["semester"] == 3

    # 3. GET /api/student/timetable
    tt_res = client.get("/api/student/timetable")
    assert tt_res.status_code == 200
    tt_data = tt_res.get_json()["data"]
    assert len(tt_data) == 1
    assert tt_data[0]["exam_code"] == "EXAM-CO301"
    assert tt_data[0]["subject_code"] == "CO301"

    # 4. GET /api/student/my-seat
    seat_res = client.get("/api/student/my-seat")
    assert seat_res.status_code == 200
    seat_data = seat_res.get_json()["data"]
    assert len(seat_data) == 1
    assert seat_data[0]["exam_code"] == "EXAM-CO301"
    assert seat_data[0]["room_number"] == "101"
    assert "seat_number" in seat_data[0]

    # 5. GET /api/student/notifications
    notif_res = client.get("/api/student/notifications")
    assert notif_res.status_code == 200
    notif_data = notif_res.get_json()["data"]
    assert len(notif_data) >= 1
    assert any("Seating Allocation Published" in n["title"] for n in notif_data)

    # 6. Logout and test Public / Kiosk Seat Search (/api/student/seat-search)
    client.post("/api/auth/logout")
    kiosk_res = client.get("/api/student/seat-search?roll_number=CO301")
    assert kiosk_res.status_code == 200
    k_data = kiosk_res.get_json()["data"]
    assert len(k_data) == 1
    assert k_data[0]["student_roll"] == "CO301"
    assert k_data[0]["room_number"] == "101"


def test_teacher_portal_endpoints_end_to_end(client, app):
    """
    Verify complete teacher portal functionality:
    - Profile retrieval
    - Assigned duties list
    - Faculty availability / leave submission
    * Duty swap request initiation and swap list
    - Active colleagues list for swap selection
    - Teacher notifications
    """
    with app.app_context():
        # Setup Academic Data
        dept = AcademicService.create_department(code="ME", name="Mechanical Engineering")
        subj = AcademicService.create_subject(code="ME401", name="Thermodynamics", department_id=dept.id, semester=4)

        # Create Exam
        exam = ExamService.create_exam({
            "subject_id": subj.id,
            "exam_code": "EXAM-ME401",
            "title": "Thermodynamics Exam",
            "exam_date": "2026-11-22",
            "start_time": "14:00:00",
            "end_time": "17:00:00",
            "session_name": "AFTERNOON",
        })

        # Create Room
        room = RoomService.create_room({
            "room_number": "201",
            "building": "Mech Block",
            "floor": 2,
            "rows_count": 3,
            "columns_count": 3,
            "actual_capacity": 9,
        })

        # Create Teacher 1 (Requester)
        t1 = TeacherService.create_teacher({
            "first_name": "Suresh",
            "last_name": "Patil",
            "email": "suresh.patil@poly.edu",
            "username": "suresh_p",
            "password": "Password123!",
            "department_id": dept.id,
            "employee_id": "EMP-ME-01",
            "designation": "Lecturer",
            "max_duties": 5,
        })

        # Create Teacher 2 (Target for duty swap)
        t2 = TeacherService.create_teacher({
            "first_name": "Amit",
            "last_name": "Kulkarni",
            "email": "amit.kulkarni@poly.edu",
            "username": "amit_k",
            "password": "Password123!",
            "department_id": dept.id,
            "employee_id": "EMP-ME-02",
            "designation": "Lecturer",
            "max_duties": 5,
        })

        # Assign Teacher 1 to Exam Invigilation
        duty = InvigilationDuty(
            exam_id=exam.id,
            teacher_id=t1.id,
            room_id=room.id,
            duty_role="CHIEF_INVIGILATOR",
            status="ASSIGNED",
        )
        db.session.add(duty)
        db.session.commit()
        duty_id = duty.id
        t2_id = t2.id

    # 1. Login as Teacher 1
    login_res = login_client(client, "suresh_p", "Password123!")
    assert login_res.status_code == 200

    # 2. GET /api/teacher/profile
    profile_res = client.get("/api/teacher/profile")
    assert profile_res.status_code == 200
    p_data = profile_res.get_json()["data"]
    assert p_data["employee_id"] == "EMP-ME-01"
    assert p_data["first_name"] == "Suresh"

    # 3. GET /api/teacher/duties
    duties_res = client.get("/api/teacher/duties")
    assert duties_res.status_code == 200
    d_data = duties_res.get_json()["data"]
    assert len(d_data) == 1
    assert d_data[0]["exam_code"] == "EXAM-ME401"
    assert d_data[0]["room_number"] == "201"

    # 4. POST /api/teacher/availability
    avail_res = client.post(
        "/api/teacher/availability",
        json={
            "date": "2026-11-25",
            "time_slot": "MORNING",
            "is_available": False,
            "reason": "Attending university workshop",
        },
    )
    assert avail_res.status_code == 201
    assert avail_res.get_json()["data"]["is_available"] is False

    # 5. GET /api/teacher/colleagues (Should include Teacher 2, exclude Teacher 1)
    colleagues_res = client.get("/api/teacher/colleagues")
    assert colleagues_res.status_code == 200
    c_data = colleagues_res.get_json()["data"]
    assert len(c_data) == 1
    assert c_data[0]["id"] == t2_id
    assert c_data[0]["employee_id"] == "EMP-ME-02"

    # 6. POST /api/teacher/duty-swap
    swap_res = client.post(
        "/api/teacher/duty-swap",
        json={
            "duty_id": duty_id,
            "target_teacher_id": t2_id,
            "reason": "Personal medical appointment",
        },
    )
    assert swap_res.status_code == 201
    s_data = swap_res.get_json()["data"]
    assert s_data["status"] == "PENDING"
    assert s_data["reason"] == "Personal medical appointment"

    # 7. GET /api/teacher/duty-swaps
    swaps_res = client.get("/api/teacher/duty-swaps")
    assert swaps_res.status_code == 200
    swaps_data = swaps_res.get_json()["data"]
    assert len(swaps_data["sent"]) == 1
    assert swaps_data["sent"][0]["target_teacher_id"] == t2_id

    # 8. Check Notifications received by Teacher 2
    login_client(client, "amit_k", "Password123!")
    t2_notif_res = client.get("/api/teacher/notifications")
    assert t2_notif_res.status_code == 200
    t2_notifs = t2_notif_res.get_json()["data"]
    assert len(t2_notifs) >= 1
    assert any("Duty Swap Request Received" in n["title"] for n in t2_notifs)
    client.post("/api/auth/logout")


def test_portal_rbac_security_isolation(app):
    """
    Verify security isolation:
    - 401 Unauthorized for unauthenticated calls
    - 403 Forbidden for cross-portal role access
    """
    client = app.test_client()
    with app.app_context():
        dept = AcademicService.create_department(code="EE", name="Electrical Engineering")

        StudentService.create_student({
            "first_name": "Anil",
            "last_name": "Kumar",
            "email": "anil.k@poly.edu",
            "username": "anil_k",
            "password": "Password123!",
            "department_id": dept.id,
            "roll_number": "EE201",
            "enrollment_number": "ENR-EE-201",
            "semester": 2,
            "division": "A",
            "academic_year": "2026-2027",
        })

        TeacherService.create_teacher({
            "first_name": "Pooja",
            "last_name": "Deshmukh",
            "email": "pooja.d@poly.edu",
            "username": "pooja_d",
            "password": "Password123!",
            "department_id": dept.id,
            "employee_id": "EMP-EE-01",
            "designation": "HOD",
            "max_duties": 8,
        })

    # Unauthenticated student profile -> 401
    res = client.get("/api/student/profile")
    assert res.status_code == 401

    # Unauthenticated teacher profile -> 401
    res = client.get("/api/teacher/profile")
    assert res.status_code == 401

    # Login as Student -> Forbidden on Teacher Portal
    login_client(client, "anil_k", "Password123!")
    forbidden_res = client.get("/api/teacher/profile")
    assert forbidden_res.status_code == 403
    assert "TEACHER" in forbidden_res.get_json()["message"]

    # Login as Teacher -> Forbidden on Student Portal
    login_client(client, "pooja_d", "Password123!")
    forbidden_res2 = client.get("/api/student/profile")
    assert forbidden_res2.status_code == 403
    assert "STUDENT" in forbidden_res2.get_json()["message"]
