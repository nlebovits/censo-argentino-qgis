import duckdb
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant


def get_entity_types(progress_callback=None):
    """Query metadata.parquet and return list of available entity types"""
    try:
        if progress_callback:
            progress_callback(10, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")

        if progress_callback:
            progress_callback(50, "Loading entity types...")

        query = """
            SELECT DISTINCT entidad
            FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet'
            WHERE entidad IN ('HOGAR', 'PERSONA', 'VIVIENDA')
            ORDER BY entidad
        """

        result = con.execute(query).fetchall()
        con.close()

        if progress_callback:
            progress_callback(100, "Entity types loaded")

        return [row[0] for row in result]
    except Exception as e:
        raise Exception(f"Error loading entity types: {str(e)}")


def get_variables(entity_type=None, progress_callback=None):
    """Query metadata.parquet and return list of (codigo_variable, etiqueta_variable) for entity type"""
    try:
        if progress_callback:
            progress_callback(10, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")

        if progress_callback:
            progress_callback(30, "Loading variable metadata...")

        if entity_type:
            query = """
                SELECT DISTINCT codigo_variable, etiqueta_variable
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet'
                WHERE entidad = ?
                ORDER BY codigo_variable
            """
            result = con.execute(query, [entity_type]).fetchall()
        else:
            query = """
                SELECT DISTINCT codigo_variable, etiqueta_variable
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet'
                ORDER BY codigo_variable
            """
            result = con.execute(query).fetchall()

        con.close()

        if progress_callback:
            progress_callback(100, "Variables loaded")

        return [(row[0], row[1]) for row in result]
    except Exception as e:
        raise Exception(f"Error loading variables: {str(e)}")


def load_census_layer(variable_code, geo_level="RADIO", progress_callback=None):
    """Run DuckDB join and return QgsVectorLayer with census data

    Args:
        variable_code: Census variable code
        geo_level: Geographic level - "RADIO", "FRACC", "DEPTO", or "PROV"
        progress_callback: Optional callback for progress updates
    """
    try:
        if progress_callback:
            progress_callback(5, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        if progress_callback:
            progress_callback(15, f"Querying census data at {geo_level} level...")

        # Define grouping columns and ID fields based on geographic level
        geo_config = {
            "RADIO": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC, g.RADIO",
                "id_field": "g.COD_2022",
                "id_alias": "geo_id",
                "dissolve": False
            },
            "FRACC": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC",
                "id_field": "g.PROV || '-' || g.DEPTO || '-' || g.FRACC",
                "id_alias": "geo_id",
                "dissolve": True
            },
            "DEPTO": {
                "group_cols": "g.PROV, g.DEPTO",
                "id_field": "g.PROV || '-' || g.DEPTO",
                "id_alias": "geo_id",
                "dissolve": True
            },
            "PROV": {
                "group_cols": "g.PROV",
                "id_field": "g.PROV",
                "id_alias": "geo_id",
                "dissolve": True
            }
        }

        config = geo_config[geo_level]

        if config["dissolve"]:
            # Aggregate geometries and sum data
            query = f"""
                SELECT
                    {config['id_field']} as {config['id_alias']},
                    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
                    SUM(c.conteo) as conteo
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE c.codigo_variable = ?
                GROUP BY {config['group_cols']}
            """
        else:
            # No aggregation needed for RADIO level
            query = f"""
                SELECT
                    {config['id_field']} as {config['id_alias']},
                    ST_AsText(g.geometry) as wkt,
                    c.conteo
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE c.codigo_variable = ?
            """

        if progress_callback:
            progress_callback(30, "Streaming query results...")

        df = con.execute(query, [variable_code]).df()
        con.close()

        if df.empty:
            raise Exception("No data returned for selected variable")

        if progress_callback:
            progress_callback(50, "Creating layer...")

        # Create memory layer
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", f"Censo - {variable_code} ({geo_level})", "memory")
        provider = layer.dataProvider()

        # Add fields
        provider.addAttributes([
            QgsField("geo_id", QVariant.String),
            QgsField("conteo", QVariant.Double)
        ])
        layer.updateFields()

        if progress_callback:
            progress_callback(60, f"Adding {len(df)} features...")

        # Add features
        features = []
        total_rows = len(df)
        for idx, row in df.iterrows():
            feature = QgsFeature()

            # Parse geometry from WKT (converted by ST_AsText)
            geom = QgsGeometry.fromWkt(row['wkt'])

            if geom.isNull():
                raise Exception(f"Invalid geometry for feature {row['geo_id']}")

            feature.setGeometry(geom)
            feature.setAttributes([row['geo_id'], float(row['conteo'])])
            features.append(feature)

            # Update progress every 100 features
            if progress_callback and idx % 100 == 0:
                percent = 60 + int((idx / total_rows) * 30)
                progress_callback(percent, f"Processing features: {idx}/{total_rows}")

        if progress_callback:
            progress_callback(90, "Finalizing layer...")

        provider.addFeatures(features)
        layer.updateExtents()

        if progress_callback:
            progress_callback(100, "Layer loaded successfully")

        return layer

    except Exception as e:
        raise Exception(f"Error loading census layer: {str(e)}")
