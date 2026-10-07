"""
Realistic Polytechnic Database Seeder (Phase 17).
Populates the PostgreSQL database with comprehensive, coherent, and realistic
Polytechnic / Diploma institution examination planning data.

Target Domain: Diploma / Polytechnic Institutions (Version 1).
Disciplines: Computer, IT, Mechanical, Civil, Electrical, Electronics Engineering.
Structure:
  Institution -> Departments -> Subjects (Semesters 1-6) -> Examination Timetables
  -> Rooms & Physical Grid Seats -> Faculty & Workload Limits -> Students
  -> Subject Enrollments -> Seating Plans & Allocations -> Invigilation Duties
  -> Duty Swaps -> Notifications -> Audit Trails.

Usage:
  python seed.py          # Seeds initial data (idempotent if already seeded)
  python seed.py --reset  # Cleans existing tables and re-seeds from scratch
"""

import sys
import argparse
from datetime import datetime, date, time
from typing import Dict, List, Any

from app import create_app
from app.extensions import db
from app.models.user import User
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

from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.room_service import RoomService
from app.services.teacher_service import TeacherService
from app.services.student_service import StudentService
from app.services.exam_service import ExamService
from app.services.registration_service import RegistrationService
from app.services.planning_service import PlanningService
from app.services.notification_service import NotificationService
from app.utils.audit import log_audit


def reset_database() -> None:
    """Wipes all transactional and master data in reverse dependency order."""
    print("[*] Resetting database tables...")
    Notification.query.delete()
    DutySwap.query.delete()
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
    AuditLog.query.delete()
    User.query.delete()
    db.session.commit()
    print("[+] All database tables cleared successfully.")


def seed_admin_users() -> Dict[str, User]:
    """Creates institutional exam cell administrators."""
    print("[*] Seeding Administrative Accounts...")
    admins = {}

    admin_data = [
        ("admin", "admin@polytechnic.ac.in", "Admin@12345", "Institutional Administrator"),
        ("coe_admin", "coe@polytechnic.ac.in", "Admin@12345", "Controller of Examinations"),
    ]

    for uname, email, pwd, label in admin_data:
        user = User.query.filter_by(username=uname).first()
        if not user:
            _, user, _ = AuthService.create_user(
                username=uname,
                email=email,
                password=pwd,
                role="ADMIN",
            )
            print(f"  [+] Created Admin: {uname} ({label})")
        admins[uname] = user

    return admins


def seed_departments() -> Dict[str, Department]:
    """Creates standard Polytechnic Diploma engineering branches."""
    print("[*] Seeding Polytechnic Departments...")
    depts = {}
    dept_definitions = [
        ("CO", "Computer Engineering", "Department of Computer Engineering & Software Applications"),
        ("IT", "Information Technology", "Department of Information Technology & Cyber Infrastructure"),
        ("ME", "Mechanical Engineering", "Department of Mechanical Engineering & Thermal Science"),
        ("CE", "Civil Engineering", "Department of Civil & Construction Technology"),
        ("EE", "Electrical Engineering", "Department of Electrical Power & Machines"),
        ("EJ", "Electronics & Telecommunication", "Department of Electronics & Communication Systems"),
    ]

    for code, name, desc in dept_definitions:
        dept = Department.query.filter_by(code=code).first()
        if not dept:
            dept = AcademicService.create_department(code=code, name=name, description=desc)
            print(f"  [+] Created Department: [{code}] {name}")
        depts[code] = dept

    return depts


