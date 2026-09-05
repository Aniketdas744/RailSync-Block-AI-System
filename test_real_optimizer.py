from real_dataset import get_real_dataset
from optimizer import solve_railway_blocks


# ============================================================
# TIME FORMATTER
# ============================================================

def minutes_to_time(minutes):

    minutes = int(minutes)

    day = minutes // 1440

    minutes = minutes % 1440

    hours = minutes // 60

    mins = minutes % 60

    if day > 0:

        return (
            f"{hours:02d}:{mins:02d}"
            f" (+{day} day)"
        )

    return (
        f"{hours:02d}:{mins:02d}"
    )


# ============================================================
# HEADER
# ============================================================

print(
    "========================================"
)

print(
    "   REAL RAILWAY OPTIMIZER DEBUG TEST"
)

print(
    "========================================"
)


# ============================================================
# LOAD DATASET
# ============================================================

dataset = get_real_dataset()

print()

print(
    "Input dataset:"
)

print(
    f"Sections : "
    f"{len(dataset.sections)}"
)

print(
    f"Trains   : "
    f"{len(dataset.trains)}"
)

print(
    f"Demands  : "
    f"{len(dataset.demands)}"
)

print(
    f"Horizon  : "
    f"{dataset.horizon_minutes} minutes"
)


# ============================================================
# TRAIN DETAILS
# ============================================================

print()

print(
    "Train details:"
)

for train in dataset.trains:

    print()

    print(
        f"{train.train_id} - "
        f"{train.name}"
    )

    print(
        f"  Direction           : "
        f"{train.direction}"
    )

    print(
        f"  Scheduled departure : "
        f"{train.scheduled_departure_min}"
    )

    print(
        f"  Max preferred delay : "
        f"{train.max_departure_delay_min}"
    )

    print(
        f"  Transit duration    : "
        f"{train.transit_duration_min}"
    )

    print(
        f"  Sections            : "
        f"{len(train.occupied_sections)}"
    )

    print(
        "  Timetable sections:"
    )

    for section_id in (
        train.occupied_sections
    ):

        duration = (
            train.section_durations[
                section_id
            ]
        )

        offset = (
            train.section_start_offsets.get(
                section_id,
                0
            )
        )

        print(
            f"    {section_id} "
            f"-> offset {offset} min, "
            f"duration {duration} min"
        )


# ============================================================
# RUN OPTIMIZER
# ============================================================

print()

print(
    "----------------------------------------"
)

print(
    "Running CP-SAT optimizer..."
)

print(
    "----------------------------------------"
)

result = solve_railway_blocks(
    dataset
)


# ============================================================
# RESULT
# ============================================================

print()

print(
    "========================================"
)

print(
    "           OPTIMIZER RESULT"
)

print(
    "========================================"
)

print(
    f"Status          : "
    f"{result.get('status')}"
)

print(
    f"Solver          : "
    f"{result.get('solver')}"
)

print(
    f"Solver Time     : "
    f"{result.get('solver_time_seconds')} sec"
)

print(
    f"Objective Value : "
    f"{result.get('objective_value')}"
)


# ============================================================
# DISRUPTION
# ============================================================

disruption = result.get(
    "disruption",
    {}
)

print()

print(
    "Disruption:"
)

print(
    f"  Active      : "
    f"{disruption.get('active')}"
)

print(
    f"  Train       : "
    f"{disruption.get('train_id')}"
)

print(
    f"  Added delay : "
    f"{disruption.get('additional_delay_min')} min"
)


# ============================================================
# PERFORMANCE METRICS
# ============================================================

metrics = result.get(
    "metrics",
    {}
)

print()

print(
    "Performance:"
)

print(
    f"  Passenger Delay     : "
    f"{metrics.get('passenger_delay', 0)} min"
)

print(
    f"  Freight Delay       : "
    f"{metrics.get('freight_delay', 0)} min"
)

print(
    f"  Total Delay         : "
    f"{metrics.get('total_delay', 0)} min"
)

print(
    f"  Possession Duration : "
    f"{metrics.get('possession_duration', 0)} min"
)

print(
    f"  Bundling            : "
    f"{metrics.get('bundling_percentage', 0)}%"
)


# ============================================================
# SAFETY
# ============================================================

safety = result.get(
    "safety",
    {}
)

print()

print(
    "Safety:"
)

print(
    f"  Safe           : "
    f"{safety.get('safe')}"
)

print(
    f"  Conflict Count : "
    f"{safety.get('conflict_count', 0)}"
)

if safety.get("conflicts"):

    print(
        "  Conflicts:"
    )

    for conflict in safety[
        "conflicts"
    ]:

        print(
            f"    - {conflict}"
        )


# ============================================================
# TRAIN SCHEDULE
# ============================================================

train_schedule = result.get(
    "train_schedule",
    []
)

print()

print(
    "========================================"
)

print(
    "          OPTIMIZED TRAIN SCHEDULE"
)

print(
    "========================================"
)


if not train_schedule:

    print(
        "No train schedule generated."
    )

else:

    current_train = None

    for item in train_schedule:

        train_id = item[
            "train_id"
        ]

        if train_id != current_train:

            print()

            print(
                f"Train {train_id}"
            )

            print(
                "----------------------------------------"
            )

            current_train = train_id

        start = item[
            "start_min"
        ]

        end = item[
            "end_min"
        ]

        delay = item.get(
            "train_delay_min",
            0
        )

        print(
            f"  {item['section_id']}: "
            f"{minutes_to_time(start)} "
            f"-> "
            f"{minutes_to_time(end)} "
            f"| delay={delay} min"
        )


# ============================================================
# MAINTENANCE
# ============================================================

maintenance = result.get(
    "maintenance_schedule",
    []
)

print()

print(
    "========================================"
)

print(
    "        MAINTENANCE SCHEDULE"
)

print(
    "========================================"
)


if not maintenance:

    print(
        "No maintenance demands "
        "in the real dataset."
    )

else:

    for item in maintenance:

        print(
            f"{item['demand_id']} | "
            f"{item['section_id']} | "
            f"{minutes_to_time(item['start_min'])} "
            f"-> "
            f"{minutes_to_time(item['end_min'])}"
        )


# ============================================================
# COMPLETE
# ============================================================

print()

print(
    "========================================"
)

print(
    "          TEST COMPLETED"
)

print(
    "========================================"
)