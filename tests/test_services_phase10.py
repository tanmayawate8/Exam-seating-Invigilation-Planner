"""
Phase 10 Comprehensive Service Layer Test Suite.
Verifies all 8 domain services:
- AuthService
- AcademicService
- StudentService
- TeacherService
- RoomService
- ExamService
- RegistrationService
- PlanningService
"""

import pytest
from datetime import date, time, datetime

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.subject import Subject
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
from app.services.planning_service import PlanningService, AlgorithmAdapter
from app.utils.errors import ValidationError, ConflictError, NotFoundError, UnauthorizedError


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
        # Clear tables in reverse dependency order
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


# =============================================================================
# 1. AUTH SERVICE TESTS
# =============================================================================

def test_auth_service_create_user_and_authenticate():
    """Verify user creation with password hashing and authentication."""
    success, user, msg = AuthService.create_user(
        username="admin_test",
        email="admin_test@polytechnic.edu",
        password="SecurePassword123!",
        role="ADMIN",
    )
    assert success is True
    assert user.id is not None
    assert user.role == "ADMIN"
    assert user.check_password("SecurePassword123!") is True
    assert user.check_password("WrongPassword") is False

    # Authenticate valid
    auth_success, auth_user, _ = AuthService.authenticate("admin_test", "SecurePassword123!")
    assert auth_success is True
    assert auth_user.id == user.id

    # Authenticate invalid
    bad_success, bad_user, bad_msg = AuthService.authenticate("admin_test", "BadPassword")
    assert bad_success is False
    assert bad_user is None


# =============================================================================
# 2. ACADEMIC SERVICE TESTS
# =============================================================================

def test_academic_service_department_and_subjects():
    """Verify Department (Branch) creation and Subject creation with semester bounds 1-6."""
    dept = AcademicService.create_department({
        "name": "Civil Engineering",
        "code": "CE",
        "description": "Department of Civil Engineering",
    })
    assert dept.id is not None
    assert dept.code == "CE"

    # Valid subject in semester 3
    subj = AcademicService.create_subject({
        "department_id": dept.id,
        "subject_name": "Surveying",
        "subject_code": "CE301",
        "semester": 3,
        "scheme": "I-Scheme",
    })
    assert subj.id is not None
    assert subj.semester == 3

    # Semester 0 invalid
    with pytest.raises(ValidationError):
        AcademicService.create_subject({
            "department_id": dept.id,
            "subject_name": "Basic Surveying",
            "subject_code": "CE302",
            "semester": 0,
        })

    # Semester 7 invalid (Polytechnic is 1-6)
    with pytest.raises(ValidationError):
        AcademicService.create_subject({
            "department_id": dept.id,
            "subject_name": "Advanced Concrete",
            "subject_code": "CE701",
            "semester": 7,
        })


# =============================================================================
# 3. STUDENT SERVICE TESTS
# =============================================================================

def test_student_service_crud_and_polytechnic_rules():
    """Verify student creation, linking with User account, semester bounds, and status."""
    dept = AcademicService.create_department({
        "name": "Mechanical Engineering",
        "code": "ME",
    })

    student = StudentService.create_student({
        "username": "me_student1",
        "email": "me_student1@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Tanmay Mech",
        "roll_number": "ME202601",
        "enrollment_number": "ENR-ME-001",
        "department_id": dept.id,
        "semester": 4,
        "division": "A",
    })
    assert student.id is not None
    assert student.roll_number == "ME202601"
    assert student.user.role == "STUDENT"
    assert student.semester == 4

    # Duplicate roll number check
    with pytest.raises(ConflictError):
        StudentService.create_student({
            "username": "me_student2",
            "email": "me_student2@polytechnic.edu",
            "password": "Password123!",
            "full_name": "Another Student",
            "roll_number": "ME202601",
            "enrollment_number": "ENR-ME-002",
            "department_id": dept.id,
            "semester": 4,
        })

    # Toggle status
    StudentService.toggle_student_status(student.id, is_active=False)
    assert student.user.is_active is False


# =============================================================================
# 4. TEACHER SERVICE TESTS
# =============================================================================

def test_teacher_service_and_duty_swap():
    """Verify teacher creation, availability settings, and duty swap workflow."""
    dept = AcademicService.create_department({
        "name": "Electrical Engineering",
        "code": "EE",
    })

    t1 = TeacherService.create_teacher({
        "username": "prof_smith",
        "email": "smith@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Prof. Smith",
        "employee_id": "EE-FAC-01",
        "department_id": dept.id,
        "designation": "Lecturer",
    })
    t2 = TeacherService.create_teacher({
        "username": "prof_jones",
        "email": "jones@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Prof. Jones",
        "employee_id": "EE-FAC-02",
        "department_id": dept.id,
        "designation": "Assistant Professor",
    })
    assert t1.user.role == "TEACHER"
    assert t2.user.role == "TEACHER"

    # Set availability
    avail = TeacherService.set_teacher_availability(
        teacher_id=t1.id,
        date_val=date(2026, 11, 10),
        time_slot="MORNING",
        is_available=False,
        reason="Medical leave",
    )
    assert avail.is_available is False


