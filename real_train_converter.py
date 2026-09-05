import pandas as pd

from models import TrainPath
from real_data_loader import load_real_timetable


# ============================================================
# TIME UTILITIES
# ============================================================

def time_to_minutes(time_value):
    """
    Convert HH:MM into minutes from midnight.

    Invalid or missing timetable values return None.
    """

    if time_value is None:
        return None

    value = str(time_value).strip()

    if value in (
        "",
        "--",
        "nan",
        "NaN",
        "None",
        "null",
        "NULL",
    ):
        return None

    try:
        parts = value.split(":")

        if len(parts) != 2:
            return None

        hours = int(parts[0])
        minutes = int(parts[1])

        if hours < 0 or hours > 23:
            return None

        if minutes < 0 or minutes > 59:
            return None

        return hours * 60 + minutes

    except (ValueError, TypeError):
        return None


def adjusted_time(
    current_minutes,
    previous_minutes
):
    """
    Handle midnight crossing.

    Example:

        previous = 23:50 -> 1430
        current  = 00:30 -> 30

    becomes:

        current = 1470
    """

    if current_minutes is None:
        return None

    if previous_minutes is None:
        return current_minutes

    while current_minutes < previous_minutes:
        current_minutes += 24 * 60

    return current_minutes


# ============================================================
# SAFE ROW VALUE
# ============================================================

def get_value(row, column, default=None):
    """
    Safely retrieve a column value from a pandas Series
    or dictionary.

    This prevents:
        string indices must be integers
    errors when timetable data is represented differently.
    """

    if isinstance(row, pd.Series):
        return row[column] if column in row.index else default

    if isinstance(row, dict):
        return row.get(column, default)

    try:
        return row[column]
    except (KeyError, IndexError, TypeError):
        return default


# ============================================================
# NORMALIZE TRAIN DATA
# ============================================================

def normalize_train_data(train_data):
    """
    Ensure train_data is a pandas DataFrame.

    The normal path is already a DataFrame from pandas.groupby().
    This additional handling protects the converter from list/dict
    representations without changing the section-based architecture.
    """

    if isinstance(train_data, pd.DataFrame):
        return train_data.reset_index(drop=True)

    if isinstance(train_data, pd.Series):
        return pd.DataFrame([train_data.to_dict()])

    if isinstance(train_data, dict):
        return pd.DataFrame([train_data])

    if isinstance(train_data, list):
        if not train_data:
            return pd.DataFrame()

        if all(isinstance(item, dict) for item in train_data):
            return pd.DataFrame(train_data)

        if all(isinstance(item, pd.Series) for item in train_data):
            return pd.DataFrame(
                [item.to_dict() for item in train_data]
            )

    raise TypeError(
        "Unsupported timetable data type: "
        f"{type(train_data).__name__}"
    )


# ============================================================
# CONVERT ONE TRAIN
# ============================================================

