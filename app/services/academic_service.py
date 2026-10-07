"""
Academic Service Module (Polytechnic Domain).
Manages Polytechnic branches (departments), diploma semester structures (1 to 6),
and curriculum subject allocations.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import or_

from app.extensions import db
from app.models.department import Department
from app.models.subject import Subject
from app.utils.errors import NotFoundError, ConflictError, ValidationError
from app.utils.validators import validate_unique_field, validate_positive_int
from app.utils.audit import log_audit

# Standard 3-Year Diploma / Polytechnic Semester Boundaries
VALID_POLYTECHNIC_SEMESTERS = {1, 2, 3, 4, 5, 6}


class AcademicService:
    """Service layer managing Polytechnic branches, semesters, and subjects."""

    # =========================================================================
    # DEPARTMENTS / ENGINEERING BRANCHES
    # =========================================================================

    @staticmethod
    def get_departments(search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves list of Polytechnic engineering branches / departments."""
        query = Department.query

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(Department.code.ilike(pattern), Department.name.ilike(pattern))
            )

        departments = query.order_by(Department.name.asc()).all()
        return [dept.to_dict() for dept in departments]

    @staticmethod
    def get_department_by_id(department_id: int) -> Department:
        """Fetches single department by ID or raises NotFoundError."""
        department = Department.query.get(department_id)
        if not department:
            raise NotFoundError(f"Department/Branch with ID {department_id} not found.")
        return department

    @staticmethod
    def create_department(
        code: Optional[Any] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> Department:
        """Creates a new Polytechnic branch (e.g., Computer Engineering). Accepts dict or kwargs."""
        if isinstance(code, dict):
            data = code
            code = data.get("code")
            name = data.get("name")
            description = data.get("description")
            operator_user_id = operator_user_id or data.get("operator_user_id")
            ip_address = ip_address or data.get("ip_address")

        if not code or not name:
            raise ValidationError("Branch code and name are required.")

        clean_code = str(code).strip().upper()
        clean_name = str(name).strip()

        validate_unique_field(Department, "code", clean_code)
        validate_unique_field(Department, "name", clean_name)

        department = Department(
            code=clean_code,
            name=clean_name,
            description=description.strip() if description else None,
        )
        db.session.add(department)
        db.session.commit()

        log_audit(
            action="DEPARTMENT_CREATED",
            entity_type="Department",
            entity_id=str(department.id),
            user_id=operator_user_id,
            details=f"Created Polytechnic branch '{department.name}' ({department.code}).",
            ip_address=ip_address,
        )

        return department

    @staticmethod
    def update_department(
        department_id: int,
        code: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Department:
        """Updates department/branch parameters."""
        dept = AcademicService.get_department_by_id(department_id)

        if code:
            clean_code = code.strip().upper()
            validate_unique_field(Department, "code", clean_code, exclude_id=dept.id)
            dept.code = clean_code

        if name:
            clean_name = name.strip()
            validate_unique_field(Department, "name", clean_name, exclude_id=dept.id)
            dept.name = clean_name

        if description is not None:
            dept.description = description.strip() or None

        db.session.commit()

        log_audit(
            action="DEPARTMENT_UPDATED",
            entity_type="Department",
            entity_id=str(dept.id),
            user_id=operator_user_id,
            details=f"Updated department {dept.code}.",
            ip_address=ip_address,
        )

        return dept

    @staticmethod
    def delete_department(
        department_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Deletes department if no students, teachers, or subjects are assigned."""
        dept = AcademicService.get_department_by_id(department_id)

        if dept.students.count() > 0:
            raise ConflictError("Cannot delete department with enrolled students.")
        if dept.teachers.count() > 0:
            raise ConflictError("Cannot delete department with assigned faculty members.")
        if dept.subjects.count() > 0:
            raise ConflictError("Cannot delete department with existing course subjects.")

        code = dept.code
        db.session.delete(dept)
        db.session.commit()

        log_audit(
            action="DEPARTMENT_DELETED",
            entity_type="Department",
            entity_id=str(department_id),
            user_id=operator_user_id,
            details=f"Deleted department {code}.",
            ip_address=ip_address,
        )

        return True

    # =========================================================================
    # SEMESTER RULES (POLYTECHNIC SPECIFIC)
    # =========================================================================

    @staticmethod
    def get_polytechnic_semesters() -> List[Dict[str, Any]]:
        """Returns the structured semester roadmap for a 3-Year Diploma program."""
        return [
            {"semester": 1, "year": "First Year (FY)", "academic_term": "Odd"},
            {"semester": 2, "year": "First Year (FY)", "academic_term": "Even"},
            {"semester": 3, "year": "Second Year (SY)", "academic_term": "Odd"},
            {"semester": 4, "year": "Second Year (SY)", "academic_term": "Even"},
            {"semester": 5, "year": "Third Year (TY)", "academic_term": "Odd"},
            {"semester": 6, "year": "Third Year (TY)", "academic_term": "Even"},
        ]

    @staticmethod
    def validate_polytechnic_semester(semester: int) -> int:
        """Validates that semester belongs to the valid Polytechnic range (1 to 6)."""
        sem = validate_positive_int(semester, "semester", min_val=1, max_val=6)
        if sem not in VALID_POLYTECHNIC_SEMESTERS:
            raise ValidationError(
                f"Invalid semester '{semester}'. Polytechnic Diploma programs support Semesters 1 through 6."
            )
        return sem

    # =========================================================================
    # SUBJECTS / COURSES
    # =========================================================================

    @staticmethod
    def get_subjects(
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves subjects filtered by branch and semester."""
        query = Subject.query

        if department_id:
            query = query.filter(Subject.department_id == department_id)

        if semester:
            query = query.filter(Subject.semester == semester)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(Subject.code.ilike(pattern), Subject.name.ilike(pattern))
            )

        subjects = query.order_by(Subject.semester.asc(), Subject.code.asc()).all()
        return [sub.to_dict() for sub in subjects]

    @staticmethod
    def get_subject_by_id(subject_id: int) -> Subject:
        """Fetches single subject by ID or raises NotFoundError."""
        subject = Subject.query.get(subject_id)
        if not subject:
            raise NotFoundError(f"Subject with ID {subject_id} not found.")
        return subject

    @staticmethod
    def create_subject(
        code: Optional[Any] = None,
        name: Optional[str] = None,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        credits: int = 3,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> Subject:
        """Creates an academic subject within a Polytechnic branch curriculum. Accepts dict or kwargs."""
        if isinstance(code, dict):
            data = code
            code = data.get("code") or data.get("subject_code")
            name = data.get("name") or data.get("subject_name")
            department_id = data.get("department_id")
            semester = data.get("semester")
            credits = data.get("credits", 3)
            operator_user_id = operator_user_id or data.get("operator_user_id")
            ip_address = ip_address or data.get("ip_address")

        if not code or not name or department_id is None or semester is None:
            raise ValidationError("Subject code, name, department_id, and semester are required.")

        clean_code = str(code).strip().upper()
        clean_name = str(name).strip()

        AcademicService.get_department_by_id(department_id)
        sem = AcademicService.validate_polytechnic_semester(semester)
        cred = validate_positive_int(credits, "credits", min_val=1, max_val=10)

        validate_unique_field(Subject, "code", clean_code)

        subject = Subject(
            code=clean_code,
            name=clean_name,
            department_id=department_id,
            semester=sem,
            credits=cred,
        )
        db.session.add(subject)
        db.session.commit()

        log_audit(
            action="SUBJECT_CREATED",
            entity_type="Subject",
            entity_id=str(subject.id),
            user_id=operator_user_id,
            details=f"Created subject {subject.code} ({subject.name}) for Semester {sem}.",
            ip_address=ip_address,
        )

        return subject

    @staticmethod
    def update_subject(
        subject_id: int,
        code: Optional[str] = None,
        name: Optional[str] = None,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        credits: Optional[int] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Subject:
        """Updates subject attributes."""
        subject = AcademicService.get_subject_by_id(subject_id)

        if code:
            clean_code = code.strip().upper()
            validate_unique_field(Subject, "code", clean_code, exclude_id=subject.id)
            subject.code = clean_code

        if name:
            subject.name = name.strip()

        if department_id:
            AcademicService.get_department_by_id(department_id)
            subject.department_id = department_id

        if semester:
            subject.semester = AcademicService.validate_polytechnic_semester(semester)

        if credits:
            subject.credits = validate_positive_int(credits, "credits", min_val=1, max_val=10)

        db.session.commit()

        log_audit(
            action="SUBJECT_UPDATED",
            entity_type="Subject",
            entity_id=str(subject.id),
            user_id=operator_user_id,
            details=f"Updated subject {subject.code}.",
            ip_address=ip_address,
        )

        return subject

    @staticmethod
    def delete_subject(
        subject_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Deletes subject if no examinations are scheduled for it."""
        subject = AcademicService.get_subject_by_id(subject_id)

        if subject.exams.count() > 0:
            raise ConflictError("Cannot delete subject with scheduled examinations.")

        code = subject.code
        db.session.delete(subject)
        db.session.commit()

        log_audit(
            action="SUBJECT_DELETED",
            entity_type="Subject",
            entity_id=str(subject_id),
            user_id=operator_user_id,
            details=f"Deleted subject {code}.",
            ip_address=ip_address,
        )

        return True
