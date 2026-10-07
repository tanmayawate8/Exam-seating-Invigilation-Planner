"""
Contracts Package Initialization.
Exports all data contracts between Member 3 (Backend) and Member 4 (Algorithms & Reports).
"""

from app.contracts.seating_contract import (
    StudentContractItem,
    SeatContractItem,
    RoomContractItem,
    SeatingAlgorithmInput,
    SeatingAllocationOutputItem,
    SeatingAlgorithmOutput,
)
from app.contracts.invigilation_contract import (
    TeacherContractItem,
    InvigilationRoomContractItem,
    InvigilationAlgorithmInput,
    InvigilationDutyOutputItem,
    InvigilationAlgorithmOutput,
)
from app.contracts.report_contract import (
    SeatingChartItem,
    SeatingChartReportContract,
    RoomNoticeCandidateItem,
    RoomNoticeReportContract,
    AttendanceCandidateItem,
    AttendanceSheetReportContract,
    DutyRosterItem,
    DutyRosterReportContract,
)

__all__ = [
    "StudentContractItem",
    "SeatContractItem",
    "RoomContractItem",
    "SeatingAlgorithmInput",
    "SeatingAllocationOutputItem",
    "SeatingAlgorithmOutput",
    "TeacherContractItem",
    "InvigilationRoomContractItem",
    "InvigilationAlgorithmInput",
    "InvigilationDutyOutputItem",
    "InvigilationAlgorithmOutput",
    "SeatingChartItem",
    "SeatingChartReportContract",
    "RoomNoticeCandidateItem",
    "RoomNoticeReportContract",
    "AttendanceCandidateItem",
    "AttendanceSheetReportContract",
    "DutyRosterItem",
    "DutyRosterReportContract",
]
