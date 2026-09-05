from real_data_loader import load_real_timetable
from models import Section


def get_real_sections():
    df = load_real_timetable()

    unique_sections = {}

    # Make sure the timetable is a DataFrame
    if not hasattr(df, "groupby"):
        raise TypeError(
            "Real timetable data must be a Pandas DataFrame."
        )

    for train_id, train_data in df.groupby("train_id"):

        train_data = train_data.reset_index(drop=True)

        for i in range(len(train_data) - 1):

            current = train_data.iloc[i]
            next_station = train_data.iloc[i + 1]

            from_code = str(
                current["station_code"]
            ).strip()

            to_code = str(
                next_station["station_code"]
            ).strip()

            # Ignore invalid station rows
            if (
                not from_code
                or not to_code
                or from_code == "nan"
                or to_code == "nan"
            ):
                continue

            section_id = (
                f"REAL_{from_code}_{to_code}"
            )

            if section_id in unique_sections:
                continue

            try:
                from_distance = float(
                    current["distance_km"]
                )

                to_distance = float(
                    next_station["distance_km"]
                )
            except (
                ValueError,
                TypeError
            ):
                continue

            distance = abs(
                to_distance - from_distance
            )

            running_time = max(
                5,
                round(distance / 1.2)
            )

            start_km = min(
                from_distance,
                to_distance
            )

            end_km = max(
                from_distance,
                to_distance
            )

            unique_sections[section_id] = Section(
                section_id=section_id,
                name=(
                    f"{from_code} - {to_code}"
                ),
                from_km=start_km,
                to_km=end_km,
                capacity=1,
                headway_minutes=5,
                running_time_up_minutes=running_time,
                running_time_down_minutes=running_time,
            )

    return list(
        unique_sections.values()
    )


if __name__ == "__main__":
    sections = get_real_sections()

    print(
        f"Loaded {len(sections)} real railway sections."
    )

    for section in sections[:10]:
        print(section)#python -c "from real_dataset import get_real_dataset; d=get_real_dataset(); print('SUCCESS'); print('Trains:', len(d.trains)); print('Sections:', len(d.sections)); print('Maintenance:', len(d.demands))"