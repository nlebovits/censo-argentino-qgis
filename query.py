import json
from pathlib import Path

import duckdb
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant


class DuckDBConnectionPool:
    """Singleton connection pool for DuckDB to avoid repeated connection/extension setup"""

    _instance = None
    _connection = None
    _extensions_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self, load_extensions=True):
        """Get or create a DuckDB connection with extensions loaded"""
        if self._connection is None:
            self._connection = duckdb.connect()

        if load_extensions and not self._extensions_loaded:
            self._connection.execute("INSTALL httpfs; LOAD httpfs;")
            self._connection.execute("INSTALL spatial; LOAD spatial;")
            self._extensions_loaded = True

        return self._connection

    def close(self):
        """Close the connection (typically only needed on plugin unload)"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._extensions_loaded = False


# Global connection pool instance
_connection_pool = DuckDBConnectionPool()


def get_cache_dir():
    """Get or create cache directory for census data"""
    cache_dir = Path.home() / ".cache" / "qgis-censo-argentino"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_data(cache_key):
    """Retrieve cached data if it exists"""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # If cache is corrupted, ignore and re-fetch
            return None
    return None


def save_cached_data(cache_key, data):
    """Save data to cache"""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
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
            progress_callback(100, "Tipos de entidad cargados desde caché")
        return cached

    try:
        if progress_callback:
            progress_callback(10, "Conectando a fuente de datos...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(50, "Cargando tipos de entidad...")

        query = """
            SELECT DISTINCT entidad
            FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet'
            WHERE entidad IN ('HOGAR', 'PERSONA', 'VIVIENDA')
            ORDER BY entidad
        """

        result = con.execute(query).fetchall()
        # Don't close - keep connection alive in pool

        entity_types = [row[0] for row in result]

        # Save to cache
        save_cached_data(cache_key, entity_types)

        if progress_callback:
            progress_callback(100, "Tipos de entidad cargados")

        return entity_types
    except Exception as e:
        raise Exception(f"Error cargando tipos de entidad: {str(e)}")


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
            progress_callback(100, f"Códigos de {geo_level} cargados desde caché")
        # Convert back to tuples
        return [(item[0], item[1]) for item in cached]

    try:
        if progress_callback:
            progress_callback(10, "Conectando a fuente de datos...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(50, f"Cargando códigos de {geo_level}...")

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
            """,
            "RADIO": """
                SELECT DISTINCT
                    c.id_geo as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento || ' - Radio ' || c.valor_radio as label
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                ORDER BY c.valor_provincia, c.valor_departamento, c.valor_fraccion, c.valor_radio
            """,
        }

        query = geo_queries.get(geo_level, geo_queries["PROV"])
        result = con.execute(query).fetchall()
        # Don't close - keep connection alive in pool

        geo_codes = [(row[0], row[1]) for row in result]

        # Save to cache
        save_cached_data(cache_key, geo_codes)

        if progress_callback:
            progress_callback(100, "Códigos geográficos cargados")

        return geo_codes
    except Exception as e:
        raise Exception(f"Error cargando códigos geográficos: {str(e)}")


