
import pandas as pd
from pathlib import Path


# ============================================================
# REAL RAILWAY TIMETABLE CSV
# ============================================================

CSV_PATH = (
    Path(__file__).parent
    / "railway_real_train_timetable.csv"
)


# ============================================================
# LOAD REAL TIMETABLE
# ============================================================

def load_real_timetable():
    """
    Load the real railway timetable CSV.

    IMPORTANT:
    This function always returns a Pandas DataFrame.

    The train converter depends on DataFrame.groupby().
    """

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Real timetable CSV not found: {CSV_PATH}"
        )

    df = pd.read_csv(
        CSV_PATH,
        dtype=str
    )

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "train_id",
        "train_name",
        "origin_code",
        "destination_code",
        "station_code",
        "station_name",
        "arrival",
        "departure",
        "halt_min",
        "distance_km",
        "running_days",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns in timetable CSV: "
            f"{missing}"
        )

    # --------------------------------------------------------
    # Clean string fields
    # --------------------------------------------------------

    string_columns = [
        "train_id",
        "train_name",
        "origin_code",
        "destination_code",
        "station_code",
        "station_name",
        "arrival",
        "departure",
        "halt_min",
        "distance_km",
        "running_days",
    ]

    for column in string_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # Convert known missing markers
    #
    # Keep "--" in the timetable because the converter
    # understands it as a missing time.
    # --------------------------------------------------------

    df["arrival"] = df["arrival"].replace(
        {
            "nan": "--",
            "NaN": "--",
            "None": "--",
            "null": "--",
            "NULL": "--",
            "": "--",
        }
    )

    df["departure"] = df["departure"].replace(
        {
            "nan": "--",
            "NaN": "--",
            "None": "--",
            "null": "--",
            "NULL": "--",
            "": "--",
        }
    )

    # --------------------------------------------------------
    # Validate train IDs
    # --------------------------------------------------------

    df = df[
        df["train_id"].str.strip() != ""
    ].copy()

    if df.empty:
        raise ValueError(
            "Real railway timetable contains no valid "
            "train records."
        )

    # --------------------------------------------------------
    # Validate station codes
    # --------------------------------------------------------

    df = df[
        df["station_code"].str.strip() != ""
    ].copy()

    if df.empty:
        raise ValueError(
            "Real railway timetable contains no valid "
            "station records."
        )

    # --------------------------------------------------------
    # Ensure correct timetable order
    #
    # Preserve the original CSV order within each train.
    # --------------------------------------------------------

    df["_original_order"] = range(
        len(df)
    )

    df = df.sort_values(
        [
            "train_id",
            "_original_order"
        ],
        kind="stable"
    )

    df = df.drop(
        columns=["_original_order"]
    )

    # --------------------------------------------------------
    # FINAL TYPE CHECK
    # --------------------------------------------------------

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "load_real_timetable() must return "
            "a Pandas DataFrame."
        )

    return df


# ============================================================
# GET ONE TRAIN
# ============================================================

def get_train(train_id):

    df = load_real_timetable()

    train = df[
        df["train_id"].astype(str)
        == str(train_id)
    ]

    if train.empty:
        raise ValueError(
            f"Train {train_id} not found in timetable."
        )

    return train


# ============================================================
# GET AVAILABLE TRAINS
# ============================================================

def get_available_trains():

    df = load_real_timetable()

    trains = (
        df[
            [
                "train_id",
                "train_name",
                "origin_code",
                "destination_code",
                "running_days",
            ]
        ]
        .drop_duplicates()
        .to_dict(
            orient="records"
        )
    )

    return trains


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    df = load_real_timetable()

    print(
        "========================================"
    )

    print(
        "      REAL RAILWAY TIMETABLE"
    )

    print(
        "========================================"
    )

    print(
        f"CSV file: {CSV_PATH}"
    )

    print(
        f"Total timetable rows: {len(df)}"
    )

    print(
        f"Data type: {type(df).__name__}"
    )

    print()

    print(
        "Available trains:"
    )

    for train in get_available_trains():

        print(
            f"{train['train_id']} - "
            f"{train['train_name']} | "
            f"{train['origin_code']} -> "
            f"{train['destination_code']}"
        )

    print()

    print(
        "Timetable loading: PASSED"
    )

