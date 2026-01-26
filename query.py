import duckdb
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant


def get_variables(progress_callback=None):
    """Query metadata.parquet and return list of (codigo_variable, etiqueta_variable)"""
    try:
        if progress_callback:
            progress_callback(10, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")

        if progress_callback:
            progress_callback(30, "Loading variable metadata...")

        query = """
            SELECT codigo_variable, etiqueta_variable
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


def load_census_layer(variable_code, progress_callback=None):
    """Run DuckDB join and return QgsVectorLayer with census data"""
    try:
        if progress_callback:
            progress_callback(5, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        if progress_callback:
            progress_callback(15, "Querying census data...")

        query = """
            SELECT g.cod_2022, ST_AsText(g.geometry) as wkt, c.conteo
            FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
            JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ON g.cod_2022 = c.id_geo
            WHERE c.codigo_variable = ?
        """

        if progress_callback:
            progress_callback(30, "Downloading data...")

        df = con.execute(query, [variable_code]).df()
        con.close()

        if df.empty:
            raise Exception("No data returned for selected variable")

        if progress_callback:
            progress_callback(50, "Creating layer...")

        # Create memory layer
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", f"Censo - {variable_code}", "memory")
        provider = layer.dataProvider()

        # Add fields
        provider.addAttributes([
            QgsField("cod_2022", QVariant.String),
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
                raise Exception(f"Invalid geometry for feature {row['cod_2022']}")

            feature.setGeometry(geom)
            feature.setAttributes([row['cod_2022'], float(row['conteo'])])
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
