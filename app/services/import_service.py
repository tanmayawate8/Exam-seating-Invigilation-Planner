"""
Student Import Service Module.
Handles parsing, schema validation, academic verification, duplicate detection,
preview generation, and transactional database persistence for student records.

Supports official Polytechnic roll-call data imports (e.g. TYCO C Roll-Call List)
via Excel (.xlsx) and CSV files.
"""

import io
import csv
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.department import Department
from app.services.academic_service import AcademicService
from app.services.auth_service import AuthService
from app.utils.errors import ValidationError, BadRequestError
from app.utils.audit import log_audit


# Roman numeral mapping for Polytechnic semesters
ROMAN_SEMESTER_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "SEM 1": 1, "SEM 2": 2, "SEM 3": 3, "SEM 4": 4, "SEM 5": 5, "SEM 6": 6,
    "SEMESTER 1": 1, "SEMESTER 2": 2, "SEMESTER 3": 3,
    "SEMESTER 4": 4, "SEMESTER 5": 5, "SEMESTER 6": 6,
    "SEMESTER I": 1, "SEMESTER II": 2, "SEMESTER III": 3,
    "SEMESTER IV": 4, "SEMESTER V": 5, "SEMESTER VI": 6,
}

# Standardized template column definitions
TEMPLATE_COLUMNS = [
    ("sr_no", "Sr.No.", "Serial roll-call number (e.g., 1, 2, 3)"),
    ("enrollment_no", "Enrollment No.", "Institutional Enrollment Number (e.g., 24252271491)"),
    ("name", "Name of the Student", "Official student name preserving source spelling"),
    ("student_contact", "Student Contact No.", "10-digit mobile number as text"),
    ("parent_contact_1", "Parent Contact No.1", "Primary parent contact number"),
    ("parent_contact_2", "Parent Contact No.2", "Secondary parent contact number"),
    ("department", "Department", "Polytechnic branch name or code (e.g., Computer Engineering or CO)"),
    ("semester", "Semester", "Semester 1 to 6 (or Roman numerals I to VI)"),
    ("division", "Division", "Class division (e.g., C)"),
    ("batch", "Batch", "Practical batch (e.g., C1, C2)"),
    ("academic_year", "Academic Year", "Academic session (e.g., 2026-2027)"),
    ("class_name", "Class", "Class identifier (e.g., TYCO)"),
]


