"""
Phase 17 Database Seeder Test Suite.
Verifies the execution, integrity, and idempotency of the realistic
Polytechnic Database Seeder (`seed.py`).
"""

import pytest
from app import create_app
from app.extensions import db
from app.models.department import Department
from app.models.subject import Subject
from app.models.room import Room
from app.models.seat import Seat
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.exam import Exam
from app.models.registration import Registration
from app.models.seating_plan import SeatingPlan
from app.models.seat_allocation import SeatAllocation
from app.models.invigilation_duty import InvigilationDuty
from app.models.duty_swap import DutySwap
from app.models.teacher_availability import TeacherAvailability
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from seed import run_seeder


@pytest.fixture(scope="module")
def app():
    """Create and configure a testing Flask app instance."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def test_polytechnic_database_seeder_workflow(app):
    """
    Executes the seeder and verifies that all polytechnic academic entities,
    rooms, grids, faculty, students, exams, seating plans, invigilations,
    and notifications are correctly populated and consistent.
    """
    with app.app_context():
        # 1. Execute seeder with reset
        run_seeder(reset=True)

        # 2. Verify Departments
        departments = Department.query.all()
        dept_codes = {d.code for d in departments}
        assert len(departments) == 6
        assert {"CO", "IT", "ME", "CE", "EE", "EJ"}.issubset(dept_codes)

        # 3. Verify Subjects strictly within Semesters 1 to 6
        subjects = Subject.query.all()
        assert len(subjects) >= 20
        for subj in subjects:
            assert 1 <= subj.semester <= 6

        # 4. Verify Examination Halls and coordinate seat grids
        rooms = Room.query.all()
        assert len(rooms) >= 6
        total_seats = Seat.query.count()
        assert total_seats >= 180
        # Check coordinate format of seats
        sample_seats = Seat.query.limit(10).all()
        for s in sample_seats:
            assert s.seat_number.startswith(f"R{s.row_num}-C{s.col_num}")

        # 5. Verify Teachers & Availability
        teachers = Teacher.query.all()
        assert len(teachers) == 10
        availabilities = TeacherAvailability.query.all()
        assert len(availabilities) >= 1
        assert any(a.is_available is False for a in availabilities)

        # 6. Verify Students & Diploma Semesters
        students = Student.query.all()
        assert len(students) >= 15
        for st in students:
            assert 1 <= st.semester <= 6
            assert st.roll_number is not None
            assert st.enrollment_number is not None

        # 7. Verify Exams & Candidate Registrations
        exams = Exam.query.all()
        assert len(exams) >= 4
        registrations = Registration.query.all()
        assert len(registrations) >= 20

        # 8. Verify Seating Plans and published allocations
        plans = SeatingPlan.query.all()
        assert len(plans) >= 2
        published_plan = SeatingPlan.query.filter_by(status="PUBLISHED").first()
        assert published_plan is not None
        assert published_plan.allocations.count() > 0

        # 9. Verify Invigilation Duty and Duty Swap Request
        duties = InvigilationDuty.query.all()
        assert len(duties) >= 1
        swaps = DutySwap.query.all()
        assert len(swaps) >= 1
        assert swaps[0].status == "PENDING"

        # 10. Verify Notifications & System Audit Trail
        notifications = Notification.query.all()
        assert len(notifications) >= 30
        audit_logs = AuditLog.query.all()
        assert len(audit_logs) >= 50

        # 11. Verify Seeder Idempotency
        # Running without reset must detect existing data and preserve database state
        initial_dept_count = len(departments)
        run_seeder(reset=False)
        assert Department.query.count() == initial_dept_count