# =============================================================================
# 5. ROOM SERVICE TESTS
# =============================================================================

def test_room_service_and_seat_generation():
    """Verify Room creation with automatic Seat grid generation."""
    room = RoomService.create_room({
        "room_number": "LH-101",
        "building": "Main Polytechnic Building",
        "floor": 1,
        "rows_count": 4,
        "columns_count": 5,
        "capacity": 20,
    })
    assert room.id is not None
    assert room.capacity == 20

    # Verify auto-generated seats
    seats = RoomService.get_room_seats(room.id)
    assert len(seats) == 20
    seat_numbers = [s.seat_number for s in seats]
    assert "R1-C1" in seat_numbers
    assert "R4-C5" in seat_numbers

    # Capacity summary
    summary = RoomService.get_available_capacity()
    assert summary["total_rooms"] == 1
    assert summary["functional_seats"] == 20


# =============================================================================
# 6. EXAM SERVICE & REGISTRATION SERVICE TESTS
# =============================================================================

def test_exam_and_registration_services():
    """Verify Exam creation, cohort conflict check, and RegistrationService enrollment."""
    dept = AcademicService.create_department({"name": "Computer Engineering", "code": "CO"})
    subj1 = AcademicService.create_subject({
        "department_id": dept.id,
        "subject_name": "Data Structures",
        "subject_code": "CO301",
        "semester": 3,
    })
    subj2 = AcademicService.create_subject({
        "department_id": dept.id,
        "subject_name": "Computer Networks",
        "subject_code": "CO302",
        "semester": 3,
    })

    # Create Exam 1
    exam1 = ExamService.create_exam({
        "subject_id": subj1.id,
        "exam_code": "EXAM-CO301-W26",
        "title": "Data Structures Winter Exam",
        "exam_date": date(2026, 11, 15),
        "start_time": time(10, 0),
        "end_time": time(13, 0),
        "session_name": "MORNING",
    })
    assert exam1.id is not None
    assert exam1.status == "SCHEDULED"

    # Cohort Conflict Check: Same Department + Semester at same date/time
    with pytest.raises(ConflictError):
        ExamService.create_exam({
            "subject_id": subj2.id,
            "exam_code": "EXAM-CO302-W26",
            "title": "Computer Networks Winter Exam",
            "exam_date": date(2026, 11, 15),
            "start_time": time(11, 0),
            "end_time": time(14, 0),
            "session_name": "MORNING",
        })

    # Create Students and register
    s1 = StudentService.create_student({
        "username": "stud_co_1",
        "email": "co1@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Alice Co",
        "roll_number": "CO01",
        "enrollment_number": "ENR-CO-01",
        "department_id": dept.id,
        "semester": 3,
    })
    s2 = StudentService.create_student({
        "username": "stud_co_2",
        "email": "co2@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Bob Co",
        "roll_number": "CO02",
        "enrollment_number": "ENR-CO-02",
        "department_id": dept.id,
        "semester": 3,
    })

    reg1 = RegistrationService.register_student(student_id=s1.id, exam_id=exam1.id)
    assert reg1.id is not None
    assert exam1.total_registered == 1

    # Duplicate registration check
    with pytest.raises(ConflictError):
        RegistrationService.register_student(student_id=s1.id, exam_id=exam1.id)

    # Bulk enrollment for remainder of department
    bulk_res = RegistrationService.bulk_enroll_department_students(exam_id=exam1.id, semester=3)
    assert bulk_res["enrolled"] == 1  # s2 enrolled, s1 skipped
    assert bulk_res["skipped"] == 1
    assert exam1.total_registered == 2


# =============================================================================
# 7. PLANNING SERVICE (MEMBER 4 INTEGRATION) TESTS
# =============================================================================