def seed_subjects(depts: Dict[str, Department]) -> Dict[str, Subject]:
    """Creates diploma subjects strictly for Semesters 1 to 6 (AICTE / MSBTE scheme)."""
    print("[*] Seeding Polytechnic Curricular Subjects (Semesters 1-6)...")
    subjects = {}

    subject_data = [
        # Common / First Year (Semester 1 & 2)
        ("22101", "English", "CO", 1, "I-SCHEME", 3),
        ("22102", "Basic Science", "CO", 1, "I-SCHEME", 4),
        ("22103", "Basic Mathematics", "CO", 1, "I-SCHEME", 4),
        ("22224", "Applied Mathematics", "CO", 2, "I-SCHEME", 4),
        ("22226", "Programming in C", "CO", 2, "I-SCHEME", 4),
        # Computer Engineering (CO)
        ("22316", "Object Oriented Programming Using C++", "CO", 3, "I-SCHEME", 4),
        ("22317", "Data Structures Using C", "CO", 3, "I-SCHEME", 5),
        ("22318", "Computer Graphics", "CO", 3, "I-SCHEME", 3),
        ("22412", "Java Programming", "CO", 4, "I-SCHEME", 5),
        ("22413", "Software Engineering", "CO", 4, "I-SCHEME", 4),
        ("22414", "Database Management System", "CO", 4, "I-SCHEME", 4),
        ("22516", "Operating Systems", "CO", 5, "I-SCHEME", 4),
        ("22517", "Advanced Java Programming", "CO", 5, "I-SCHEME", 5),
        ("22616", "Network & Information Security", "CO", 6, "I-SCHEME", 4),
        ("22617", "Mobile Application Development", "CO", 6, "I-SCHEME", 5),
        # Information Technology (IT)
        ("22319", "Database Systems", "IT", 3, "I-SCHEME", 4),
        ("22415", "Web Development using PHP", "IT", 4, "I-SCHEME", 4),
        # Mechanical Engineering (ME)
        ("22306", "Strength of Materials", "ME", 3, "I-SCHEME", 4),
        ("22310", "Basic Mechanical Engineering", "ME", 3, "I-SCHEME", 3),
        ("22438", "Theory of Machines", "ME", 4, "I-SCHEME", 4),
        ("22562", "Advanced Manufacturing Processes", "ME", 5, "I-SCHEME", 4),
        # Civil Engineering (CE)
        ("22305", "Building Construction", "CE", 3, "I-SCHEME", 4),
        ("22509", "Design of Steel & RCC Structures", "CE", 5, "I-SCHEME", 5),
        # Electrical Engineering (EE)
        ("22311", "Electrical Circuits & Networks", "EE", 3, "I-SCHEME", 4),
        # Electronics (EJ)
        ("22320", "Digital Techniques", "EJ", 3, "I-SCHEME", 4),
    ]

    for code, name, dept_code, sem, scheme, credits in subject_data:
        subj = Subject.query.filter_by(code=code).first()
        if not subj:
            subj = AcademicService.create_subject(
                code=code,
                name=name,
                department_id=depts[dept_code].id,
                semester=sem,
                scheme=scheme,
                credits=credits,
            )
            print(f"  [+] Created Subject: [{code}] {name} (Sem {sem})")
        subjects[code] = subj

    return subjects


def seed_rooms() -> Dict[str, Room]:
    """Creates examination lecture halls and auto-generates coordinate seat grids."""
    print("[*] Seeding Examination Halls and Physical Seat Grids...")
    rooms = {}

    room_data = [
        ("LH-101", "Main Academic Block", 1, 5, 6, 30),
        ("LH-102", "Main Academic Block", 1, 5, 6, 30),
        ("LH-201", "Main Academic Block", 2, 6, 6, 36),
        ("LH-202", "Main Academic Block", 2, 6, 6, 36),
        ("MB-301", "Mechanical Workshop Block", 3, 8, 6, 48),
        ("CS-LAB1", "IT Computing Center", 1, 4, 5, 20),
    ]

    for room_num, bldg, floor, rows, cols, cap in room_data:
        room = Room.query.filter_by(room_number=room_num).first()
        if not room:
            room = RoomService.create_room({
                "room_number": room_num,
                "building": bldg,
                "floor": floor,
                "rows_count": rows,
                "columns_count": cols,
                "actual_capacity": cap,
            })
            print(f"  [+] Created Room {room_num} ({rows}x{cols} = {cap} physical seats generated)")
        rooms[room_num] = room

    return rooms