def convert_train(
    train_id,
    train_data
):

    train_data = normalize_train_data(train_data)

    if train_data.empty:
        raise ValueError(
            f"Train {train_id} contains no timetable rows."
        )

    if len(train_data) < 2:
        raise ValueError(
            f"Train {train_id} does not contain "
            f"enough stations."
        )

    required_columns = [
        "train_name",
        "origin_code",
        "destination_code",
        "station_code",
        "arrival",
        "departure",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in train_data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Train {train_id} timetable is missing "
            f"columns: {missing_columns}"
        )

    train_data = train_data.reset_index(drop=True)

    # ========================================================
    # BASIC TRAIN INFORMATION
    # ========================================================

    first_row = train_data.iloc[0]
    last_row = train_data.iloc[-1]

    train_name = str(
        get_value(
            first_row,
            "train_name",
            f"Train {train_id}"
        )
    ).strip()

    origin_code = str(
        get_value(
            first_row,
            "origin_code",
            ""
        )
    ).strip()

    destination_code = str(
        get_value(
            first_row,
            "destination_code",
            ""
        )
    ).strip()

    # ========================================================
    # FIRST DEPARTURE
    # ========================================================

    first_departure = time_to_minutes(
        get_value(
            first_row,
            "departure"
        )
    )

    # Some railway timetable rows may have no departure
    # at the first station. Use arrival as fallback.

    if first_departure is None:

        first_departure = time_to_minutes(
            get_value(
                first_row,
                "arrival"
            )
        )

    if first_departure is None:
        raise ValueError(
            f"Train {train_id} has no valid "
            f"departure/arrival time at its first station."
        )

    # ========================================================
    # STORAGE
    # ========================================================

    occupied_sections = []

    section_durations = {}

    section_start_offsets = {}

    previous_event_time = first_departure

    # ========================================================
    # PROCESS EVERY CONSECUTIVE STATION PAIR
    # ========================================================

    for i in range(len(train_data) - 1):

        current = train_data.iloc[i]

        next_station = train_data.iloc[i + 1]

        # ----------------------------------------------------
        # STATION CODES
        # ----------------------------------------------------

        from_code = str(
            get_value(
                current,
                "station_code",
                ""
            )
        ).strip()

        to_code = str(
            get_value(
                next_station,
                "station_code",
                ""
            )
        ).strip()

        if not from_code:
            raise ValueError(
                f"Train {train_id} has an empty "
                f"station code at row {i}."
            )

        if not to_code:
            raise ValueError(
                f"Train {train_id} has an empty "
                f"station code at row {i + 1}."
            )

        section_id = (
            f"REAL_{from_code}_{to_code}"
        )

        # ----------------------------------------------------
        # CURRENT STATION DEPARTURE
        # ----------------------------------------------------

        departure = time_to_minutes(
            get_value(
                current,
                "departure"
            )
        )

        # If departure is missing, use arrival.

        if departure is None:

            departure = time_to_minutes(
                get_value(
                    current,
                    "arrival"
                )
            )

        if departure is None:
            raise ValueError(
                f"Missing departure/arrival time "
                f"for train {train_id} at "
                f"{from_code}."
            )

        # ----------------------------------------------------
        # NEXT STATION ARRIVAL
        # ----------------------------------------------------

        arrival = time_to_minutes(
            get_value(
                next_station,
                "arrival"
            )
        )

        # If arrival is missing, use departure.

        if arrival is None:

            arrival = time_to_minutes(
                get_value(
                    next_station,
                    "departure"
                )
            )

        if arrival is None:
            raise ValueError(
                f"Missing arrival/departure time "
                f"for train {train_id} at "
                f"{to_code}."
            )

        # ----------------------------------------------------
        # MIDNIGHT ADJUSTMENT
        # ----------------------------------------------------

        departure = adjusted_time(
            departure,
            previous_event_time
        )

        arrival = adjusted_time(
            arrival,
            departure
        )

        # ----------------------------------------------------
        # SECTION DURATION
        # ----------------------------------------------------

        duration = arrival - departure

        if duration <= 0:

            # Try one additional 24-hour adjustment.

            arrival += 24 * 60

            duration = arrival - departure

        if duration <= 0:
            raise ValueError(
                f"Invalid section duration for "
                f"train {train_id}: "
                f"{from_code} -> {to_code}. "
                f"Departure={departure}, "
                f"Arrival={arrival}."
            )

        # ----------------------------------------------------
        # OFFSET FROM ORIGINAL TRAIN DEPARTURE
        # ----------------------------------------------------

        start_offset = (
            departure - first_departure
        )

        while start_offset < 0:
            start_offset += 24 * 60

        # ----------------------------------------------------
        # STORE SECTION
        # ----------------------------------------------------

        occupied_sections.append(
            section_id
        )

        section_durations[
            section_id
        ] = int(duration)

        section_start_offsets[
            section_id
        ] = int(start_offset)

        previous_event_time = arrival

    # ========================================================
    # FINAL ARRIVAL
    # ========================================================

    final_arrival = time_to_minutes(
        get_value(
            last_row,
            "arrival"
        )
    )

    if final_arrival is None:

        final_arrival = time_to_minutes(
            get_value(
                last_row,
                "departure"
            )
        )

    if final_arrival is None:
        raise ValueError(
            f"Train {train_id} has no valid "
            f"final arrival/departure time."
        )

    final_arrival = adjusted_time(
        final_arrival,
        previous_event_time
    )

    while final_arrival <= first_departure:
        final_arrival += 24 * 60

    total_transit_duration = (
        final_arrival - first_departure
    )

    if total_transit_duration <= 0:
        raise ValueError(
            f"Invalid final arrival time "
            f"for train {train_id}."
        )

    # ========================================================
    # PRIORITY
    # ========================================================

    if "Rajdhani" in train_name:

        priority = 100

        passenger_weight = 10

        freight_weight = 0

    else:

        priority = 80

        passenger_weight = 8

        freight_weight = 0

    # ========================================================
    # DIRECTION
    # ========================================================

    if origin_code == "NDLS":

        direction = "UP"

    else:

        direction = "DOWN"

    # ========================================================
    # CREATE TRAIN OBJECT
    # ========================================================

    train = TrainPath(

        train_id=str(
            train_id
        ),

        name=train_name,

        priority=priority,

        direction=direction,

        scheduled_departure_min=int(
            first_departure
        ),

        # Keep the original planning limit.
        max_departure_delay_min=240,

        transit_duration_min=int(
            total_transit_duration
        ),

        passenger_weight=passenger_weight,

        freight_weight=freight_weight,

        current_delay_min=0,

        occupied_sections=occupied_sections,

        station_dwell_minutes=5,

        speed_factor=1.0,

        section_durations=section_durations,

        section_start_offsets=section_start_offsets
    )

    return train


