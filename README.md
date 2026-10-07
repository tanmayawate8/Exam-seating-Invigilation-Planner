# 🎓 Smart Polytechnic Exam Seating & Invigilation Planner (Backend Core)

[![Tests Status](https://img.shields.io/badge/pytest-36%20passed-brightgreen.svg)](#automated-testing--verification)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL%2014+-blue.svg)](https://www.postgresql.org/)
[![Architecture](https://img.shields.io/badge/role-Member%203%20Backend%20Architect-orange.svg)](#system-architecture)

**Version 1.0 — Polytechnic / Diploma Institution Edition**  
Developed as the definitive backend engine, relational persistence layer, and REST API gateway for automated examination seating and invigilation logistics.

---

## 📋 Table of Contents
1. [Institutional Domain & Scope](#institutional-domain--scope)
2. [System Architecture & Tech Stack](#system-architecture--tech-stack)
3. [Relational Database Schema (17 Tables)](#relational-database-schema-17-tables)
4. [Environment Setup & Quickstart](#environment-setup--quickstart)
5. [Database Seeder & Test Accounts](#database-seeder--test-accounts)
6. [Complete REST API Specification Catalog](#complete-rest-api-specification-catalog)
   - [1. Authentication & Session (`/api/auth`)](#1-authentication--session-apiauth)
   - [2. Departments & Semesters (`/api/departments`)](#2-departments--semesters-apidepartments)
   - [3. Curriculum Subjects (`/api/subjects`)](#3-curriculum-subjects-apisubjects)
   - [4. Student Directory (`/api/students`)](#4-student-directory-apistudents)
   - [5. Faculty & Staff (`/api/teachers`)](#5-faculty--staff-apiteachers)
   - [6. Examination Halls & Seats (`/api/rooms`)](#6-examination-halls--seats-apirooms)
   - [7. Exam Timetables & Registration (`/api/exams`)](#7-exam-timetables--registration-apiexams)
   - [8. Seating & Invigilation Planning (`/api/planning`)](#8-seating--invigilation-planning-apiplanning)
   - [9. Dedicated Student Portal (`/api/student`)](#9-dedicated-student-portal-apistudent)
   - [10. Dedicated Faculty Portal (`/api/teacher`)](#10-dedicated-faculty-portal-apiteacher)
   - [11. Notifications Hub (`/api/notifications`)](#11-notifications-hub-apinotifications)
   - [12. Forensic Audit Trail (`/api/audit-logs`)](#12-forensic-audit-trail-apiaudit-logs)
   - [13. Document Reports & Exports Gateway (`/api/reports`)](#13-document-reports--exports-gateway-apireports)
7. [Team Integration Guide & Data Contracts](#team-integration-guide--data-contracts)
   - [Member 1: Admin Web Portal](#member-1-admin-web-portal-integration)
   - [Member 2: Student & Faculty Web Portals](#member-2-student--faculty-portals-integration)
   - [Member 4: Optimization Algorithms & Reports](#member-4-optimization-algorithms--reports-gateway)
8. [Automated Testing & Verification](#automated-testing--verification)

---

## 🏛 Institutional Domain & Scope

Version 1 is strictly customized for **Diploma & Polytechnic Institutions** (governed by frameworks such as MSBTE / AICTE / State Technical Boards). School or 4-year degree structures are excluded.

### Core Domain Rules
* **3-Year Diploma Structure**: Strictly Semesters 1 through 6 (`1, 2, 3, 4, 5, 6`).
* **Engineering Disciplines**:
  - `CO` — Computer Engineering
  - `IT` — Information Technology
  - `ME` — Mechanical Engineering
  - `CE` — Civil Engineering
  - `EE` — Electrical Engineering
  - `EJ` — Electronics & Telecommunication Engineering
* **Exam Sessions**: Morning (`10:00 AM - 01:00 PM`) and Afternoon (`02:00 PM - 05:00 PM`).
* **Seat Arrangement Rules**:
  - 2D Hall Matrix ($R \text{ rows} \times C \text{ columns}$).
  - Strict anti-cheating separation: Students belonging to the same department and semester cannot sit in adjacent seats.
  - Damaged or inactive seats are dynamically skipped during allocation.
* **Faculty Invigilation Constraints**:
  - Conflict of interest prevention: Faculty members are never assigned to invigilate exams of their own teaching department.
  - Workload caps: Strict upper limit on consecutive sessions and total duties per faculty member.
  - Faculty availability / leave calendars are respected.
  - Peer-to-peer duty swap requests require institutional exam cell administrator approval.

---

## 🏗 System Architecture & Tech Stack

```
   ┌───────────────────────────────────────────────────────────────┐
   │                  Member 1: Admin Web Portal                   │
   │            Member 2: Student & Faculty Portals                │
   │           Member 4: External Algorithmic Runners              │
   └───────────────────────────────┬───────────────────────────────┘
                                   │ HTTP / JSON REST APIs (Session Cookies / RBAC)
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │                   Flask Application Server                    │
   │  ┌─────────────────────────────────────────────────────────┐  │
   │  │ 13 REST API Blueprints (Auth, Academics, Planning, etc.)│  │
   │  └────────────────────────────┬────────────────────────────┘  │
   │                               │ Invokes Service Logic         │
   │  ┌────────────────────────────▼────────────────────────────┐  │
   │  │ Service Layer (AuthService, PlanningService, Reports)   │  │
   │  └────────────────────────────┬────────────────────────────┘  │
   │                               │ Validates & Orchestrates      │
   │  ┌────────────────────────────▼────────────────────────────┐  │
   │  │ Data Contracts (`app/contracts/`)                       │  │
   │  │ ReportLab (PDF Engine) & openpyxl (Excel Engine)        │  │
   │  └────────────────────────────┬────────────────────────────┘  │
   │                               │ SQLAlchemy ORM                │
   └───────────────────────────────┼───────────────────────────────┘
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │              PostgreSQL Relational Database                   │
   │          17 Normalized Tables with Audit Logging              │
   └───────────────────────────────────────────────────────────────┘
```

* **Core Framework**: Flask 3.0+ (Application Factory Pattern with environment configuration)
* **ORM & Database**: SQLAlchemy 2.0+ & PostgreSQL 14+ with Alembic / Flask-Migrate
* **Authentication**: Flask-Login session management with PBKDF2/scrypt password hashing
* **Access Control**: Role-Based Access Control (`ADMIN`, `TEACHER`, `STUDENT`) with custom decorators
* **Report Generation**: ReportLab 4.x (vector PDF documents) & openpyxl (Excel workbooks)
* **Test Suite**: pytest 8.x with SQLite in-memory and PostgreSQL test runners

---

## 🗄 Relational Database Schema (17 Tables)

```mermaid
erDiagram
    users ||--o| teachers : "profile"
    users ||--o| students : "profile"
    users ||--o{ notifications : "receives"
    users ||--o{ audit_logs : "triggers"
    departments ||--o{ subjects : "offers"
    departments ||--o{ teachers : "employs"
    departments ||--o{ students : "enrolls"
    subjects ||--o{ exams : "scheduled for"
    rooms ||--o{ seats : "contains"
    exams ||--o{ registrations : "enrolls"
    students ||--o{ registrations : "registers"
    exams ||--o{ seating_plans : "generates"
    seating_plans ||--o{ seat_allocations : "maps"
    seats ||--o{ seat_allocations : "assigned"
    students ||--o{ seat_allocations : "occupies"
    exams ||--o{ invigilation_duties : "requires"
    teachers ||--o{ invigilation_duties : "performs"
    rooms ||--o{ invigilation_duties : "supervises"
    invigilation_duties ||--o{ duty_swaps : "requested swap"
    teachers ||--o{ teacher_availabilities : "declares"
```

### Table Dictionary
1. `users`: Master authentication credentials, role flags (`ADMIN`, `TEACHER`, `STUDENT`), and active status.
2. `departments`: Polytechnic engineering branches (`CO`, `IT`, `ME`, `CE`, `EE`, `EJ`).
3. `subjects`: Curricular course modules with semester tags (1–6), credits, and scheme codes.
4. `teachers`: Faculty member records, designations, department links, and duty limits.
5. `teacher_availabilities`: Session-level leave and unavailability declarations for faculty.
6. `students`: Student records, enrollment numbers, roll numbers, semesters, and divisions.
7. `rooms`: Examination halls, buildings, floors, row/column dimensions, and capacity.
8. `seats`: Individual physical chairs with row/col coordinates and functional condition flags.
9. `exams`: Scheduled examination sessions, date, start/end times, and lifecycle status.
10. `registrations`: Student enrollment in specific exams, eligibility flags, and attendance.
11. `seating_plans`: Versioned master seating plan records (`DRAFT`, `PUBLISHED`, `CANCELLED`).
12. `seat_allocations`: Individual mappings linking student, seat, room, and seating plan.
13. `invigilation_duties`: Assigned supervisory roles (`CHIEF_INVIGILATOR`, `ASSISTANT_INVIGILATOR`).
14. `duty_swaps`: Peer faculty swap requests, reasons, target teachers, and administrative review status.
15. `notifications`: In-app notification messages, unread flags, and cohort broadcasts.
16. `audit_logs`: Immutable forensic audit trail capturing actor ID, action, entity, and IP address.
17. `alembic_version`: Database migration tracking table.

---

## 🚀 Environment Setup & Quickstart

### Prerequisites
* Python 3.10 to 3.13
* PostgreSQL 14 or higher
* Git

### 1. Clone Repository & Create Virtual Environment
```bash
git clone <repository_url>
cd "exam-planner"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)
Create a `.env` file in the root directory:
```ini
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
PORT=5000

# Security Secret Key
SECRET_KEY=exam-planner-secret-key-polytechnic-2026-xyz

# PostgreSQL Database Connections
DATABASE_URL=postgresql://postgres:123456@localhost:5432/exam_seating_planner
TEST_DATABASE_URL=sqlite:///:memory:
```

### 4. Create Database & Apply Migrations
Ensure PostgreSQL is running, create the database, and run migrations:
```bash
# In PostgreSQL CLI:
CREATE DATABASE exam_seating_planner;

# Apply Alembic Migrations:
flask db upgrade
```

### 5. Seed Realistic Polytechnic Data
```bash
# Reset any previous records and seed fresh institutional data:
python seed.py --reset

# Alternatively via Flask CLI:
flask seed --reset
```

### 6. Run Application Server
```bash
python run.py
```
Server starts on `http://127.0.0.1:5000`.

---

## 🔑 Database Seeder & Test Accounts

The seeder (`seed.py`) populates realistic Polytechnic data:
* 6 Departments (`CO`, `IT`, `ME`, `CE`, `EE`, `EJ`)
* 24 Curricular Subjects (Semesters 1 through 6)
* 4 Examination Venues with 2D Seat Grids (80 physical seats generated)
* 10 Faculty Members with workload limits and leave calendars
* 30 Polytechnic Students across branches
* 4 Scheduled Examination Sessions with registrations
* Generated Seating Plans, Invigilation Duties, Notifications, and Audit Logs

### Default Credentials

| Role | Username | Password | Email | Full Name / Description |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@12345` | `admin@polytechnic.ac.in` | Institutional Administrator |
| **Admin** | `coe_admin` | `Admin@12345` | `coe@polytechnic.ac.in` | Controller of Examinations |
| **Faculty (CO)** | `dr_kulkarni` | `Password123!` | `anand.kulkarni@polytechnic.ac.in` | Dr. Anand Kulkarni (HOD) |
| **Faculty (CO)** | `prof_patil` | `Password123!` | `suresh.patil@polytechnic.ac.in` | Prof. Suresh Patil (Lecturer) |
| **Faculty (ME)** | `dr_shinde` | `Password123!` | `ramesh.shinde@polytechnic.ac.in` | Dr. Ramesh Shinde (HOD) |
| **Faculty (ME)** | `prof_jadhav` | `Password123!` | `manoj.jadhav@polytechnic.ac.in` | Prof. Manoj Jadhav (Leave on 2026-11-23) |
| **Student (CO)** | `rahul_s` | `Password123!` | `rahul.sharma@poly.ac.in` | Rahul Sharma (Roll: CO2401, Sem 3) |
| **Student (CO)** | `sneha_p` | `Password123!` | `sneha.patil@poly.ac.in` | Sneha Patil (Roll: CO2402, Sem 3) |
| **Student (ME)** | `amit_m` | `Password123!` | `amit.more@poly.ac.in` | Amit More (Roll: ME2401, Sem 3) |

---

## 📖 Complete REST API Specification Catalog

Standard API Response Envelope:
```json
{
  "success": true,
  "data": { ... },
  "message": "Human readable confirmation.",
  "meta": { "pagination": { "page": 1, "per_page": 20, "total": 100 } }
}
```

---

### 1. Authentication & Session (`/api/auth`)
Mounted on `/api/auth`. Manages user sessions via HTTP cookies.

| Method | Endpoint | Access | Description & Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/auth/ping` | Public | Blueprint health ping. |
| `POST` | `/api/auth/login` | Public | **Body**: `{"username": "admin", "password": "...", "remember": false}`. Establishes session. |
| `POST` | `/api/auth/logout` | Authenticated | Terminates active user session and clears cookie. |
| `GET` | `/api/auth/me` | Authenticated | Retrieves current authenticated user profile and roles. |
| `POST` | `/api/auth/change-password` | Authenticated | **Body**: `{"current_password": "...", "new_password": "...", "confirm_password": "..."}`. |

---

### 2. Departments & Semesters (`/api/departments`)
Mounted on `/api/departments`. Manages academic disciplines.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/departments` | Authenticated | List all departments. Optional `?search=comp`. |
| `GET` | `/api/departments/semesters` | Authenticated | Returns standard 6-semester Polytechnic structure `[1, 2, 3, 4, 5, 6]`. |
| `GET` | `/api/departments/<id>` | Authenticated | Retrieve single department by primary key ID. |
| `POST` | `/api/departments` | Admin | **Body**: `{"code": "CO", "name": "Computer Engineering", "description": "..."}`. |
| `PUT` | `/api/departments/<id>` | Admin | **Body**: `{"name": "...", "description": "..."}`. |
| `DELETE` | `/api/departments/<id>` | Admin | Removes department if no students or subjects are linked. |

---

### 3. Curriculum Subjects (`/api/subjects`)
Mounted on `/api/subjects`. Manages courses across Semesters 1–6.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/subjects` | Authenticated | Filter by `?department_id=1&semester=3&search=data`. |
| `GET` | `/api/subjects/<id>` | Authenticated | Retrieve subject details. |
| `POST` | `/api/subjects` | Admin | **Body**: `{"code": "22317", "name": "Data Structures", "department_id": 1, "semester": 3, "credits": 4}`. |
| `PUT` | `/api/subjects/<id>` | Admin | Update subject attributes. |
| `DELETE` | `/api/subjects/<id>` | Admin | Deletes subject if unreferenced in active exams. |

---

### 4. Student Directory & Roll-Call Import (`/api/students`)
Mounted on `/api/students`. Administrative management of student records and official roll-call data imports (based on official TYCO C Roll-Call specification).

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/students` | Admin, Teacher | Paginated list. `?page=1&per_page=20&department_id=1&semester=3&is_active=true&search=rahul`. |
| `GET` | `/api/students/<id>` | Admin, Teacher, Self | Single student profile (parent contact numbers protected by default). |
| `POST` | `/api/students` | Admin | Manual single-student enrollment. |
| `PUT` | `/api/students/<id>` | Admin | Update student attributes. |
| `PATCH` | `/api/students/<id>/status` | Admin | **Body**: `{"is_active": false}`. Activates or deactivates student. |
| `DELETE` | `/api/students/<id>` | Admin | Removes student record and linked user credentials. |
| `GET` | `/api/students/import/template` | Admin | `?format=excel` or `?format=csv`. Downloads official student import template based on TYCO C Roll-Call structure. |
| `POST` | `/api/students/import/preview` | Admin | Multipart upload or JSON `{"rows": [...]}`. Validates academic references, checks duplicates in file/DB, flags malformed records, and returns preview report. |
| `POST` | `/api/students/import/commit` | Admin | **Body**: `{"rows": [...]}`. Commits validated students inside atomic PostgreSQL transaction; creates student profiles and linked User accounts with initial password = Enrollment Number from the official roll call (hashed securely). |

#### 🎓 Official Student Data Import Specification (TYCO C Roll-Call Reference)
* **Institutional Mapping**:
  * **Department**: Computer Engineering (`CO`)
  * **Semester**: `VI` (6)
  * **Class & Division**: `TYCO` - Division `C`
  * **Batches**: `C1` (Sr.No 01 to 35), `C2` (Sr.No 35 onwards)
  * **Academic Year**: `2026-2027`
  * **Class Teacher**: Prof. Poonam Chavhan
* **Student Identifier & Authentication**:
  * **Username / Identifier**: **Student Name** (e.g., `ADHAV HARSH NIVRUTTI`) or **Enrollment Number** (`24252271491`)
  * **Password**: **Enrollment Number** from the official roll-call PDF (e.g., `24252271491`)
  * **Security**: Initial password is the student's Enrollment Number, stored strictly as a secure cryptographic hash (`password_hash` via Werkzeug), never in plaintext.
  * **Duplicate Name Resolution**: Multiple students with identical names are disambiguated transparently using their unique institutional Enrollment Number.
  * **Privacy**: Parent contact numbers (`parent_contact_1`, `parent_contact_2`) are strictly kept administrative and never exposed on the public Student Portal.

---

### 5. Faculty & Staff (`/api/teachers`)
Mounted on `/api/teachers`. Faculty records, leave availability, and duty swaps.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/teachers` | Authenticated | Filter by `?page=1&per_page=20&department_id=1&designation=HOD&is_active=true&search=patil`. |
| `GET` | `/api/teachers/<id>` | Authenticated | Retrieve faculty member profile. |
| `POST` | `/api/teachers` | Admin | **Body**: `{"username": "...", "email": "...", "password": "...", "employee_id": "EMP-CO-01", "first_name": "...", "last_name": "...", "department_id": 1, "designation": "HOD", "max_duties": 6}`. |
| `PUT` | `/api/teachers/<id>` | Admin | Update faculty profile and duty quota. |
| `PATCH` | `/api/teachers/<id>/status` | Admin | **Body**: `{"is_active": false}`. |
| `DELETE` | `/api/teachers/<id>` | Admin | Deletes faculty record. |
| `POST` | `/api/teachers/<id>/availability` | Admin, Self | **Body**: `{"date": "2026-11-23", "time_slot": "MORNING", "is_available": false, "reason": "AICTE FDP"}`. |
| `GET` | `/api/teachers/<id>/duties` | Admin, Self | List assigned invigilation duties. `?status=ASSIGNED`. |
| `POST` | `/api/teachers/duty-swap` | Teacher | **Body**: `{"duty_id": 1, "target_teacher_id": 2, "reason": "Medical emergency"}`. |
| `PATCH` | `/api/teachers/duty-swap/<id>/review`| Admin | **Body**: `{"approve": true, "admin_comment": "Approved"}`. |

---

### 6. Examination Halls & Seats (`/api/rooms`)
Mounted on `/api/rooms`. Hall logistics, 2D capacity, and seat condition maintenance.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/rooms` | Authenticated | List rooms. `?building=Poly+Block&floor=1&is_active=true`. |
| `GET` | `/api/rooms/capacity-summary` | Authenticated | Aggregate capacity calculator. `?room_ids=1,2`. |
| `GET` | `/api/rooms/<id>` | Authenticated | Retrieve room details. `?include_seats=true` embeds seats. |
| `POST` | `/api/rooms` | Admin | **Body**: `{"room_number": "HALL-101", "building": "Main", "floor": 1, "rows_count": 5, "columns_count": 6, "capacity": 30}`. Automatically generates 30 physical seat coordinates. |
| `PUT` | `/api/rooms/<id>` | Admin | Update room metadata and dimensions. |
| `PATCH` | `/api/rooms/<id>/status` | Admin | **Body**: `{"is_active": false}`. |
| `DELETE` | `/api/rooms/<id>` | Admin | Deletes room if no active plans reference it. |
| `GET` | `/api/rooms/<id>/seats` | Authenticated | Retrieve seat list. `?is_active_only=true`. |
| `PATCH` | `/api/rooms/seats/<id>/status` | Admin | **Body**: `{"is_active": false}`. Marks damaged seat as disabled. |

---

### 7. Exam Timetables & Registration (`/api/exams`)
Mounted on `/api/exams`. Exam scheduling and student candidate enrollment.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/exams` | Authenticated | Filter by `?status=SCHEDULED&date=2026-11-20&department_id=1&semester=3`. |
| `GET` | `/api/exams/<id>` | Authenticated | Single exam timetable details. |
| `POST` | `/api/exams` | Admin | **Body**: `{"subject_id": 1, "exam_code": "EXAM-CO301", "title": "Data Structures", "exam_date": "2026-11-20", "start_time": "10:00:00", "end_time": "13:00:00", "session_name": "MORNING"}`. Checks schedule conflicts. |
| `PUT` | `/api/exams/<id>` | Admin | Update schedule times. |
| `PATCH` | `/api/exams/<id>/status` | Admin | **Body**: `{"status": "PLANNED"}` (`SCHEDULED`, `PLANNED`, `COMPLETED`, `CANCELLED`). |
| `DELETE` | `/api/exams/<id>` | Admin | Deletes unallocated exam session. |
| `GET` | `/api/exams/<id>/registrations` | Authenticated | Paginated enrolled candidate list. `?is_eligible=true&search=CO01`. |
| `POST` | `/api/exams/<id>/registrations` | Admin | **Body**: `{"student_id": 1, "is_eligible": true}`. Individual student enrollment. |
| `POST` | `/api/exams/<id>/bulk-enroll` | Admin | **Body**: `{"semester": 3}`. Enrolls entire branch semester cohort in batch. |
| `DELETE` | `/api/exams/<id>/registrations/<student_id>` | Admin | Deregisters candidate from examination. |
| `PATCH` | `/api/exams/registrations/<id>` | Admin | **Body**: `{"is_eligible": true, "attendance_status": "PRESENT"}`. |

---

### 8. Seating & Invigilation Planning (`/api/planning`)
Mounted on `/api/planning`. Execution engine for seating algorithms and faculty duty assignments.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/planning/seating/generate` | Admin | **Body**: `{"exam_id": 1, "room_ids": [1, 2]}`. Triggers Member 4 seating adapter and persists seat allocations atomically. |
| `GET` | `/api/planning/seating/<id>` | Authenticated | Master seating plan details and total allocations count. |
| `GET` | `/api/planning/seating/exam/<exam_id>` | Authenticated | All generated plan versions for an exam. |
| `POST` | `/api/planning/seating/<id>/publish` | Admin | Transitions status to `PUBLISHED` and sends notifications to all students. |
| `POST` | `/api/planning/seating/<id>/cancel` | Admin | Cancels seating plan. |
| `GET` | `/api/planning/seating/<plan_id>/matrix/<room_id>` | Authenticated | Returns 2D grid matrix of physical seats, row/col indices, and assigned student info for hall rendering. |
| `POST` | `/api/planning/invigilation/generate` | Admin | **Body**: `{"exam_id": 1, "room_ids": [1]}`. Triggers Member 4 invigilation adapter and persists faculty assignments. |
| `GET` | `/api/planning/invigilation/exam/<exam_id>` | Authenticated | All scheduled invigilator duties for exam session. |

---

### 9. Dedicated Student Portal (`/api/student`)
Mounted on `/api/student`. Student self-service endpoints and hall kiosk lookups.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/student/profile` | Student | Returns student's personal academic profile. |
| `GET` | `/api/student/timetable` | Student | Returns personalized examination timetable for enrolled subjects. |
| `GET` | `/api/student/my-seat` | Student | Returns published hall number, room, and seat coordinates. |
| `GET` | `/api/student/seat-search` | Public | **Kiosk lookup**: `?roll_number=CO2401&exam_id=1`. Enables public notice board search without login. |
| `GET` | `/api/student/notifications`| Student | Student notification announcements feed. |

---

### 10. Dedicated Faculty Portal (`/api/teacher`)
Mounted on `/api/teacher`. Faculty self-service endpoints and duty swap requests.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/teacher/profile` | Teacher | Returns teacher's profile and duty metrics. |
| `GET` | `/api/teacher/duties` | Teacher | Returns assigned invigilation duties. Optional `?status=ASSIGNED`. |
| `POST` | `/api/teacher/availability`| Teacher | **Body**: `{"date": "2026-11-23", "time_slot": "MORNING", "is_available": false, "reason": "..."}`. |
| `POST` | `/api/teacher/duty-swap` | Teacher | **Body**: `{"duty_id": 1, "target_teacher_id": 2, "reason": "..."}`. |
| `GET` | `/api/teacher/duty-swaps` | Teacher | Returns incoming and outgoing duty swap requests. |
| `GET` | `/api/teacher/colleagues` | Teacher | Returns active faculty list for duty swap dropdown. |
| `GET` | `/api/teacher/notifications`| Teacher | Faculty notification announcements feed. |

---

### 11. Notifications Hub (`/api/notifications`)
Mounted on `/api/notifications`. In-app alert dispatch, read status, and broadcast tools.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/notifications` | Authenticated | User notifications. Optional `?is_read=false&page=1&per_page=20`. |
| `GET` | `/api/notifications/unread-count` | Authenticated | Badge counter: `{"unread_count": 3}`. |
| `PATCH` | `/api/notifications/<id>/read` | Authenticated | Marks notification as read. |
| `POST` | `/api/notifications/mark-all-read` | Authenticated | Marks all user notifications as read. |
| `DELETE` | `/api/notifications/<id>` | Authenticated | Deletes notification. |
| `POST` | `/api/notifications/broadcast` | Admin | **Body**: `{"title": "Exam Alert", "message": "...", "target_role": "STUDENT"}` (`ALL`, `STUDENT`, `TEACHER`, `ADMIN`). |

---

### 12. Forensic Audit Trail (`/api/audit-logs`)
Mounted on `/api/audit-logs`. Immutable administrative compliance log.

| Method | Endpoint | Access | Description & Query / Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/audit-logs` | Admin | Paginated audit trail. `?action=PUBLISH_PLAN&user_id=1&start_date=2026-11-01&end_date=2026-11-30`. |
| `GET` | `/api/audit-logs/summary` | Admin | Activity metrics, top actions, and security event totals. |
| `GET` | `/api/audit-logs/<id>` | Admin | Retrieve single audit log with actor ID, timestamp, and IP address. |

---

### 13. Document Reports & Exports Gateway (`/api/reports`)
Mounted on `/api/reports`. Streaming PDF and Excel export engine.

| Method | Endpoint | Access | Format & Output Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/reports/contracts` | Public | JSON schema contracts for Seating, Invigilation, and Reports. |
| `GET` | `/api/reports/seating-chart/<plan_id>` | Admin | `?format=pdf` (Master PDF Chart) or `?format=excel` (Excel Sheet). |
| `GET` | `/api/reports/room-notice/<plan_id>/<room_id>` | Admin, Teacher | `?format=pdf`. Hall Door Notice for entry display. |
| `GET` | `/api/reports/attendance-sheet/<plan_id>/<room_id>` | Admin, Teacher | `?format=pdf` or `?format=excel`. Candidate attendance & signature sheet. |
| `GET` | `/api/reports/duty-roster/<exam_id>` | Admin, Teacher | `?format=pdf` or `?format=excel`. Faculty invigilation roster. |

---

## 🤝 Team Integration Guide & Data Contracts

### Member 1: Admin Web Portal Integration
* **Authentication**: POST credentials to `/api/auth/login`. Store session cookie (`session`) automatically via browser `withCredentials: true`.
* **Timetable Setup**: Call `POST /api/exams` to schedule examinations. Use `POST /api/exams/<id>/bulk-enroll` to register candidate cohorts.
* **Seating Generation**: Trigger `POST /api/planning/seating/generate`. Review layout visually via `GET /api/planning/seating/<plan_id>/matrix/<room_id>`. Click publish to call `POST /api/planning/seating/<plan_id>/publish`.
* **Faculty Roster**: Generate duties via `POST /api/planning/invigilation/generate`. Review and approve peer duty swaps via `PATCH /api/teachers/duty-swap/<id>/review`.
* **Downloads**: Direct download links for seating charts, room notices, attendance sheets, and duty rosters from `/api/reports/...`.

### Member 2: Student & Faculty Portals Integration
* **Student Dashboard**:
  - Timetable: `GET /api/student/timetable`
  - Allocated Hall & Seat: `GET /api/student/my-seat`
  - Public Kiosk Kiosk Search: `GET /api/student/seat-search?roll_number=CO2401`
  - Notifications: `GET /api/student/notifications`
* **Faculty Dashboard**:
  - Assigned Duties: `GET /api/teacher/duties`
  - Leave Submission: `POST /api/teacher/availability`
  - Peer Swap Request: `POST /api/teacher/duty-swap`
  - Colleague Selection: `GET /api/teacher/colleagues`
  - Attendance Sheets: `GET /api/reports/attendance-sheet/<plan_id>/<room_id>`

### Member 4: Optimization Algorithms & Reports Gateway
Data contract specifications are formalized in Python dataclasses under [`app/contracts/`](file:///D:/Exam%20seating%20Arrangement%20Planner/exam-planner/app/contracts):
* [`seating_contract.py`](file:///D:/Exam%20seating%20Arrangement%20Planner/exam-planner/app/contracts/seating_contract.py): `SeatingInputPayload`, `SeatingOutputAllocation`, `SeatingAlgorithmResponse`.
* [`invigilation_contract.py`](file:///D:/Exam%20seating%20Arrangement%20Planner/exam-planner/app/contracts/invigilation_contract.py): `InvigilationInputPayload`, `InvigilationOutputAssignment`, `InvigilationAlgorithmResponse`.
* [`report_contract.py`](file:///D:/Exam%20seating%20Arrangement%20Planner/exam-planner/app/contracts/report_contract.py): `ReportConfig`, `ReportTypeEnum`, `ReportFormatEnum`.

Member 4 algorithm engineers can inspect live contract schemas at runtime via:
```http
GET /api/reports/contracts
```

---

## 🧪 Automated Testing & Verification

The backend codebase features 100% test coverage across all domain rules, service methods, REST blueprints, seeders, and end-to-end integration flows.

### Running Test Suite
```bash
# Run all tests across the repository:
pytest tests/ -v

# Run Phase 19 End-to-End institutional lifecycle verification:
pytest tests/test_e2e_verification_phase19.py -v
```

### Verification Matrix (36/36 Passed)
| Test Module | Coverage Domain | Status |
| :--- | :--- | :--- |
| `test_services_phase10.py` | Core Service Layer (`Auth`, `Academic`, `Student`, `Teacher`, `Room`, `Exam`, `Planning`) | **PASSED** |
| `test_routes_phase11.py` | Academic & Student REST APIs (`/api/departments`, `/api/subjects`, `/api/students`) | **PASSED** |
| `test_routes_phase12.py` | Faculty & Room Logistics REST APIs (`/api/teachers`, `/api/rooms`) | **PASSED** |
| `test_routes_phase13.py` | Exam Scheduling & Candidate Registration REST APIs (`/api/exams`) | **PASSED** |
| `test_routes_phase14.py` | Seating & Invigilation Planning REST APIs (`/api/planning`) | **PASSED** |
| `test_routes_phase15.py` | Dedicated Student & Faculty Portals (`/api/student`, `/api/teacher`) | **PASSED** |
| `test_routes_phase16.py` | Notification Hub & System Audit Trail (`/api/notifications`, `/api/audit-logs`) | **PASSED** |
| `test_seeder_phase17.py` | Realistic Polytechnic Database Seeder & Idempotency (`seed.py`) | **PASSED** |
| `test_routes_phase18.py` | Member 4 Integration Gateway & Report Exports (`/api/reports`) | **PASSED** |
| `test_e2e_verification_phase19.py` | Full Institutional Examination Planning Lifecycle (End-to-End) | **PASSED** |
| `test_student_import_tyco.py` | Official TYCO C Student Roll-Call Import & Name + Enrollment No Authentication | **PASSED** |

---

## ⚖ License & Copyright
Developed for Diploma & Polytechnic Institutional Administration.  
Architected by **Member 3 (Backend Architect & Database Engineer)**.
