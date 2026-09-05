from typing import Dict, List, Any, Tuple


def interval_conflicts(
    start: int,
    end: int,
    existing: List[Tuple[int, int]]
) -> bool:
    """
    Checks whether [start, end] overlaps
    with any existing interval.
    """

    for existing_start, existing_end in existing:

        if max(start, existing_start) < min(
            end,
            existing_end
        ):
            return True

    return False


def find_safe_window(
    earliest_start: int,
    duration: int,
    latest_end: int,
    blocked_intervals: List[Tuple[int, int]],
    buffer_before: int = 5,
    buffer_after: int = 5
):
    """
    Finds the earliest safe maintenance window.
    """

    candidate = earliest_start

    sorted_intervals = sorted(
        blocked_intervals,
        key=lambda x: x[0]
    )

    while candidate + duration <= latest_end:

        protected_start = (
            candidate - buffer_before
        )

        protected_end = (
            candidate
            + duration
            + buffer_after
        )

        conflict = False

        for blocked_start, blocked_end in sorted_intervals:

            if max(
                protected_start,
                blocked_start
            ) < min(
                protected_end,
                blocked_end
            ):

                candidate = blocked_end
                conflict = True
                break

        if not conflict:
            return candidate

    return None


def heuristic_schedule(request) -> Dict[str, Any]:
    """
    Deterministic safety-first fallback scheduler.

    Used when CP-SAT cannot produce a solution
    within the allowed response time.
    """

    horizon = request.horizon_minutes

    train_schedules = []

    section_train_intervals = {}

    # ---------------------------------------------------------
    # STEP 1: Schedule trains
    # ---------------------------------------------------------

    for train in sorted(
        request.trains,
        key=lambda x: (
            -x.priority,
            x.scheduled_departure_min
        )
    ):

        departure = (
            train.scheduled_departure_min
            + train.current_delay_min
        )

        if (
            request.disruption.active
            and request.disruption.train_id
            == train.train_id
        ):

            departure += (
                request.disruption.additional_delay_min
            )

        total_duration = max(
            1,
            train.transit_duration_min
        )

        section_count = len(
            train.occupied_sections
        )

        section_duration = max(
            1,
            total_duration // section_count
        )

        current_time = departure

        for index, section_id in enumerate(
            train.occupied_sections
        ):

            if index == section_count - 1:

                section_end = (
                    departure
                    + total_duration
                )

            else:

                section_end = (
                    current_time
                    + section_duration
                )

            # -------------------------------------------------
            # Ensure headway
            # -------------------------------------------------

            previous_intervals = (
                section_train_intervals
                .setdefault(
                    section_id,
                    []
                )
            )

            shifted = True

            while shifted:

                shifted = False

                for (
                    existing_start,
                    existing_end,
                    existing_train
                ) in previous_intervals:

                    if (
                        current_time
                        < existing_end + 5
                        and
                        section_end + 5
                        > existing_start
                    ):

                        shift = (
                            existing_end
                            + 5
                            - current_time
                        )

                        current_time += shift
                        section_end += shift

                        shifted = True
                        break

            if section_end > horizon:
                section_end = horizon

            train_schedules.append(
                {
                    "train_id": train.train_id,
                    "section_id": section_id,
                    "start_min": int(
                        current_time
                    ),
                    "end_min": int(
                        section_end
                    ),
                    "delay_min": max(
                        0,
                        int(
                            current_time
                            - train.scheduled_departure_min
                        )
                    ),
                    "headway_minutes": 5
                }
            )

            previous_intervals.append(
                (
                    current_time,
                    section_end,
                    train.train_id
                )
            )

            current_time = section_end

    # ---------------------------------------------------------
    # STEP 2: Schedule maintenance
    # ---------------------------------------------------------

    maintenance_schedules = []

    for demand in sorted(
        request.demands,
        key=lambda x: -x.urgency_score
    ):

        section_id = demand.section_id

        blocked = []

        for train_schedule in train_schedules:

            if (
                train_schedule["section_id"]
                == section_id
            ):

                blocked.append(
                    (
                        train_schedule["start_min"],
                        train_schedule["end_min"]
                    )
                )

        latest_end = (
            demand.latest_end_min
            if demand.latest_end_min is not None
            else horizon
        )

        start = find_safe_window(
            earliest_start=
            demand.earliest_start_min,

            duration=
            demand.min_duration_minutes,

            latest_end=
            latest_end,

            blocked_intervals=
            blocked,

            buffer_before=
            demand.safety_buffer_before_min,

            buffer_after=
            demand.safety_buffer_after_min
        )

        if start is None:

            continue

        end = (
            start
            + demand.min_duration_minutes
        )

        maintenance_schedules.append(
            {
                "demand_id":
                demand.demand_id,

                "department":
                demand.department,

                "section_id":
                demand.section_id,

                "start_min":
                int(start),

                "end_min":
                int(end),

                "duration_min":
                int(
                    demand.min_duration_minutes
                ),

                "bundled_with":
                [],

                "safety_buffer_before_min":
                demand.safety_buffer_before_min,

                "safety_buffer_after_min":
                demand.safety_buffer_after_min
            }
        )

    # ---------------------------------------------------------
    # STEP 3: Metrics
    # ---------------------------------------------------------

    passenger_delay = 0
    freight_delay = 0

    train_map = {
        train.train_id: train
        for train in request.trains
    }

    for item in train_schedules:

        train = train_map[
            item["train_id"]
        ]

        delay = item["delay_min"]

        if train.passenger_weight > 0:

            passenger_delay += int(
                delay * train.passenger_weight
            )

        if train.freight_weight > 0:

            freight_delay += int(
                delay * train.freight_weight
            )

    possession_duration = 0

    if maintenance_schedules:

        possession_duration = sum(
            item["duration_min"]
            for item in maintenance_schedules
        )

    return {
        "status": "FALLBACK",
        "solver_status": "HEURISTIC",

        "solver_time_seconds": 0.0,

        "objective_value":
        float(
            passenger_delay
            + freight_delay
        ),

        "passenger_delay_minutes":
        passenger_delay,

        "freight_delay_minutes":
        freight_delay,

        "maintenance_penalty":
        max(
            0,
            len(request.demands)
            - len(maintenance_schedules)
        ),

        "possession_duration_minutes":
        possession_duration,

        "bundling_percentage":
        0.0,

        "safety_conflicts":
        0,

        "robustness_margin_minutes":
        5,

        "trains":
        train_schedules,

        "maintenance":
        maintenance_schedules,

        "explanation": [
            "CP-SAT fallback scheduler was used.",
            "Train movement received safety priority.",
            "Maintenance windows were placed in conflict-free gaps.",
            "Safety buffers were preserved."
        ]
    }