import duckdb
import json
import os
from pathlib import Path
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant


def get_cache_dir():
    """Get or create cache directory for census data"""
    cache_dir = Path.home() / '.cache' / 'qgis-censo-argentino'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_data(cache_key):
    """Retrieve cached data if it exists"""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If cache is corrupted, ignore and re-fetch
            return None
    return None


def save_cached_data(cache_key, data):
    """Save data to cache"""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # If we can't write cache, that's okay - just continue without caching
        pass


def get_entity_types(progress_callback=None):
    """Query metadata.parquet and return list of available entity types (with caching)"""
    cache_key = "entity_types"

    # Check cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        if progress_callback:
            progress_callback(100, "Entity types loaded from cache")
        return cached

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

        entity_types = [row[0] for row in result]

        # Save to cache
        save_cached_data(cache_key, entity_types)

        if progress_callback:
            progress_callback(100, "Entity types loaded")

        return entity_types
    except Exception as e:
        raise Exception(f"Error loading entity types: {str(e)}")


def get_geographic_codes(geo_level="PROV", progress_callback=None):
    """Query radios.parquet and return list of available geographic codes for the level (with caching)

    Args:
        geo_level: Geographic level - "RADIO", "FRACC", "DEPTO", or "PROV"
        progress_callback: Optional callback for progress updates

    Returns:
        List of tuples: (code, label) for each geographic unit
    """
    cache_key = f"geo_codes_{geo_level}"

    # Check cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        if progress_callback:
            progress_callback(100, f"{geo_level} codes loaded from cache")
        # Convert back to tuples
        return [(item[0], item[1]) for item in cached]

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

        geo_codes = [(row[0], row[1]) for row in result]

        # Save to cache
        save_cached_data(cache_key, geo_codes)

        if progress_callback:
            progress_callback(100, "Geographic codes loaded")

        return geo_codes
    except Exception as e:
        raise Exception(f"Error loading geographic codes: {str(e)}")


