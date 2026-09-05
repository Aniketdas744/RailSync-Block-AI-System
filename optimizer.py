from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from models import OptimizationRequest


def classify_delay(delay):
    d = max(0, int(delay or 0))

    if d <= 0:
        return {
            "level": "NORMAL",
            "action": "KEEP_PLAN",
            "description": "No train delay.",
        }

    if d <= 15:
        return {
            "level": "MINOR",
            "action": "MONITOR",
            "description": "Minor delay: monitor the plan.",
        }

    if d <= 30:
        return {
            "level": "MODERATE",
            "action": "CHECK_AND_ADJUST",
            "description": (
                "Moderate delay: check affected sections "
                "and adjust if required."
            ),
        }

    return {
        "level": "MAJOR",
        "action": "FULL_REOPTIMIZE",
        "description": (
            "Major delay: fully re-optimize the train "
            "and maintenance plan."
        ),
    }


def _value(value):
    return getattr(value, "value", str(value))


def _train_sections(train):
    if train.occupied_sections:
        return list(train.occupied_sections)

    return list(train.section_durations.keys())


def _train_delay(request, train):
    disruption = request.disruption

    if (
        disruption
        and disruption.active
        and disruption.train_id == train.train_id
    ):
        return max(
            0,
            int(disruption.additional_delay_min or 0),
        )

    return max(
        0,
        int(train.current_delay_min or 0),
    )


def _availability(request, section_id, duration):
    windows = [
        window
        for window in request.corridor_availability
        if (
            window.section_id == section_id
            and window.available
            and int(window.end_min)
            - int(window.start_min)
            >= duration
        )
    ]

    return sorted(
        windows,
        key=lambda window: (
            int(window.start_min),
            int(window.end_min),
        ),
    )


def _candidate_starts(request, demand):
    duration = int(demand.min_duration_minutes)

    earliest = max(
        0,
        int(demand.earliest_start_min or 0),
    )

    horizon = int(request.horizon_minutes)

    latest_end = (
        int(demand.latest_end_min)
        if demand.latest_end_min is not None
        else horizon
    )

    latest_start = min(
        horizon - duration,
        latest_end - duration,
    )

    if demand.max_possession_minutes is not None:
        latest_start = min(
            latest_start,
            horizon - int(
                demand.max_possession_minutes
            ),
        )

    if latest_start < earliest:
        return []

    windows = _availability(
        request,
        demand.section_id,
        duration,
    )

    starts = []

    if windows:
        for window in windows:

            low = max(
                earliest,
                int(window.start_min),
            )

            high = min(
                latest_start,
                int(window.end_min) - duration,
            )

            for start in range(
                low,
                high + 1,
                5,
            ):
                starts.append(start)

    else:

        for start in range(
            earliest,
            latest_start + 1,
            5,
        ):
            starts.append(start)

    return sorted(set(starts))


def _overlap(a, b, c, d):
    return a < d and c < b


def _priority_weight(demand):
    score = float(
        demand.ai_priority_score or 0
    )

    level = _value(
        demand.priority_level
    )

    if level == "CRITICAL" or score >= 8.5:
        return 1000

    if level == "HIGH" or score >= 7:
        return 700

    if level == "MEDIUM" or score >= 5:
        return 400

    return 150


def _congestion(
    request,
    section_id,
    start,
    end,
):
    values = [
        int(forecast.congestion_level)
        for forecast in request.goods_forecasts
        if (
            forecast.section_id == section_id
            and _overlap(
                start,
                end,
                int(forecast.start_min),
                int(forecast.end_min),
            )
        )
    ]

    return max(values, default=0)


