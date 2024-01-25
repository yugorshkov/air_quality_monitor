import pandas as pd
from dadata import Dadata
from pandas import DataFrame
from prefect import task
from prefect.blocks.system import Secret
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import inspect

token = Secret.load("geocoder-token").get()
secret = Secret.load("geocoder-secret").get()


def get_city(client: Dadata, lat: float, lon: float) -> str:
    """
    Преобразует координаты в адрес и извлекает название города
    """
    result = client.geolocate(
        name="address", lat=lat, lon=lon, count=1, radius_meters=1000
    )

    return result[0]["data"]["city"] or result[0]["data"]["settlement"]


@task
def add_city_to_location(df: DataFrame) -> DataFrame:
    """
    Отбирает локации, данных по которым нет в базе. Добавляет к ним название города.
    """
    database_block = SqlAlchemyConnector.load("postgres")
    engine = database_block.get_client(client_type="engine")
    insp = inspect(engine)
    if insp.has_table("location"):
        df = pd.merge(
            df,
            pd.read_sql("location", engine, columns=["location.id", "city"]),
            how="left",
            on="location.id",
        )
        df = df[df["city"].isna()].drop(columns=["city"])

    coords = zip(df["location.latitude"], df["location.longitude"])
    with Dadata(token, secret) as dadata:
        df["city"] = [get_city(dadata, lat, lon) for lat, lon in coords]

    return df
