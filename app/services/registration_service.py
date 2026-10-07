"""
Registration Service Module.
Encapsulates business logic for student examination enrollment,
bulk departmental registrations, eligibility tracking, and attendance verification.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import or_

from app.extensions import db
from app.models.exam import Exam
from app.models.student import Student
from app.models.user import User
from app.models.registration import Registration
from app.models.seat_allocation import SeatAllocation
from app.models.seating_plan import SeatingPlan
from app.utils.errors import NotFoundError, ConflictError, ValidationError, BadRequestError
from app.utils.audit import log_audit


class RegistrationService:
    """Service layer managing examination candidate enrollments and eligibility."""

    @staticmethod
    def get_exam_registrations(
        exam_id: int,
        page: Optional[int] = 1,
        per_page: int = 20,
        is_eligible: Optional[bool] = None,
        attendance_status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves paginated student registrations for a specific examination.
        Supports filtering by eligibility, attendance status, and student search.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} not found.")

        query = Registration.query.filter_by(exam_id=exam.id).join(Registration.student)

        if is_eligible is not None:
            query = query.filter(Registration.is_eligible.is_(is_eligible))

        if attendance_status:
            query = query.filter(Registration.attendance_status == attendance_status.upper())

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.roll_number.ilike(search_term),
                    Student.full_name.ilike(search_term),
                    Student.enrollment_number.ilike(search_term),
                )
            )

        query = query.order_by(Student.roll_number.asc())

        if page is not None:
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "registrations": [reg.to_dict() for reg in paginated.items],
                "pagination": {
                    "total": paginated.total,
                    "page": paginated.page,
                    "pages": paginated.pages,
                    "per_page": paginated.per_page,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }

        all_regs = query.all()
        return {
            "registrations": [reg.to_dict() for reg in all_regs],
            "total": len(all_regs),
        }

    @staticmethod
    def register_student(
        student_id: int,
        exam_id: int,
        is_eligible: bool = True,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Registration:
        """
        Enrolls an individual student into an examination session.
        Validates student existence, active status, exam status, and uniqueness.
        """
        student = Student.query.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} was not found.")

        if not student.user.is_active:
            raise ValidationError(f"Cannot register inactive student {student.roll_number}.")

        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} was not found.")

        if exam.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
            raise ConflictError(f"Cannot register for an examination with status '{exam.status}'.")

        # Check existing registration
        existing = Registration.query.filter_by(student_id=student.id, exam_id=exam.id).first()
        if existing:
            raise ConflictError(f"Student {student.roll_number} is already registered for Exam {exam.exam_code}.")

        reg = Registration(
            student_id=student.id,
            exam_id=exam.id,
            is_eligible=is_eligible,
            attendance_status="PENDING",
            registration_date=datetime.utcnow(),
        )
        db.session.add(reg)
        exam.total_registered += 1
        db.session.commit()

        log_audit(
            action="STUDENT_REGISTERED",
            entity_type="Registration",
            entity_id=str(reg.id),
            user_id=operator_user_id,
            details=f"Student {student.roll_number} ({student.full_name}) registered for {exam.exam_code}.",
            ip_address=ip_address,
        )

        return reg

    @staticmethod
    def deregister_student(
        student_id: int,
        exam_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Removes a student's registration from an examination session.
        Prevents deregistration if student is already assigned a seat in an active plan.
        """
        reg = Registration.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if not reg:
            raise NotFoundError(f"No registration found for Student ID {student_id} in Exam ID {exam_id}.")

        # Check if student already has a seat allocated in a generated/published plan
        active_alloc = (
            SeatAllocation.query.join(SeatAllocation.seating_plan)
            .filter(
                SeatAllocation.student_id == student_id,
                SeatingPlan.exam_id == exam_id,
                SeatingPlan.status.in_(["GENERATED", "PUBLISHED"]),
            )
            .first()
        )
        if active_alloc:
            raise ConflictError(
                "Cannot deregister student: candidate has an active seat allocation in a generated or "
                "published seating plan. Regenerate or cancel the plan first."
            )

        student_roll = reg.student.roll_number
        exam = reg.exam

        db.session.delete(reg)
        if exam.total_registered > 0:
            exam.total_registered -= 1
        db.session.commit()

        log_audit(
            action="STUDENT_DEREGISTERED",
            entity_type="Registration",
            entity_id=f"Student:{student_id}-Exam:{exam_id}",
            user_id=operator_user_id,
            details=f"Deregistered Student {student_roll} from Exam {exam.exam_code}.",
            ip_address=ip_address,
        )

        return True

    @staticmethod
    def bulk_enroll_department_students(
        exam_id: int,
        semester: Optional[int] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Enrolls all active students belonging to the exam subject's department in a single batch.
        Optionally filters to the specific semester.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} not found.")

        if exam.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
            raise ConflictError(f"Cannot enroll students for an examination with status '{exam.status}'.")

        dept_id = exam.subject.department_id

        # Query active students in the target department
        student_query = (
            Student.query.join(Student.user)
            .filter(
                Student.department_id == dept_id,
                User.is_active.is_(True),
            )
        )

        target_semester = semester if semester is not None else exam.subject.semester
        if target_semester is not None:
            student_query = student_query.filter(Student.semester == target_semester)

        students = student_query.all()
        if not students:
            return {"enrolled": 0, "skipped": 0, "total": exam.total_registered}

        # Identify students already registered
        existing_student_ids = {
            r.student_id
            for r in Registration.query.filter_by(exam_id=exam.id).all()
        }

        new_enrollments = 0
        skipped_count = 0

        for student in students:
            if student.id in existing_student_ids:
                skipped_count += 1
                continue

            reg = Registration(
                student_id=student.id,
                exam_id=exam.id,
                is_eligible=True,
                attendance_status="PENDING",
                registration_date=datetime.utcnow(),
            )
            db.session.add(reg)
            new_enrollments += 1

        exam.total_registered += new_enrollments
        db.session.commit()

        log_audit(
            action="BULK_ENROLLMENT_COMPLETED",
            entity_type="Exam",
            entity_id=str(exam.id),
            user_id=operator_user_id,
            details=(
                f"Bulk enrolled {new_enrollments} students (Dept: {dept_id}, Sem: {target_semester}) "
                f"into Exam {exam.exam_code}. Skipped {skipped_count} already registered."
            ),
            ip_address=ip_address,
        )

        return {
            "enrolled": new_enrollments,
            "skipped": skipped_count,
            "total": exam.total_registered,
        }

    @staticmethod
    def bulk_register_students(
        student_ids: List[int],
        exam_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enrolls a specific explicit list of student IDs into an examination.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} not found.")

        if exam.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
            raise ConflictError(f"Cannot enroll students for an examination with status '{exam.status}'.")

        existing_reg_ids = {
            r.student_id for r in Registration.query.filter_by(exam_id=exam.id).all()
        }

        enrolled_ids = []
        skipped_ids = []
        not_found_ids = []

        for sid in student_ids:
            if sid in existing_reg_ids:
                skipped_ids.append(sid)
                continue

            student = Student.query.get(sid)
            if not student or not student.user.is_active:
                not_found_ids.append(sid)
                continue

            reg = Registration(
                student_id=student.id,
                exam_id=exam.id,
                is_eligible=True,
                attendance_status="PENDING",
                registration_date=datetime.utcnow(),
            )
            db.session.add(reg)
            enrolled_ids.append(sid)

        exam.total_registered += len(enrolled_ids)
        db.session.commit()

        log_audit(
            action="BATCH_STUDENT_REGISTRATION",
            entity_type="Exam",
            entity_id=str(exam.id),
            user_id=operator_user_id,
            details=f"Batch registered {len(enrolled_ids)} students for Exam {exam.exam_code}.",
            ip_address=ip_address,
        )

        return {
            "enrolled_count": len(enrolled_ids),
            "enrolled_ids": enrolled_ids,
            "skipped_ids": skipped_ids,
            "not_found_or_inactive_ids": not_found_ids,
            "total_registered": exam.total_registered,
        }

    @staticmethod
    def update_registration_status(
        registration_id: int,
        is_eligible: Optional[bool] = None,
        attendance_status: Optional[str] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Registration:
        """Updates eligibility or attendance status of an enrolled candidate."""
        reg = Registration.query.get(registration_id)
        if not reg:
            raise NotFoundError(f"Registration with ID {registration_id} not found.")

        if is_eligible is not None:
            reg.is_eligible = bool(is_eligible)

        if attendance_status is not None:
            status_upper = attendance_status.strip().upper()
            allowed = ("PENDING", "PRESENT", "ABSENT")
            if status_upper not in allowed:
                raise ValidationError(f"Invalid attendance status '{attendance_status}'. Must be one of {allowed}.")
            reg.attendance_status = status_upper

        db.session.commit()

        log_audit(
            action="REGISTRATION_STATUS_UPDATED",
            entity_type="Registration",
            entity_id=str(reg.id),
            user_id=operator_user_id,
            details=(
                f"Updated Registration {reg.id} (Student: {reg.student_id}, Exam: {reg.exam_id}) - "
                f"Eligible: {reg.is_eligible}, Attendance: {reg.attendance_status}"
            ),
            ip_address=ip_address,
        )

        return reg