def seed_teachers(depts: Dict[str, Department]) -> Dict[str, Teacher]:
    """Creates polytechnic faculty accounts across departments."""
    print("[*] Seeding Faculty & Staff...")
    teachers = {}

    teacher_data = [
        ("dr_kulkarni", "anand.kulkarni@polytechnic.ac.in", "Anand", "Kulkarni", "CO", "EMP-CO-01", "HOD", 6),
        ("prof_patil", "suresh.patil@polytechnic.ac.in", "Suresh", "Patil", "CO", "EMP-CO-02", "Lecturer", 5),
        ("prof_deshmukh", "sunita.deshmukh@polytechnic.ac.in", "Sunita", "Deshmukh", "CO", "EMP-CO-03", "Lecturer", 5),
        ("dr_shinde", "ramesh.shinde@polytechnic.ac.in", "Ramesh", "Shinde", "ME", "EMP-ME-01", "HOD", 6),
        ("prof_jadhav", "manoj.jadhav@polytechnic.ac.in", "Manoj", "Jadhav", "ME", "EMP-ME-02", "Lecturer", 5),
        ("prof_iyer", "meena.iyer@polytechnic.ac.in", "Meena", "Iyer", "IT", "EMP-IT-01", "HOD", 6),
        ("prof_verma", "rajesh.verma@polytechnic.ac.in", "Rajesh", "Verma", "IT", "EMP-IT-02", "Lecturer", 5),
        ("dr_joshi", "prakash.joshi@polytechnic.ac.in", "Prakash", "Joshi", "CE", "EMP-CE-01", "HOD", 6),
        ("prof_sawant", "snehal.sawant@polytechnic.ac.in", "Snehal", "Sawant", "EE", "EMP-EE-01", "Lecturer", 5),
        ("prof_more", "nitin.more@polytechnic.ac.in", "Nitin", "More", "EJ", "EMP-EJ-01", "Lecturer", 5),
    ]

    for uname, email, fname, lname, dept_code, emp_id, desig, max_d in teacher_data:
        teacher = Teacher.query.filter_by(employee_id=emp_id).first()
        if not teacher:
            teacher = TeacherService.create_teacher({
                "username": uname,
                "email": email,
                "password": "Password123!",
                "first_name": fname,
                "last_name": lname,
                "department_id": depts[dept_code].id,
                "employee_id": emp_id,
                "designation": desig,
                "max_duties": max_d,
            })
            print(f"  [+] Created Faculty: {fname} {lname} [{emp_id}] ({desig}, Dept: {dept_code})")
        teachers[uname] = teacher

    # Record sample leave / availability for testing conflict algorithms
    prof_jadhav = teachers["prof_jadhav"]
    TeacherService.set_teacher_availability(
        teacher_id=prof_jadhav.id,
        date_val=date(2026, 11, 23),
        time_slot="MORNING",
        is_available=False,
        reason="Attending AICTE Faculty Development Program on Robotics",
    )
    print("  [+] Recorded Leave / Unavailability for Prof. Manoj Jadhav on 2026-11-23 (Morning)")

    return teachers


