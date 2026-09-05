from typing import List

from models import (
    BlockDemand,
    Department,
    MaintenanceData,
    MaintenanceSource,
)


# ============================================================
# TMS - TRACK MANAGEMENT SYSTEM
# ============================================================

def load_tms_data() -> List[MaintenanceData]:
    """
    Representative TMS data.
    """
    return [
        MaintenanceData(
            record_id="TMS-001",
            source_system=MaintenanceSource.TMS,
            department=Department.P_WAY,
            asset_id="TRACK-GAYA-DDU-01",
            asset_type="TRACK",
            section_id="REAL_GAYA_DDU",
            defect_description="Track condition requires scheduled maintenance",
            defect_severity=8,
            overdue_days=12,
            asset_criticality=9,
            safety_impact=9,
            train_operation_impact=7,
            estimated_work_minutes=90,
            is_overdue=True,
            requested_by="P-WAY",
            source_reference="TMS-001",
        ),
        MaintenanceData(
            record_id="TMS-002",
            source_system=MaintenanceSource.TMS,
            department=Department.P_WAY,
            asset_id="TRACK-ASN-DHN-01",
            asset_type="TRACK",
            section_id="REAL_ASN_DHN",
            defect_description="Preventive track maintenance due",
            defect_severity=6,
            overdue_days=5,
            asset_criticality=7,
            safety_impact=7,
            train_operation_impact=6,
            estimated_work_minutes=75,
            is_overdue=True,
            requested_by="P-WAY",
            source_reference="TMS-002",
        ),
    ]


# ============================================================
# SMMS - SIGNAL MAINTENANCE & MANAGEMENT SYSTEM
# ============================================================

def load_smms_data() -> List[MaintenanceData]:
    """
    Representative SMMS data.
    """
    return [
        MaintenanceData(
            record_id="SMMS-001",
            source_system=MaintenanceSource.SMMS,
            department=Department.S_AND_T,
            asset_id="SIGNAL-GAYA-DDU-01",
            asset_type="SIGNAL",
            section_id="REAL_GAYA_DDU",
            defect_description="Signal equipment preventive maintenance required",
            defect_severity=7,
            overdue_days=8,
            asset_criticality=9,
            safety_impact=10,
            train_operation_impact=8,
            estimated_work_minutes=45,
            is_overdue=True,
            requested_by="S&T",
            source_reference="SMMS-001",
        ),
    ]


# ============================================================
# TDMS - TRACTION DISTRIBUTION MANAGEMENT SYSTEM
# ============================================================

def load_tdms_data() -> List[MaintenanceData]:
    """
    Representative TDMS data.
    """
    return [
        MaintenanceData(
            record_id="TDMS-001",
            source_system=MaintenanceSource.TDMS,
            department=Department.TRD,
            asset_id="OHE-DDU-CNB-01",
            asset_type="OHE",
            section_id="REAL_DDU_CNB",
            defect_description="Traction distribution preventive maintenance required",
            defect_severity=7,
            overdue_days=4,
            asset_criticality=8,
            safety_impact=9,
            train_operation_impact=8,
            estimated_work_minutes=60,
            is_overdue=True,
            requested_by="TRD",
            source_reference="TDMS-001",
        ),
    ]


# ============================================================
# UNIFIED MAINTENANCE DATA
# ============================================================

def load_all_maintenance_data() -> List[MaintenanceData]:
    """
    Combines maintenance records from TMS, SMMS and TDMS
    into one unified dataset.
    """
    records = []
    records.extend(load_tms_data())
    records.extend(load_smms_data())
    records.extend(load_tdms_data())
    return records


# ============================================================
# CONVERT MAINTENANCE RECORD TO BLOCK DEMAND
# ============================================================

def maintenance_to_block_demand(
    record: MaintenanceData,
    demand_id: str,
) -> BlockDemand:

    # 1. Generate realistic, staggered shift times!
    # This prevents the AI from putting all blocks at the far left edge (minute 0).
    staggered_start_min = 0
    if "TMS" in record.record_id:
        staggered_start_min = 180   # 03:00 AM (Cooler hours for track work)
    elif "SMMS" in record.record_id:
        staggered_start_min = 540   # 09:00 AM (Daylight for signal work)
    elif "TDMS" in record.record_id:
        staggered_start_min = 840   # 02:00 PM (Afternoon shift)
    else:
        staggered_start_min = 120

    return BlockDemand(
        demand_id=demand_id,
        department=record.department,
        section_id=record.section_id,
        start_km=0.0,
        end_km=0.0,
        min_duration_minutes=record.estimated_work_minutes,
        
        # 2. Apply the dynamic staggered start time here
        earliest_start_min=staggered_start_min,
        
        latest_end_min=None,
        urgency_score=max(
            record.defect_severity,
            record.asset_criticality,
            record.safety_impact,
        ),
        crew_required=1,
        crew_group=f"{record.department.value}_CREW",
        possession_group=f"{record.section_id}_MAINTENANCE",
        compatible_departments=[],
        safety_buffer_before_min=15,
        safety_buffer_after_min=15,
        max_possession_minutes=(
            record.estimated_work_minutes + 30
        ),
        source_system=record.source_system,
        asset_id=record.asset_id,
        asset_type=record.asset_type,
        defect_severity=record.defect_severity,
        overdue_days=record.overdue_days,
        asset_criticality=record.asset_criticality,
        safety_impact=record.safety_impact,
        train_operation_impact=record.train_operation_impact,
        priority_level="Medium",
        reason=record.defect_description,
    )


# ============================================================
# SOURCE SUMMARY
# ============================================================

def get_source_summary():
    records = load_all_maintenance_data()
    summary = {
        "TMS": 0,
        "SMMS": 0,
        "TDMS": 0,
    }
    for record in records:
        summary[record.source_system.value] += 1
    return {
        "total_records": len(records),
        "sources": summary,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RAILSYNC-AI MAINTENANCE DATA INTEGRATION")
    print("=" * 60)

    records = load_all_maintenance_data()
    print(f"\nTotal maintenance records: {len(records)}")
    print("\nSource distribution:")
    summary = get_source_summary()
    for source, count in summary["sources"].items():
        print(f"  {source}: {count}")

    print("\nMaintenance records:")
    for record in records:
        print(
            f"\n"
            f"ID: {record.record_id}\n"
            f"Source: {record.source_system.value}\n"
            f"Department: {record.department.value}\n"
            f"Asset: {record.asset_id}\n"
            f"Section: {record.section_id}\n"
            f"Severity: {record.defect_severity}/10\n"
            f"Overdue: {record.overdue_days} days\n"
            f"Criticality: {record.asset_criticality}/10\n"
            f"Safety impact: {record.safety_impact}/10\n"
            f"Work duration: {record.estimated_work_minutes} min"
        )

    print("\n" + "=" * 60)
    print("MAINTENANCE INTEGRATION TEST PASSED")
    print("=" * 60)