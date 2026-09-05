from db_connection import get_connection


def get_maintenance_demands():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                demand_id,
                department,
                section_id,
                start_km,
                end_km,
                min_duration_minutes,
                earliest_start_min,
                latest_end_min,
                urgency_score,
                crew_required,
                crew_group,
                possession_group,
                max_possession_minutes,
                safety_buffer_before_min,
                safety_buffer_after_min,
                status
            FROM maintenance_demands
            WHERE status = 'PENDING'
            ORDER BY urgency_score DESC;
            """
        )

        rows = cursor.fetchall()

        demands = []

        for row in rows:

            demand_id = row[0]

            db_start_min = row[6]

            staggered_start = db_start_min

            if not staggered_start or staggered_start == 0:

                if (
                    "001" in demand_id
                    or "TMS" in demand_id
                ):
                    staggered_start = 180

                elif (
                    "002" in demand_id
                    or "SMMS" in demand_id
                ):
                    staggered_start = 540

                elif (
                    "003" in demand_id
                    or "TDMS" in demand_id
                ):
                    staggered_start = 840

                else:
                    staggered_start = 240

            demands.append(
                {
                    "demand_id": demand_id,

                    "department": row[1],

                    "section_id": row[2],

                    "start_km": float(row[3]),

                    "end_km": float(row[4]),

                    "min_duration_minutes": row[5],

                    "earliest_start_min":
                        staggered_start,

                    "latest_end_min": row[7],

                    "urgency_score": row[8],

                    "crew_required": row[9],

                    "crew_group": row[10],

                    "possession_group": row[11],

                    "max_possession_minutes": row[12],

                    "safety_buffer_before_min":
                        row[13],

                    "safety_buffer_after_min":
                        row[14],

                    "status": row[15],
                }
            )

        cursor.close()

        return demands

    finally:

        conn.close()


if __name__ == "__main__":

    demands = get_maintenance_demands()

    print(
        "Maintenance demands loaded from PostgreSQL:"
    )

    for demand in demands:
        print(demand)