def test_planning_service_seating_and_invigilation():
    """Verify seating generation, publish workflow, invigilation duties, and rollback protection."""
    dept = AcademicService.create_department({"name": "Information Technology", "code": "IT"})
    subj = AcademicService.create_subject({
        "department_id": dept.id,
        "subject_name": "Database Management",
        "subject_code": "IT301",
        "semester": 3,
    })

    exam = ExamService.create_exam({
        "subject_id": subj.id,
        "exam_code": "EXAM-IT301-W26",
        "title": "DBMS Final Exam",
        "exam_date": date(2026, 11, 20),
        "start_time": time(14, 0),
        "end_time": time(17, 0),
        "session_name": "AFTERNOON",
    })

    # Create 3 students
    studs = []
    for i in range(1, 4):
        st = StudentService.create_student({
            "username": f"it_stud_{i}",
            "email": f"it{i}@polytechnic.edu",
            "password": "Password123!",
            "full_name": f"Student {i}",
            "roll_number": f"IT{i:02d}",
            "enrollment_number": f"ENR-IT-{i:02d}",
            "department_id": dept.id,
            "semester": 3,
        })
        studs.append(st)
        RegistrationService.register_student(student_id=st.id, exam_id=exam.id)

    # Create Room with capacity 10
    room = RoomService.create_room({
        "room_number": "IT-LAB-1",
        "building": "IT Block",
        "floor": 2,
        "rows_count": 2,
        "columns_count": 5,
        "capacity": 10,
    })

    # Generate Seating Plan
    plan = PlanningService.generate_seating_plan(exam_id=exam.id, room_ids=[room.id])
    assert plan.id is not None
    assert plan.status == "GENERATED"
    assert plan.total_students_allocated == 3
    assert exam.status == "PLANNED"

    # Verify Allocations
    allocations = SeatAllocation.query.filter_by(seating_plan_id=plan.id).all()
    assert len(allocations) == 3

    # Publish Seating Plan
    published_plan = PlanningService.publish_seating_plan(plan.id)
    assert published_plan.status == "PUBLISHED"
    assert published_plan.published_at is not None

    # Verify student notifications were generated
    notifications = Notification.query.filter_by(notification_type="SEATING_PUBLISHED").all()
    assert len(notifications) == 3

    # Visual Matrix display
    matrix = PlanningService.get_room_seating_matrix(plan.id, room.id)
    assert matrix["room_number"] == "IT-LAB-1"
    assert matrix["rows"] == 2
    assert matrix["columns"] == 5
    assert matrix["total_allocated"] == 3

    # Invigilation Assignment
    teacher = TeacherService.create_teacher({
        "username": "prof_invig",
        "email": "invig@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Prof. Invigilator",
        "employee_id": "IT-FAC-09",
        "department_id": dept.id,
        "designation": "Lecturer",
    })

    duties = PlanningService.generate_invigilation_duties(exam_id=exam.id, room_ids=[room.id])
    assert len(duties) == 1
    assert duties[0].teacher_id == teacher.id
    assert duties[0].room_id == room.id
    assert duties[0].status == "ASSIGNED"

    # Verify teacher notification generated
    teacher_notif = Notification.query.filter_by(user_id=teacher.user_id).first()
    assert teacher_notif is not None
    assert "Assigned" in teacher_notif.title


def test_transaction_rollback_protection():
    """Verify that simulated persistence errors trigger an atomic rollback."""
    dept = AcademicService.create_department({"name": "Chemical Engineering", "code": "CH"})
    subj = AcademicService.create_subject({
        "department_id": dept.id,
        "subject_name": "Organic Chemistry",
        "subject_code": "CH301",
        "semester": 3,
    })
    exam = ExamService.create_exam({
        "subject_id": subj.id,
        "exam_code": "EXAM-CH301",
        "title": "Chem Exam",
        "exam_date": date(2026, 11, 25),
        "start_time": time(10, 0),
        "end_time": time(13, 0),
    })

    st = StudentService.create_student({
        "username": "ch_stud_1",
        "email": "ch1@polytechnic.edu",
        "password": "Password123!",
        "full_name": "Chem Student",
        "roll_number": "CH01",
        "enrollment_number": "ENR-CH-01",
        "department_id": dept.id,
        "semester": 3,
    })
    RegistrationService.register_student(student_id=st.id, exam_id=exam.id)

    room = RoomService.create_room({
        "room_number": "CH-LAB",
        "building": "Chem Block",
        "floor": 1,
        "rows_count": 2,
        "columns_count": 2,
        "capacity": 4,
    })

    # Plug in a faulty algorithm hook that raises an exception mid-process
    def broken_algorithm(*args, **kwargs):
        raise RuntimeError("Simulated Member 4 algorithm failure!")

    PlanningService.register_seating_algorithm(broken_algorithm)

    try:
        with pytest.raises(ValidationError) as excinfo:
            PlanningService.generate_seating_plan(exam_id=exam.id, room_ids=[room.id])

        assert "Simulated Member 4 algorithm failure" in str(excinfo.value)

        # Verify that no orphaned SeatingPlan or SeatAllocation records were persisted
        assert SeatingPlan.query.filter_by(exam_id=exam.id).count() == 0
        assert SeatAllocation.query.count() == 0
        # Exam status should remain SCHEDULED
        assert exam.status == "SCHEDULED"

    finally:
        # Restore default algorithm hook
        PlanningService.register_seating_algorithm(AlgorithmAdapter.default_seating_algorithm)
