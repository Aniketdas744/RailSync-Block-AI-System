from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models import (
    OptimizationRequest,
    Disruption,
)

from optimizer import (
    solve_railway_blocks,
)

from integration import (
    router as integration_router,
)

from database import (
    database_status,
)

from database_queries import (
    get_trains,
)

from database_maintenence import (
    get_maintenance_demands,
)

from real_dataset import (
    get_real_dataset,
)


app = FastAPI(
    title="RailSync-AI Operations API",
    version="2.1.2",
    description=(
        "AI-assisted railway possession "
        "planning and maintenance block "
        "optimization using OR-Tools CP-SAT."
    ),
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "null",
    ],

    allow_credentials=False,

    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],

    allow_headers=["*"],
)


app.include_router(
    integration_router
)


class RealOptimizationRequest(BaseModel):

    disruption_active: bool = False

    disruption_train_id: Optional[str] = None

    disruption_section_id: Optional[str] = None

    disruption_delay_min: int = Field(
        default=35,
        ge=0,
        le=1440,
    )

    disruption_reason: str = (
        "Simulated disruption"
    )


@app.get("/")
def root():

    return {
        "application": "RailSync-AI",

        "status": "ONLINE",

        "version": "2.1.2",

        "engine": (
            "Google OR-Tools CP-SAT"
        ),

        "data_mode": (
            "REAL_RAILWAY_TIMETABLE"
        ),

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/api/health")
def health():

    return {
        "status": "ONLINE",

        "service": "RailSync-AI",

        "engine": (
            "OR-Tools CP-SAT"
        ),

        "data_mode": (
            "REAL_RAILWAY_TIMETABLE"
        ),

        "database": database_status(),

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@app.get("/api/trains")
def trains():

    try:

        train_list = get_trains()

        return {
            "status": "success",

            "count": len(
                train_list
            ),

            "trains": train_list,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,

            detail=(
                "Database query failed: "
                f"{exc}"
            ),
        )


@app.get("/api/maintenance")
def maintenance():

    try:

        demand_list = (
            get_maintenance_demands()
        )

        return {
            "status": "success",

            "count": len(
                demand_list
            ),

            "maintenance_demands":
                demand_list,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,

            detail=(
                "Database query failed: "
                f"{exc}"
            ),
        )


@app.get("/api/version")
def version():

    return {
        "application": "RailSync-AI",

        "version": "2.1.2",

        "architecture": (
            "FastAPI + CP-SAT + "
            "PostgreSQL/PostGIS + "
            "Real Railway Timetable"
        ),

        "data_mode": (
            "REAL_RAILWAY_TIMETABLE"
        ),
    }


@app.get("/api/real-dataset")
def real_dataset():

    try:

        dataset = (
            get_real_dataset()
        )

        if dataset.disruption is None:

            dataset.disruption = Disruption(
                active=False,

                train_id=None,

                additional_delay_min=0,

                affected_section_ids=[],

                reason=(
                    "No active disruption"
                ),
            )

        elif isinstance(
            dataset.disruption,
            dict,
        ):

            dataset.disruption = (
                Disruption.model_validate(
                    dataset.disruption
                )
            )

        return {

            "status": "success",

            "data_mode": (
                "REAL_RAILWAY_TIMETABLE"
            ),

            "corridor_id":
                dataset.corridor_id,

            "counts": {

                "trains":
                    len(dataset.trains),

                "sections":
                    len(dataset.sections),

                "maintenance_demands":
                    len(dataset.demands),
            },

            "data":
                dataset.model_dump(
                    mode="json"
                ),
        }

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(
                "Real dataset loading "
                f"failed: {exc}"
            ),
        )


@app.post("/api/real-optimize")
def real_optimize(
    request: RealOptimizationRequest,
):

    try:

        dataset = get_real_dataset()

        if dataset.disruption is None:

            dataset.disruption = Disruption(
                active=False,

                train_id=None,

                additional_delay_min=0,

                affected_section_ids=[],

                reason=(
                    "No active disruption"
                ),
            )

        if not request.disruption_active:

            dataset.disruption = Disruption(

                active=False,

                train_id=None,

                additional_delay_min=0,

                affected_section_ids=[],

                reason=(
                    "No active disruption"
                ),
            )

        else:

            if not request.disruption_train_id:

                raise HTTPException(

                    status_code=400,

                    detail=(
                        "disruption_train_id "
                        "is required when "
                        "disruption_active "
                        "is true."
                    ),
                )

            train_ids = {

                str(train.train_id)

                for train in dataset.trains

            }

            if (
                str(
                    request.disruption_train_id
                )
                not in train_ids
            ):

                raise HTTPException(

                    status_code=400,

                    detail=(
                        f"Train "
                        f"{request.disruption_train_id} "
                        "was not found in the "
                        "real timetable dataset."
                    ),
                )

            affected_sections = []

            for train in dataset.trains:

                if (
                    str(train.train_id)
                    ==
                    str(
                        request.disruption_train_id
                    )
                ):

                    train_sections = list(
                        train.section_durations.keys()
                    )

                    if request.disruption_section_id:

                        if (
                            request.disruption_section_id
                            not in train_sections
                        ):

                            raise HTTPException(

                                status_code=400,

                                detail=(
                                    f"Section "
                                    f"{request.disruption_section_id} "
                                    "is not occupied by "
                                    f"train "
                                    f"{request.disruption_train_id}."
                                ),
                            )

                        affected_sections = [
                            request.disruption_section_id
                        ]

                    else:

                        affected_sections = (
                            train_sections
                        )

                    break

            dataset.disruption = Disruption(

                active=True,

                train_id=(
                    str(
                        request.disruption_train_id
                    )
                ),

                additional_delay_min=int(
                    request.disruption_delay_min
                ),

                affected_section_ids=(
                    affected_sections
                ),

                reason=(
                    request.disruption_reason
                ),
            )

        result = solve_railway_blocks(
            dataset
        )

        return {

            "status": "success",

            "data_mode": (
                "REAL_RAILWAY_TIMETABLE"
            ),

            "corridor_id":
                dataset.corridor_id,

            "disruption":
                dataset.disruption.model_dump(
                    mode="json"
                ),

            "dataset_summary": {

                "trains":
                    len(dataset.trains),

                "sections":
                    len(dataset.sections),

                "maintenance_demands":
                    len(dataset.demands),

                "horizon_minutes":
                    dataset.horizon_minutes,
            },

            "result":
                result,
        }

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(
                "Real railway optimization "
                f"failed: {exc}"
            ),
        )


@app.post("/api/optimize")
def optimize(
    request: OptimizationRequest,
):

    if not request.trains:

        raise HTTPException(

            status_code=400,

            detail=(
                "At least one train "
                "is required."
            ),
        )

    if not request.demands:

        raise HTTPException(

            status_code=400,

            detail=(
                "At least one maintenance "
                "demand is required."
            ),
        )

    try:

        if request.disruption is not None:

            if isinstance(
                request.disruption,
                dict,
            ):

                request.disruption = (
                    Disruption.model_validate(
                        request.disruption
                    )
                )

        result = solve_railway_blocks(
            request
        )

        return result

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(
                "Optimization failure: "
                f"{exc}"
            ),
        )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=False,
    )