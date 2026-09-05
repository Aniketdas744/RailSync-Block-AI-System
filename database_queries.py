from db_connection import get_connection


def get_trains():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                train_id,
                name,
                priority,
                direction,
                passenger_weight,
                freight_weight,
                active
            FROM trains
            WHERE active = TRUE
            ORDER BY priority DESC;
            """
        )

        rows = cursor.fetchall()

        trains = []

        for row in rows:

            trains.append(
                {
                    "train_id": row[0],
                    "name": row[1],
                    "priority": row[2],
                    "direction": row[3],
                    "passenger_weight": float(
                        row[4]
                    ),
                    "freight_weight": float(
                        row[5]
                    ),
                    "active": row[6],
                }
            )

        cursor.close()

        return trains

    finally:
        conn.close()


if __name__ == "__main__":

    trains = get_trains()

    print(
        "Trains loaded from PostgreSQL:"
    )

    for train in trains:
        print(train)