import duckdb
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant
import json


def get_variables():
    """Query metadata.parquet and return list of (codigo_variable, etiqueta_variable)"""
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")

        query = """
            SELECT codigo_variable, etiqueta_variable
            FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet'
            ORDER BY codigo_variable
        """

        result = con.execute(query).fetchall()
        con.close()

        return [(row[0], row[1]) for row in result]
    except Exception as e:
        raise Exception(f"Error loading variables: {str(e)}")


def load_census_layer(variable_code):
    """Run DuckDB join and return QgsVectorLayer with census data"""
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        query = """
            SELECT g.cod_2022, g.geometry, c.conteo
            FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
            JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ON g.cod_2022 = c.id_geo
            WHERE c.codigo_variable = ?
        """

        df = con.execute(query, [variable_code]).df()
        con.close()

        if df.empty:
            raise Exception("No data returned for selected variable")

        # Create memory layer
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", f"Censo - {variable_code}", "memory")
        provider = layer.dataProvider()

        # Add fields
        provider.addAttributes([
            QgsField("cod_2022", QVariant.String),
            QgsField("conteo", QVariant.Double)
        ])
        layer.updateFields()

        # Add features
        features = []
        for idx, row in df.iterrows():
            feature = QgsFeature()

            # Parse geometry from GeoJSON
            geom_dict = json.loads(row['geometry'])
            geom = QgsGeometry.fromWkt(geom_dict['coordinates'] if isinstance(geom_dict, dict) else row['geometry'])

            # Try different geometry parsing approaches
            if geom.isNull():
                # Try as WKB hex
                try:
                    from shapely import wkb
                    from shapely.geometry import shape
                    import geopandas as gpd

                    # Convert geometry column properly
                    if isinstance(row['geometry'], str):
                        geom_obj = wkb.loads(bytes.fromhex(row['geometry']))
                    else:
                        geom_obj = shape(row['geometry'])

                    geom = QgsGeometry.fromWkt(geom_obj.wkt)
                except:
                    # Last resort: try direct WKT
                    geom = QgsGeometry.fromWkt(str(row['geometry']))

            feature.setGeometry(geom)
            feature.setAttributes([row['cod_2022'], float(row['conteo'])])
            features.append(feature)

        provider.addFeatures(features)
        layer.updateExtents()

        return layer

    except Exception as e:
        raise Exception(f"Error loading census layer: {str(e)}")
