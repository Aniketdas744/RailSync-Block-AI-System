from models import (
    BlockDemand,
    CorridorAvailability,
    Department,
    Disruption,
    OptimizationRequest,
    PriorityLevel,
)

from priority_engine import (
    MaintenancePriorityEngine,
)

from real_sections import (
    get_real_sections,
)

from real_train_converter import (
    get_real_trains,
)

from traffic_forecast import (
    build_goods_forecast,
)


def get_real_dataset():

    trains = get_real_trains()

    sections = get_real_sections()

    engine = MaintenancePriorityEngine()

    demands = []

    # ---------------------------------------------------------
    # Representative maintenance demands
    # ---------------------------------------------------------

    for index, section in enumerate(
        sections[:3]
    ):

        department = [
            Department.P_WAY,
            Department.TRD,
            Department.S_AND_T,
        ][index % 3]

        demand = BlockDemand(

            demand_id=(
                f"B{index + 1:03d}"
            ),

            department=department,

            section_id=section.section_id,

            start_km=section.from_km,

            end_km=section.to_km,

            min_duration_minutes=(
                60
                + index * 30
            ),

            earliest_start_min=(
                180
                + index * 30
            ),

            latest_end_min=(
                600
                + index * 60
            ),

            urgency_score=(
                8 - index
            ),

            crew_required=1,

            crew_group=(
                f"CREW-{index + 1}"
            ),

            possession_group=(
                section.section_id
            ),

            compatible_departments=[],

            safety_buffer_before_min=5,

            safety_buffer_after_min=5,

            max_possession_minutes=180,

            asset_id=(
                f"ASSET-{index + 1:03d}"
            ),

            asset_type=(
                "TRACK"
                if department == Department.P_WAY
                else "ELECTRICAL"
                if department == Department.TRD
                else "SIGNALLING"
            ),

            defect_severity=(
                8 - index
            ),

            overdue_days=(
                10 - index * 2
            ),

            asset_criticality=(
                9 - index
            ),

            safety_impact=(
                9 - index
            ),

            train_operation_impact=(
                7 - index
            ),

            priority_level=(
                PriorityLevel.HIGH
            ),
        )

        demand = engine.evaluate(
            demand
        )

        demands.append(
            demand
        )

    # ---------------------------------------------------------
    # Availability
    # ---------------------------------------------------------

    availability = []

    for section in sections:

        availability.append(
            CorridorAvailability(

                section_id=(
                    section.section_id
                ),

                start_min=120,

                end_min=1440,

                available=True,

                reason=(
                    "Control office "
                    "maintenance window."
                ),
            )
        )

    # ---------------------------------------------------------
    # Goods forecast
    # ---------------------------------------------------------

    goods_forecasts = (
        build_goods_forecast(
            sections,
            2880
        )
    )

    # ---------------------------------------------------------
    # Final request
    # ---------------------------------------------------------

    return OptimizationRequest(

        corridor_id=(
            "REAL_RAILWAY_CORRIDOR"
        ),

        horizon_minutes=2880,

        sections=sections,

        trains=trains,

        demands=demands,

        disruption=Disruption(
            active=False,

            train_id=None,

            additional_delay_min=0,

            affected_section_ids=[],

            reason=(
                "No active disruption"
            ),
        ),

        solver_timeout_seconds=10,

        allow_fallback=True,

        state_version=3,

        maintenance_records=[],

        goods_forecasts=goods_forecasts,

        corridor_availability=availability,
    )