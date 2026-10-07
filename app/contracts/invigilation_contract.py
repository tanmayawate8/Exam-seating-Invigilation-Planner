"""
Invigilation Algorithm Data Contract Module (Member 3 <-> Member 4 Gateway).
Defines standard input and output payloads exchanged between Member 3's backend
and Member 4's invigilation roster scheduling algorithm.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TeacherContractItem:
    """Faculty candidate payload provided to algorithm."""
    teacher_id: int
    employee_id: str
    full_name: str
    department_code: str
    max_duties: int
    current_assigned_duties: int


@dataclass
class InvigilationRoomContractItem:
    """Room requiring invigilation."""
    room_id: int
    room_number: str
    allocated_students_count: int


@dataclass
class InvigilationAlgorithmInput:
    """Complete input contract passed into Member 4's invigilation scheduler."""
    exam_id: int
    exam_code: str
    exam_date: str
    session_name: str
    rooms: List[InvigilationRoomContractItem]
    teachers: List[TeacherContractItem]
    options: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvigilationDutyOutputItem:
    """Individual duty assignment returned by algorithm."""
    teacher_id: int
    room_id: int
    duty_role: str = "CHIEF_INVIGILATOR"


@dataclass
class InvigilationAlgorithmOutput:
    """Result payload returned by Member 4's scheduler to Member 3 for persistence."""
    duties: List[InvigilationDutyOutputItem]
    unassigned_room_ids: List[int]
    status: str  # SUCCESS, PARTIAL, FAILED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