def seed_students(depts: Dict[str, Department]) -> List[Student]:
    """Creates polytechnic students across branches and semesters."""
    print("[*] Seeding Polytechnic Diploma Students...")
    students = []

    student_data = [
        # Computer Engineering - Semester 3
        ("rahul_s", "rahul.sharma@poly.ac.in", "Rahul", "Sharma", "CO", "CO2401", "2400150001", 3, "A"),
        ("sneha_p", "sneha.patil@poly.ac.in", "Sneha", "Patil", "CO", "CO2402", "2400150002", 3, "A"),
        ("amit_d", "amit.deshmukh@poly.ac.in", "Amit", "Deshmukh", "CO", "CO2403", "2400150003", 3, "A"),
        ("pooja_k", "pooja.kadam@poly.ac.in", "Pooja", "Kadam", "CO", "CO2404", "2400150004", 3, "A"),
        ("rohan_j", "rohan.joshi@poly.ac.in", "Rohan", "Joshi", "CO", "CO2405", "2400150005", 3, "A"),
        ("priya_n", "priya.nair@poly.ac.in", "Priya", "Nair", "CO", "CO2406", "2400150006", 3, "A"),
        ("tanmay_b", "tanmay.bhosale@poly.ac.in", "Tanmay", "Bhosale", "CO", "CO2407", "2400150007", 3, "A"),
        ("ananya_m", "ananya.mane@poly.ac.in", "Ananya", "Mane", "CO", "CO2408", "2400150008", 3, "A"),
        ("vikas_y", "vikas.yadav@poly.ac.in", "Vikas", "Yadav", "CO", "CO2409", "2400150009", 3, "A"),
        ("neha_s", "neha.shinde@poly.ac.in", "Neha", "Shinde", "CO", "CO2410", "2400150010", 3, "A"),
        # Mechanical Engineering - Semester 3
        ("aditya_k", "aditya.kulkarni@poly.ac.in", "Aditya", "Kulkarni", "ME", "ME2401", "2400160001", 3, "A"),
        ("kunal_p", "kunal.pawar@poly.ac.in", "Kunal", "Pawar", "ME", "ME2402", "2400160002", 3, "A"),
        ("sanket_g", "sanket.gaikwad@poly.ac.in", "Sanket", "Gaikwad", "ME", "ME2403", "2400160003", 3, "A"),
        ("pranav_s", "pranav.sawant@poly.ac.in", "Pranav", "Sawant", "ME", "ME2404", "2400160004", 3, "A"),
        # Information Technology - Semester 3
        ("divya_t", "divya.thorat@poly.ac.in", "Divya", "Thorat", "IT", "IT2401", "2400170001", 3, "A"),
        ("varun_m", "varun.mehta@poly.ac.in", "Varun", "Mehta", "IT", "IT2402", "2400170002", 3, "A"),
        # First Year Common - Semester 1
        ("atharva_j", "atharva.joshi@poly.ac.in", "Atharva", "Joshi", "CO", "FY2401", "2400110001", 1, "A"),
        ("riya_c", "riya.chavan@poly.ac.in", "Riya", "Chavan", "CO", "FY2402", "2400110002", 1, "A"),
        ("samir_k", "samir.khan@poly.ac.in", "Samir", "Khan", "ME", "FY2403", "2400110003", 1, "A"),
        ("tanvi_r", "tanvi.raut@poly.ac.in", "Tanvi", "Raut", "EE", "FY2404", "2400110004", 1, "A"),
    ]

    for uname, email, fname, lname, dept_code, roll, enr, sem, div in student_data:
        student = Student.query.filter_by(roll_number=roll).first()
        if not student:
            student = StudentService.create_student({
                "username": uname,
                "email": email,
                "password": "Password123!",
                "first_name": fname,
                "last_name": lname,
                "department_id": depts[dept_code].id,
                "roll_number": roll,
                "enrollment_number": enr,
                "semester": sem,
                "division": div,
                "academic_year": "2026-2027",
            })
            print(f"  [+] Created Student: {fname} {lname} [{roll}] (Sem {sem}-{div}, Dept: {dept_code})")
        students.append(student)

    return students


def seed_exams_and_registrations(
    subjects: Dict[str, Subject], students: List[Student]
) -> Dict[str, Exam]:
    """Schedules realistic diploma examination sessions and registers student cohorts."""
    print("[*] Scheduling Winter 2026 Examinations & Candidate Registrations...")
    exams = {}

    exam_schedules = [
        ("EXAM-W26-22317", "Data Structures Using C Exam", "22317", date(2026, 11, 20), time(10, 0), time(13, 0), "MORNING"),
        ("EXAM-W26-22316", "OOP Using C++ Exam", "22316", date(2026, 11, 23), time(10, 0), time(13, 0), "MORNING"),
        ("EXAM-W26-22306", "Strength of Materials Exam", "22306", date(2026, 11, 20), time(10, 0), time(13, 0), "MORNING"),
        ("EXAM-W26-22101", "First Year English Exam", "22101", date(2026, 11, 25), time(14, 0), time(17, 0), "AFTERNOON"),
    ]

    for code, title, subj_code, ex_date, s_time, e_time, session in exam_schedules:
        exam = Exam.query.filter_by(exam_code=code).first()
        if not exam:
            exam = ExamService.create_exam({
                "subject_id": subjects[subj_code].id,
                "exam_code": code,
                "title": title,
                "exam_date": ex_date,
                "start_time": s_time,
                "end_time": e_time,
                "session_name": session,
            })
            print(f"  [+] Scheduled Exam: [{code}] {title} on {ex_date} ({session})")
        exams[code] = exam

    # Register students based on their department and semester
    exam_ds = exams["EXAM-W26-22317"]
    exam_oop = exams["EXAM-W26-22316"]
    exam_som = exams["EXAM-W26-22306"]
    exam_eng = exams["EXAM-W26-22101"]

    for st in students:
        if st.department.code == "CO" and st.semester == 3:
            RegistrationService.register_student(student_id=st.id, exam_id=exam_ds.id)
            RegistrationService.register_student(student_id=st.id, exam_id=exam_oop.id)
        elif st.department.code == "ME" and st.semester == 3:
            RegistrationService.register_student(student_id=st.id, exam_id=exam_som.id)
        elif st.semester == 1:
            RegistrationService.register_student(student_id=st.id, exam_id=exam_eng.id)

    print(f"  [+] Enrolled {exam_ds.total_registered} students in {exam_ds.exam_code}")
    print(f"  [+] Enrolled {exam_som.total_registered} students in {exam_som.exam_code}")
    print(f"  [+] Enrolled {exam_eng.total_registered} students in {exam_eng.exam_code}")

    return exams


