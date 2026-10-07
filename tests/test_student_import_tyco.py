"""
Test Suite: Student Import Based on Official TYCO C Roll-Call Structure.
Verifies Excel/CSV import validation, duplicate detection, malformed row handling,
transaction rollback, password hashing, and Student Name + Enrollment Number authentication.
"""

import os
import io
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.department import Department
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.import_service import ImportService


@pytest.fixture
def app_instance():
    """Configures application with testing database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed Computer Engineering department
        dept = Department.query.filter_by(code="CO").first()
        if not dept:
            dept = Department(
                code="CO",
                name="Computer Engineering",
                description="Department of Computer Engineering",
            )
            db.session.add(dept)
            db.session.commit()

        # Seed admin user
        admin = User.query.filter_by(username="admin_import_tester").first()
        if not admin:
            _, admin, _ = AuthService.create_user(
                username="admin_import_tester",
                email="admin_import@polytechnic.ac.in",
                password="AdminPassword123!",
                role="ADMIN",
            )

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def admin_client(app_instance):
    client = app_instance.test_client()
    client.post("/api/auth/login", json={
        "username": "admin_import_tester",
        "password": "AdminPassword123!",
    })
    return client


# =============================================================================
# 1. TEMPLATE GENERATION TESTS
# =============================================================================

def test_import_template_downloads(admin_client):
    """Verifies that Excel and CSV import templates download with correct headers without ZPRN."""
    # Excel template
    res_excel = admin_client.get("/api/students/import/template?format=excel")
    assert res_excel.status_code == 200
    assert "spreadsheetml" in res_excel.content_type
    assert len(res_excel.data) > 0

    # CSV template
    res_csv = admin_client.get("/api/students/import/template?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    csv_text = res_csv.data.decode("utf-8-sig")
    assert "sr_no" in csv_text
    assert "enrollment_no" in csv_text
    # ZPRN removed
    assert "zprn" not in csv_text
    assert "Computer Engineering" in csv_text


# =============================================================================
# 2. VALIDATION & PREVIEW TESTS WITH TYCO C DATASET
# =============================================================================

def test_preview_with_tyco_c_sample_file(admin_client):
    """
    Tests preview parsing using the official TYCO C Roll-Call sample data.
    Verifies valid rows, batch separation (C1 and C2), duplicate enrollment handling,
    and handling of rows with blank contacts (Row 68).
    """
    csv_path = os.path.join("sample_data", "TYCO_C_Roll_Call_Sample.csv")
    assert os.path.exists(csv_path), "Sample CSV file must exist."

    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    data = {
        "file": (io.BytesIO(file_bytes), "TYCO_C_Roll_Call_Sample.csv")
    }
    res = admin_client.post(
        "/api/students/import/preview",
        data=data,
        content_type="multipart/form-data"
    )
    assert res.status_code == 200
    preview = res.get_json()["data"]

    assert preview["total_rows"] == 67
    assert preview["invalid_count"] == 0
    assert preview["valid_count"] == 67
    assert preview["duplicate_count"] == 0

    # Check first row (Batch C1)
    r1 = preview["rows"][0]
    assert r1["enrollment_no"] == "24252271491"
    assert r1["name"] == "ADHAV HARSH NIVRUTTI"
    assert r1["batch"] == "C1"
    assert r1["division"] == "C"
    assert r1["semester"] == 6
    assert r1["status"] == "VALID"

    # Check a row in Batch C2 (e.g. row 40, sr_no 40)
    r40 = [r for r in preview["rows"] if r["sr_no"] == 40][0]
    assert r40["batch"] == "C2"
    assert r40["status"] == "VALID"

    # Check row 68 (valid row with blank contact warning, Pawar Sandesh)
    r68 = [r for r in preview["rows"] if r["sr_no"] == 68][0]
    assert r68["status"] == "VALID"
    assert any("blank" in w.lower() for w in r68["warnings"])


# =============================================================================
# 3. COMMIT & ATOMIC TRANSACTION TESTS
# =============================================================================

def test_commit_student_import_and_account_creation(admin_client, app_instance):
    """
    Tests committing validated TYCO C student data into PostgreSQL.
    Verifies atomic creation of Student profiles and linked User accounts with hashed Enrollment No password.
    """
    students_to_commit = [
        {
            "sr_no": 1,
            "enrollment_no": "24252271491",
            "name": "ADHAV HARSH NIVRUTTI",
            "student_contact": "9623693560",
            "parent_contact_1": "9284720924",
            "parent_contact_2": "8805160997",
            "department_id": 1,
            "semester": 6,
            "division": "C",
            "batch": "C1",
            "academic_year": "2026-2027",
            "class_name": "TYCO",
        },
        {
            "sr_no": 36,
            "enrollment_no": "24252271613",
            "name": "SALUNKE AARYAN KAPIL",
            "student_contact": "9850000588",
            "parent_contact_1": "9850000588",
            "parent_contact_2": "7972101015",
            "department_id": 1,
            "semester": 6,
            "division": "C",
            "batch": "C2",
            "academic_year": "2026-2027",
            "class_name": "TYCO",
        },
    ]

    commit_res = admin_client.post("/api/students/import/commit", json={"rows": students_to_commit})
    assert commit_res.status_code == 201
    c_data = commit_res.get_json()["data"]
    assert c_data["imported_count"] == 2

    with app_instance.app_context():
        # Verify Student 1
        s1 = Student.query.filter_by(enrollment_number="24252271491").first()
        assert s1 is not None
        assert s1.name == "ADHAV HARSH NIVRUTTI"
        assert s1.batch == "C1"
        assert s1.division == "C"
        assert s1.semester == 6
        assert s1.class_name == "TYCO"
        assert s1.student_contact == "9623693560"

        # Verify linked User account
        u1 = s1.user
        assert u1 is not None
        assert u1.role == "STUDENT"
        assert u1.is_active is True
        assert u1.username == "24252271491"
        # Plaintext Enrollment Number must NEVER be stored in password hash
        assert u1.password_hash != "24252271491"
        assert u1.check_password("24252271491") is True

        # Verify Student 2 (Batch C2)
        s2 = Student.query.filter_by(enrollment_number="24252271613").first()
        assert s2 is not None
        assert s2.batch == "C2"
        assert s2.user.username == "24252271613"
        assert s2.user.check_password("24252271613") is True


# =============================================================================
# 4. STUDENT NAME + ENROLLMENT NUMBER LOGIN & DASHBOARD TESTS
# =============================================================================

def test_student_login_with_name_and_enrollment_no(admin_client, client):
    """
    Verifies that a student can authenticate using Student Name as identifier and Enrollment Number as password.
    Verifies that the Student Dashboard displays their academic profile while keeping parent contacts private.
    """
    # 1. Import a student
    student_data = [{
        "sr_no": 2,
        "enrollment_no": "24252271492",
        "name": "ANDHALE SHWETA SURYAKANT",
        "student_contact": "8856087006",
        "parent_contact_1": "9970009421",
        "parent_contact_2": "8856087006",
        "department_id": 1,
        "semester": 6,
        "division": "C",
        "batch": "C1",
        "academic_year": "2026-2027",
        "class_name": "TYCO",
    }]
    admin_client.post("/api/students/import/commit", json={"rows": student_data})

    # 2. Student logs in with Name + Password (Enrollment No)
    login_res = client.post("/api/auth/login", json={
        "name": "ANDHALE SHWETA SURYAKANT",
        "password": "24252271492",
    })
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True

    # 3. Student visits Student Portal Profile
    profile_res = client.get("/api/student/profile")
    assert profile_res.status_code == 200
    p_data = profile_res.get_json()["data"]

    assert p_data["name"] == "ANDHALE SHWETA SURYAKANT"
    assert p_data["enrollment_no"] == "24252271492"
    assert p_data["semester"] == 6
    assert p_data["division"] == "C"
    assert p_data["batch"] == "C1"
    assert p_data["class_name"] == "TYCO"
    assert p_data["academic_year"] == "2026-2027"

    # Privacy verification: parent contact numbers must NOT be exposed on student portal
    assert "parent_contact_1" not in p_data
    assert "parent_contact_2" not in p_data

    # 4. Student can also log in directly using Enrollment Number as both identifier and password
    alt_client = client.application.test_client()
    alt_login = alt_client.post("/api/auth/login", json={
        "username": "24252271492",
        "password": "24252271492",
    })
    assert alt_login.status_code == 200
    assert alt_login.get_json()["success"] is True


# =============================================================================
# 5. DUPLICATE NAME HANDLING & ENROLLMENT NUMBER IDENTITY RESOLUTION
# =============================================================================

def test_duplicate_name_handling_and_enrollment_no_identity_resolution(admin_client, app_instance):
    """
    Verifies Section 14:
    Multiple students can have the exact same name (e.g. 'Rahul Patil').
    The system uses the unique Enrollment Number to resolve identity without ambiguity.
    """
    students_data = [
        {
            "sr_no": 10,
            "enrollment_no": "ENR-RP-01",
            "name": "Rahul Patil",
            "student_contact": "9800000001",
            "department_id": 1,
            "semester": 6,
            "division": "C",
            "batch": "C1",
            "academic_year": "2026-2027",
            "class_name": "TYCO",
        },
        {
            "sr_no": 11,
            "enrollment_no": "ENR-RP-02",
            "name": "Rahul Patil",
            "student_contact": "9800000002",
            "department_id": 1,
            "semester": 6,
            "division": "C",
            "batch": "C1",
            "academic_year": "2026-2027",
            "class_name": "TYCO",
        },
    ]
    admin_client.post("/api/students/import/commit", json={"rows": students_data})

    # Student 1 logs in with Name + Password: ENR-RP-01
    s1_client = app_instance.test_client()
    s1_login = s1_client.post("/api/auth/login", json={
        "name": "Rahul Patil",
        "password": "ENR-RP-01",
    })
    assert s1_login.status_code == 200
    s1_profile = s1_client.get("/api/student/profile").get_json()["data"]
    assert s1_profile["enrollment_no"] == "ENR-RP-01"

    # Student 2 logs in with Name + Password: ENR-RP-02
    s2_client = app_instance.test_client()
    s2_login = s2_client.post("/api/auth/login", json={
        "name": "Rahul Patil",
        "password": "ENR-RP-02",
    })
    assert s2_login.status_code == 200
    s2_profile = s2_client.get("/api/student/profile").get_json()["data"]
    assert s2_profile["enrollment_no"] == "ENR-RP-02"

    # Security test: Mismatched Name + Enrollment No returns generic failure without leaking existence
    bad_client = app_instance.test_client()
    bad_login = bad_client.post("/api/auth/login", json={
        "name": "Wrong Name",
        "password": "ENR-RP-01",
    })
    assert bad_login.status_code == 401
    assert "Invalid" in bad_login.get_json()["message"]


# =============================================================================
# 6. IMPORT VALIDATION & MALFORMED ROW DETECTION TESTS
# =============================================================================

def test_import_validation_detects_malformed_and_duplicate_rows(app_instance):
    """
    Tests row validation against missing fields, malformed rows, and duplicates.
    """
    raw_rows = [
        # Missing Student Name
        {
            "_row_number": 2,
            "enrollment_no": "2425000001",
            "name": "",
            "department": "Computer Engineering",
            "semester": "6",
        },
        # Missing Enrollment No
        {
            "_row_number": 3,
            "enrollment_no": "",
            "name": "Test Student",
            "department": "Computer Engineering",
            "semester": "6",
        },
        # Duplicate Enrollment No in file (duplicate of row 2)
        {
            "_row_number": 4,
            "enrollment_no": "2425000001",
            "name": "Pawar Sandesh",
            "department": "Computer Engineering",
            "semester": "6",
        },
        # Invalid Semester (Out of bounds for Polytechnic)
        {
            "_row_number": 5,
            "enrollment_no": "2425000004",
            "name": "Degree Candidate",
            "department": "Computer Engineering",
            "semester": "8",
        },
        # Malformed footer row
        {
            "_row_number": 6,
            "name": "GFM Coordinator Class Teacher Head of Department",
            "enrollment_no": "",
        },
    ]

    report = ImportService.validate_student_rows(raw_rows)
    assert report["total_rows"] == 5
    assert report["invalid_count"] == 5
    assert report["valid_count"] == 0

    # Verify specific error messages
    r2_errs = report["rows"][0]["errors"]
    assert any("Student Name is missing" in e for e in r2_errs)

    r3_errs = report["rows"][1]["errors"]
    assert any("Enrollment Number is missing" in e for e in r3_errs)

    r4_errs = report["rows"][2]["errors"]
    assert any("Duplicate Enrollment No" in e for e in r4_errs)

    r5_errs = report["rows"][3]["errors"]
    assert any("Semester 8 out of bounds" in e for e in r5_errs)

    r6_errs = report["rows"][4]["errors"]
    assert any("Non-student table footer" in e for e in r6_errs)


# =============================================================================
# 7. TRANSACTION ROLLBACK INTEGRITY TEST
# =============================================================================

def test_transaction_rollback_on_commit_failure(admin_client, app_instance):
    """
    Verifies that if an error occurs during commit, the entire database transaction
    rolls back and leaves no partial or orphaned student/user records.
    """
    malformed_commit_batch = [
        {
            "sr_no": 99,
            "enrollment_no": "ENR-ROLLBACK-1",
            "name": "Rollback Candidate One",
            "department_id": 1,
            "semester": 6,
        },
        {
            "sr_no": 100,
            "enrollment_no": "ENR-ROLLBACK-2",
            "name": "Rollback Candidate Two",
            "department_id": 9999,  # Non-existent department causes failure
            "semester": 6,
        },
    ]

    res = admin_client.post("/api/students/import/commit", json={"rows": malformed_commit_batch})
    assert res.status_code in (400, 422)

    with app_instance.app_context():
        # Confirm student 1 was rolled back and NOT created
        assert Student.query.filter_by(enrollment_number="ENR-ROLLBACK-1").first() is None
        assert User.query.filter_by(username="ENR-ROLLBACK-1").first() is None
