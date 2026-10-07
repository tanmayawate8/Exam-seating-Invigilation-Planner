"""
Phase 16 REST API Route Test Suite.
Tests endpoints for:
- Notification Management (/api/notifications)
  * GET /api/notifications (paginated & filterable by is_read)
  * GET /api/notifications/unread-count
  * PATCH /api/notifications/<id>/read
  * POST /api/notifications/mark-all-read
  * DELETE /api/notifications/<id>
  * POST /api/notifications/broadcast (Admin announcement broadcasting)
- System Audit Trail Management (/api/audit-logs)
  * GET /api/audit-logs (paginated, multi-attribute filterable)
  * GET /api/audit-logs/<id>
  * GET /api/audit-logs/summary
- Immutability & Strict RBAC Isolation:
  * Non-admins forbidden from broadcasting announcements (403)
  * Non-admins forbidden from reading audit logs (403)
  * Unauthenticated calls rejected (401)
  * Audit logs immutable (read-only endpoints)
"""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.department import Department
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService
from app.utils.audit import log_audit


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
        AuditLog.query.delete()
        Student.query.delete()
        Teacher.query.delete()
        Department.query.delete()
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


def test_notification_endpoints(client, app):
    """
    Verify full user notification lifecycle:
    - Listing notifications
    - Unread count badge
    - Marking single notification as read
    - Marking all as read
    - Notification deletion
    - Ownership boundary enforcement
    """
    with app.app_context():
        dept = AcademicService.create_department(code="CO", name="Computer Engineering")

        student = StudentService.create_student({
            "first_name": "Siddharth",
            "last_name": "Rao",
            "email": "sid.rao@poly.edu",
            "username": "sid_rao",
            "password": "Password123!",
            "department_id": dept.id,
            "roll_number": "CO101",
            "enrollment_number": "ENR-CO-101",
            "semester": 1,
            "division": "A",
            "academic_year": "2026-2027",
        })

        teacher = TeacherService.create_teacher({
            "first_name": "Meena",
            "last_name": "Iyer",
            "email": "meena.iyer@poly.edu",
            "username": "meena_i",
            "password": "Password123!",
            "department_id": dept.id,
            "employee_id": "EMP-CO-05",
            "designation": "Lecturer",
            "max_duties": 4,
        })

        # Create two notifications for student
        n1 = NotificationService.create_notification(
            user_id=student.user_id,
            title="Seating Allocation Published",
            message="Your seat is Room 101, Seat R1-C1.",
            notification_type="SEATING_PUBLISHED",
        )
        n2 = NotificationService.create_notification(
            user_id=student.user_id,
            title="Timetable Notice",
            message="Semester 1 exams commence on Nov 25.",
            notification_type="EXAM_UPDATE",
        )
        n1_id = n1.id
        n2_id = n2.id
        stud_uid = student.user_id

    # 1. Login as Student
    login_client(client, "sid_rao", "Password123!")

    # 2. GET /api/notifications
    list_res = client.get("/api/notifications")
    assert list_res.status_code == 200
    res_data = list_res.get_json()["data"]
    assert res_data["pagination"]["total"] == 2
    assert len(res_data["notifications"]) == 2

    # 3. GET /api/notifications/unread-count
    count_res = client.get("/api/notifications/unread-count")
    assert count_res.status_code == 200
    assert count_res.get_json()["data"]["unread_count"] == 2

    # 4. PATCH /api/notifications/<id>/read
    read_res = client.patch(f"/api/notifications/{n1_id}/read")
    assert read_res.status_code == 200
    assert read_res.get_json()["data"]["is_read"] is True

    # Check unread count is now 1
    count_res2 = client.get("/api/notifications/unread-count")
    assert count_res2.get_json()["data"]["unread_count"] == 1

    # 5. POST /api/notifications/mark-all-read
    mark_all_res = client.post("/api/notifications/mark-all-read")
    assert mark_all_res.status_code == 200
    assert mark_all_res.get_json()["data"]["updated_count"] == 1

    # Check unread count is now 0
    count_res3 = client.get("/api/notifications/unread-count")
    assert count_res3.get_json()["data"]["unread_count"] == 0

    # 6. DELETE /api/notifications/<id>
    del_res = client.delete(f"/api/notifications/{n1_id}")
    assert del_res.status_code == 200

    # Check listing now has 1 remaining notification
    list_res2 = client.get("/api/notifications")
    assert list_res2.get_json()["data"]["pagination"]["total"] == 1

    # 7. Ownership boundary: Teacher attempts to delete or read student's remaining notification
    login_client(client, "meena_i", "Password123!")
    unauth_read = client.patch(f"/api/notifications/{n2_id}/read")
    assert unauth_read.status_code == 403
    assert "belonging to another user" in unauth_read.get_json()["message"]

    unauth_del = client.delete(f"/api/notifications/{n2_id}")
    assert unauth_del.status_code == 403
    assert "belonging to another user" in unauth_del.get_json()["message"]


