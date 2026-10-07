"""
Phase 19 End-to-End System Integration Test Suite.
Verifies the complete, unified institutional workflow across all 19 phases:
1. Admin Authentication & Session Management
2. Polytechnic Department, Subject, and Room Setup (with Coordinate Seat Grids)
3. Faculty & Student Profile Provisioning with RBAC
4. Examination Timetable Creation & Candidate Registration
5. Seating Arrangement Generation, 2D Grid Visual Matrix, and Publication
6. Invigilation Assignment
7. Student Portal Access (Timetable, Hall Ticket Seat, Notifications, Kiosk Lookup)
8. Teacher Portal Access (Duties, Availability Submission)
9. Official Institutional Document Exports (PDF & Excel Seating Charts, Notices, Attendance, Rosters)
10. Administrative Announcements Broadcast & Compliance Audit Trail Logging
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
from app.models.audit_log import AuditLog

from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.room_service import RoomService
from app.services.teacher_service import TeacherService
from app.services.student_service import StudentService
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
    """Clean all tables before each test to ensure test isolation."""
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
        AuditLog.query.delete()
        User.query.delete()
        db.session.commit()
        db.session.remove()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


def login_client(client, username, password):
    """Helper to log in via Flask test client session."""
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_complete_polytechnic_system_lifecycle_e2e(client, app):
    """
    Executes the entire end-to-end examination management lifecycle.
    """
    # -------------------------------------------------------------------------
    # STEP 1: Administrative Account Setup & Authentication
    # -------------------------------------------------------------------------
    with app.app_context():
        AuthService.create_user("admin_e2e", "admin.e2e@poly.edu", "AdminPass123!", role="ADMIN")

    login_res = login_client(client, "admin_e2e", "AdminPass123!")
    assert login_res.status_code == 200
    assert login_res.get_json()["data"]["user"]["role"] == "ADMIN"

    # -------------------------------------------------------------------------
    # STEP 2: Academic Master Setup (Department, Subject, Room Grid)
    # -------------------------------------------------------------------------
    # Create Department
    dept_res = client.post(
        "/api/departments",
        json={"code": "CO", "name": "Computer Engineering", "description": "Dept of Computer Engg"},
    )
    assert dept_res.status_code == 201
    dept_id = dept_res.get_json()["data"]["id"]

    # Create Subject (Semester 3)
    subj_res = client.post(
        "/api/subjects",
        json={
            "code": "22317",
            "name": "Data Structures Using C",
            "department_id": dept_id,
            "semester": 3,
            "scheme": "I-SCHEME",
            "credits": 5,
        },
    )
    assert subj_res.status_code == 201
    subj_id = subj_res.get_json()["data"]["id"]

    # Create Room with Automatic Coordinate Grid Seats (2 rows x 3 cols = 6 seats)
    room_res = client.post(
        "/api/rooms",
        json={
            "room_number": "LH-301",
            "building": "Main Block",
            "floor": 3,
            "rows_count": 2,
            "columns_count": 3,
            "capacity": 6,
        },
    )
    assert room_res.status_code == 201
    room_id = room_res.get_json()["data"]["id"]

    # Verify physical grid generation
    seats_res = client.get(f"/api/rooms/{room_id}/seats")
    assert seats_res.status_code == 200
    assert len(seats_res.get_json()["data"]) == 6

    # -------------------------------------------------------------------------
    # STEP 3: Faculty and Student Master Provisioning
    # -------------------------------------------------------------------------
    # Create Faculty
    teacher_res = client.post(
        "/api/teachers",
        json={
            "username": "prof_kulkarni",
            "email": "kulkarni@poly.edu",
            "password": "Password123!",
            "first_name": "Anand",
            "last_name": "Kulkarni",
            "department_id": dept_id,
            "employee_id": "EMP-CO-01",
            "designation": "HOD",
            "max_duties": 6,
        },
    )
    assert teacher_res.status_code == 201
    teacher_id = teacher_res.get_json()["data"]["id"]

    # Create 2 Students
    s1_res = client.post(
        "/api/students",
        json={
            "username": "stud_rahul",
            "email": "rahul@poly.edu",
            "password": "Password123!",
            "first_name": "Rahul",
            "last_name": "Sharma",
            "department_id": dept_id,
            "roll_number": "CO2401",
            "enrollment_number": "2400150001",
            "semester": 3,
            "division": "A",
            "academic_year": "2026-2027",
        },
    )
    assert s1_res.status_code == 201
    s1_id = s1_res.get_json()["data"]["id"]

    s2_res = client.post(
        "/api/students",
        json={
            "username": "stud_sneha",
            "email": "sneha@poly.edu",
            "password": "Password123!",
            "first_name": "Sneha",
            "last_name": "Patil",
            "department_id": dept_id,
            "roll_number": "CO2402",
            "enrollment_number": "2400150002",
            "semester": 3,
            "division": "A",
            "academic_year": "2026-2027",
        },
    )
    assert s2_res.status_code == 201
    s2_id = s2_res.get_json()["data"]["id"]

    # -------------------------------------------------------------------------
    # STEP 4: Exam Scheduling and Candidate Registration
    # -------------------------------------------------------------------------
    exam_res = client.post(
        "/api/exams",
        json={
            "subject_id": subj_id,
            "exam_code": "EXAM-W26-22317",
            "title": "Data Structures Exam",
            "exam_date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "13:00:00",
            "session_name": "MORNING",
        },
    )
    assert exam_res.status_code == 201
    exam_id = exam_res.get_json()["data"]["id"]

    # Register candidates
    reg1_res = client.post(
        f"/api/exams/{exam_id}/registrations",
        json={"student_id": s1_id},
    )
    assert reg1_res.status_code == 201

    reg2_res = client.post(
        f"/api/exams/{exam_id}/registrations",
        json={"student_id": s2_id},
    )
    assert reg2_res.status_code == 201

    # -------------------------------------------------------------------------
    # STEP 5: Seating Generation, Visual 2D Matrix, and Publication
    # -------------------------------------------------------------------------
    gen_res = client.post(
        "/api/planning/seating/generate",
        json={"exam_id": exam_id, "room_ids": [room_id]},
    )
    assert gen_res.status_code == 201
    plan_id = gen_res.get_json()["data"]["id"]

    # Retrieve visual 2D seating layout grid
    matrix_res = client.get(f"/api/planning/seating/{plan_id}/matrix/{room_id}")
    assert matrix_res.status_code == 200
    m_data = matrix_res.get_json()["data"]
    assert len(m_data["matrix"]) == 2  # 2 rows
    assert len(m_data["matrix"][0]) == 3  # 3 columns
    assert m_data["summary"]["allocated_count"] == 2

    # Publish Seating Plan
    pub_res = client.post(f"/api/planning/seating/{plan_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.get_json()["data"]["status"] == "PUBLISHED"

    # Assign Invigilator
    with app.app_context():
        duty = InvigilationDuty(
            exam_id=exam_id,
            teacher_id=teacher_id,
            room_id=room_id,
            duty_role="CHIEF_INVIGILATOR",
            status="ASSIGNED",
        )
        db.session.add(duty)
        db.session.commit()

    # Logout Admin
    client.post("/api/auth/logout")

    # -------------------------------------------------------------------------
    # STEP 6: Student Dedicated Portal Experience
    # -------------------------------------------------------------------------
    login_client(client, "stud_rahul", "Password123!")

    # Profile
    p_res = client.get("/api/student/profile")
    assert p_res.status_code == 200
    assert p_res.get_json()["data"]["roll_number"] == "CO2401"

    # Timetable
    tt_res = client.get("/api/student/timetable")
    assert tt_res.status_code == 200
    assert len(tt_res.get_json()["data"]) == 1

    # Allocated Seat
    my_seat_res = client.get("/api/student/my-seat")
    assert my_seat_res.status_code == 200
    s_data = my_seat_res.get_json()["data"]
    assert len(s_data) == 1
    assert s_data[0]["room_number"] == "LH-301"

    # Notification received for seating publish
    s_notif_res = client.get("/api/student/notifications")
    assert s_notif_res.status_code == 200
    assert len(s_notif_res.get_json()["data"]) >= 1

    client.post("/api/auth/logout")

    # Public Kiosk lookup (Unauthenticated)
    kiosk_res = client.get("/api/student/seat-search?roll_number=CO2401")
    assert kiosk_res.status_code == 200
    assert kiosk_res.get_json()["data"][0]["room_number"] == "LH-301"

    # -------------------------------------------------------------------------
    # STEP 7: Teacher Dedicated Portal Experience
    # -------------------------------------------------------------------------
    login_client(client, "prof_kulkarni", "Password123!")

    # Check Assigned Duties
    duties_res = client.get("/api/teacher/duties")
    assert duties_res.status_code == 200
    assert len(duties_res.get_json()["data"]) == 1
    assert duties_res.get_json()["data"][0]["room_number"] == "LH-301"

    # Submit Session Availability / Leave
    avail_res = client.post(
        "/api/teacher/availability",
        json={
            "date": "2026-11-25",
            "time_slot": "AFTERNOON",
            "is_available": False,
            "reason": "Department review meeting",
        },
    )
    assert avail_res.status_code == 201

    client.post("/api/auth/logout")

    # -------------------------------------------------------------------------
    # STEP 8: Official Institutional Document Exports (Member 4 Gateway)
    # -------------------------------------------------------------------------
    login_client(client, "admin_e2e", "AdminPass123!")

    # PDF Master Seating Chart
    pdf_chart = client.get(f"/api/reports/seating-chart/{plan_id}?format=pdf")
    assert pdf_chart.status_code == 200
    assert pdf_chart.mimetype == "application/pdf"
    assert pdf_chart.data.startswith(b"%PDF")

    # Excel Master Seating Chart
    excel_chart = client.get(f"/api/reports/seating-chart/{plan_id}?format=excel")
    assert excel_chart.status_code == 200
    assert "spreadsheetml.sheet" in excel_chart.mimetype

    # Room Door Notice PDF
    room_notice = client.get(f"/api/reports/room-notice/{plan_id}/{room_id}?format=pdf")
    assert room_notice.status_code == 200
    assert room_notice.mimetype == "application/pdf"

    # Attendance Sheet PDF
    att_sheet = client.get(f"/api/reports/attendance-sheet/{plan_id}/{room_id}?format=pdf")
    assert att_sheet.status_code == 200
    assert att_sheet.mimetype == "application/pdf"

    # -------------------------------------------------------------------------
    # STEP 9: Institutional Announcements Broadcast & Audit Trail
    # -------------------------------------------------------------------------
    # Broadcast alert to all students
    bc_res = client.post(
        "/api/notifications/broadcast",
        json={
            "title": "Exam Room Guidelines",
            "message": "Report 15 minutes before exam start.",
            "target_role": "STUDENT",
        },
    )
    assert bc_res.status_code == 201

    # Check Forensic Audit Trail
    audit_res = client.get("/api/audit-logs")
    assert audit_res.status_code == 200
    assert audit_res.get_json()["data"]["pagination"]["total"] >= 10

    # Check Audit Summary Metrics
    summary_res = client.get("/api/audit-logs/summary")
    assert summary_res.status_code == 200
    assert summary_res.get_json()["data"]["total_logs"] >= 10

    client.post("/api/auth/logout")
