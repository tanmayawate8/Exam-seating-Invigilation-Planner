"""
Report Data Contract Module (Member 3 <-> Member 4 Gateway).
Defines standard institutional report payloads assembled by Member 3's backend
and consumed by Member 4's ReportLab (PDF) and openpyxl (Excel) rendering engines.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class SeatingChartItem:
    """Individual candidate allocation entry in seating charts."""
    student_roll: str
    student_name: str
    department_code: str
    semester: int
    room_number: str
    seat_number: str
    row_num: int
    col_num: int


@dataclass
class SeatingChartReportContract:
    """Master Seating Chart report payload."""
    institution_name: str
    plan_code: str
    exam_code: str
    subject_code: str
    subject_name: str
    exam_date: str
    start_time: str
    end_time: str
    session_name: str
    allocations: List[SeatingChartItem]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoomNoticeCandidateItem:
    """Candidate entry on room door / noticeboard charts."""
    seat_number: str
    roll_number: str
    student_name: str
    department_code: str
    semester: int


@dataclass
class RoomNoticeReportContract:
    """Room Door Notice / Hall Seating List payload."""
    institution_name: str
    exam_code: str
    subject_name: str
    exam_date: str
    session_name: str
    room_number: str
    building: str
    floor: int
    capacity: int
    candidates: List[RoomNoticeCandidateItem]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttendanceCandidateItem:
    """Candidate entry on exam attendance signature sheet."""
    sr_no: int
    roll_number: str
    enrollment_number: str
    student_name: str
    seat_number: str


@dataclass
class AttendanceSheetReportContract:
    """Examination Hall Attendance & Signature Sheet payload."""
    institution_name: str
    exam_code: str
    subject_code: str
    subject_name: str
    exam_date: str
    session_name: str
    room_number: str
    invigilator_name: Optional[str]
    candidates: List[AttendanceCandidateItem]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DutyRosterItem:
    """Faculty duty entry on duty rosters."""
    sr_no: int
    faculty_name: str
    employee_id: str
    department_code: str
    designation: str
    room_number: str
    building: str
    duty_role: str


@dataclass
class DutyRosterReportContract:
    """Invigilation Duty Roster report payload."""
    institution_name: str
    exam_code: str
    exam_title: str
    exam_date: str
    session_name: str
    start_time: str
    end_time: str
    duties: List[DutyRosterItem]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