class ImportService:
    """Service layer orchestrating student Excel/CSV data import operations."""

    @staticmethod
    def generate_template(format_type: str = "excel") -> Tuple[io.BytesIO, str, str]:
        """
        Generates official downloadable student import template based on
        the official Polytechnic TYCO C Roll-Call structure.
        """
        format_type = format_type.lower()
        if format_type == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            # Write header row
            writer.writerow([col[0] for col in TEMPLATE_COLUMNS])
            # Write sample data row
            writer.writerow([
                "1",
                "24252271491",
                "ADHAV HARSH NIVRUTTI",
                "9623693560",
                "9284720924",
                "8805160997",
                "Computer Engineering",
                "VI",
                "C",
                "C1",
                "2026-2027",
                "TYCO",
            ])
            buf = io.BytesIO()
            buf.write(output.getvalue().encode("utf-8-sig"))
            buf.seek(0)
            return buf, "Student_Import_Template.csv", "text/csv"

        # Generate Styled Excel Template using openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student_Import"

        # Styles
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        guide_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        guide_font = Font(name="Arial", size=10, italic=True, color="475569")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1'),
        )

        # 1. Header row
        for col_idx, col_def in enumerate(TEMPLATE_COLUMNS, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_def[0])
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # 2. Sample reference row (TYCO C Roll-Call sample)
        sample_row = [
            "1",
            "24252271491",
            "ADHAV HARSH NIVRUTTI",
            "9623693560",
            "9284720924",
            "8805160997",
            "Computer Engineering",
            "VI",
            "C",
            "C1",
            "2026-2027",
            "TYCO",
        ]
        for col_idx, val in enumerate(sample_row, 1):
            cell = ws.cell(row=2, column=col_idx, value=val)
            cell.fill = guide_fill
            cell.font = guide_font
            cell.border = thin_border
            # Treat numeric strings explicitly as text
            cell.number_format = '@'

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf, "Student_Import_Template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def read_student_file(cls, file_stream, filename: str) -> List[Dict[str, Any]]:
        """
        Parses uploaded Excel or CSV file into a list of normalized row dictionaries.
        Preserves string formatting and leading zeros for contacts and enrollment numbers.
        """
        filename_lower = filename.lower()
        rows: List[Dict[str, Any]] = []

        if filename_lower.endswith(".csv"):
            content = file_stream.read()
            if isinstance(content, bytes):
                text = content.decode("utf-8-sig", errors="replace")
            else:
                text = content

            reader = csv.reader(io.StringIO(text))
            header_row = next(reader, None)
            if not header_row:
                raise BadRequestError("Uploaded CSV file is completely empty.")

            norm_headers = [cls._normalize_header_name(h) for h in header_row]
            for row_idx, raw_vals in enumerate(reader, start=2):
                if not any(v.strip() for v in raw_vals):
                    continue  # Skip empty lines
                row_dict = {}
                for h_name, val in zip(norm_headers, raw_vals):
                    row_dict[h_name] = str(val).strip() if val is not None else ""
                row_dict["_row_number"] = row_idx
                rows.append(row_dict)

        elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
            try:
                wb = openpyxl.load_workbook(file_stream, data_only=True)
            except Exception as exc:
                raise BadRequestError(f"Could not read Excel workbook: {exc}")

            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            if not all_rows:
                raise BadRequestError("Uploaded Excel sheet contains no data.")

            header_row = all_rows[0]
            norm_headers = [cls._normalize_header_name(str(h or '')) for h in header_row]

            for row_idx, raw_vals in enumerate(all_rows[1:], start=2):
                if not any(v is not None and str(v).strip() for v in raw_vals):
                    continue
                row_dict = {}
                for h_name, val in zip(norm_headers, raw_vals):
                    if val is None:
                        row_dict[h_name] = ""
                    else:
                        row_dict[h_name] = str(val).strip()
                row_dict["_row_number"] = row_idx
                rows.append(row_dict)

        elif filename_lower.endswith(".pdf"):
            try:
                import pdfplumber
                if hasattr(file_stream, "seek"):
                    file_stream.seek(0)
                with pdfplumber.open(file_stream) as pdf:
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        if not tables:
                            continue
                        for table in tables:
                            for raw_vals in table:
                                if not raw_vals or len(raw_vals) < 3:
                                    continue
                                sr_val = str(raw_vals[0] or "").strip()
                                if sr_val.isdigit():
                                    sr_no = int(sr_val)
                                    batch = "C1" if sr_no <= 35 else "C2"
                                    enr_val = str(raw_vals[1] or "").strip() if len(raw_vals) > 1 else ""
                                    name_val = str(raw_vals[2] or "").strip() if len(raw_vals) > 2 else ""
                                    s_contact = str(raw_vals[3] or "").strip() if len(raw_vals) > 3 else ""
                                    p1_contact = str(raw_vals[4] or "").strip() if len(raw_vals) > 4 else ""
                                    p2_contact = str(raw_vals[5] or "").strip() if len(raw_vals) > 5 else ""

                                    rows.append({
                                        "_row_number": len(rows) + 2,
                                        "sr_no": sr_no,
                                        "enrollment_no": enr_val,
                                        "name": name_val,
                                        "student_contact": s_contact,
                                        "parent_contact_1": p1_contact,
                                        "parent_contact_2": p2_contact,
                                        "department": "Computer Engineering",
                                        "semester": "VI",
                                        "division": "C",
                                        "batch": batch,
                                        "academic_year": "2026-2027",
                                        "class_name": "TYCO",
                                    })
            except Exception as exc:
                raise BadRequestError(f"Could not parse PDF student roll-call document: {exc}")
        else:
            raise BadRequestError("Unsupported file type. Please upload a valid .xlsx, .csv, or .pdf file.")

        return rows

    @staticmethod
    def _normalize_header_name(h: str) -> str:
        """Maps various natural-language header variants to canonical field keys."""
        h_clean = re.sub(r"[^\w\s]", "", h).strip().lower()
        h_clean = re.sub(r"\s+", "_", h_clean)

        mapping = {
            "srno": "sr_no",
            "sr_no": "sr_no",
            "serial_no": "sr_no",
            "enrollment_no": "enrollment_no",
            "enrollmentno": "enrollment_no",
            "enrollment_number": "enrollment_no",
            "enrollment": "enrollment_no",
            "name_of_the_student": "name",
            "student_name": "name",
            "name": "name",
            "full_name": "name",
            "zprn": "zprn",
            "student_contact_no": "student_contact",
            "student_contact": "student_contact",
            "contact": "student_contact",
            "mobile": "student_contact",
            "parent_contact_no1": "parent_contact_1",
            "parent_contact_no_1": "parent_contact_1",
            "parent_contact_1": "parent_contact_1",
            "parent_contact_no2": "parent_contact_2",
            "parent_contact_no_2": "parent_contact_2",
            "parent_contact_2": "parent_contact_2",
            "department": "department",
            "branch": "department",
            "dept": "department",
            "semester": "semester",
            "sem": "semester",
            "division": "division",
            "div": "division",
            "batch": "batch",
            "academic_year": "academic_year",
            "year": "academic_year",
            "class": "class_name",
            "class_name": "class_name",
            "roll_number": "roll_number",
            "roll_no": "roll_number",
        }
        return mapping.get(h_clean, h_clean)

    @classmethod
    def validate_student_rows(cls, raw_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates parsed rows against academic constraints, duplicates, and malformed records.
        Returns detailed per-row statuses, validation errors, and summary metrics.
        """
        validated_rows: List[Dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0
        duplicate_count = 0

        # In-memory tracking for duplicate detection within the same file
        seen_enrollments_in_file: Dict[str, int] = {}

        # Fetch existing departments for academic foreign-key validation
        dept_lookup = {}
        from flask import has_app_context
        has_ctx = has_app_context()

        if has_ctx:
            try:
                all_departments = Department.query.all()
                for d in all_departments:
                    dept_lookup[d.code.upper()] = d
                    dept_lookup[d.name.strip().upper()] = d
            except Exception:
                pass

        # Fallback for standard Polytechnic branches if DB uninitialized or offline
        if not dept_lookup:
            for code, name in [
                ("CO", "Computer Engineering"),
                ("IT", "Information Technology"),
                ("ME", "Mechanical Engineering"),
                ("CE", "Civil Engineering"),
                ("EE", "Electrical Engineering"),
                ("EJ", "Electronics & Telecommunication"),
            ]:
                mock_d = type("MockDept", (), {"id": 1, "code": code, "name": name})()
                dept_lookup[code] = mock_d
                dept_lookup[name.upper()] = mock_d

        for row in raw_rows:
            row_num = row.get("_row_number", len(validated_rows) + 1)
            errors: List[str] = []
            warnings: List[str] = []

            # 1. Detect Footer / Non-Student Rows (e.g., GFM Coordinator)
            raw_text = " ".join(str(v) for v in row.values()).upper()
            if any(term in raw_text for term in ["GFM COORDINATOR", "CLASS TEACHER", "HEAD OF DEPARTMENT", "REV. NO"]):
                invalid_count += 1
                validated_rows.append({
                    "row_number": row_num,
                    "sr_no": row.get("sr_no"),
                    "enrollment_no": row.get("enrollment_no"),
                    "name": row.get("name"),
                    "status": "ERROR",
                    "errors": ["Non-student table footer or SOP header row detected."],
                    "warnings": [],
                    "data": row,
                })
                continue

            # 2. Validate Student Name
            name = (row.get("name") or "").strip()
            if not name:
                errors.append("Student Name is missing or source columns appear misaligned (Admin review required).")
            elif len(name) < 2:
                errors.append(f"Student name '{name}' is unreasonably short.")

            # 3. Validate Enrollment Number
            enrollment_no = (row.get("enrollment_no") or "").strip()
            if not enrollment_no:
                errors.append("Enrollment Number is missing.")
            else:
                # Check duplicate within uploaded file
                if enrollment_no in seen_enrollments_in_file:
                    duplicate_count += 1
                    first_row = seen_enrollments_in_file[enrollment_no]
                    errors.append(f"Duplicate Enrollment No. in file (already appeared in row {first_row}).")
                else:
                    seen_enrollments_in_file[enrollment_no] = row_num

                # Check duplicate in database
                if has_ctx:
                    try:
                        existing_student_enr = Student.query.filter_by(enrollment_number=enrollment_no).first()
                        if existing_student_enr:
                            duplicate_count += 1
                            errors.append(f"Enrollment No. '{enrollment_no}' already exists in database (Student: {existing_student_enr.full_name}).")
                    except Exception:
                        pass

            # 4. Validate Department / Branch
            dept_str = (row.get("department") or "Computer Engineering").strip().upper()
            dept = dept_lookup.get(dept_str)
            if not dept:
                errors.append(f"Unknown Department '{row.get('department')}'. Please specify a valid Polytechnic branch (e.g., Computer Engineering or CO).")

            # 5. Validate Semester (1 to 6)
            sem_raw = str(row.get("semester") or "VI").strip().upper()
            sem_num = None
            if sem_raw.isdigit():
                sem_num = int(sem_raw)
            elif sem_raw in ROMAN_SEMESTER_MAP:
                sem_num = ROMAN_SEMESTER_MAP[sem_raw]
            else:
                errors.append(f"Invalid Semester '{sem_raw}'. Polytechnic semesters must be between 1 and 6 (or Roman I to VI).")

            if sem_num is not None and not (1 <= sem_num <= 6):
                errors.append(f"Semester {sem_num} out of bounds. Version 1 strictly supports Polytechnic Semesters 1 to 6.")

            # 6. Validate Division & Batch
            division = (row.get("division") or "C").strip().upper()
            batch = (row.get("batch") or "").strip().upper()
            class_name = (row.get("class_name") or "TYCO").strip()
            academic_year = (row.get("academic_year") or "2026-2027").strip()

            # 7. Validate Contacts (Store as strings, preserve leading zeros)
            student_contact = str(row.get("student_contact") or "").strip()
            parent_contact_1 = str(row.get("parent_contact_1") or "").strip()
            parent_contact_2 = str(row.get("parent_contact_2") or "").strip()

            if student_contact and not cls._is_valid_contact(student_contact):
                warnings.append(f"Student contact '{student_contact}' has unexpected format or length.")

            if not student_contact:
                warnings.append("Student contact number is blank in source data.")

            # Compile row validation output
            status = "ERROR" if errors else "VALID"
            if status == "VALID":
                valid_count += 1
            else:
                invalid_count += 1

            # Prepare cleaned parsed record
            cleaned_record = {
                "sr_no": int(row.get("sr_no")) if str(row.get("sr_no", "")).isdigit() else None,
                "enrollment_no": enrollment_no,
                "name": name,
                "zprn": None,
                "student_contact": student_contact or None,
                "parent_contact_1": parent_contact_1 or None,
                "parent_contact_2": parent_contact_2 or None,
                "department": dept.name if dept else dept_str,
                "department_id": dept.id if dept else None,
                "department_code": dept.code if dept else None,
                "semester": sem_num or 6,
                "division": division,
                "batch": batch or None,
                "class_name": class_name,
                "academic_year": academic_year,
                "roll_number": (row.get("roll_number") or "").strip() or None,
            }

            validated_rows.append({
                "row_number": row_num,
                "sr_no": cleaned_record["sr_no"],
                "enrollment_no": enrollment_no,
                "name": name,
                "zprn": None,
                "department": cleaned_record["department"],
                "semester": cleaned_record["semester"],
                "division": division,
                "batch": batch,
                "academic_year": academic_year,
                "class_name": class_name,
                "status": status,
                "errors": errors,
                "warnings": warnings,
                "data": cleaned_record,
            })

        return {
            "total_rows": len(validated_rows),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "duplicate_count": duplicate_count,
            "rows": validated_rows,
        }

    @staticmethod
    def _is_valid_contact(contact: str) -> bool:
        """Validates phone number string format (allows 10-digit standard or country codes)."""
        clean = re.sub(r"[\s\-\+]", "", contact)
        return clean.isdigit() and 8 <= len(clean) <= 15

    @classmethod
    def preview_student_import(cls, file_stream, filename: str) -> Dict[str, Any]:
        """
        Processes uploaded Excel or CSV file and generates validation preview for Admin.
        Does NOT alter the database.
        """
        raw_rows = cls.read_student_file(file_stream, filename)
        if not raw_rows:
            raise BadRequestError("File does not contain any student rows.")
        return cls.validate_student_rows(raw_rows)

    @classmethod
    def commit_student_import(
        cls,
        valid_student_data: List[Dict[str, Any]],
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Commits validated student data into PostgreSQL inside an atomic database transaction.
        Creates linked User account with securely hashed initial Enrollment Number password for each student.
        Rolls back completely if any database constraint fails.
        """
        if not valid_student_data:
            raise BadRequestError("No student records provided for import.")

        imported_count = 0
        skipped_count = 0
        created_students: List[Student] = []

        try:
            for item in valid_student_data:
                # If item is wrapped in row wrapper dict, unwrap it
                record = item.get("data") if "data" in item else item

                enrollment_no = record["enrollment_no"].strip()
                zprn = (record.get("zprn") or "").strip() or None
                name = record["name"].strip()
                dept_id = record["department_id"]
                semester = int(record["semester"])
                division = record.get("division", "C")
                batch = record.get("batch")
                academic_year = record.get("academic_year", "2026-2027")
                class_name = record.get("class_name", "TYCO")
                sr_no = record.get("sr_no")

                # Ensure Department exists
                dept = Department.query.get(dept_id)
                if not dept:
                    raise ValidationError(f"Department ID {dept_id} does not exist.")

                # Format roll number: use specified roll_number or format from class/div/sr_no
                roll_number = record.get("roll_number")
                if not roll_number:
                    if sr_no:
                        roll_number = f"{division}{int(sr_no):02d}"
                    else:
                        roll_number = enrollment_no

                # Check uniqueness in current transaction
                if Student.query.filter_by(enrollment_number=enrollment_no).first():
                    skipped_count += 1
                    continue

                # 1. Create linked User Account (Polytechnic student login: Enrollment No as username & password)
                username = enrollment_no
                email = f"{enrollment_no}@polytechnic.ac.in"

                # Check if user already exists
                existing_user = User.query.filter(
                    (User.username == username) | (User.email == email)
                ).first()

                if existing_user:
                    user = existing_user
                else:
                    user = User(
                        username=username,
                        email=email,
                        role="STUDENT",
                        is_active=True,
                    )
                    # Initial Password = Enrollment Number from PDF, securely hashed with Werkzeug pbkdf2/scrypt!
                    user.set_password(enrollment_no)
                    db.session.add(user)
                    db.session.flush()  # Retrieve user.id

                # Split name into first and last for backward-compatibility fields
                parts = name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

                # 2. Create Student Profile Record
                student = Student(
                    user_id=user.id,
                    sr_no=sr_no,
                    roll_number=roll_number,
                    enrollment_number=enrollment_no,
                    zprn=zprn,
                    name=name,
                    first_name=first_name,
                    last_name=last_name,
                    department_id=dept.id,
                    semester=semester,
                    division=division,
                    batch=batch,
                    academic_year=academic_year,
                    class_name=class_name,
                    student_contact=record.get("student_contact"),
                    parent_contact_1=record.get("parent_contact_1"),
                    parent_contact_2=record.get("parent_contact_2"),
                )
                db.session.add(student)
                created_students.append(student)
                imported_count += 1

            # Commit all records atomically
            db.session.commit()

            # Forensic Audit Trail logging
            log_audit(
                action="STUDENT_IMPORT_COMMITTED",
                entity_type="Student",
                user_id=creator_user_id,
                details=(
                    f"Successfully imported {imported_count} students from official roll-call "
                    f"into Semester {semester} ({division} Div). Skipped {skipped_count} existing."
                ),
                ip_address=ip_address,
            )

            return {
                "success": True,
                "total_processed": len(valid_student_data),
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "message": f"Successfully imported {imported_count} student records with authenticated User accounts.",
            }

        except Exception as exc:
            db.session.rollback()
            raise ValidationError(f"Import transaction rolled back due to error: {exc}")
