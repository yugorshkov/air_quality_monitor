from dadata import Dadata
from pandas import DataFrame
from prefect import task
from prefect.blocks.system import Secret

token = Secret.load("geocoder-token").get()
secret = Secret.load("geocoder-secret").get()


def get_city(client: Dadata, lat: float, lon: float) -> str:
    """
    Преобразует координаты в адрес и извлекает название города
    """
    result = client.geolocate(
        name="address", lat=lat, lon=lon, count=1, radius_meters=1000
    )
    return result[0]["data"]["city"]


@task
def add_city_to_location(df: DataFrame) -> DataFrame:
    """
    Добавляет город к данным о расположении датчиков
    """
    coords = zip(df["location.latitude"], df["location.longitude"])
    with Dadata(token, secret) as dadata:
        df["city"] = [get_city(dadata, lat, lon) for lat, lon in coords]
    return df
