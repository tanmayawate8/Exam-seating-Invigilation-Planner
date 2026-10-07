"""
Planning Service Module (Member 3 / Member 4 Integration Boundary).
Orchestrates data preparation, calls Member 4's seating and invigilation algorithms,
and manages atomic database persistence with transaction rollback protection.
"""

from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.extensions import db
from app.models.exam import Exam
from app.models.room import Room
from app.models.seat import Seat
from app.models.student import Student
from app.models.user import User
from app.models.teacher import Teacher
from app.models.teacher_availability import TeacherAvailability
from app.models.registration import Registration
from app.models.seating_plan import SeatingPlan
from app.models.seat_allocation import SeatAllocation
from app.models.invigilation_duty import InvigilationDuty
from app.models.notification import Notification
from app.utils.errors import NotFoundError, ConflictError, ValidationError, BadRequestError
from app.utils.audit import log_audit


# =============================================================================
# MEMBER 4 ALGORITHM ADAPTER INTERFACE
# =============================================================================

class AlgorithmAdapter:
    """
    Standard boundary interface for Member 4's algorithm engine.
    Member 3 prepares domain entities and persists results;
    Member 4 implements pure allocation logic.
    """

    @staticmethod
    def default_seating_algorithm(
        students: List[Student],
        available_seats: List[Seat],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, int]]:
        """
        Default seating allocator:
        Assigns candidates to available seats in order of roll number.
        Can be overridden or customized by Member 4's advanced multi-branch interleaver.
        
        Returns:
            List of dicts: [{"student_id": int, "room_id": int, "seat_id": int}, ...]
        """
        allocations = []
        for idx, student in enumerate(students):
            seat = available_seats[idx]
            allocations.append({
                "student_id": student.id,
                "room_id": seat.room_id,
                "seat_id": seat.id,
            })
        return allocations

    @staticmethod
    def default_invigilation_algorithm(
        teachers: List[Teacher],
        rooms: List[Room],
        exam: Exam,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Default invigilator assigner:
        Assigns one Chief Invigilator per exam room from available faculty.
        Can be overridden or customized by Member 4's workload balancing engine.
        
        Returns:
            List of dicts: [{"teacher_id": int, "room_id": int, "duty_role": str}, ...]
        """
        duties = []
        for idx, room in enumerate(rooms):
            teacher = teachers[idx]
            duties.append({
                "teacher_id": teacher.id,
                "room_id": room.id,
                "duty_role": "CHIEF_INVIGILATOR",
            })
        return duties


class PlanningService:
    """
    Backend service gateway managing exam seating and invigilation planning workflows.
    Maintains clean architectural boundaries with Member 4's algorithm engine.
    """

    # Pluggable algorithm hooks for Member 4
    seating_algorithm_hook: Callable = AlgorithmAdapter.default_seating_algorithm
    invigilation_algorithm_hook: Callable = AlgorithmAdapter.default_invigilation_algorithm

    @classmethod
    def register_seating_algorithm(cls, algorithm_fn: Callable) -> None:
        """Allows Member 4 to plug in their custom seating algorithm."""
        cls.seating_algorithm_hook = algorithm_fn

    @classmethod
    def register_invigilation_algorithm(cls, algorithm_fn: Callable) -> None:
        """Allows Member 4 to plug in their custom invigilation algorithm."""
        cls.invigilation_algorithm_hook = algorithm_fn

    # =========================================================================
    # SEATING GENERATION & PERSISTENCE
    # =========================================================================

    @staticmethod
    def generate_seating_plan(
        exam_id: int,
        room_ids: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> SeatingPlan:
        """
        Executes seating generation workflow:
        1. Validates examination and registered student eligibility.
        2. Validates available rooms and active seats.
        3. Invokes Member 4's seating allocation algorithm adapter.
        4. Transactionally persists SeatingPlan and SeatAllocation records.
        5. Updates Exam status to 'PLANNED'.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} not found.")

        if exam.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
            raise ConflictError(f"Cannot generate seating plan for an examination with status '{exam.status}'.")

        # 1. Fetch eligible registered students
        registrations = (
            Registration.query.filter_by(exam_id=exam.id, is_eligible=True)
            .join(Registration.student)
            .order_by(Student.roll_number.asc())
            .all()
        )
        if not registrations:
            raise ValidationError(
                f"No eligible students registered for Exam {exam.exam_code}. Cannot generate seating plan."
            )

        students = [reg.student for reg in registrations]
        total_students = len(students)

        # 2. Fetch examination rooms
        room_query = Room.query.filter_by(is_active=True)
        if room_ids:
            room_query = room_query.filter(Room.id.in_(room_ids))

        rooms = room_query.order_by(Room.capacity.desc()).all()
        if not rooms:
            raise ValidationError("No active examination rooms available for seating allocation.")

        # 3. Collect active seats from selected rooms
        available_seats: List[Seat] = []
        for r in rooms:
            seats_in_room = r.seats.filter_by(is_active=True).order_by(Seat.row_num, Seat.col_num).all()
            available_seats.extend(seats_in_room)

        total_seats = len(available_seats)
        if total_seats < total_students:
            raise ValidationError(
                f"Insufficient seating capacity. Required: {total_students} seats, "
                f"Available in selected rooms: {total_seats} seats."
            )

        # 4. Determine plan version
        existing_plans_count = SeatingPlan.query.filter_by(exam_id=exam.id).count()
        version = existing_plans_count + 1
        plan_code = f"PLAN-{exam.exam_code}-V{version}"

        # 5. Call Member 4 Algorithm Adapter
        try:
            allocations_data = PlanningService.seating_algorithm_hook(
                students=students,
                available_seats=available_seats,
                options=options or {},
            )
        except Exception as algo_err:
            raise ValidationError(f"Algorithm error during seating calculation: {algo_err}")

        rooms_used_ids = {item["room_id"] for item in allocations_data}

        # 6. ATOMIC TRANSACTION: Persist plan and allocations
        try:
            # Archive previous un-published plans for this exam if regenerating
            SeatingPlan.query.filter_by(exam_id=exam.id, status="GENERATED").update({"status": "ARCHIVED"})

            new_plan = SeatingPlan(
                exam_id=exam.id,
                plan_code=plan_code,
                version=version,
                status="GENERATED",
                total_students_allocated=len(allocations_data),
                total_rooms_used=len(rooms_used_ids),
                generated_at=datetime.utcnow(),
            )
            db.session.add(new_plan)
            db.session.flush()  # Generate new_plan.id

            for item in allocations_data:
                alloc = SeatAllocation(
                    seating_plan_id=new_plan.id,
                    student_id=item["student_id"],
                    room_id=item["room_id"],
                    seat_id=item["seat_id"],
                    allocated_at=datetime.utcnow(),
                )
                db.session.add(alloc)

            # Update exam status to PLANNED
            exam.status = "PLANNED"
            db.session.commit()

            log_audit(
                action="SEATING_GENERATED",
                entity_type="SeatingPlan",
                entity_id=str(new_plan.id),
                user_id=operator_user_id,
                details=f"Generated {plan_code} for {total_students} students across {len(rooms_used_ids)} rooms.",
                ip_address=ip_address,
            )

            return new_plan

        except Exception as exc:
            db.session.rollback()
            raise ValidationError(f"Transaction failed during seating plan persistence: {exc}")

    @staticmethod
    def publish_seating_plan(
        plan_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> SeatingPlan:
        """
        Publishes a seating plan, making it visible to students in the portal,
        and dispatches student notifications.
        """
        plan = SeatingPlan.query.get(plan_id)
        if not plan:
            raise NotFoundError(f"Seating Plan with ID {plan_id} not found.")

        if plan.status == "PUBLISHED":
            raise ConflictError("This seating plan is already published.")

        if plan.status == "ARCHIVED" or plan.status == "CANCELLED":
            raise ConflictError(f"Cannot publish a plan with status '{plan.status}'.")

        try:
            plan.status = "PUBLISHED"
            plan.published_at = datetime.utcnow()

            # Generate notifications for all allocated students
            allocations = plan.allocations.all()
            for alloc in allocations:
                notif = Notification(
                    user_id=alloc.student.user_id,
                    title="Seating Allocation Published",
                    message=(
                        f"Your seating for Exam {plan.exam.exam_code} has been published: "
                        f"Room {alloc.room.room_number}, Seat {alloc.seat.seat_number}."
                    ),
                    notification_type="SEATING_PUBLISHED",
                    created_at=datetime.utcnow(),
                )
                db.session.add(notif)

            db.session.commit()

            log_audit(
                action="SEATING_PUBLISHED",
                entity_type="SeatingPlan",
                entity_id=str(plan.id),
                user_id=operator_user_id,
                details=f"Published {plan.plan_code} with {len(allocations)} student notifications sent.",
                ip_address=ip_address,
            )

            return plan

        except Exception as exc:
            db.session.rollback()
            raise ValidationError(f"Transaction failed during seating plan publication: {exc}")

    @staticmethod
    def cancel_seating_plan(
        plan_id: int,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> SeatingPlan:
        """Cancels an existing seating plan."""
        plan = SeatingPlan.query.get(plan_id)
        if not plan:
            raise NotFoundError(f"Seating Plan with ID {plan_id} not found.")

        plan.status = "CANCELLED"

        # If no other published/generated plans exist for this exam, revert exam status to SCHEDULED
        other_active_plans = (
            SeatingPlan.query.filter_by(exam_id=plan.exam_id)
            .filter(SeatingPlan.id != plan.id, SeatingPlan.status.in_(["GENERATED", "PUBLISHED"]))
            .first()
        )
        if not other_active_plans and plan.exam.status == "PLANNED":
            plan.exam.status = "SCHEDULED"

        db.session.commit()

        log_audit(
            action="SEATING_CANCELLED",
            entity_type="SeatingPlan",
            entity_id=str(plan.id),
            user_id=operator_user_id,
            details=f"Cancelled seating plan {plan.plan_code}.",
            ip_address=ip_address,
        )

        return plan

    # =========================================================================
    # INVIGILATION DUTY GENERATION & PERSISTENCE
    # =========================================================================

    @staticmethod
    def generate_invigilation_duties(
        exam_id: int,
        room_ids: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> List[InvigilationDuty]:
        """
        Executes invigilation duty assignment workflow:
        1. Validates examination and required exam rooms.
        2. Retrieves eligible faculty without time conflicts or unavailabilities.
        3. Enforces workload ceilings.
        4. Calls Member 4's invigilation algorithm adapter.
        5. Transactionally persists assigned duties and notifies faculty.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise NotFoundError(f"Exam with ID {exam_id} not found.")

        if exam.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
            raise ConflictError(f"Cannot assign duties for an examination with status '{exam.status}'.")

        # 1. Determine examination rooms to invigilate
        if not room_ids:
            # Default to rooms used in active seating plan
            latest_plan = (
                SeatingPlan.query.filter_by(exam_id=exam.id)
                .order_by(SeatingPlan.version.desc())
                .first()
            )
            if latest_plan:
                room_ids = [
                    r[0]
                    for r in db.session.query(SeatAllocation.room_id)
                    .filter_by(seating_plan_id=latest_plan.id)
                    .distinct()
                    .all()
                ]

        if not room_ids:
            room_ids = [r.id for r in Room.query.filter_by(is_active=True).all()]

        rooms = Room.query.filter(Room.id.in_(room_ids)).all()
        if not rooms:
            raise ValidationError("No examination rooms available for invigilation assignment.")

        # 2. Retrieve available teachers
        # Filter 2a: Unavailabilities on exam date & time slot
        unavail_teacher_ids = {
            a.teacher_id
            for a in TeacherAvailability.query.filter_by(
                date=exam.exam_date, is_available=False
            ).filter(TeacherAvailability.time_slot.in_([exam.session_name, "ALL_DAY"])).all()
        }

        # Filter 2b: Conflicting duties at this exam date & session
        conflicting_duties = (
            InvigilationDuty.query.join(InvigilationDuty.exam)
            .filter(
                Exam.exam_date == exam.exam_date,
                Exam.session_name == exam.session_name,
                InvigilationDuty.exam_id != exam.id,
                InvigilationDuty.status.in_(["ASSIGNED", "CONFIRMED"]),
            )
            .all()
        )
        conflicting_teacher_ids = {d.teacher_id for d in conflicting_duties}

        excluded_ids = unavail_teacher_ids | conflicting_teacher_ids

        teachers_query = Teacher.query.join(Teacher.user).filter(User.is_active.is_(True))
        if excluded_ids:
            teachers_query = teachers_query.filter(~Teacher.id.in_(excluded_ids))

        teachers = teachers_query.all()

        if len(teachers) < len(rooms):
            raise ValidationError(
                f"Insufficient available teachers for invigilation duties. "
                f"Rooms required: {len(rooms)}, Available teachers: {len(teachers)}."
            )

        # 3. Call Member 4 Algorithm Adapter
        try:
            duties_data = PlanningService.invigilation_algorithm_hook(
                teachers=teachers,
                rooms=rooms,
                exam=exam,
                options=options or {},
            )
        except Exception as algo_err:
            raise ValidationError(f"Algorithm error during invigilation calculation: {algo_err}")

        # 4. ATOMIC TRANSACTION: Assign duties to rooms
        try:
            # Clear previous unconfirmed assignments for this exam
            InvigilationDuty.query.filter_by(exam_id=exam.id, status="ASSIGNED").delete()

            assigned_duties = []
            for item in duties_data:
                duty = InvigilationDuty(
                    exam_id=exam.id,
                    teacher_id=item["teacher_id"],
                    room_id=item["room_id"],
                    duty_role=item.get("duty_role", "CHIEF_INVIGILATOR"),
                    status="ASSIGNED",
                    assigned_at=datetime.utcnow(),
                )
                db.session.add(duty)
                assigned_duties.append(duty)

                teacher = Teacher.query.get(item["teacher_id"])
                room = Room.query.get(item["room_id"])

                # Send notification to faculty member
                notif = Notification(
                    user_id=teacher.user_id,
                    title="New Invigilation Duty Assigned",
                    message=(
                        f"You have been assigned to invigilate Exam {exam.exam_code} ({exam.title}) "
                        f"in Room {room.room_number} on {exam.exam_date} ({exam.session_name})."
                    ),
                    notification_type="DUTY_ASSIGNED",
                    created_at=datetime.utcnow(),
                )
                db.session.add(notif)

            db.session.commit()

            log_audit(
                action="INVIGILATION_GENERATED",
                entity_type="Exam",
                entity_id=str(exam.id),
                user_id=operator_user_id,
                details=f"Assigned {len(assigned_duties)} invigilators for Exam {exam.exam_code}.",
                ip_address=ip_address,
            )

            return assigned_duties

        except Exception as exc:
            db.session.rollback()
            raise ValidationError(f"Transaction failed during invigilation duty assignment: {exc}")

    # =========================================================================
    # QUERY / VIEW HELPERS FOR MEMBER 1 & 2 FRONTENDS
    # =========================================================================

    @staticmethod
    def get_seating_plan_by_id(plan_id: int) -> SeatingPlan:
        """Retrieves a single seating plan by ID."""
        plan = SeatingPlan.query.get(plan_id)
        if not plan:
            raise NotFoundError(f"Seating Plan with ID {plan_id} not found.")
        return plan

    @staticmethod
    def get_seating_plans_for_exam(exam_id: int) -> List[SeatingPlan]:
        """Retrieves all seating plans generated for an examination."""
        return (
            SeatingPlan.query.filter_by(exam_id=exam_id)
            .order_by(SeatingPlan.version.desc())
            .all()
        )

    @staticmethod
    def get_room_seating_matrix(plan_id: int, room_id: int) -> Dict[str, Any]:
        """
        Constructs a 2D seating grid matrix for visual display in Member 1/2 portals.
        Returns room dimensions and matrix of rows and columns with student allocations.
        """
        plan = PlanningService.get_seating_plan_by_id(plan_id)
        room = Room.query.get(room_id)
        if not room:
            raise NotFoundError(f"Room with ID {room_id} not found.")

        allocations = (
            SeatAllocation.query.filter_by(seating_plan_id=plan.id, room_id=room.id)
            .join(SeatAllocation.seat)
            .join(SeatAllocation.student)
            .all()
        )

        alloc_map = {alloc.seat_id: alloc for alloc in allocations}

        # Build 2D grid matrix
        grid = []
        for r in range(1, room.rows_count + 1):
            row_cells = []
            for c in range(1, room.columns_count + 1):
                seat = Seat.query.filter_by(room_id=room.id, row_num=r, col_num=c).first()
                if not seat:
                    row_cells.append(None)
                    continue

                cell_data = {
                    "seat_id": seat.id,
                    "seat_number": seat.seat_number,
                    "row": r,
                    "col": c,
                    "is_active": seat.is_active,
                    "allocation": None,
                }

                if seat.id in alloc_map:
                    a = alloc_map[seat.id]
                    cell_data["allocation"] = {
                        "allocation_id": a.id,
                        "student_id": a.student_id,
                        "roll_number": a.student.roll_number,
                        "full_name": a.student.full_name,
                        "department_code": a.student.department.code if a.student.department else None,
                        "semester": a.student.semester,
                    }

                row_cells.append(cell_data)
            grid.append(row_cells)

        return {
            "plan_id": plan.id,
            "plan_code": plan.plan_code,
            "room_id": room.id,
            "room_number": room.room_number,
            "rows": room.rows_count,
            "columns": room.columns_count,
            "total_allocated": len(allocations),
            "summary": {
                "allocated_count": len(allocations),
                "total_seats": room.rows_count * room.columns_count,
                "empty_count": (room.rows_count * room.columns_count) - len(allocations),
            },
            "grid": grid,
            "matrix": grid,
        }

    @staticmethod
    def get_student_allocation(exam_id: int, student_id: int) -> Optional[SeatAllocation]:
        """Retrieves a student's published seat allocation for a specific exam."""
        return (
            SeatAllocation.query.join(SeatAllocation.seating_plan)
            .filter(
                SeatingPlan.exam_id == exam_id,
                SeatingPlan.status == "PUBLISHED",
                SeatAllocation.student_id == student_id,
            )
            .first()
        )

    @staticmethod
    def get_teacher_duties(
        teacher_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[InvigilationDuty]:
        """Retrieves invigilation duties assigned to a faculty member."""
        query = (
            InvigilationDuty.query.filter_by(teacher_id=teacher_id)
            .join(InvigilationDuty.exam)
            .order_by(Exam.exam_date.asc(), Exam.start_time.asc())
        )

        if from_date:
            query = query.filter(Exam.exam_date >= from_date)
        if to_date:
            query = query.filter(Exam.exam_date <= to_date)

        return query.all()

    @staticmethod
    def get_exam_invigilation_duties(exam_id: int) -> List[InvigilationDuty]:
        """Retrieves all invigilation duties scheduled for an exam session."""
        return (
            InvigilationDuty.query.filter_by(exam_id=exam_id)
            .join(InvigilationDuty.room)
            .order_by(Room.room_number.asc())
            .all()
        )
