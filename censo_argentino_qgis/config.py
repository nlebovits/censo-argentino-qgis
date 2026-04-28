"""Configuración de URLs y parámetros por año censal."""

BASE_URL = "https://data.source.coop/nlebovits/censo-argentino"

CENSUS_CONFIG = {
    "2022": {
        "geo_id_column": "COD_2022",
        "geometry_column": "geometry",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/2022/census-data.parquet",
            "metadata": f"{BASE_URL}/2022/metadata.parquet",
            "radios": f"{BASE_URL}/2022/radios.parquet",
        },
    },
    "2010": {
        "geo_id_column": "COD_2010",
        "geometry_column": "geometry",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/2010/census-data.parquet",
            "metadata": f"{BASE_URL}/2010/metadata.parquet",
            "radios": f"{BASE_URL}/2010/radios.parquet",
        },
    },
    "2001": {
        "geo_id_column": "COD_2001",
        "geometry_column": "geom",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/2001/census-data.parquet",
            "metadata": f"{BASE_URL}/2001/metadata.parquet",
            "radios": f"{BASE_URL}/2001/radios.parquet",
        },
    },
    "1991": {
        "geo_id_column": "COD_1991",
        "geometry_column": "geom",
        "entities": ["HOGAR", "PERSONA", "VIVIENDA"],
        "urls": {
            "census": f"{BASE_URL}/1991/census-data.parquet",
            "metadata": f"{BASE_URL}/1991/metadata.parquet",
            "radios": f"{BASE_URL}/1991/radios.parquet",
        },
    },
}

# Años disponibles en orden (más reciente primero)
AVAILABLE_YEARS = ["2022", "2010", "2001", "1991"]