def get_variables(entity_type=None, progress_callback=None):
    """Query metadata.parquet and return list of (codigo_variable, etiqueta_variable) for entity type (with caching)"""
    cache_key = f"variables_{entity_type if entity_type else 'all'}"

    # Check cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        if progress_callback:
            progress_callback(100, "Variables cargadas desde caché")
        # Convert back to tuples
        return [(item[0], item[1]) for item in cached]

    try:
        if progress_callback:
            progress_callback(10, "Conectando a fuente de datos...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(30, "Cargando metadatos de variables...")

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

        # Don't close - keep connection alive in pool

        variables = [(row[0], row[1]) for row in result]

        # Save to cache
        save_cached_data(cache_key, variables)

        if progress_callback:
            progress_callback(100, "Variables cargadas")

        return variables
    except Exception as e:
        raise Exception(f"Error cargando variables: {str(e)}")


def load_census_layer(
    variable_codes, geo_level="RADIO", geo_filters=None, bbox=None, progress_callback=None
):
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
            progress_callback(2, "Inicializando conexión DuckDB...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(10, f"Preparando consulta para nivel {geo_level}...")

        # Define grouping columns and ID fields based on geographic level
        geo_config = {
            "RADIO": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC, g.RADIO",
                "id_field": "g.COD_2022",
                "id_alias": "geo_id",
                "dissolve": False,
            },
            "FRACC": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC",
                "id_field": "g.PROV || '-' || g.DEPTO || '-' || g.FRACC",
                "id_alias": "geo_id",
                "dissolve": True,
            },
            "DEPTO": {
                "group_cols": "g.PROV, g.DEPTO",
                "id_field": "g.PROV || '-' || g.DEPTO",
                "id_alias": "geo_id",
                "dissolve": True,
            },
            "PROV": {
                "group_cols": "g.PROV",
                "id_field": "g.PROV",
                "id_alias": "geo_id",
                "dissolve": True,
            },
        }

        config = geo_config[geo_level]

        # Build WHERE clause for census data (variable filter only)
        variable_placeholders = ", ".join(["?" for _ in variable_codes])
        census_where_clause = f"c.codigo_variable IN ({variable_placeholders})"
        query_params = list(variable_codes)

        # Build geographic filter for the geometry subquery
        geo_filter = ""
        if geo_filters and len(geo_filters) > 0:
            # Build filter based on geo_level - these go in the subquery
            if geo_level == "PROV":
                placeholders = ", ".join(["?" for _ in geo_filters])
                geo_filter = f" AND PROV IN ({placeholders})"
                query_params.extend(geo_filters)
            elif geo_level == "DEPTO":
                # Parse "PROV-DEPTO" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split("-")
                    if len(parts) == 2:
                        filter_conditions.append("(PROV = ? AND DEPTO = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    geo_filter = f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "FRACC":
                # Parse "PROV-DEPTO-FRACC" format
                filter_conditions = []
                for gf in geo_filters:
                    parts = gf.split("-")
                    if len(parts) == 3:
                        filter_conditions.append("(PROV = ? AND DEPTO = ? AND FRACC = ?)")
                        query_params.extend(parts)
                if filter_conditions:
                    geo_filter = f" AND ({' OR '.join(filter_conditions)})"
            elif geo_level == "RADIO":
                placeholders = ", ".join(["?" for _ in geo_filters])
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
                pivot_columns.append(
                    f"SUM(CASE WHEN c.codigo_variable = '{var_code}' THEN c.conteo ELSE 0 END) as \"{var_code}\""
                )
            else:
                pivot_columns.append(
                    f"MAX(CASE WHEN c.codigo_variable = '{var_code}' THEN c.conteo ELSE NULL END) as \"{var_code}\""
                )

        pivot_sql = ",\n                    ".join(pivot_columns)

        if config["dissolve"]:
            # Aggregate geometries and sum data for each variable
            # Use subquery to filter geometries first, then join with census data
            query = f"""
                SELECT
                    {config["id_field"]} as geo_id,
                    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
                    {pivot_sql}
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter}
                ) g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {census_where_clause}
                GROUP BY {config["group_cols"]}
            """
        else:
            # No aggregation needed for RADIO level
            query = f"""
                SELECT
                    {config["id_field"]} as geo_id,
                    ST_AsText(g.geometry) as wkt,
                    {pivot_sql}
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter}
                ) g
                JOIN 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    ON g.COD_2022 = c.id_geo
                WHERE {census_where_clause}
                GROUP BY {config["id_field"]}, g.geometry
            """

        if progress_callback:
            progress_callback(20, "Construyendo consulta...")

        # Log the query for debugging
        from qgis.core import Qgis, QgsMessageLog

        QgsMessageLog.logMessage("=== DEBUG DE CONSULTA CENSO ===", "Censo Argentino", Qgis.Info)
        QgsMessageLog.logMessage(f"Nivel Geográfico: {geo_level}", "Censo Argentino", Qgis.Info)
        QgsMessageLog.logMessage(
            f"Códigos de variables: {variable_codes}", "Censo Argentino", Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Filtros geográficos: {geo_filters if geo_filters else 'Ninguno'}",
            "Censo Argentino",
            Qgis.Info,
        )
        if bbox:
            QgsMessageLog.logMessage(f"Filtro bbox: {bbox}", "Censo Argentino", Qgis.Info)
        QgsMessageLog.logMessage(
            f"Parámetros de consulta: {query_params}", "Censo Argentino", Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Filtro geográfico SQL: {geo_filter if geo_filter else 'Ninguno'}",
            "Censo Argentino",
            Qgis.Info,
        )
        QgsMessageLog.logMessage(
            f"Filtro espacial SQL: {spatial_filter if spatial_filter else 'Ninguno'}",
            "Censo Argentino",
            Qgis.Info,
        )
        QgsMessageLog.logMessage(f"Consulta completa:\n{query}", "Censo Argentino", Qgis.Info)

        # Pass query to callback for Query Log tab (substitute parameters for readability)
        if progress_callback:
            # Replace ? placeholders with actual values for logging
            logged_query = query
            for param in query_params:
                # Quote strings, leave numbers as-is
                if isinstance(param, str):
                    logged_query = logged_query.replace("?", f"'{param}'", 1)
                else:
                    logged_query = logged_query.replace("?", str(param), 1)
            progress_callback(25, f"QUERY_TEXT:{logged_query}")

        if progress_callback:
            progress_callback(30, "Ejecutando consulta...")

        df = con.execute(query, query_params).df()

        if progress_callback:
            progress_callback(60, f"La consulta devolvió {len(df)} filas...")

        # Don't close - keep connection alive in pool

        if df.empty:
            error_msg = "No se devolvieron datos para los filtros seleccionados."
            if bbox:
                error_msg += f" Intente alejar el zoom o deshabilite el filtro de ventana. Bbox usado: {bbox}"
            if geo_filters:
                error_msg += f" Filtros geográficos: {geo_filters}"
            QgsMessageLog.logMessage(f"ERROR: {error_msg}", "Censo Argentino", Qgis.Warning)
            # Create a dummy layer just to store the query for logging
            error_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Error - Sin Datos", "memory")
            error_layer.setCustomProperty("censo_query", query)
            error_layer.setCustomProperty("censo_error", error_msg)
            raise Exception(error_msg)

        if progress_callback:
            progress_callback(70, "Creando capa...")

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
            progress_callback(75, f"Procesando {len(df)} entidades...")

        # Add features
        features = []
        total_rows = len(df)
        for idx, row in df.iterrows():
            feature = QgsFeature()

            # Parse geometry from WKT (converted by ST_AsText)
            geom = QgsGeometry.fromWkt(row["wkt"])

            if geom.isNull():
                raise Exception(f"Geometría inválida para entidad {row['geo_id']}")

            feature.setGeometry(geom)

            # Set attributes: geo_id + all variable values
            attributes = [row["geo_id"]]
            for var_code in variable_codes:
                val = row[var_code]
                # Handle NaN/NULL values
                attributes.append(float(val) if val is not None and str(val) != "nan" else None)

            feature.setAttributes(attributes)
            features.append(feature)

            # Update progress more frequently for better feedback
            if progress_callback and (idx % 50 == 0 or idx == total_rows - 1):
                percent = 75 + int((idx / total_rows) * 20)
                progress_callback(percent, f"Procesando entidades: {idx + 1}/{total_rows}")

        if progress_callback:
            progress_callback(96, "Agregando entidades a la capa...")

        provider.addFeatures(features)

        if progress_callback:
            progress_callback(98, "Actualizando extensiones de la capa...")

        layer.updateExtents()

        if progress_callback:
            progress_callback(100, "Capa cargada exitosamente")

        QgsMessageLog.logMessage(
            f"Se cargaron exitosamente {len(features)} entidades con {len(variable_codes)} variables",
            "Censo Argentino",
            Qgis.Info,
        )

        # Store query as custom property for Query Log tab
        layer.setCustomProperty("censo_query", query)

        return layer

    except Exception as e:
        raise Exception(f"Error cargando capa censal: {str(e)}")


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
            progress_callback(10, "Conectando a fuente de datos...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(20, "Creando vistas de tablas...")

        con.execute("""
            CREATE VIEW radios AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet';
            CREATE VIEW census AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet';
            CREATE VIEW metadata AS SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/metadata.parquet';
        """)

        if progress_callback:
            progress_callback(30, "Ejecutando consulta...")

        df = con.execute(sql).df()
        # Don't close - keep connection alive in pool

        if df.empty:
            return None, "La consulta no devolvió resultados"

        if progress_callback:
            progress_callback(50, "Procesando resultados...")

        # Check if result has geometry (wkt column)
        if "wkt" in df.columns:
            layer = _df_to_layer(df, progress_callback)
            return layer, None
        else:
            return df, None

    except Exception as e:
        return None, str(e)


def _df_to_layer(df, progress_callback=None):
    """Convert DataFrame with wkt column to QgsVectorLayer"""
    from qgis.core import Qgis, QgsMessageLog

    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Resultado de Consulta SQL", "memory")
    provider = layer.dataProvider()

    # Build fields from non-geometry columns
    fields = []
    for col in df.columns:
        if col == "wkt":
            continue
        if df[col].dtype in ["int64", "int32"]:
            fields.append(QgsField(col, QVariant.LongLong))
        elif df[col].dtype in ["float64", "float32"]:
            fields.append(QgsField(col, QVariant.Double))
        else:
            fields.append(QgsField(col, QVariant.String))

    provider.addAttributes(fields)
    layer.updateFields()

    if progress_callback:
        progress_callback(60, f"Agregando {len(df)} entidades...")

    features = []
    non_wkt_cols = [c for c in df.columns if c != "wkt"]

    for idx, row in df.iterrows():
        feature = QgsFeature()
        geom = QgsGeometry.fromWkt(row["wkt"])
        if not geom.isNull():
            feature.setGeometry(geom)
            feature.setAttributes([row[c] for c in non_wkt_cols])
            features.append(feature)

        # Update progress
        if progress_callback and idx % 50 == 0:
            percent = 60 + int((idx / len(df)) * 35)
            progress_callback(percent, f"Procesando entidades: {idx + 1}/{len(df)}")

    provider.addFeatures(features)
    layer.updateExtents()

    if progress_callback:
        progress_callback(100, "Listo")

    QgsMessageLog.logMessage(
        f"Consulta SQL creó capa con {len(features)} entidades", "Censo Argentino", Qgis.Info
    )

    return layer
