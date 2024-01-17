import httpx
import pandas as pd
from pandas import DataFrame
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect_sqlalchemy import SqlAlchemyConnector

from cities import add_city_to_location


@task(retries=3, retry_delay_seconds=[10, 20, 40])
def load_sensor_data() -> list[dict]:
    """
    Загрузка средних значений всех измерений по каждому датчику за последний час
    """
    url = "https://data.sensor.community/static/v2/data.1h.json"
    r = httpx.get(url, timeout=5)
    r.raise_for_status()

    return r.json()


@task
def transform_data(data: list[dict]) -> DataFrame:
    """
    Преобразует данные JSON в плоскую таблицу
    """
    df = pd.json_normalize(
        data,
        record_path=["sensordatavalues"],
        meta=[
            "timestamp",
            ["location", "id"],
            ["location", "latitude"],
            ["location", "longitude"],
            ["location", "country"],
            ["sensor", "id"],
        ],
    )
    df.drop(columns=["id"], inplace=True)
    df = df.astype(
        {
            "value": float,
            "timestamp": "datetime64[ns]",
            "location.id": int,
            "location.latitude": float,
            "location.longitude": float,
            "sensor.id": int,
        },
    )

    return df


@task
def create_subsets(df: DataFrame, cc: list[str], value_types: list[str]) -> DataFrame:
    """
    Отбор записей по списку стран и типу измерений
    """
    df.query("`location.country` in @cc and value_type in @value_types", inplace=True)
    measurements = df[["sensor.id", "timestamp", "location.id", "value_type", "value"]]
    locations = df.filter(regex="location").drop_duplicates()

    return measurements, locations


@task
def export_data_to_postgres(df: DataFrame, table: str, if_exists: str) -> None:
    """
    Запись данных в Postgres
    """
    database_block = SqlAlchemyConnector.load("postgres")
    engine = database_block.get_client(client_type="engine")
    df.to_sql(name=table, con=engine, if_exists=if_exists, index=False)

    create_markdown_artifact(f"Записано строк в Postgres: {len(df)}")


@flow(name="air_quality_monitor_etl")
def main():
    sensor_data = load_sensor_data()
    df = transform_data(sensor_data)
    cc = ["RU"]
    value_types = ["P1", "P2", "temperature", "humidity"]
    measurements, locations = create_subsets(df, cc, value_types)
    locations = add_city_to_location(locations)
    export_data_to_postgres(measurements, "sensor", "append")
    export_data_to_postgres(locations, "location", "replace")


if __name__ == "__main__":
    main.serve(name="AQM-docker")
    