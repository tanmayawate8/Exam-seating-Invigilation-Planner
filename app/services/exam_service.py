"""
Exam Service Module.
Encapsulates business logic for examination timetable scheduling,
schedule conflict prevention, academic state transitions, and exam lifecycle management.
"""

from datetime import date, time
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, and_

from app.extensions import db
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.registration import Registration
from app.models.seating_plan import SeatingPlan
from app.services.registration_service import RegistrationService
from app.utils.errors import NotFoundError, ConflictError, ValidationError, BadRequestError
from app.utils.validators import validate_state_transition
from app.utils.audit import log_audit

# Permitted status lifecycle transitions for Exam
EXAM_ALLOWED_TRANSITIONS = {
    "DRAFT": ["SCHEDULED", "CANCELLED"],
    "SCHEDULED": ["PLANNED", "CANCELLED", "COMPLETED"],
    "PLANNED": ["SCHEDULED", "COMPLETED", "CANCELLED"],
    "COMPLETED": ["ARCHIVED"],
    "CANCELLED": ["DRAFT"],
    "ARCHIVED": [],
}


class ExamService:
    """Service layer managing examinations, timetables, and academic session scheduling."""

    @staticmethod
    def get_exams(
        page: Optional[int] = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        date_val: Optional[date] = None,
        subject_id: Optional[int] = None,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves examination timetables with optional filters and pagination.
        Supports filtering by status, date, subject, department, and semester.
        """
        query = Exam.query.join(Exam.subject)

        if status:
            query = query.filter(Exam.status == status.upper())

        if date_val:
            query = query.filter(Exam.exam_date == date_val)

        if subject_id:
            query = query.filter(Exam.subject_id == subject_id)

        if department_id:
            query = query.filter(Subject.department_id == department_id)

        if semester:
            query = query.filter(Subject.semester == semester)

        query = query.order_by(Exam.exam_date.asc(), Exam.start_time.asc())

        if page is not None:
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "exams": [ex.to_dict() for ex in paginated.items],
                "pagination": {
                    "total": paginated.total,
                    "page": paginated.page,
                    "pages": paginated.pages,
                    "per_page": paginated.per_page,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }

        all_exams = query.all()
        return {
            "exams": [ex.to_dict() for ex in all_exams],
            "total": len(all_exams),
        }

    @staticmethod
    def get_exam_by_id(exam_id: int) -> Exam:
        """Fetches single exam by ID or raises NotFoundError."""
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} was not found.")
        return exam

    @staticmethod
    def get_exam_by_code(exam_code: str) -> Optional[Exam]:
        """Fetches single exam by unique exam_code."""
        return Exam.query.filter_by(exam_code=exam_code.strip().upper()).first()

    @staticmethod
    def create_exam(
        validated_data: Dict[str, Any],
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Exam:
        """
        Creates an examination schedule with comprehensive conflict checking:
        1. Validates subject existence and activity.
        2. Ensures start_time < end_time.
        3. Checks for overlapping exams in the same subject on the same date.
        4. Checks for overlapping exams in the same department and semester on the same date.
        """
        subj_id = validated_data["subject_id"]
        subject = Subject.query.get(subj_id)
        if not subject:
            raise NotFoundError(f"Subject with ID {subj_id} not found.")

        ex_date = validated_data["exam_date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        if start_time >= end_time:
            raise ValidationError("Exam start time must be earlier than end time.")

        exam_code = validated_data["exam_code"].strip().upper()
        if ExamService.get_exam_by_code(exam_code):
            raise ConflictError(f"Exam code '{exam_code}' is already assigned to another exam.")

        # Conflict check 1: Exact same subject overlapping on the same date
        subject_conflict = Exam.query.filter(
            Exam.subject_id == subj_id,
            Exam.exam_date == ex_date,
            Exam.status != "CANCELLED",
            or_(
                and_(Exam.start_time <= start_time, Exam.end_time > start_time),
                and_(Exam.start_time < end_time, Exam.end_time >= end_time),
                and_(Exam.start_time >= start_time, Exam.end_time <= end_time),
            ),
        ).first()

        if subject_conflict:
            raise ConflictError(
                f"Conflicting exam for subject '{subject.subject_name}' ({subject.subject_code}) "
                f"already scheduled on {ex_date} between {subject_conflict.start_time} and {subject_conflict.end_time}."
            )

        # Conflict check 2: Same Department & Semester overlap (students can't take two exams at once)
        cohort_conflict = (
            Exam.query.join(Exam.subject)
            .filter(
                Subject.department_id == subject.department_id,
                Subject.semester == subject.semester,
                Exam.exam_date == ex_date,
                Exam.status != "CANCELLED",
                or_(
                    and_(Exam.start_time <= start_time, Exam.end_time > start_time),
                    and_(Exam.start_time < end_time, Exam.end_time >= end_time),
                    and_(Exam.start_time >= start_time, Exam.end_time <= end_time),
                ),
            )
            .first()
        )

        if cohort_conflict:
            raise ConflictError(
                f"Cohort conflict: Department {subject.department.code} Semester {subject.semester} "
                f"already has Exam '{cohort_conflict.exam_code}' scheduled at {ex_date} {cohort_conflict.start_time}-{cohort_conflict.end_time}."
            )

        exam = Exam(
            subject_id=subj_id,
            exam_code=exam_code,
            title=validated_data["title"].strip(),
            exam_date=ex_date,
            start_time=start_time,
            end_time=end_time,
            session_name=validated_data.get("session_name", "MORNING"),
            status=validated_data.get("status", "SCHEDULED"),
            total_registered=0,
        )

        db.session.add(exam)
        db.session.commit()

        log_audit(
            action="EXAM_CREATED",
            entity_type="Exam",
            entity_id=str(exam.id),
            user_id=creator_user_id,
            details=f"Exam {exam.exam_code} ({exam.title}) created for {exam.exam_date}.",
            ip_address=ip_address,
        )

        return exam

    @staticmethod
    def update_exam(
        exam_id: int,
        validated_data: Dict[str, Any],
        modifier_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Exam:
        """Updates exam timetable parameters and validates state transitions."""
        exam = ExamService.get_exam_by_id(exam_id)

        # State transition validation
        if "status" in validated_data and validated_data["status"] != exam.status:
            validate_state_transition(
                current_state=exam.status,
                next_state=validated_data["status"],
                allowed_transitions=EXAM_ALLOWED_TRANSITIONS,
                entity_name="Exam",
            )

        # Time logic check if updated
        new_start = validated_data.get("start_time", exam.start_time)
        new_end = validated_data.get("end_time", exam.end_time)
        if new_start >= new_end:
            raise ValidationError("Exam start time must be earlier than end time.")

        # Code uniqueness check if changed
        if "exam_code" in validated_data:
            new_code = validated_data["exam_code"].strip().upper()
            if new_code != exam.exam_code:
                existing = ExamService.get_exam_by_code(new_code)
                if existing:
                    raise ConflictError(f"Exam code '{new_code}' is already in use.")
                exam.exam_code = new_code

        for key in ["title", "session_name", "status", "exam_date", "start_time", "end_time"]:
            if key in validated_data:
                setattr(exam, key, validated_data[key])

        db.session.commit()

        log_audit(
            action="EXAM_UPDATED",
            entity_type="Exam",
            entity_id=str(exam.id),
            user_id=modifier_user_id,
            details=f"Exam {exam.exam_code} updated.",
            ip_address=ip_address,
        )

        return exam

    @staticmethod
    def change_exam_status(
        exam_id: int,
        new_status: str,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Exam:
        """Transitions exam status through the defined lifecycle."""
        exam = ExamService.get_exam_by_id(exam_id)
        status_upper = new_status.strip().upper()

        validate_state_transition(
            current_state=exam.status,
            next_state=status_upper,
            allowed_transitions=EXAM_ALLOWED_TRANSITIONS,
            entity_name="Exam",
        )

        exam.status = status_upper
        db.session.commit()

        log_audit(
            action="EXAM_STATUS_CHANGED",
            entity_type="Exam",
            entity_id=str(exam.id),
            user_id=operator_user_id,
            details=f"Exam {exam.exam_code} transitioned to {status_upper}.",
            ip_address=ip_address,
        )

        return exam

    @staticmethod
    def delete_exam(
        exam_id: int,
        deleter_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Deletes exam after ensuring no published seating plans exist."""
        exam = ExamService.get_exam_by_id(exam_id)

        # Prevent deletion if published seating plans exist
        has_published = exam.seating_plans.filter_by(status="PUBLISHED").first()
        if has_published:
            raise ConflictError(
                "Cannot delete an examination with an active published seating plan. Archive or cancel it instead."
            )

        code = exam.exam_code
        db.session.delete(exam)
        db.session.commit()

        log_audit(
            action="EXAM_DELETED",
            entity_type="Exam",
            entity_id=str(exam_id),
            user_id=deleter_user_id,
            details=f"Exam {code} deleted.",
            ip_address=ip_address,
        )

        return True

    # -------------------------------------------------------------------------
    # Forwarding methods for RegistrationService integration
    # -------------------------------------------------------------------------

    @staticmethod
    def register_student(
        student_id: int,
        exam_id: int,
        is_eligible: bool = True,
        operator_user_id: Optional[int] = None,
    ) -> Registration:
        """Delegates student registration to RegistrationService."""
        return RegistrationService.register_student(
            student_id=student_id,
            exam_id=exam_id,
            is_eligible=is_eligible,
            operator_user_id=operator_user_id,
        )

    @staticmethod
    def deregister_student(
        student_id: int,
        exam_id: int,
        operator_user_id: Optional[int] = None,
    ) -> bool:
        """Delegates student deregistration to RegistrationService."""
        return RegistrationService.deregister_student(
            student_id=student_id,
            exam_id=exam_id,
            operator_user_id=operator_user_id,
        )

    @staticmethod
    def bulk_enroll_department_students(
        exam_id: int,
        semester: Optional[int] = None,
        operator_user_id: Optional[int] = None,
    ) -> int:
        """Delegates bulk departmental enrollment to RegistrationService."""
        result = RegistrationService.bulk_enroll_department_students(
            exam_id=exam_id,
            semester=semester,
            operator_user_id=operator_user_id,
        )
        return result["enrolled"]
