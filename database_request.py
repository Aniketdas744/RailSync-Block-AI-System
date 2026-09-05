from optimizer import solve_railway_blocks
from models import (
    OptimizationRequest,
    Section,
    TrainPath,
    BlockDemand,
    Disruption
)


# ============================================================
# 1. SECTIONS
# ============================================================

sections = [
    Section(
        section_id="S1",
        name="GZB-ALJN",
        from_km=0,
        to_km=26,
        capacity=2,
        headway_minutes=5,
        running_time_up_minutes=25,
        running_time_down_minutes=25
    ),

    Section(
        section_id="S2",
        name="ALJN-HRS",
        from_km=26,
        to_km=52,
        capacity=2,
        headway_minutes=5,
        running_time_up_minutes=25,
        running_time_down_minutes=25
    ),

    Section(
        section_id="S3",
        name="HRS-MTC",
        from_km=52,
        to_km=80,
        capacity=2,
        headway_minutes=5,
        running_time_up_minutes=25,
        running_time_down_minutes=25
    ),

    Section(
        section_id="S4",
        name="MTC-GZB",
        from_km=80,
        to_km=106,
        capacity=2,
        headway_minutes=5,
        running_time_up_minutes=25,
        running_time_down_minutes=25
    )
]


# ============================================================
# 2. TRAINS
# ============================================================

trains = [

    TrainPath(
        train_id="T001",
        name="Passenger Express",
        priority=1,
        direction="UP",
        scheduled_departure_min=60,
        max_departure_delay_min=30,
        transit_duration_min=100,
        passenger_weight=1,
        freight_weight=0,
        current_delay_min=0,
        occupied_sections=["S1", "S2", "S3", "S4"],
        station_dwell_minutes=5,
        speed_factor=1
    ),

    TrainPath(
        train_id="T002",
        name="Freight Express",
        priority=2,
        direction="DOWN",
        scheduled_departure_min=80,
        max_departure_delay_min=40,
        transit_duration_min=110,
        passenger_weight=0,
        freight_weight=1,
        current_delay_min=0,
        occupied_sections=["S4", "S3", "S2", "S1"],
        station_dwell_minutes=5,
        speed_factor=1
    ),

    TrainPath(
        train_id="T003",
        name="Intercity Express",
        priority=1,
        direction="UP",
        scheduled_departure_min=120,
        max_departure_delay_min=30,
        transit_duration_min=95,
        passenger_weight=1,
        freight_weight=0,
        current_delay_min=0,
        occupied_sections=["S1", "S2", "S3", "S4"],
        station_dwell_minutes=5,
        speed_factor=1
    )
]


# ============================================================
# 3. MAINTENANCE DEMANDS
# ============================================================

demands = [

    BlockDemand(
        demand_id="B001",
        department="P-WAY",
        section_id="S2",
        start_km=30,
        end_km=40,
        min_duration_minutes=60,
        earliest_start_min=150,
        latest_end_min=300,
        urgency_score=8,
        crew_required=5,
        crew_group="PWAY_TEAM",
        possession_group="BLOCK_1",
        compatible_departments=["TRD"],
        safety_buffer_before_min=5,
        safety_buffer_after_min=5,
        max_possession_minutes=90
    ),

    BlockDemand(
        demand_id="B002",
        department="TRD",
        section_id="S2",
        start_km=40,
        end_km=50,
        min_duration_minutes=45,
        earliest_start_min=150,
        latest_end_min=300,
        urgency_score=6,
        crew_required=3,
        crew_group="TRD_TEAM",
        possession_group="BLOCK_1",
        compatible_departments=["P-WAY"],
        safety_buffer_before_min=5,
        safety_buffer_after_min=5,
        max_possession_minutes=90
    ),

    BlockDemand(
        demand_id="B003",
        department="S&T",
        section_id="S3",
        start_km=55,
        end_km=65,
        min_duration_minutes=30,
        earliest_start_min=180,
        latest_end_min=330,
        urgency_score=5,
        crew_required=2,
        crew_group="SNT_TEAM",
        possession_group="BLOCK_2",
        compatible_departments=[],
        safety_buffer_before_min=5,
        safety_buffer_after_min=5,
        max_possession_minutes=60
    )
]


# ============================================================
# 4. DISRUPTION
# ============================================================

disruption = Disruption(
    active=False,
    train_id=None,
    additional_delay_min=0,
    affected_section_ids=[],
    reason="No active disruption"
)


# ============================================================
# 5. CREATE OPTIMIZATION REQUEST
# ============================================================

request = OptimizationRequest(
    corridor_id="GZB-ALJN",
    horizon_minutes=480,
    sections=sections,
    trains=trains,
    demands=demands,
    disruption=disruption,
    solver_timeout_seconds=10,
    allow_fallback=True,
    state_version=1
)


# ============================================================
# 6. RUN OPTIMIZER
# ============================================================

print("Running RailSync optimization...\n")

result = solve_railway_blocks(request)


# ============================================================
# 7. DISPLAY RESULT
# ============================================================

print("========== OPTIMIZATION RESULT ==========")

print("Status:", result.get("status"))
print("Solver:", result.get("solver"))
print(
    "Solver Time:",
    result.get("solver_time_seconds"),
    "seconds"
)

print(
    "Objective Value:",
    result.get("objective_value")
)


# ============================================================
# 8. METRICS
# ============================================================

metrics = result.get("metrics", {})

print(
    "Passenger Delay:",
    metrics.get("passenger_delay")
)

print(
    "Freight Delay:",
    metrics.get("freight_delay")
)

print(
    "Possession Duration:",
    metrics.get("possession_duration")
)

print(
    "Bundling:",
    metrics.get("bundling_percentage"),
    "%"
)


# ============================================================
# 9. SAFETY
# ============================================================

safety = result.get("safety", {})

print(
    "Safety Conflicts:",
    safety.get("conflict_count")
)


# ============================================================
# 10. TRAIN SCHEDULE
# ============================================================

print("\n--- Train Schedule ---")

for train in result.get("train_schedule", []):

    print(
        f'{train["train_id"]} | '
        f'Section: {train["section_id"]} | '
        f'{train["start_min"]}-{train["end_min"]}'
    )


# ============================================================
# 11. MAINTENANCE SCHEDULE
# ============================================================

print("\n--- Maintenance Schedule ---")

for maintenance in result.get(
    "maintenance_schedule",
    []
):

    print(
        f'{maintenance["demand_id"]} | '
        f'Department: {maintenance["department"]} | '
        f'Section: {maintenance["section_id"]} | '
        f'{maintenance["start_min"]}-'
        f'{maintenance["end_min"]}'
    )


# ============================================================
# 12. SAFETY DETAILS
# ============================================================

print("\n--- Safety ---")

print(
    "Safe:",
    safety.get("safe")
)

for conflict in safety.get("conflicts", []):

    print(
        "CONFLICT:",
        conflict
    )


print("\n=========================================\n")