# ============================================================
# CONVERT ALL REAL TRAINS
# ============================================================

def get_real_trains():

    df = load_real_timetable()

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if isinstance(df, list):

        if not df:
            return []

        if all(
            isinstance(item, dict)
            for item in df
        ):
            df = pd.DataFrame(df)

        else:
            raise TypeError(
                "load_real_timetable() returned a list "
                "that does not contain dictionary rows."
            )

    if isinstance(df, dict):

        df = pd.DataFrame(df)

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "load_real_timetable() must return a "
            "pandas DataFrame."
        )

    # --------------------------------------------------------
    # Validate train ID column
    # --------------------------------------------------------

    if "train_id" not in df.columns:

        raise ValueError(
            "Real timetable does not contain "
            "'train_id' column."
        )

    # --------------------------------------------------------
    # Clean train IDs
    # --------------------------------------------------------

    df = df.copy()

    df["train_id"] = (
        df["train_id"]
        .astype(str)
        .str.strip()
    )

    df = df[
        (df["train_id"] != "")
        & (df["train_id"] != "nan")
        & (df["train_id"] != "None")
    ]

    if df.empty:
        raise ValueError(
            "Real timetable contains no valid train IDs."
        )

    # --------------------------------------------------------
    # Convert trains
    # --------------------------------------------------------

    trains = []

    for train_id, train_data in df.groupby(
        "train_id",
        sort=False
    ):

        train = convert_train(
            train_id,
            train_data
        )

        trains.append(
            train
        )

    if not trains:
        raise ValueError(
            "No trains could be converted from "
            "the real timetable."
        )

    return trains


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "      REAL TRAIN CONVERTER"
    )

    print(
        "========================================"
    )

    trains = get_real_trains()

    print(
        f"Total trains: {len(trains)}"
    )

    for train in trains:

        print()

        print(
            f"{train.train_id} | "
            f"{train.name}"
        )

        print(
            f"Direction: "
            f"{train.direction}"
        )

        print(
            f"Scheduled departure: "
            f"{train.scheduled_departure_min}"
        )

        print(
            f"Maximum preferred delay: "
            f"{train.max_departure_delay_min} min"
        )

        print(
            f"Total transit duration: "
            f"{train.transit_duration_min} min"
        )

        print(
            f"Sections: "
            f"{len(train.occupied_sections)}"
        )

        print(
            "Timetable sections:"
        )

        for section_id in (
            train.occupied_sections
        ):

            duration = (
                train.section_durations[
                    section_id
                ]
            )

            offset = (
                train.section_start_offsets[
                    section_id
                ]
            )

            print(
                f"   {section_id} | "
                f"offset={offset} min | "
                f"duration={duration} min"
            )

        print(
            "----------------------------------------"
        )

    print(
        "\nReal train conversion: PASSED"
    )#python -c "from real_dataset import get_real_dataset; get_real_dataset()"