from models import GoodsTrainForecast


def build_goods_forecast(
    sections,
    horizon_minutes=2880,
):

    forecasts = []

    for index, section in enumerate(
        sections
    ):

        start = 0

        end = min(
            horizon_minutes,
            480
        )

        forecasts.append(
            GoodsTrainForecast(
                forecast_id=(
                    f"GF_{index + 1:03d}"
                ),

                section_id=(
                    section.section_id
                ),

                start_min=start,

                end_min=end,

                expected_goods_trains=(
                    2
                ),

                average_train_duration_min=30,

                congestion_level=2,

                source=(
                    "CONTROL_OFFICE_FORECAST"
                ),
            )
        )

    return forecasts


if __name__ == "__main__":

    print(
        "Traffic forecast module ready."
    )