def test_notification_broadcast_workflow(client, app):
    """
    Verify administrator announcement broadcasting:
    - Admin broadcasts to targeted cohort ('STUDENT')
    - Eligible recipients receive notification
    - Non-targeted cohorts do not receive notification
    - Non-admin attempts to broadcast are blocked (403 Forbidden)
    """
    with app.app_context():
        dept = AcademicService.create_department(code="IT", name="Information Technology")
        AuthService.create_user("admin_broadcast", "admin.b@poly.edu", "AdminPass123!", role="ADMIN")

        # Create 2 students
        s1 = StudentService.create_student({
            "first_name": "Kavita",
            "last_name": "Joshi",
            "email": "kavita.j@poly.edu",
            "username": "kavita_j",
            "password": "Password123!",
            "department_id": dept.id,
            "roll_number": "IT201",
            "enrollment_number": "ENR-IT-201",
            "semester": 2,
            "division": "A",
            "academic_year": "2026-2027",
        })
        s2 = StudentService.create_student({
            "first_name": "Vikram",
            "last_name": "Singh",
            "email": "vikram.s@poly.edu",
            "username": "vikram_s",
            "password": "Password123!",
            "department_id": dept.id,
            "roll_number": "IT202",
            "enrollment_number": "ENR-IT-202",
            "semester": 2,
            "division": "A",
            "academic_year": "2026-2027",
        })

        # Create 1 teacher
        t1 = TeacherService.create_teacher({
            "first_name": "Rajesh",
            "last_name": "Verma",
            "email": "rajesh.v@poly.edu",
            "username": "rajesh_v",
            "password": "Password123!",
            "department_id": dept.id,
            "employee_id": "EMP-IT-01",
            "designation": "Assistant Professor",
            "max_duties": 6,
        })

    # 1. Login as Admin and send Broadcast to STUDENT cohort
    login_client(client, "admin_broadcast", "AdminPass123!")
    broadcast_res = client.post(
        "/api/notifications/broadcast",
        json={
            "title": "Winter Examination Advisory",
            "message": "All students must carry valid polytechnic identity cards.",
            "target_role": "STUDENT",
            "notification_type": "BROADCAST",
        },
    )
    assert broadcast_res.status_code == 201
    b_data = broadcast_res.get_json()["data"]
    assert b_data["recipients_count"] == 2
    assert b_data["target_role"] == "STUDENT"

    # 2. Student 1 checks notifications
    login_client(client, "kavita_j", "Password123!")
    s1_notifs = client.get("/api/notifications").get_json()["data"]["notifications"]
    assert len(s1_notifs) == 1
    assert s1_notifs[0]["title"] == "Winter Examination Advisory"

    # 3. Student 2 checks notifications
    login_client(client, "vikram_s", "Password123!")
    s2_notifs = client.get("/api/notifications").get_json()["data"]["notifications"]
    assert len(s2_notifs) == 1
    assert s2_notifs[0]["title"] == "Winter Examination Advisory"

    # 4. Teacher checks notifications (should NOT receive student-targeted broadcast)
    login_client(client, "rajesh_v", "Password123!")
    t_notifs = client.get("/api/notifications").get_json()["data"]["notifications"]
    assert len(t_notifs) == 0

    # 5. Non-admin student attempts to broadcast -> 403 Forbidden
    login_client(client, "kavita_j", "Password123!")
    forbidden_bc = client.post(
        "/api/notifications/broadcast",
        json={
            "title": "Spam Notice",
            "message": "This should be denied.",
            "target_role": "ALL",
        },
    )
    assert forbidden_bc.status_code == 403
    client.post("/api/auth/logout")


