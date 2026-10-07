"""
Phase 18 REST API Route Test Suite.
Tests Member 4 Integration Gateway & Institutional Report Generation Endpoints:
- GET /api/reports/contracts (Data contract schema specs)
- GET /api/reports/seating-chart/<id> (PDF & Excel generation)
- GET /api/reports/room-notice/<plan_id>/<room_id> (PDF generation)
- GET /api/reports/attendance-sheet/<plan_id>/<room_id> (PDF & Excel generation)
- GET /api/reports/duty-roster/<exam_id> (PDF & Excel generation)
- RBAC isolation & error handling:
  * Unauthenticated access rejected (401)
  * Student access forbidden for admin/teacher reports (403)
  * Invalid report format rejected (400)
  * Non-existent entities return 404
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
        SeatAllocation.query.delete()
        SeatingPlan.query.delete()
        InvigilationDuty.query.delete()
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


def setup_reporting_data(app):
    """Sets up standard polytechnic test data for report generation tests."""
    with app.app_context():
        # 1. Users
        AuthService.create_user("admin_rep", "admin.rep@poly.edu", "AdminPass123!", role="ADMIN")
        AuthService.create_user("student_rep", "student.rep@poly.edu", "StudPass123!", role="STUDENT")

        # 2. Department & Subject
        dept = AcademicService.create_department(code="CO", name="Computer Engineering")
        subj = AcademicService.create_subject(code="CO301", name="Data Structures", department_id=dept.id, semester=3)

        # 3. Room & Seats
        room = RoomService.create_room({
            "room_number": "101",
            "building": "Main",
            "floor": 1,
            "rows_count": 3,
            "columns_count": 3,
            "actual_capacity": 9,
        })

        # 4. Teacher
        teacher = TeacherService.create_teacher({
            "username": "prof_rep",
            "email": "prof.rep@poly.edu",
            "password": "Password123!",
            "first_name": "Suresh",
            "last_name": "Patil",
            "department_id": dept.id,
            "employee_id": "EMP-CO-10",
            "designation": "Lecturer",
            "max_duties": 5,
        })

        # 5. Student
        student = StudentService.create_student({
            "username": "stud_rep_user",
            "email": "stud.rep.user@poly.edu",
            "password": "Password123!",
            "first_name": "Rahul",
            "last_name": "Sharma",
            "department_id": dept.id,
            "roll_number": "CO301",
            "enrollment_number": "ENR-CO-301",
            "semester": 3,
            "division": "A",
            "academic_year": "2026-2027",
        })

        # 6. Exam & Registration
        exam = ExamService.create_exam({
            "subject_id": subj.id,
            "exam_code": "EXAM-CO301",
            "title": "Data Structures Exam",
            "exam_date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "13:00:00",
            "session_name": "MORNING",
        })
        RegistrationService.register_student(student_id=student.id, exam_id=exam.id)

        # 7. Seating Plan & Publication
        plan = PlanningService.generate_seating_plan(exam.id, [room.id])
        PlanningService.publish_seating_plan(plan.id, operator_user_id=1)

        # 8. Invigilation Duty
        duty = InvigilationDuty(
            exam_id=exam.id,
            teacher_id=teacher.id,
            room_id=room.id,
            duty_role="CHIEF_INVIGILATOR",
            status="ASSIGNED",
        )
        db.session.add(duty)
        db.session.commit()

        return {
            "plan_id": plan.id,
            "room_id": room.id,
            "exam_id": exam.id,
            "teacher_id": teacher.id,
        }


def test_reports_contracts_spec_endpoint(client):
    """Verify /api/reports/contracts returns valid data contract schema specifications."""
    res = client.get("/api/reports/contracts")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["version"] == "1.0-polytechnic"
    assert "SeatingAlgorithmInput" in data["contracts"]
    assert "InvigilationAlgorithmInput" in data["contracts"]
    assert "ReportContracts" in data["contracts"]


def test_seating_chart_reports_pdf_and_excel(client, app):
    """Verify Master Seating Arrangement Chart generation in PDF and Excel formats."""
    data_ids = setup_reporting_data(app)
    login_client(client, "admin_rep", "AdminPass123!")

    # 1. PDF Seating Chart
    pdf_res = client.get(f"/api/reports/seating-chart/{data_ids['plan_id']}?format=pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.mimetype == "application/pdf"
    assert pdf_res.data.startswith(b"%PDF")
    assert "attachment; filename=" in pdf_res.headers.get("Content-Disposition", "")

    # 2. Excel Seating Chart
    excel_res = client.get(f"/api/reports/seating-chart/{data_ids['plan_id']}?format=excel")
    assert excel_res.status_code == 200
    assert "spreadsheetml.sheet" in excel_res.mimetype
    assert len(excel_res.data) > 1000
    assert "attachment; filename=" in excel_res.headers.get("Content-Disposition", "")


def test_room_notice_and_attendance_sheet_reports(client, app):
    """Verify Room Door Notices and Attendance Signature Sheets."""
    data_ids = setup_reporting_data(app)
    login_client(client, "admin_rep", "AdminPass123!")

    # 1. Room Notice PDF
    notice_res = client.get(f"/api/reports/room-notice/{data_ids['plan_id']}/{data_ids['room_id']}?format=pdf")
    assert notice_res.status_code == 200
    assert notice_res.mimetype == "application/pdf"
    assert notice_res.data.startswith(b"%PDF")

    # 2. Attendance Sheet PDF
    att_pdf = client.get(f"/api/reports/attendance-sheet/{data_ids['plan_id']}/{data_ids['room_id']}?format=pdf")
    assert att_pdf.status_code == 200
    assert att_pdf.mimetype == "application/pdf"
    assert att_pdf.data.startswith(b"%PDF")

    # 3. Attendance Sheet Excel
    att_excel = client.get(f"/api/reports/attendance-sheet/{data_ids['plan_id']}/{data_ids['room_id']}?format=excel")
    assert att_excel.status_code == 200
    assert "spreadsheetml.sheet" in att_excel.mimetype
    assert len(att_excel.data) > 1000


def test_duty_roster_reports(client, app):
    """Verify Faculty Invigilation Duty Roster generation in PDF and Excel formats."""
    data_ids = setup_reporting_data(app)
    # Teacher role is authorized to view duty roster
    login_client(client, "prof_rep", "Password123!")

    # 1. Duty Roster PDF
    roster_pdf = client.get(f"/api/reports/duty-roster/{data_ids['exam_id']}?format=pdf")
    assert roster_pdf.status_code == 200
    assert roster_pdf.mimetype == "application/pdf"
    assert roster_pdf.data.startswith(b"%PDF")

    # 2. Duty Roster Excel
    roster_excel = client.get(f"/api/reports/duty-roster/{data_ids['exam_id']}?format=excel")
    assert roster_excel.status_code == 200
    assert "spreadsheetml.sheet" in roster_excel.mimetype
    assert len(roster_excel.data) > 1000
    client.post("/api/auth/logout")


def test_reports_rbac_and_error_handling(app):
    """Verify security isolation and error conditions for report generation."""
    client = app.test_client()
    data_ids = setup_reporting_data(app)

    # 1. Unauthenticated request -> 401
    unauth_res = client.get(f"/api/reports/seating-chart/{data_ids['plan_id']}")
    assert unauth_res.status_code == 401

    # 2. Student accessing admin-only seating chart -> 403 Forbidden
    login_client(client, "student_rep", "StudPass123!")
    forbidden_res = client.get(f"/api/reports/seating-chart/{data_ids['plan_id']}")
    assert forbidden_res.status_code == 403

    # 3. Admin accessing with invalid format -> 400 Bad Request
    login_client(client, "admin_rep", "AdminPass123!")
    bad_fmt_res = client.get(f"/api/reports/seating-chart/{data_ids['plan_id']}?format=word")
    assert bad_fmt_res.status_code == 400
    assert "Unsupported report format" in bad_fmt_res.get_json()["message"]

    # 4. Non-existent seating plan -> 404 Not Found
    not_found_res = client.get("/api/reports/seating-chart/999999")
    assert not_found_res.status_code == 404
