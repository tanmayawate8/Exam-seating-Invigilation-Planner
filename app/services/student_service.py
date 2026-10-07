"""
Student Service Module (Polytechnic Domain).
Encapsulates business logic for student management, enrollment into Polytechnic branches,
semester tracking (Sem 1 to 6), activation status, and student portal queries.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.seat_allocation import SeatAllocation
from app.models.registration import Registration
from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.utils.errors import NotFoundError, ConflictError, ValidationError
from app.utils.validators import validate_unique_field
from app.utils.audit import log_audit


class StudentService:
    """Service layer managing Polytechnic student records and portal operations."""

    @staticmethod
    def get_students(
        page: int = 1,
        per_page: int = 20,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Retrieves paginated student profiles with branch and semester filters."""
        query = Student.query.join(Student.user)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if department_id:
            query = query.filter(Student.department_id == department_id)

        if semester:
            query = query.filter(Student.semester == semester)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.roll_number.ilike(pattern),
                    Student.enrollment_number.ilike(pattern),
                    Student.first_name.ilike(pattern),
                    Student.last_name.ilike(pattern),
                )
            )

        paginated = query.order_by(Student.roll_number.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "students": [s.to_dict() for s in paginated.items],
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
    def get_student_by_id(student_id: int) -> Student:
        """Fetches single student by ID or raises NotFoundError."""
        student = Student.query.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} was not found.")
        return student

    @staticmethod
    def create_student(
        validated_data: Dict[str, Any],
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Student:
        """
        Creates user account and Polytechnic student profile in an atomic transaction.
        Enforces unique roll and enrollment numbers within the branch.
        """
        # Validate Polytechnic Branch and Semester boundaries
        dept_id = validated_data["department_id"]
        AcademicService.get_department_by_id(dept_id)
        semester = AcademicService.validate_polytechnic_semester(validated_data["semester"])

        roll_number = validated_data["roll_number"].strip().upper()
        enrollment_number = validated_data["enrollment_number"].strip().upper()

        validate_unique_field(Student, "roll_number", roll_number)
        validate_unique_field(Student, "enrollment_number", enrollment_number)

        username = validated_data["username"]
        email = validated_data["email"]
        password = validated_data["password"]

        # 1. Create underlying user
        success, user, message = AuthService.create_user(
            username=username,
            email=email,
            password=password,
            role="STUDENT",
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
            first_name = parts[0] if parts and parts[0] else "Student"
            last_name = parts[1] if len(parts) > 1 and parts[1] else "Polytechnic"

        academic_year = validated_data.get("academic_year", "2025-2026")

        try:
            # 2. Create student profile
            student = Student(
                user_id=user.id,
                roll_number=roll_number,
                enrollment_number=enrollment_number,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                department_id=dept_id,
                semester=semester,
                academic_year=str(academic_year).strip(),
            )
            db.session.add(student)
            db.session.commit()

            log_audit(
                action="STUDENT_CREATED",
                entity_type="Student",
                entity_id=str(student.id),
                user_id=creator_user_id,
                details=f"Created Polytechnic student {student.roll_number} in Semester {semester}.",
                ip_address=ip_address,
            )

            return student

        except Exception as exc:
            db.session.rollback()
            User.query.filter_by(id=user.id).delete()
            db.session.commit()
            raise ValidationError(f"Failed to create student profile: {exc}")

    @staticmethod
    def update_student(
        student_id: int,
        validated_data: Dict[str, Any],
        modifier_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Student:
        """Updates student attributes atomically."""
        student = StudentService.get_student_by_id(student_id)

        if "department_id" in validated_data:
            dept_id = validated_data["department_id"]
            AcademicService.get_department_by_id(dept_id)
            student.department_id = dept_id

        if "semester" in validated_data:
            student.semester = AcademicService.validate_polytechnic_semester(validated_data["semester"])

        if "roll_number" in validated_data:
            roll = validated_data["roll_number"].strip().upper()
            validate_unique_field(Student, "roll_number", roll, exclude_id=student.id)
            student.roll_number = roll

        if "enrollment_number" in validated_data:
            enr = validated_data["enrollment_number"].strip().upper()
            validate_unique_field(Student, "enrollment_number", enr, exclude_id=student.id)
            student.enrollment_number = enr

        for key in ("first_name", "last_name", "academic_year"):
            if key in validated_data:
                setattr(student, key, validated_data[key].strip())

        db.session.commit()

        log_audit(
            action="STUDENT_UPDATED",
            entity_type="Student",
            entity_id=str(student.id),
            user_id=modifier_user_id,
            details=f"Student {student.roll_number} updated.",
            ip_address=ip_address,
        )

        return student

    @staticmethod
    def set_student_active_status(
        student_id: int,
        is_active: bool,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Student:
        """Toggles a student's active status."""
        student = StudentService.get_student_by_id(student_id)
        student.user.is_active = is_active
        db.session.commit()

        log_audit(
            action="STUDENT_STATUS_TOGGLED",
            entity_type="Student",
            entity_id=str(student.id),
            user_id=operator_user_id,
            details=f"Student {student.roll_number} active status set to {is_active}.",
            ip_address=ip_address,
        )

        return student

    @staticmethod
    def delete_student(
        student_id: int,
        deleter_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Deletes student and associated user account."""
        student = StudentService.get_student_by_id(student_id)
        user = student.user
        roll = student.roll_number

        db.session.delete(user)
        db.session.commit()

        log_audit(
            action="STUDENT_DELETED",
            entity_type="Student",
            entity_id=str(student_id),
            user_id=deleter_user_id,
            details=f"Polytechnic student {roll} deleted.",
            ip_address=ip_address,
        )

        return True

    @staticmethod
    def get_student_seating_info(student_id: int) -> List[Dict[str, Any]]:
        """Student Portal: Retrieves published seat allocations for a given student."""
        student = StudentService.get_student_by_id(student_id)

        allocations = (
            SeatAllocation.query.join(SeatAllocation.seating_plan)
            .filter(
                SeatAllocation.student_id == student.id,
                SeatAllocation.seating_plan.has(status="PUBLISHED"),
            )
            .all()
        )

        results = []
        for alloc in allocations:
            plan = alloc.seating_plan
            exam = plan.exam
            room = alloc.room
            seat = alloc.seat
            results.append({
                "allocation_id": alloc.id,
                "plan_code": plan.plan_code,
                "exam_code": exam.exam_code,
                "exam_title": exam.title,
                "exam_date": exam.exam_date.isoformat(),
                "start_time": exam.start_time.isoformat(),
                "end_time": exam.end_time.isoformat(),
                "session_name": exam.session_name,
                "room_number": room.room_number,
                "building": room.building,
                "floor": room.floor,
                "seat_number": seat.seat_number,
                "row_num": seat.row_num,
                "col_num": seat.col_num,
            })

        return results

    @staticmethod
    def get_student_timetable(student_id: int) -> List[Dict[str, Any]]:
        """Student Portal: Retrieves upcoming examination timetable for enrolled student."""
        student = StudentService.get_student_by_id(student_id)

        registrations = (
            Registration.query.filter_by(student_id=student.id, is_eligible=True)
            .join(Registration.exam)
            .all()
        )

        timetable = []
        for reg in registrations:
            ex = reg.exam
            timetable.append({
                "registration_id": reg.id,
                "exam_id": ex.id,
                "exam_code": ex.exam_code,
                "title": ex.title,
                "subject_code": ex.subject.code if ex.subject else None,
                "subject_name": ex.subject.name if ex.subject else None,
                "exam_date": ex.exam_date.isoformat(),
                "start_time": ex.start_time.isoformat(),
                "end_time": ex.end_time.isoformat(),
                "session_name": ex.session_name,
                "status": ex.status,
            })

        return timetable

    @staticmethod
    def search_student_seating(roll_number: str, exam_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Student Portal / Kiosk: Searches published seating allocations by student roll number."""
        clean_roll = roll_number.strip().upper()
        student = Student.query.filter_by(roll_number=clean_roll).first()
        if not student:
            raise NotFoundError(f"Student with roll number '{clean_roll}' was not found.")

        query = (
            SeatAllocation.query.join(SeatAllocation.seating_plan)
            .filter(
                SeatAllocation.student_id == student.id,
                SeatAllocation.seating_plan.has(status="PUBLISHED"),
            )
        )
        if exam_id:
            query = query.filter(SeatAllocation.seating_plan.has(exam_id=exam_id))

        allocations = query.all()
        results = []
        for alloc in allocations:
            plan = alloc.seating_plan
            exam = plan.exam
            room = alloc.room
            seat = alloc.seat
            results.append({
                "student_roll": student.roll_number,
                "student_name": student.full_name,
                "department_code": student.department.code if student.department else None,
                "semester": student.semester,
                "exam_code": exam.exam_code,
                "exam_title": exam.title,
                "exam_date": exam.exam_date.isoformat(),
                "start_time": exam.start_time.isoformat(),
                "end_time": exam.end_time.isoformat(),
                "session_name": exam.session_name,
                "room_number": room.room_number,
                "building": room.building,
                "floor": room.floor,
                "seat_number": seat.seat_number,
                "row_num": seat.row_num,
                "col_num": seat.col_num,
            })
        return results

    # Convenience alias
    toggle_student_status = set_student_active_status