def seed_seating_and_invigilation(
    exams: Dict[str, Exam],
    rooms: Dict[str, Room],
    teachers: Dict[str, Teacher],
    admins: Dict[str, User],
) -> None:
    """Generates seating arrangements, publishes seating plans, and assigns invigilation duties."""
    print("[*] Generating Seating Plans and Invigilation Rosters...")

    admin_user = admins["admin"]

    # 1. Generate & Publish Seating Plan for Data Structures (LH-101)
    exam_ds = exams["EXAM-W26-22317"]
    room_101 = rooms["LH-101"]
    plan_ds = PlanningService.generate_seating_plan(
        exam_id=exam_ds.id,
        room_ids=[room_101.id],
    )
    print(f"  [+] Generated Seating Plan {plan_ds.plan_code} for {exam_ds.exam_code} ({plan_ds.total_students_allocated} allocations)")

    # Publish Seating Plan (dispatches notifications to allocated students)
    published_plan = PlanningService.publish_seating_plan(plan_ds.id, operator_user_id=admin_user.id)
    print(f"  [+] Published Seating Plan {published_plan.plan_code} (Status: {published_plan.status})")

    # 2. Assign Invigilator for LH-101
    prof_patil = teachers["prof_patil"]
    duty_1 = InvigilationDuty(
        exam_id=exam_ds.id,
        teacher_id=prof_patil.id,
        room_id=room_101.id,
        duty_role="CHIEF_INVIGILATOR",
        status="ASSIGNED",
    )
    db.session.add(duty_1)
    db.session.commit()
    print(f"  [+] Assigned Chief Invigilator: Prof. Suresh Patil for Exam {exam_ds.exam_code} in {room_101.room_number}")

    # 3. Create a Peer Duty Swap Request (Prof. Patil requests swap with Prof. Deshmukh)
    prof_deshmukh = teachers["prof_deshmukh"]
    swap = TeacherService.request_duty_swap(
        duty_id=duty_1.id,
        requester_teacher_id=prof_patil.id,
        target_teacher_id=prof_deshmukh.id,
        reason="Attending family medical appointment at civil hospital",
    )
    print(f"  [+] Created Duty Swap Request #{swap.id}: Prof. Patil -> Prof. Deshmukh (Status: {swap.status})")

    # 4. Generate Draft Seating Plan for SOM (LH-102) - Unassigned/Draft state
    exam_som = exams["EXAM-W26-22306"]
    room_102 = rooms["LH-102"]
    plan_som = PlanningService.generate_seating_plan(
        exam_id=exam_som.id,
        room_ids=[room_102.id],
    )
    print(f"  [+] Generated Draft Seating Plan {plan_som.plan_code} for {exam_som.exam_code} (Draft state for admin review)")


