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


def get_geographic_codes(geo_level="PROV", progress_callback=None):
    """Query radios.parquet and return list of available geographic codes for the level

    Args:
        geo_level: Geographic level - "RADIO", "FRACC", "DEPTO", or "PROV"
        progress_callback: Optional callback for progress updates

    Returns:
        List of tuples: (code, label) for each geographic unit
    """
    try:
        if progress_callback:
            progress_callback(10, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        if progress_callback:
            progress_callback(50, f"Loading {geo_level} codes...")

        # Define queries based on geographic level
        geo_queries = {
            "PROV": """
                SELECT DISTINCT
                    c.valor_provincia as code,
                    c.etiqueta_provincia as label
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ORDER BY c.valor_provincia
            """,
            "DEPTO": """
                SELECT DISTINCT
                    c.valor_provincia || '-' || c.valor_departamento as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento as label
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ORDER BY c.valor_provincia, c.valor_departamento
            """,
            "FRACC": """
                SELECT DISTINCT
                    c.valor_provincia || '-' || c.valor_departamento || '-' || c.valor_fraccion as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento || ' - Fracc ' || c.valor_fraccion as label
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ORDER BY c.valor_provincia, c.valor_departamento, c.valor_fraccion
                LIMIT 100
            """,
            "RADIO": """
                SELECT DISTINCT
                    c.id_geo as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento || ' - Radio ' || c.valor_radio as label
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ORDER BY c.valor_provincia, c.valor_departamento, c.valor_fraccion, c.valor_radio
                LIMIT 100
            """
        }

        query = geo_queries.get(geo_level, geo_queries["PROV"])
        result = con.execute(query).fetchall()
        con.close()

        if progress_callback:
            progress_callback(100, "Geographic codes loaded")

        return [(row[0], row[1]) for row in result]
    except Exception as e:
        raise Exception(f"Error loading geographic codes: {str(e)}")


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


def load_census_layer(variable_codes, geo_level="RADIO", geo_filters=None, bbox=None, progress_callback=None):
    """Run DuckDB join and return QgsVectorLayer with census data for multiple variables

    Args:
        variable_codes: List of census variable codes (or single code as string)
        geo_level: Geographic level - "RADIO", "FRACC", "DEPTO", or "PROV"
        geo_filters: Optional list of geographic codes to filter by
        bbox: Optional bounding box (xmin, ymin, xmax, ymax) in EPSG:4326
        progress_callback: Optional callback for progress updates

    Returns:
        QgsVectorLayer with geometry and one column per variable
    """
    # Allow single variable as string
    if isinstance(variable_codes, str):
        variable_codes = [variable_codes]
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

        # Build WHERE clause with geographic and variable filters
        variable_placeholders = ', '.join(['?' for _ in variable_codes])
        where_clause = f"c.codigo_variable IN ({variable_placeholders})"
        query_params = list(variable_codes)

        if geo_filters and len(geo_filters) > 0:
            # Build filter based on geo_level
            if geo_level == "PROV":
                placeholders = ', '.join(['?' for _ in geo_filters])
                where_clause += f" AND g.PROV IN ({placeholders})"
                query_params.extend(geo_filters)
            elif geo_level == "DEPTO":
                # Parse "PROV-DEPTO" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split('-')
                    if len(parts) == 2:
                        filter_conditions.append("(g.PROV = ? AND g.DEPTO = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    where_clause += f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "FRACC":
                # Parse "PROV-DEPTO-FRACC" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split('-')
                    if len(parts) == 3:
                        filter_conditions.append("(g.PROV = ? AND g.DEPTO = ? AND g.FRACC = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    where_clause += f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "RADIO":
                placeholders = ', '.join(['?' for _ in geo_filters])
                where_clause += f" AND g.COD_2022 IN ({placeholders})"
                query_params.extend(geo_filters)

        # Add bounding box filter if provided
        if bbox:
            xmin, ymin, xmax, ymax = bbox
            # Use ST_Intersects to find any geometries that touch or overlap the bounding box
            # This ensures we get features even if they're only partially within the extent
            where_clause += " AND ST_Intersects(g.geometry, ST_GeomFromText(?))"
            # Create a polygon from the bbox coordinates in WKT format
            bbox_wkt = f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
            query_params.append(bbox_wkt)

        # Build pivot aggregation for each variable
        pivot_columns = []
        for var_code in variable_codes:
            if config["dissolve"]:
                pivot_columns.append(f"SUM(CASE WHEN c.codigo_variable = '{var_code}' THEN c.conteo ELSE 0 END) as \"{var_code}\"")
            else:
                pivot_columns.append(f"MAX(CASE WHEN c.codigo_variable = '{var_code}' THEN c.conteo ELSE NULL END) as \"{var_code}\"")

        pivot_sql = ',\n                    '.join(pivot_columns)

        if config["dissolve"]:
            # Aggregate geometries and sum data for each variable
            query = f"""
                SELECT
                    {config['id_field']} as geo_id,
                    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
                    {pivot_sql}
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {where_clause}
                GROUP BY {config['group_cols']}
            """
        else:
            # No aggregation needed for RADIO level
            query = f"""
                SELECT
                    {config['id_field']} as geo_id,
                    ST_AsText(g.geometry) as wkt,
                    {pivot_sql}
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet' g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {where_clause}
                GROUP BY {config['id_field']}, g.geometry
            """

        if progress_callback:
            progress_callback(30, "Streaming query results...")

        # Log the query for debugging
        from qgis.core import QgsMessageLog, Qgis
        QgsMessageLog.logMessage(
            f"Query params: {query_params}",
            "Censo Argentino",
            Qgis.Info
        )
        if bbox:
            QgsMessageLog.logMessage(
                f"Using bbox filter: {bbox}",
                "Censo Argentino",
                Qgis.Info
            )

        df = con.execute(query, query_params).df()
        con.close()

        if df.empty:
            error_msg = "No data returned for selected filters."
            if bbox:
                error_msg += f" Try zooming out or disabling viewport filtering. Bbox used: {bbox}"
            raise Exception(error_msg)

        if progress_callback:
            progress_callback(50, "Creating layer...")

        # Create layer name with variable list
        if len(variable_codes) == 1:
            layer_name = f"Censo - {variable_codes[0]} ({geo_level})"
        else:
            layer_name = f"Censo - {len(variable_codes)} variables ({geo_level})"

        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        # Add fields: geo_id + one field per variable
        fields = [QgsField("geo_id", QVariant.String)]
        for var_code in variable_codes:
            fields.append(QgsField(var_code, QVariant.Double))

        provider.addAttributes(fields)
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

            # Set attributes: geo_id + all variable values
            attributes = [row['geo_id']]
            for var_code in variable_codes:
                val = row[var_code]
                # Handle NaN/NULL values
                attributes.append(float(val) if val is not None and str(val) != 'nan' else None)

            feature.setAttributes(attributes)
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
