from models import (
    BlockDemand,
    PriorityLevel,
)


class MaintenancePriorityEngine:

    WEIGHTS = {
        "defect_severity": 0.25,
        "overdue": 0.15,
        "asset_criticality": 0.20,
        "safety_impact": 0.30,
        "train_operation_impact": 0.10,
    }

    def calculate_score(
        self,
        demand: BlockDemand,
    ):

        overdue_score = min(
            10,
            max(
                0,
                int(
                    demand.overdue_days
                )
            )
        )

        score = (
            demand.defect_severity
            * self.WEIGHTS[
                "defect_severity"
            ]
        )

        score += (
            overdue_score
            * self.WEIGHTS[
                "overdue"
            ]
        )

        score += (
            demand.asset_criticality
            * self.WEIGHTS[
                "asset_criticality"
            ]
        )

        score += (
            demand.safety_impact
            * self.WEIGHTS[
                "safety_impact"
            ]
        )

        score += (
            demand.train_operation_impact
            * self.WEIGHTS[
                "train_operation_impact"
            ]
        )

        return round(
            score,
            2
        )

    def priority_level(
        self,
        score,
    ):

        if score >= 8.5:
            return PriorityLevel.CRITICAL

        if score >= 7:
            return PriorityLevel.HIGH

        if score >= 5:
            return PriorityLevel.MEDIUM

        return PriorityLevel.LOW

    def evaluate(
        self,
        demand: BlockDemand,
    ):

        score = self.calculate_score(
            demand
        )

        level = self.priority_level(
            score
        )

        demand.ai_priority_score = score

        demand.priority_level = level

        demand.reason = (
            "AI priority calculated from "
            "defect severity, overdue status, "
            "asset criticality, safety impact "
            "and train operation impact."
        )

        return demand