def test_audit_logs_endpoints_and_rbac(app):
    """
    Verify system audit trail queries, summary calculations, and strict security:
    - Admin can inspect paginated audit logs
    - Filtering by action and entity_type
    - Audit summary statistics
    - Non-admin (Student/Teacher) access denied (403)
    - Unauthenticated access denied (401)
    - Immutability check: No modification or deletion endpoints
    """
    client = app.test_client()

    with app.app_context():
        _, admin, _ = AuthService.create_user("admin_audit", "admin.audit@poly.edu", "AdminPass123!", role="ADMIN")
        _, student, _ = AuthService.create_user("student_audit", "stud.audit@poly.edu", "StudPass123!", role="STUDENT")

        # Create several realistic audit events
        log_audit(
            action="LOGIN_SUCCESS",
            entity_type="User",
            entity_id=str(admin.id),
            user_id=admin.id,
            details="Admin logged in from polytechnic console.",
            ip_address="192.168.1.10",
        )
        log_audit(
            action="SEATING_PLAN_GENERATED",
            entity_type="SeatingPlan",
            entity_id="101",
            user_id=admin.id,
            details="Generated seating arrangement for Exam EXAM-CO101.",
            ip_address="192.168.1.10",
        )
        log_audit(
            action="SEATING_PUBLISHED",
            entity_type="SeatingPlan",
            entity_id="101",
            user_id=admin.id,
            details="Published seating plan #101.",
            ip_address="192.168.1.10",
        )
        log_audit(
            action="FORBIDDEN_ACCESS_ATTEMPT",
            entity_type="Endpoint",
            entity_id="admin_console",
            user_id=student.id,
            details="Unauthorized attempt to access administrative console.",
            ip_address="192.168.1.25",
        )

    # 1. Unauthenticated request to /api/audit-logs -> 401
    anon_res = client.get("/api/audit-logs")
    assert anon_res.status_code == 401

    # 2. Non-admin (Student) request -> 403 Forbidden
    login_client(client, "student_audit", "StudPass123!")
    forbidden_res = client.get("/api/audit-logs")
    assert forbidden_res.status_code == 403

    forbidden_sum = client.get("/api/audit-logs/summary")
    assert forbidden_sum.status_code == 403

    # 3. Admin login
    login_client(client, "admin_audit", "AdminPass123!")

    # 4. GET /api/audit-logs
    logs_res = client.get("/api/audit-logs")
    assert logs_res.status_code == 200
    l_data = logs_res.get_json()["data"]
    assert l_data["pagination"]["total"] >= 4
    first_log_id = l_data["audit_logs"][0]["id"]

    # 5. Filter by action
    action_res = client.get("/api/audit-logs?action=SEATING_PUBLISHED")
    assert action_res.status_code == 200
    filtered_logs = action_res.get_json()["data"]["audit_logs"]
    assert len(filtered_logs) == 1
    assert filtered_logs[0]["action"] == "SEATING_PUBLISHED"

    # 6. Filter by search text
    search_res = client.get("/api/audit-logs?search=console")
    assert search_res.status_code == 200
    search_logs = search_res.get_json()["data"]["audit_logs"]
    assert len(search_logs) >= 2

    # 7. GET /api/audit-logs/<id>
    single_res = client.get(f"/api/audit-logs/{first_log_id}")
    assert single_res.status_code == 200
    assert single_res.get_json()["data"]["id"] == first_log_id

    # 8. GET /api/audit-logs/summary
    summary_res = client.get("/api/audit-logs/summary")
    assert summary_res.status_code == 200
    s_data = summary_res.get_json()["data"]
    assert s_data["total_logs"] >= 4
    assert s_data["security_alerts_count"] >= 1
    assert any(a["action"] == "FORBIDDEN_ACCESS_ATTEMPT" for a in s_data["recent_security_alerts"])

    # 9. Audit trail immutability: POST / DELETE on /api/audit-logs are rejected (405 Method Not Allowed)
    post_res = client.post("/api/audit-logs", json={"action": "TAMPER"})
    assert post_res.status_code == 405

    del_res = client.delete(f"/api/audit-logs/{first_log_id}")
    assert del_res.status_code == 405
