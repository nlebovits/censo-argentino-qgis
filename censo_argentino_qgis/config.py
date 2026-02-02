"""Configuración de URLs y parámetros por año censal."""

BASE_URL = "https://data.source.coop/nlebovits/censo-argentino"

CENSUS_CONFIG = {
    "2022": {
        "geo_id_column": "COD_2022",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/2022/census-data.parquet",
            "metadata": f"{BASE_URL}/2022/metadata.parquet",
            "radios": f"{BASE_URL}/2022/radios.parquet",
        },
    },
    "2010": {
        "geo_id_column": "COD_2010",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/2010/census-data.parquet",
            "metadata": f"{BASE_URL}/2010/metadata.parquet",
            "radios": f"{BASE_URL}/2010/radios.parquet",
        },
    },
}

# Años disponibles en orden (más reciente primero)
AVAILABLE_YEARS = ["2022", "2010"]
