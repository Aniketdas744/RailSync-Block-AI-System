from datetime import datetime, timezone

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/integration",
    tags=["Integration"],
)


@router.get("/status")
def integration_status():

    return {
        "status": "ONLINE",
        "service": "RailSync-AI Integration Layer",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@router.post("/coa-event")
def coa_event(payload: dict):

    return {
        "status": "received",
        "source": "COA",
        "payload": payload,
    }


@router.post("/tms-event")
def tms_event(payload: dict):

    return {
        "status": "received",
        "source": "TMS",
        "payload": payload,
    }


@router.post("/ntes-event")
def ntes_event(payload: dict):

    return {
        "status": "received",
        "source": "NTES",
        "payload": payload,
    }