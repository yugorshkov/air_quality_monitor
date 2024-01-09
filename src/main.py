import pandas as pd
import requests
from pandas import DataFrame
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy.types import DateTime, Float


@task(retries=3, retry_delay_seconds=[10, 20, 40])
def load_sensor_data() -> list[dict]:
    """
    Загрузка средних значений всех измерений по каждому датчику за последний час
    """
    url = "https://data.sensor.community/static/v2/data.1h.json"
    r = requests.get(url, timeout=2)

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
            ["sensor", "sensor_type", "name"],
        ],
    )
    df.drop(columns=["id"], inplace=True)

    return df


@task
def filter_data(df: DataFrame, cc: list[str], value_types: list[str]) -> DataFrame:
    """
    Отбор записей по списку стран и типу измерений
    """
    df.query("`location.country` in @cc and value_type in @value_types", inplace=True)

    return df


@task
def export_data_to_postgres(df: DataFrame) -> None:
    """
    Запись данных в Postgres
    """
    cols_datatype = {
        "value": Float(),
        "timestamp": DateTime(),
        "location.latitude": Float(),
        "location.longitude": Float(),
    }
    database_block = SqlAlchemyConnector.load("postgres")
    engine = database_block.get_client(client_type="engine")
    written_rows = df.to_sql(
        name="test",
        con=engine,
        if_exists="replace",
        index=False,
        dtype=cols_datatype,
    )

    create_markdown_artifact(f"Записано строк в Postgres: {written_rows}")


@flow
def main():
    sensor_data = load_sensor_data()
    df = transform_data(sensor_data)
    cc = ["RU"]
    value_types = ["P1", "P2"]
    filtered_df = filter_data(df, cc, value_types)
    export_data_to_postgres(filtered_df)


if __name__ == "__main__":
    main()