def get_variables(entity_type=None, progress_callback=None):
    """Query metadata.parquet and return list of (codigo_variable, etiqueta_variable) for entity type (with caching)"""
    cache_key = f"variables_{entity_type if entity_type else 'all'}"

    # Check cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        if progress_callback:
            progress_callback(100, "Variables loaded from cache")
        # Convert back to tuples
        return [(item[0], item[1]) for item in cached]

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

        variables = [(row[0], row[1]) for row in result]

        # Save to cache
        save_cached_data(cache_key, variables)

        if progress_callback:
            progress_callback(100, "Variables loaded")

        return variables
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
            progress_callback(2, "Initializing DuckDB connection...")

        con = duckdb.connect()

        if progress_callback:
            progress_callback(5, "Loading DuckDB extensions...")

        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        if progress_callback:
            progress_callback(10, f"Preparing query for {geo_level} level...")

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

        # Build WHERE clause for census data (variable filter only)
        variable_placeholders = ', '.join(['?' for _ in variable_codes])
        census_where_clause = f"c.codigo_variable IN ({variable_placeholders})"
        query_params = list(variable_codes)

        # Build geographic filter for the geometry subquery
        geo_filter = ""
        if geo_filters and len(geo_filters) > 0:
            # Build filter based on geo_level - these go in the subquery
            if geo_level == "PROV":
                placeholders = ', '.join(['?' for _ in geo_filters])
                geo_filter = f" AND PROV IN ({placeholders})"
                query_params.extend(geo_filters)
            elif geo_level == "DEPTO":
                # Parse "PROV-DEPTO" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split('-')
                    if len(parts) == 2:
                        filter_conditions.append("(PROV = ? AND DEPTO = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    geo_filter = f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "FRACC":
                # Parse "PROV-DEPTO-FRACC" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split('-')
                    if len(parts) == 3:
                        filter_conditions.append("(PROV = ? AND DEPTO = ? AND FRACC = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    geo_filter = f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "RADIO":
                placeholders = ', '.join(['?' for _ in geo_filters])
                geo_filter = f" AND COD_2022 IN ({placeholders})"
                query_params.extend(geo_filters)

        # Build spatial filter for the geometry subquery
        # Apply spatial filter to geometry table BEFORE joining with census data
        # This ensures we get geometries even if census data doesn't exist for those variables
        spatial_filter = ""
        if bbox:
            xmin, ymin, xmax, ymax = bbox
            # Create a polygon from the bbox coordinates in WKT format
            bbox_wkt = f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
            spatial_filter = f" AND ST_Intersects(geometry, ST_GeomFromText('{bbox_wkt}'))"

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
            # Use subquery to filter geometries first, then join with census data
            query = f"""
                SELECT
                    {config['id_field']} as geo_id,
                    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
                    {pivot_sql}
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter}
                ) g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {census_where_clause}
                GROUP BY {config['group_cols']}
            """
        else:
            # No aggregation needed for RADIO level
            query = f"""
                SELECT
                    {config['id_field']} as geo_id,
                    ST_AsText(g.geometry) as wkt,
                    {pivot_sql}
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter}
                ) g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {census_where_clause}
                GROUP BY {config['id_field']}, g.geometry
            """

        if progress_callback:
            progress_callback(20, "Building query...")

        # Log the query for debugging
        from qgis.core import QgsMessageLog, Qgis
        QgsMessageLog.logMessage(
            "=== CENSO QUERY DEBUG ===",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Geo Level: {geo_level}",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Variable codes: {variable_codes}",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Geo filters: {geo_filters if geo_filters else 'None'}",
            "Censo Argentino",
            Qgis.Info
        )
        if bbox:
            QgsMessageLog.logMessage(
                f"Bbox filter: {bbox}",
                "Censo Argentino",
                Qgis.Info
            )
        QgsMessageLog.logMessage(
            f"Query parameters: {query_params}",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Geo filter SQL: {geo_filter if geo_filter else 'None'}",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Spatial filter SQL: {spatial_filter if spatial_filter else 'None'}",
            "Censo Argentino",
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Full Query:\n{query}",
            "Censo Argentino",
            Qgis.Info
        )

        if progress_callback:
            progress_callback(30, "Executing query...")

        df = con.execute(query, query_params).df()

        if progress_callback:
            progress_callback(60, f"Query returned {len(df)} rows...")

        con.close()

        if df.empty:
            error_msg = "No data returned for selected filters."
            if bbox:
                error_msg += f" Try zooming out or disabling viewport filtering. Bbox used: {bbox}"
            if geo_filters:
                error_msg += f" Geographic filters: {geo_filters}"
            QgsMessageLog.logMessage(
                f"ERROR: {error_msg}",
                "Censo Argentino",
                Qgis.Warning
            )
            raise Exception(error_msg)

        if progress_callback:
            progress_callback(70, "Creating layer...")

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
            progress_callback(75, f"Processing {len(df)} features...")

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

            # Update progress more frequently for better feedback
            if progress_callback and (idx % 50 == 0 or idx == total_rows - 1):
                percent = 75 + int((idx / total_rows) * 20)
                progress_callback(percent, f"Processing features: {idx + 1}/{total_rows}")

        if progress_callback:
            progress_callback(96, "Adding features to layer...")

        provider.addFeatures(features)

        if progress_callback:
            progress_callback(98, "Updating layer extents...")

        layer.updateExtents()

        if progress_callback:
            progress_callback(100, "Layer loaded successfully")

        QgsMessageLog.logMessage(
            f"Successfully loaded {len(features)} features with {len(variable_codes)} variables",
            "Censo Argentino",
            Qgis.Info
        )

        # Store query as custom property for Query Log tab
        layer.setCustomProperty("censo_query", query)

        return layer

    except Exception as e:
        raise Exception(f"Error loading census layer: {str(e)}")


def run_custom_query(sql, progress_callback=None):
    """Run arbitrary SQL against census data, return QgsVectorLayer or DataFrame

    Available tables:
        radios    → geometry + COD_2022, PROV, DEPTO, FRACC, RADIO
        census    → id_geo, codigo_variable, conteo, valor_provincia, etc.
        metadata  → codigo_variable, etiqueta_variable, entidad

    Returns:
        (result, error) where result is QgsVectorLayer, DataFrame, or None
    """
    try:
        if progress_callback:
            progress_callback(10, "Connecting to data source...")

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

        if progress_callback:
            progress_callback(20, "Creating table views...")

        con.execute("""
            CREATE VIEW radios AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet';
            CREATE VIEW census AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet';
            CREATE VIEW metadata AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet';
        """)

        if progress_callback:
            progress_callback(30, "Running query...")

        df = con.execute(sql).df()
        con.close()

        if df.empty:
            return None, "Query returned no results"

        if progress_callback:
            progress_callback(50, "Processing results...")

        # Check if result has geometry (wkt column)
        if 'wkt' in df.columns:
            layer = _df_to_layer(df, progress_callback)
            return layer, None
        else:
            return df, None

    except Exception as e:
        return None, str(e)


def _df_to_layer(df, progress_callback=None):
    """Convert DataFrame with wkt column to QgsVectorLayer"""
    from qgis.core import QgsMessageLog, Qgis

    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "SQL Query Result", "memory")
    provider = layer.dataProvider()

    # Build fields from non-geometry columns
    fields = []
    for col in df.columns:
        if col == 'wkt':
            continue
        if df[col].dtype in ['int64', 'int32']:
            fields.append(QgsField(col, QVariant.LongLong))
        elif df[col].dtype in ['float64', 'float32']:
            fields.append(QgsField(col, QVariant.Double))
        else:
            fields.append(QgsField(col, QVariant.String))

    provider.addAttributes(fields)
    layer.updateFields()

    if progress_callback:
        progress_callback(60, f"Adding {len(df)} features...")

    features = []
    non_wkt_cols = [c for c in df.columns if c != 'wkt']

    for idx, row in df.iterrows():
        feature = QgsFeature()
        geom = QgsGeometry.fromWkt(row['wkt'])
        if not geom.isNull():
            feature.setGeometry(geom)
            feature.setAttributes([row[c] for c in non_wkt_cols])
            features.append(feature)

        # Update progress
        if progress_callback and idx % 50 == 0:
            percent = 60 + int((idx / len(df)) * 35)
            progress_callback(percent, f"Processing features: {idx + 1}/{len(df)}")

    provider.addFeatures(features)
    layer.updateExtents()

    if progress_callback:
        progress_callback(100, "Done")

    QgsMessageLog.logMessage(
        f"SQL query created layer with {len(features)} features",
        "Censo Argentino",
        Qgis.Info
    )

    return layer
