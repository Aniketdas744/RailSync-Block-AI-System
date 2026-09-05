from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Department(str, Enum):
    P_WAY = "P-WAY"
    TRD = "TRD"
    S_AND_T = "S&T"
    OTHER = "OTHER"


class MaintenanceSource(str, Enum):
    TMS = "TMS"
    SMMS = "SMMS"
    TDMS = "TDMS"
    BDMS = "BDMS"
    MANUAL = "MANUAL"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PlanHorizon(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class Section(BaseModel):
    section_id: str
    name: str

    from_km: float
    to_km: float

    capacity: int = 1
    headway_minutes: int = 5

    running_time_up_minutes: int = 25
    running_time_down_minutes: int = 25


class TrainPath(BaseModel):
    train_id: str
    name: str

    priority: int = 50
    direction: str

    scheduled_departure_min: int
    max_departure_delay_min: int = 120

    transit_duration_min: int

    passenger_weight: int = 0
    freight_weight: int = 0

    current_delay_min: int = 0

    occupied_sections: List[str] = Field(
        default_factory=list
    )

    station_dwell_minutes: int = 5
    speed_factor: float = 1.0

    section_durations: Dict[str, int] = Field(
        default_factory=dict
    )

    section_start_offsets: Dict[str, int] = Field(
        default_factory=dict
    )


class MaintenanceData(BaseModel):
    record_id: str

    source_system: MaintenanceSource

    department: Department

    asset_id: str
    asset_type: str

    section_id: str

    defect_description: str = ""

    defect_severity: int = Field(
        default=1,
        ge=1,
        le=10
    )

    overdue_days: int = Field(
        default=0,
        ge=0
    )

    asset_criticality: int = Field(
        default=1,
        ge=1,
        le=10
    )

    safety_impact: int = Field(
        default=1,
        ge=1,
        le=10
    )

    train_operation_impact: int = Field(
        default=1,
        ge=1,
        le=10
    )

    estimated_work_minutes: int = Field(
        default=30,
        ge=1
    )

    is_overdue: bool = False

    requested_by: str = ""

    source_reference: Optional[str] = None


class BlockDemand(BaseModel):
    demand_id: str

    department: Department

    section_id: str

    start_km: float
    end_km: float

    min_duration_minutes: int

    earliest_start_min: int = 0

    latest_end_min: Optional[int] = None

    urgency_score: int = Field(
        default=1,
        ge=1,
        le=10
    )

    crew_required: int = 1

    crew_group: Optional[str] = None

    possession_group: Optional[str] = None

    compatible_departments: List[Department] = Field(
        default_factory=list
    )

    safety_buffer_before_min: int = 0

    safety_buffer_after_min: int = 0

    max_possession_minutes: Optional[int] = None

    source_system: MaintenanceSource = MaintenanceSource.BDMS

    asset_id: Optional[str] = None

    asset_type: Optional[str] = None

    defect_severity: int = Field(
        default=1,
        ge=1,
        le=10
    )

    overdue_days: int = Field(
        default=0,
        ge=0
    )

    asset_criticality: int = Field(
        default=1,
        ge=1,
        le=10
    )

    safety_impact: int = Field(
        default=1,
        ge=1,
        le=10
    )

    train_operation_impact: int = Field(
        default=1,
        ge=1,
        le=10
    )

    ai_priority_score: float = 0.0

    priority_level: PriorityLevel = PriorityLevel.MEDIUM

    reason: str = ""


class GoodsTrainForecast(BaseModel):
    forecast_id: str

    section_id: str

    start_min: int
    end_min: int

    expected_goods_trains: int = Field(
        default=0,
        ge=0
    )

    average_train_duration_min: int = Field(
        default=30,
        ge=1
    )

    congestion_level: int = Field(
        default=1,
        ge=1,
        le=10
    )

    source: str = "CONTROL_OFFICE_FORECAST"


class CorridorAvailability(BaseModel):
    section_id: str

    start_min: int
    end_min: int

    available: bool = True

    reason: str = ""


class Disruption(BaseModel):
    active: bool = False

    train_id: Optional[str] = None

    additional_delay_min: int = 0

    affected_section_ids: List[str] = Field(
        default_factory=list
    )

    reason: str = ""


class OptimizationRequest(BaseModel):
    corridor_id: str

    horizon_minutes: int = Field(
        default=480,
        le=2880
    )

    sections: List[Section] = Field(
        default_factory=list
    )

    trains: List[TrainPath] = Field(
        default_factory=list
    )

    demands: List[BlockDemand] = Field(
        default_factory=list
    )

    disruption: Optional[Disruption] = None

    solver_timeout_seconds: int = 10

    allow_fallback: bool = True

    state_version: int = 1

    maintenance_records: List[MaintenanceData] = Field(
        default_factory=list
    )

    goods_forecasts: List[GoodsTrainForecast] = Field(
        default_factory=list
    )

    corridor_availability: List[CorridorAvailability] = Field(
        default_factory=list
    )

    planning_horizon: PlanHorizon = PlanHorizon.DAILY


class PriorityResult(BaseModel):
    demand_id: str
    ai_priority_score: float
    priority_level: PriorityLevel
    explanation: str


class MaintenanceSchedule(BaseModel):
    demand_id: str

    department: Department

    section_id: str

    start_min: int
    end_min: int
    duration_min: int

    bundled: bool = False

    priority_level: PriorityLevel = PriorityLevel.MEDIUM

    ai_priority_score: float = 0.0

    safe: bool = True

    affected_trains: List[str] = Field(
        default_factory=list
    )

    explanation: str = ""


class PlanningRequest(BaseModel):
    corridor_id: str

    horizon: PlanHorizon = PlanHorizon.DAILY

    optimization_request: OptimizationRequest


class HumanDecision(BaseModel):
    action: str = Field(
        description="ACCEPT, MODIFY or REJECT"
    )

    reason: str = ""

    operator_name: Optional[str] = None