def _empty_result(
    request,
    reason,
):
    disruption = request.disruption

    active = bool(
        disruption
        and disruption.active
    )

    train_id = (
        disruption.train_id
        if active
        else None
    )

    delay = (
        int(disruption.additional_delay_min or 0)
        if active
        else 0
    )

    policy = classify_delay(delay)

    return {
        "status": "INFEASIBLE",
        "reason": reason,
        "solver": "CP-SAT",
        "objective_value": 0.0,
        "solver_time_seconds": 0.0,

        "disruption": {
            "active": active,
            "train_id": train_id,
            "additional_delay_min": delay,
            "affected_section_ids": (
                list(disruption.affected_section_ids)
                if active
                else []
            ),
            "level": policy["level"],
            "action": policy["action"],
            "description": policy["description"],
        },

        "metrics": {
            "passenger_delay": 0,
            "freight_delay": 0,
            "total_delay": 0,
            "total_waiting": 0,
            "possession_duration": 0,
            "bundling_percentage": 0.0,
            "scheduled_tasks": 0,
            "deferred_tasks": len(request.demands),

            "critical_tasks": sum(
                _value(d.priority_level) == "CRITICAL"
                for d in request.demands
            ),

            "high_priority_tasks": sum(
                _value(d.priority_level) == "HIGH"
                for d in request.demands
            ),

            "medium_priority_tasks": sum(
                _value(d.priority_level) == "MEDIUM"
                for d in request.demands
            ),

            "low_priority_tasks": sum(
                _value(d.priority_level) == "LOW"
                for d in request.demands
            ),
        },

        "train_schedule": [],

        "maintenance_schedule": [],

        "deferred_maintenance": [
            {
                "demand_id": demand.demand_id,
                "section_id": demand.section_id,
                "priority_level": _value(
                    demand.priority_level
                ),
                "reason": "No feasible candidate window.",
            }
            for demand in request.demands
        ],

        "safety": {
            "safe": True,
            "conflict_count": 0,
            "conflicts": [],
        },

        "planning_summary": {
            "corridor_id": request.corridor_id,
            "planning_horizon": _value(
                request.planning_horizon
            ),
            "human_approval_required": True,
        },
    }


def _department_label(department):
    raw = _value(department)

    return {
        "P-WAY": "Track / Civil",
        "TRD": "Electrical / Traction",
        "S&T": "Signalling & Telecom",
        "OTHER": "Other",
    }.get(
        raw,
        raw,
    )