def seed_announcements_and_audit(admins: Dict[str, User]) -> None:
    """Dispatches realistic announcements and records institutional audit events."""
    print("[*] Recording System Announcements and Institutional Audit Trails...")

    admin_user = admins["admin"]

    # Broadcast institutional notification to all students
    NotificationService.broadcast_notification(
        validated_data={
            "title": "Winter 2026 Polytechnic Examination Guidelines",
            "message": (
                "All candidates must report to their respective examination halls 30 minutes "
                "before commencement. Digital devices and programmable calculators are strictly prohibited."
            ),
            "target_role": "STUDENT",
            "notification_type": "BROADCAST",
        },
        sender_user_id=admin_user.id,
        ip_address="192.168.1.1",
    )
    print("  [+] Broadcast Institutional Advisory dispatched to all Polytechnic Students.")

    # Broadcast faculty advisory to all teachers
    NotificationService.broadcast_notification(
        validated_data={
            "title": "Invigilation Duties Roster & Guidelines",
            "message": (
                "Faculty members are requested to collect sealed question paper packets from the "
                "Exam Control Room 20 minutes before each session. Please report any student absence on the portal."
            ),
            "target_role": "TEACHER",
            "notification_type": "BROADCAST",
        },
        sender_user_id=admin_user.id,
        ip_address="192.168.1.1",
    )
    print("  [+] Broadcast Duty Advisory dispatched to all Polytechnic Faculty.")

    # Historical audit entries
    log_audit(
        action="INSTITUTION_INITIALIZED",
        entity_type="System",
        entity_id="POLY-MSBTE-2026",
        user_id=admin_user.id,
        details="Polytechnic Exam Seating & Invigilation Planner initialized with MSBTE I-Scheme curriculum.",
        ip_address="192.168.1.1",
    )
    print("  [+] System Audit Log entry recorded.")


def run_seeder(reset: bool = False) -> None:
    """Main seeder workflow orchestrator."""
    print("=" * 70)
    print("  SMART POLYTECHNIC EXAM SEATING & INVIGILATION PLANNER")
    print("  Phase 17 - Realistic Polytechnic Database Seeder (Version 1)")
    print("=" * 70)

    if reset:
        reset_database()
    else:
        # Check if master records already exist
        existing_depts = Department.query.count()
        if existing_depts > 0:
            print(f"[*] Found {existing_depts} existing departments in database.")
            print("[*] To re-create a clean dataset, run: python seed.py --reset")
            print("=" * 70)
            return

    # Execute structured seeding sequence
    admins = seed_admin_users()
    depts = seed_departments()
    subjects = seed_subjects(depts)
    rooms = seed_rooms()
    teachers = seed_teachers(depts)
    students = seed_students(depts)
    exams = seed_exams_and_registrations(subjects, students)
    seed_seating_and_invigilation(exams, rooms, teachers, admins)
    seed_announcements_and_audit(admins)

    print("=" * 70)
    print("  DATABASE SEEDING COMPLETED SUCCESSFULLY!")
    print(f"  * Departments:      {Department.query.count()}")
    print(f"  * Subjects:         {Subject.query.count()}")
    print(f"  * Exam Halls:       {Room.query.count()}")
    print(f"  * Physical Seats:   {Seat.query.count()}")
    print(f"  * Faculty:          {Teacher.query.count()}")
    print(f"  * Students:         {Student.query.count()}")
    print(f"  * Scheduled Exams:  {Exam.query.count()}")
    print(f"  * Registrations:    {Registration.query.count()}")
    print(f"  * Seating Plans:    {SeatingPlan.query.count()}")
    print(f"  * Seat Allocations: {SeatAllocation.query.count()}")
    print(f"  * Invigilation Duties: {InvigilationDuty.query.count()}")
    print(f"  * Duty Swaps:       {DutySwap.query.count()}")
    print(f"  * Notifications:    {Notification.query.count()}")
    print(f"  * Audit Logs:       {AuditLog.query.count()}")
    print("=" * 70)
    print("  DEFAULT CREDENTIALS FOR TESTING:")
    print("  - Admin:    admin / Admin@12345")
    print("  - Teacher:  prof_patil / Password123!")
    print("  - Student:  rahul_s / Password123!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed realistic Polytechnic examination data.")
    parser.add_argument("--reset", action="store_true", help="Clear all database tables before seeding.")
    args = parser.parse_args()

    env_name = "development"
    app = create_app(env_name)
    with app.app_context():
        run_seeder(reset=args.reset)
