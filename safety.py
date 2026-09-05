from typing import List, Dict, Any


def intervals_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int
) -> bool:
    """
    Check whether two time intervals overlap.

    Example:
    A = 10 to 20
    B = 15 to 25

    They overlap, so the function returns True.
    """

    return max(start_a, start_b) < min(
        end_a,
        end_b
    )


def validate_train_schedule(
    train_schedules: List[Dict[str, Any]]
) -> List[str]:
    """
    Check whether two trains violate the required
    headway on the same railway section.
    """

    conflicts = []

    # Group trains by section
    grouped = {}

    for train in train_schedules:

        section_id = train["section_id"]

        if section_id not in grouped:
            grouped[section_id] = []

        grouped[section_id].append(train)

    # Check each section separately
    for section_id, trains in grouped.items():

        # Sort by starting time
        trains = sorted(
            trains,
            key=lambda x: x["start_min"]
        )

        # Compare neighbouring trains
        for i in range(
            len(trains) - 1
        ):

            current = trains[i]

            following = trains[i + 1]

            current_end = current[
                "end_min"
            ]

            following_start = following[
                "start_min"
            ]

            headway = current.get(
                "headway_minutes",
                5
            )

            required_start = (
                current_end
                + headway
            )

            if following_start < required_start:

                conflicts.append(
                    f"Train conflict on section "
                    f"{section_id}: "
                    f"{current['train_id']} and "
                    f"{following['train_id']}"
                )

    return conflicts


def validate_maintenance_schedule(
    train_schedules: List[Dict[str, Any]],
    maintenance_schedules: List[Dict[str, Any]]
) -> List[str]:
    """
    Check that maintenance possession does not
    overlap with train movement on the same section.
    """

    conflicts = []

    for maintenance in maintenance_schedules:

        maintenance_section = (
            maintenance["section_id"]
        )

        maintenance_start = (
            maintenance["start_min"]
        )

        maintenance_end = (
            maintenance["end_min"]
        )

        buffer_before = maintenance.get(
            "safety_buffer_before_min",
            0
        )

        buffer_after = maintenance.get(
            "safety_buffer_after_min",
            0
        )

        # Expand maintenance interval
        # using the safety buffers.
        protected_start = (
            maintenance_start
            - buffer_before
        )

        protected_end = (
            maintenance_end
            + buffer_after
        )

        for train in train_schedules:

            # Only compare if they use
            # the same section.
            if (
                train["section_id"]
                != maintenance_section
            ):
                continue

            train_start = train[
                "start_min"
            ]

            train_end = train[
                "end_min"
            ]

            if intervals_overlap(
                protected_start,
                protected_end,
                train_start,
                train_end
            ):

                conflicts.append(
                    f"Maintenance "
                    f"{maintenance['demand_id']} "
                    f"conflicts with train "
                    f"{train['train_id']} "
                    f"on section "
                    f"{maintenance_section}"
                )

    return conflicts


def validate_maintenance_duration(
    maintenance_schedules: List[Dict[str, Any]]
) -> List[str]:
    """
    Check that every maintenance activity receives
    at least its required duration.
    """

    conflicts = []

    for maintenance in maintenance_schedules:

        actual_duration = (
            maintenance["end_min"]
            - maintenance["start_min"]
        )

        required_duration = (
            maintenance["duration_min"]
        )

        if actual_duration < required_duration:

            conflicts.append(
                f"Maintenance "
                f"{maintenance['demand_id']} "
                f"has insufficient duration."
            )

    return conflicts


def validate_all(
    train_schedules: List[Dict[str, Any]],
    maintenance_schedules: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Main safety validation function.

    This function combines all deterministic
    safety checks.
    """

    conflicts = []

    # --------------------------------------------------------
    # Check train-to-train conflicts
    # --------------------------------------------------------

    conflicts.extend(
        validate_train_schedule(
            train_schedules
        )
    )

    # --------------------------------------------------------
    # Check train-to-maintenance conflicts
    # --------------------------------------------------------

    conflicts.extend(
        validate_maintenance_schedule(
            train_schedules,
            maintenance_schedules
        )
    )

    # --------------------------------------------------------
    # Check maintenance duration
    # --------------------------------------------------------

    conflicts.extend(
        validate_maintenance_duration(
            maintenance_schedules
        )
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {
        "safe":
            len(conflicts) == 0,

        "conflict_count":
            len(conflicts),

        "conflicts":
            conflicts
    } 