def solve_railway_blocks(
    request: OptimizationRequest,
):
    model = cp_model.CpModel()

    horizon = int(
        request.horizon_minutes
    )

    train_intervals = []

    train_schedule_template = []

    for train in request.trains:

        delay = _train_delay(
            request,
            train,
        )

        sections = _train_sections(train)

        if not sections:
            continue

        for section_id in sections:

            duration = int(
                train.section_durations.get(
                    section_id,
                    5,
                )
            )

            offset = int(
                train.section_start_offsets.get(
                    section_id,
                    0,
                )
            )

            start = (
                int(train.scheduled_departure_min)
                + delay
                + offset
            )

            end = start + max(1, duration)

            if start >= horizon:
                continue

            train_intervals.append(
                (
                    section_id,
                    start,
                    min(end, horizon),
                    train.train_id,
                )
            )

            train_schedule_template.append(
                {
                    "train_id": train.train_id,
                    "name": train.name,
                    "section_id": section_id,
                    "start_min": start,
                    "end_min": min(end, horizon),
                    "departure_delay_min": delay,
                    "direction": train.direction,
                }
            )

    scheduled_vars = {}

    interval_vars = []

    for demand in request.demands:

        starts = _candidate_starts(
            request,
            demand,
        )

        if not starts:

            scheduled_vars[
                demand.demand_id
            ] = model.NewConstant(0)

            continue

        scheduled = model.NewBoolVar(
            f"scheduled_{demand.demand_id}"
        )

        scheduled_vars[
            demand.demand_id
        ] = scheduled

        choices = []

        for index, start in enumerate(starts):

            choice = model.NewBoolVar(
                f"{demand.demand_id}_choice_{index}"
            )

            choices.append(choice)

            duration = int(
                demand.min_duration_minutes
            )

            end = start + duration

            interval = model.NewOptionalIntervalVar(
                start,
                duration,
                end,
                choice,
                f"maint_{demand.demand_id}_{index}",
            )

            interval_vars.append(
                (
                    demand,
                    interval,
                    choice,
                    start,
                    end,
                )
            )

        model.Add(
            sum(choices) == scheduled
        )

    by_section = {}

    for (
        demand,
        interval,
        choice,
        start,
        end,
    ) in interval_vars:

        by_section.setdefault(
            demand.section_id,
            [],
        ).append(interval)

    for intervals in by_section.values():
        model.AddNoOverlap(intervals)

    for (
        demand,
        interval,
        choice,
        start,
        end,
    ) in interval_vars:

        before = int(
            demand.safety_buffer_before_min or 0
        )

        after = int(
            demand.safety_buffer_after_min or 0
        )

        for (
            section_id,
            train_start,
            train_end,
            train_id,
        ) in train_intervals:

            if section_id != demand.section_id:
                continue

            if _overlap(
                start - before,
                end + after,
                train_start,
                train_end,
            ):
                model.Add(choice == 0)
                break

    objective_terms = []

    for demand in request.demands:

        variable = scheduled_vars[
            demand.demand_id
        ]

        weight = _priority_weight(demand)

        objective_terms.append(
            weight * variable
        )

    for (
        demand,
        interval,
        choice,
        start,
        end,
    ) in interval_vars:

        congestion = _congestion(
            request,
            demand.section_id,
            start,
            end,
        )

        objective_terms.append(
            -congestion * choice
        )

        objective_terms.append(
            -(start // 5) * choice
        )

    if objective_terms:
        model.Maximize(
            sum(objective_terms)
        )

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = max(
        1,
        int(
            request.solver_timeout_seconds or 10
        ),
    )

    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        return _empty_result(
            request,
            "No safe plan found within the supplied constraints.",
        )

    maintenance_schedule = []

    deferred = []

    selected_by_section = {}

    for demand in request.demands:

        selected = []

        for (
            current_demand,
            interval,
            choice,
            start,
            end,
        ) in interval_vars:

            if (
                current_demand.demand_id
                == demand.demand_id
                and solver.Value(choice) == 1
            ):

                selected.append(
                    (start, end)
                )

        if not selected:

            deferred.append(
                {
                    "demand_id": demand.demand_id,
                    "section_id": demand.section_id,
                    "priority_level": _value(
                        demand.priority_level
                    ),
                    "reason": (
                        "Deferred because no "
                        "conflict-free window "
                        "was selected."
                    ),
                }
            )

            continue

        start, end = selected[0]

        affected = []

        before = int(
            demand.safety_buffer_before_min or 0
        )

        after = int(
            demand.safety_buffer_after_min or 0
        )

        for (
            section_id,
            train_start,
            train_end,
            train_id,
        ) in train_intervals:

            if (
                section_id == demand.section_id
                and _overlap(
                    start - before,
                    end + after,
                    train_start,
                    train_end,
                )
            ):
                affected.append(train_id)

        selected_by_section.setdefault(
            demand.section_id,
            [],
        ).append(
            (
                start,
                end,
                demand,
            )
        )

        maintenance_schedule.append(
            {
                "demand_id": demand.demand_id,

                "department": _value(
                    demand.department
                ),

                "department_label": _department_label(
                    demand.department
                ),

                "section_id": demand.section_id,

                "start_min": start,

                "end_min": end,

                "duration_min": end - start,

                "bundled": False,

                "priority_level": _value(
                    demand.priority_level
                ),

                "ai_priority_score": float(
                    demand.ai_priority_score or 0
                ),

                "safe": len(affected) == 0,

                "affected_trains": affected,

                "explanation": (
                    demand.reason
                    or
                    f"Scheduled in a conflict-free "
                    f"window for {demand.section_id}."
                ),
            }
        )

    for section_id, rows in selected_by_section.items():

        for i, (
            start_a,
            end_a,
            demand_a,
        ) in enumerate(rows):

            for (
                start_b,
                end_b,
                demand_b,
            ) in rows[i + 1:]:

                if (
                    _overlap(
                        start_a,
                        end_a,
                        start_b,
                        end_b,
                    )
                    and demand_a.department
                    != demand_b.department
                ):

                    for item in maintenance_schedule:

                        if item["demand_id"] in (
                            demand_a.demand_id,
                            demand_b.demand_id,
                        ):
                            item["bundled"] = True

    scheduled_tasks = len(
        maintenance_schedule
    )

    total_tasks = len(
        request.demands
    )

    bundles = sum(
        1
        for item in maintenance_schedule
        if item["bundled"]
    )

    merged_possession = 0

    for section_id, rows in selected_by_section.items():

        spans = sorted(
            (
                row[0],
                row[1],
            )
            for row in rows
        )

        merged = []

        for start, end in spans:

            if (
                not merged
                or start > merged[-1][1]
            ):
                merged.append(
                    [start, end]
                )
            else:
                merged[-1][1] = max(
                    merged[-1][1],
                    end,
                )

        merged_possession += sum(
            end - start
            for start, end in merged
        )

    passenger_delay = 0
    freight_delay = 0
    total_waiting = 0

    train_delays = {}

    for train in request.trains:

        delay = _train_delay(
            request,
            train,
        )

        train_delays[
            train.train_id
        ] = delay

        if int(train.passenger_weight or 0) > 0:
            passenger_delay += delay

        if int(train.freight_weight or 0) > 0:
            freight_delay += delay

        total_waiting += delay

    total_delay = sum(
        train_delays.values()
    )

    disruption = request.disruption

    active = bool(
        disruption
        and disruption.active
    )

    disrupted_train_id = (
        disruption.train_id
        if active
        else None
    )

    disruption_delay = (
        int(
            disruption.additional_delay_min or 0
        )
        if active
        else 0
    )

    policy = classify_delay(
        disruption_delay
    )

    affected_sections = (
        list(
            disruption.affected_section_ids
        )
        if active
        else []
    )

    if active and not affected_sections:

        disrupted_train = next(
            (
                train
                for train in request.trains
                if train.train_id
                == disrupted_train_id
            ),
            None,
        )

        if disrupted_train:
            affected_sections = _train_sections(
                disrupted_train
            )

    safety_conflicts = [
        item
        for item in maintenance_schedule
        if not item["safe"]
    ]

    safe = len(
        safety_conflicts
    ) == 0

    return {
        "status": (
            "OPTIMAL"
            if status == cp_model.OPTIMAL
            else "FEASIBLE"
        ),

        "solver": "CP-SAT",

        "objective_value": float(
            solver.ObjectiveValue()
        ),

        "solver_time_seconds": round(
            solver.WallTime(),
            4,
        ),

        "disruption": {
            "active": active,

            "train_id": disrupted_train_id,

            "additional_delay_min": disruption_delay,

            "affected_section_ids": affected_sections,

            "level": policy["level"],

            "action": policy["action"],

            "description": policy["description"],

            "recommended_action": {
                "NORMAL":
                    "Keep the maintenance plan.",

                "MINOR":
                    "Monitor the revised train movement.",

                "MODERATE":
                    "Check affected sections "
                    "and adjust conflicting work.",

                "MAJOR":
                    "Fully re-optimize and obtain "
                    "controller approval.",
            }[policy["level"]],
        },

        "metrics": {
            "passenger_delay": passenger_delay,

            "freight_delay": freight_delay,

            "total_delay": total_delay,

            "total_waiting": total_waiting,

            "possession_duration": merged_possession,

            "bundling_percentage": round(
                100
                * bundles
                / max(
                    1,
                    scheduled_tasks,
                ),
                1,
            ),

            "scheduled_tasks": scheduled_tasks,

            "deferred_tasks": (
                total_tasks
                - scheduled_tasks
            ),

            "critical_tasks": sum(
                _value(
                    demand.priority_level
                ) == "CRITICAL"
                for demand in request.demands
            ),

            "high_priority_tasks": sum(
                _value(
                    demand.priority_level
                ) == "HIGH"
                for demand in request.demands
            ),

            "medium_priority_tasks": sum(
                _value(
                    demand.priority_level
                ) == "MEDIUM"
                for demand in request.demands
            ),

            "low_priority_tasks": sum(
                _value(
                    demand.priority_level
                ) == "LOW"
                for demand in request.demands
            ),
        },

        "train_schedule": train_schedule_template,

        "maintenance_schedule": maintenance_schedule,

        "deferred_maintenance": deferred,

        "safety": {
            "safe": safe,

            "conflict_count": len(
                safety_conflicts
            ),

            "conflicts": [
                (
                    f"Maintenance "
                    f"{item['demand_id']} "
                    f"overlaps a protected "
                    f"train movement."
                )
                for item in safety_conflicts
            ],
        },

        "planning_summary": {
            "corridor_id": request.corridor_id,

            "planning_horizon": _value(
                request.planning_horizon
            ),

            "sections": len(
                request.sections
            ),

            "trains": len(
                request.trains
            ),

            "maintenance_tasks": total_tasks,

            "scheduled_tasks": scheduled_tasks,

            "deferred_tasks": (
                total_tasks
                - scheduled_tasks
            ),

            "goods_forecast_records": len(
                request.goods_forecasts
            ),

            "candidate_windows": len(
                request.corridor_availability
            ),

            "ai_priority_enabled": any(
                float(
                    demand.ai_priority_score or 0
                ) > 0
                for demand in request.demands
            ),

            "goods_forecast_enabled": bool(
                request.goods_forecasts
            ),

            "corridor_availability_enabled": bool(
                request.corridor_availability
            ),

            "human_approval_required": True,

            "decision_support_only": True,

            "delay_policy": {
                "0_min": "KEEP_PLAN",
                "1_15_min": "MONITOR",
                "16_30_min": "CHECK_AND_ADJUST",
                "31_plus_min": "FULL_REOPTIMIZE",
            },
        },
    }