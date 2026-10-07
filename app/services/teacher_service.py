"""
Teacher Service Module (Polytechnic Domain).
Encapsulates business logic for faculty management, availability submissions,
assigned invigilation duties, and peer duty-swap requests across Polytechnic branches.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User
from app.models.teacher import Teacher
from app.models.teacher_availability import TeacherAvailability
from app.models.invigilation_duty import InvigilationDuty
from app.models.duty_swap import DutySwap
from app.models.notification import Notification
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.utils.errors import NotFoundError, ConflictError, ValidationError, BadRequestError
from app.utils.validators import validate_unique_field
from app.utils.audit import log_audit


class TeacherService:
    """Service layer managing faculty profiles, duties, and swap workflows."""

    @staticmethod
    def get_teachers(
        page: int = 1,
        per_page: int = 20,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        designation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves paginated teacher profiles with branch, designation, and search filters."""
        query = Teacher.query.join(Teacher.user)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if department_id:
            query = query.filter(Teacher.department_id == department_id)

        if designation:
            query = query.filter(Teacher.designation.ilike(f"%{designation.strip()}%"))

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Teacher.employee_id.ilike(pattern),
                    Teacher.first_name.ilike(pattern),
                    Teacher.last_name.ilike(pattern),
                    Teacher.designation.ilike(pattern),
                )
            )

        paginated = query.order_by(Teacher.first_name.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "teachers": [t.to_dict() for t in paginated.items],
            "pagination": {
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages,
                "per_page": paginated.per_page,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            },
        }

    @staticmethod
    def get_teacher_by_id(teacher_id: int) -> Teacher:
        """Fetches single teacher by ID or raises NotFoundError."""
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            raise NotFoundError(f"Teacher with ID {teacher_id} was not found.")
        return teacher

    @staticmethod
    def create_teacher(
        validated_data: Dict[str, Any],
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Teacher:
        """Creates user account and faculty profile in an atomic transaction."""
        dept_id = validated_data["department_id"]
        AcademicService.get_department_by_id(dept_id)

        emp_id = validated_data["employee_id"].strip().upper()
        validate_unique_field(Teacher, "employee_id", emp_id)

        username = validated_data["username"]
        email = validated_data["email"]
        password = validated_data["password"]

        success, user, message = AuthService.create_user(
            username=username,
            email=email,
            password=password,
            role="TEACHER",
            created_by_user_id=creator_user_id,
            ip_address=ip_address,
        )

        if not success:
            raise ConflictError(message)

        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name")
        if not first_name or not last_name:
            full_name = validated_data.get("full_name", "")
            parts = full_name.strip().split(" ", 1)
            first_name = parts[0] if parts and parts[0] else "Faculty"
            last_name = parts[1] if len(parts) > 1 and parts[1] else "Member"

        try:
            teacher = Teacher(
                user_id=user.id,
                employee_id=emp_id,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                department_id=dept_id,
                designation=validated_data.get("designation", "Lecturer").strip(),
                phone_number=validated_data.get("phone_number"),
                max_duties_per_week=validated_data.get("max_duties_per_week", 5),
            )
            db.session.add(teacher)
            db.session.commit()

            log_audit(
                action="TEACHER_CREATED",
                entity_type="Teacher",
                entity_id=str(teacher.id),
                user_id=creator_user_id,
                details=f"Created faculty member {teacher.employee_id} ({teacher.full_name}).",
                ip_address=ip_address,
            )

            return teacher

        except Exception as exc:
            db.session.rollback()
            User.query.filter_by(id=user.id).delete()
            db.session.commit()
            raise ValidationError(f"Failed to create teacher profile: {exc}")

    @staticmethod
    def update_teacher(
        teacher_id: int,
        validated_data: Dict[str, Any],
        modifier_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Teacher:
        """Updates teacher attributes atomically."""
        teacher = TeacherService.get_teacher_by_id(teacher_id)

        if "department_id" in validated_data:
            dept_id = validated_data["department_id"]
            AcademicService.get_department_by_id(dept_id)
            teacher.department_id = dept_id

        if "employee_id" in validated_data:
            emp = validated_data["employee_id"].strip().upper()
            validate_unique_field(Teacher, "employee_id", emp, exclude_id=teacher.id)
            teacher.employee_id = emp

        for key in ("first_name", "last_name", "designation", "phone_number", "max_duties_per_week"):
            if key in validated_data:
                setattr(teacher, key, validated_data[key])

        db.session.commit()

        log_audit(
            action="TEACHER_UPDATED",
            entity_type="Teacher",
            entity_id=str(teacher.id),
            user_id=modifier_user_id,
            details=f"Teacher {teacher.employee_id} updated.",
            ip_address=ip_address,
        )

        return teacher

    @staticmethod
    def set_teacher_active_status(
        teacher_id: int,
        is_active: bool,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Teacher:
        """Toggles a teacher's active status."""
        teacher = TeacherService.get_teacher_by_id(teacher_id)
        teacher.user.is_active = is_active
        db.session.commit()

        log_audit(
            action="TEACHER_STATUS_TOGGLED",
            entity_type="Teacher",
            entity_id=str(teacher.id),
            user_id=operator_user_id,
            details=f"Teacher {teacher.employee_id} active status set to {is_active}.",
            ip_address=ip_address,
        )

        return teacher

    @staticmethod
    def delete_teacher(
        teacher_id: int,
        deleter_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Deletes teacher and associated user account."""
        teacher = TeacherService.get_teacher_by_id(teacher_id)
        user = teacher.user
        emp_id = teacher.employee_id

        db.session.delete(user)
        db.session.commit()

        log_audit(
            action="TEACHER_DELETED",
            entity_type="Teacher",
            entity_id=str(teacher_id),
            user_id=deleter_user_id,
            details=f"Teacher {emp_id} deleted.",
            ip_address=ip_address,
        )

        return True

    @staticmethod
    def set_availability(
        teacher_id: int,
        date_val: date,
        time_slot: str,
        is_available: bool = True,
        reason: Optional[str] = None,
        exam_id: Optional[int] = None,
    ) -> TeacherAvailability:
        """Records teacher availability/leave window."""
        teacher = TeacherService.get_teacher_by_id(teacher_id)

        avail = TeacherAvailability.query.filter_by(
            teacher_id=teacher.id, date=date_val, time_slot=time_slot.upper()
        ).first()

        if avail:
            avail.is_available = is_available
            avail.reason = reason
            avail.exam_id = exam_id
        else:
            avail = TeacherAvailability(
                teacher_id=teacher.id,
                date=date_val,
                time_slot=time_slot.upper(),
                is_available=is_available,
                reason=reason,
                exam_id=exam_id,
            )
            db.session.add(avail)

        db.session.commit()
        return avail

    @staticmethod
    def get_teacher_duties(teacher_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Teacher Portal: Retrieves invigilation duties assigned to this faculty member."""
        teacher = TeacherService.get_teacher_by_id(teacher_id)
        query = InvigilationDuty.query.filter_by(teacher_id=teacher.id)

        if status:
            query = query.filter_by(status=status.upper())

        duties = query.all()
        return [duty.to_dict() for duty in duties]

    @staticmethod
    def request_duty_swap(
        duty_id: int,
        requester_teacher_id: int,
        target_teacher_id: int,
        reason: str,
    ) -> DutySwap:
        """
        Creates a formal peer duty swap request.
        Validates ownership, prevents swapping to self, and checks for conflicts.
        """
        if requester_teacher_id == target_teacher_id:
            raise BadRequestError("You cannot request a duty swap with yourself.")

        duty = InvigilationDuty.query.get(duty_id)
        if not duty:
            raise NotFoundError(f"Duty with ID {duty_id} does not exist.")

        if duty.teacher_id != requester_teacher_id:
            raise BadRequestError("You can only request a swap for your own assigned duty.")

        target_teacher = TeacherService.get_teacher_by_id(target_teacher_id)

        conflict = InvigilationDuty.query.filter_by(
            exam_id=duty.exam_id, teacher_id=target_teacher.id
        ).first()
        if conflict:
            raise ConflictError(
                f"Teacher {target_teacher.full_name} is already assigned to a duty for this exam."
            )

        swap = DutySwap(
            duty_id=duty.id,
            requester_id=requester_teacher_id,
            target_teacher_id=target_teacher.id,
            reason=reason.strip(),
            status="PENDING",
        )
        db.session.add(swap)

        # Notify target teacher
        notif = Notification(
            user_id=target_teacher.user_id,
            title="Duty Swap Request Received",
            message=f"Faculty member {duty.teacher.full_name} has requested a duty swap for Exam {duty.exam.exam_code} in Room {duty.room.room_number}.",
            notification_type="DUTY_SWAP",
        )
        db.session.add(notif)
        db.session.commit()

        log_audit(
            action="DUTY_SWAP_REQUESTED",
            entity_type="DutySwap",
            entity_id=str(swap.id),
            user_id=duty.teacher.user_id,
            details=f"Swap requested for duty {duty.id} with teacher {target_teacher.id}.",
        )

        return swap

    @staticmethod
    def admin_review_duty_swap(
        swap_id: int,
        admin_user_id: int,
        approve: bool,
        admin_comment: Optional[str] = None,
    ) -> DutySwap:
        """Admin action approving or rejecting an invigilation duty swap."""
        swap = DutySwap.query.get(swap_id)
        if not swap:
            raise NotFoundError(f"Swap request {swap_id} not found.")

        if swap.status in ("APPROVED_BY_ADMIN", "REJECTED", "CANCELLED"):
            raise BadRequestError(f"Swap request is already in terminal state '{swap.status}'.")

        swap.reviewed_at = datetime.utcnow()
        swap.admin_comment = admin_comment

        if approve:
            swap.status = "APPROVED_BY_ADMIN"
            duty = swap.duty
            duty.teacher_id = swap.target_teacher_id
            duty.status = "SWAPPED"

            n1 = Notification(
                user_id=swap.requester.user_id,
                title="Duty Swap Approved",
                message=f"Your duty swap request for Exam {duty.exam.exam_code} was approved by Admin.",
                notification_type="DUTY_SWAP",
            )
            n2 = Notification(
                user_id=swap.target_teacher.user_id,
                title="Duty Reassigned to You",
                message=f"You have been officially reassigned to invigilate Exam {duty.exam.exam_code} in Room {duty.room.room_number}.",
                notification_type="DUTY_ASSIGNED",
            )
            db.session.add_all([n1, n2])
        else:
            swap.status = "REJECTED"
            n1 = Notification(
                user_id=swap.requester.user_id,
                title="Duty Swap Rejected",
                message=f"Your duty swap request for Exam {swap.duty.exam.exam_code} was rejected by Admin.",
                notification_type="DUTY_SWAP",
            )
            db.session.add(n1)

        db.session.commit()

        log_audit(
            action="DUTY_SWAP_REVIEWED",
            entity_type="DutySwap",
            entity_id=str(swap.id),
            user_id=admin_user_id,
            details=f"Swap {swap.id} {'APPROVED' if approve else 'REJECTED'}. Comment: {admin_comment}",
        )

        return swap

    @staticmethod
    def get_teacher_swap_requests(teacher_id: int) -> Dict[str, Any]:
        """Teacher Portal: Retrieves sent and received duty swap requests."""
        sent = DutySwap.query.filter_by(requester_id=teacher_id).order_by(DutySwap.requested_at.desc()).all()
        received = DutySwap.query.filter_by(target_teacher_id=teacher_id).order_by(DutySwap.requested_at.desc()).all()
        return {
            "sent": [s.to_dict() for s in sent],
            "received": [s.to_dict() for s in received],
        }

    # Convenience aliases
    set_teacher_availability = set_availability
    toggle_teacher_status = set_teacher_active_status
