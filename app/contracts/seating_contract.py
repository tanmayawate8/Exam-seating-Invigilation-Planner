"""
Seating Algorithm Data Contract Module (Member 3 <-> Member 4 Gateway).
Defines standard input and output payloads exchanged between Member 3's backend
and Member 4's examination seating arrangement algorithm.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class StudentContractItem:
    """Student payload schema provided to algorithm."""
    student_id: int
    roll_number: str
    department_code: str
    semester: int
    division: Optional[str] = "A"


@dataclass
class SeatContractItem:
    """Physical seat payload schema provided to algorithm."""
    seat_id: int
    seat_number: str
    row_num: int
    col_num: int


@dataclass
class RoomContractItem:
    """Examination hall payload schema provided to algorithm."""
    room_id: int
    room_number: str
    capacity: int
    seats: List[SeatContractItem]


@dataclass
class SeatingAlgorithmInput:
    """Complete input contract passed into Member 4's seating algorithm."""
    exam_id: int
    exam_code: str
    students: List[StudentContractItem]
    rooms: List[RoomContractItem]
    options: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeatingAllocationOutputItem:
    """Individual seat allocation returned by Member 4's algorithm."""
    student_id: int
    room_id: int
    seat_id: int


@dataclass
class SeatingAlgorithmOutput:
    """Result payload returned by Member 4's seating algorithm to Member 3 for persistence."""
    allocations: List[SeatingAllocationOutputItem]
    unallocated_student_ids: List[int]
    total_allocated: int
    status: str  # SUCCESS, PARTIAL, FAILED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
