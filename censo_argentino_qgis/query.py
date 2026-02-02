import json
import re
import time
import unicodedata
from pathlib import Path

import duckdb
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

from .config import CENSUS_CONFIG


class DuckDBConnectionPool:
    """Pool de conexiones singleton para DuckDB para evitar configuración repetida de conexión/extensiones"""

    _instance = None
    _connection = None
    _extensions_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self, load_extensions=True):
        """Obtener o crear una conexión DuckDB con extensiones cargadas"""
        if self._connection is None:
            self._connection = duckdb.connect()

        if load_extensions and not self._extensions_loaded:
            self._connection.execute("INSTALL httpfs; LOAD httpfs;")
            self._connection.execute("INSTALL spatial; LOAD spatial;")
            self._extensions_loaded = True

        return self._connection

    def close(self):
        """Cerrar la conexión (típicamente solo necesario al descargar el plugin)"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._extensions_loaded = False


# Global connection pool instance
_connection_pool = DuckDBConnectionPool()


def sanitize_category_label(label):
    """
    Convert category label to valid QGIS field name.

    NO LENGTH TRUNCATION - Full names for modern GIS formats.
    Shapefile users should export to GeoPackage or GeoParquet instead.

    Rules:
    - Lowercase only
    - Underscores for spaces/hyphens
    - Remove accents and special characters
    - Must start with letter (prefix with 'cat_' if starts with digit)

    Args:
        label: Original category label (e.g., "Sin instrucción")

    Returns:
        Sanitized field name (e.g., "sin_instruccion")

    Examples:
        >>> sanitize_category_label("Sin instrucción")
        'sin_instruccion'
        >>> sanitize_category_label("0-14 años")
        'cat_0_14_anos'
        >>> sanitize_category_label("Primario completo")
        'primario_completo'
    """
    if not label:
        return "unknown"

    # Remove accents/diacritics
    label = unicodedata.normalize("NFKD", label).encode("ASCII", "ignore").decode()

    # Convert to lowercase
    label = label.lower()

    # Replace spaces, hyphens, and slashes with underscores
    label = label.replace(" ", "_").replace("-", "_").replace("/", "_")

    # Remove non-alphanumeric except underscores
    label = re.sub(r"[^a-z0-9_]", "", label)

    # Remove consecutive underscores
    label = re.sub(r"_+", "_", label)

    # Remove leading/trailing underscores
    label = label.strip("_")

    # Ensure starts with letter
    if label and label[0].isdigit():
        label = "cat_" + label

    return label or "unknown"


def get_cache_dir():
    """Obtener o crear directorio de caché para datos del censo"""
    cache_dir = Path.home() / ".cache" / "qgis-censo-argentino"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_data(cache_key):
    """Recuperar datos en caché si existen y son válidos.

    Returns:
        Datos cacheados si existen y son no-vacíos, None en caso contrario.
        Los datos vacíos ({}, []) se consideran inválidos y se ignoran.
    """
    cache_file = get_cache_dir() / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                # Validar que los datos no estén vacíos (cache corrupto)
                if data is None or data == {} or data == []:
                    # Cache vacío/corrupto - eliminar y retornar None
                    try:
                        cache_file.unlink()
                    except Exception:
                        pass
                    return None
                return data
        except Exception:
            # Si el cache está corrupto, eliminarlo y re-fetch
            try:
                cache_file.unlink()
            except Exception:
                pass
            return None
    return None


def save_cached_data(cache_key, data):
    """Guardar datos en caché usando escritura atómica.

    Solo guarda si los datos son no-vacíos. Usa escritura atómica
    (escribir a archivo temporal, luego renombrar) para prevenir
    archivos de caché corruptos por interrupciones.
    """
    # No guardar datos vacíos
    if data is None or data == {} or data == []:
        return

    cache_file = get_cache_dir() / f"{cache_key}.json"
    temp_file = cache_file.with_suffix(".json.tmp")

    try:
        # Escribir a archivo temporal primero
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Renombrar atómicamente (en la mayoría de sistemas de archivos)
        temp_file.replace(cache_file)
    except Exception:
        # Si no podemos escribir, limpiar archivo temporal si existe
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass


def get_entity_types(year="2022", progress_callback=None):
    """Consultar metadata.parquet y devolver lista de tipos de entidad disponibles (con caché)

    Args:
        year: Año del censo ("2022" o "2010")
        progress_callback: Callback opcional para actualizaciones de progreso

    Returns:
        Lista de tipos de entidad disponibles
    """
    cache_key = f"entity_types_{year}"
    config = CENSUS_CONFIG[year]

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

        # Usar entidades configuradas para este año
        entities = config["entities"]
        placeholders = ", ".join([f"'{e}'" for e in entities])

        query = f"""
            SELECT DISTINCT entidad
            FROM '{config["urls"]["metadata"]}'
            WHERE entidad IN ({placeholders})
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


def get_geographic_codes(year="2022", geo_level="PROV", progress_callback=None):
    """Consultar radios.parquet y devolver lista de códigos geográficos disponibles para el nivel (con caché)

    Args:
        year: Año del censo ("2022" o "2010")
        geo_level: Nivel geográfico - "RADIO", "FRACC", "DEPTO", o "PROV"
        progress_callback: Callback opcional para actualizaciones de progreso

    Returns:
        Lista de tuplas: (código, etiqueta) para cada unidad geográfica
    """
    cache_key = f"geo_codes_{year}_{geo_level}"
    config = CENSUS_CONFIG[year]
    census_url = config["urls"]["census"]

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

        # Define queries based on geographic level (usando URL dinámica)
        geo_queries = {
            "PROV": f"""
                SELECT DISTINCT
                    c.valor_provincia as code,
                    c.etiqueta_provincia as label
                FROM '{census_url}' c
                ORDER BY c.valor_provincia
            """,
            "DEPTO": f"""
                SELECT DISTINCT
                    c.valor_provincia || '-' || c.valor_departamento as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento as label
                FROM '{census_url}' c
                ORDER BY c.valor_provincia, c.valor_departamento
            """,
            "FRACC": f"""
                SELECT DISTINCT
                    c.valor_provincia || '-' || c.valor_departamento || '-' || c.valor_fraccion as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento || ' - Fracc ' || c.valor_fraccion as label
                FROM '{census_url}' c
                ORDER BY c.valor_provincia, c.valor_departamento, c.valor_fraccion
            """,
            "RADIO": f"""
                SELECT DISTINCT
                    c.id_geo as code,
                    c.etiqueta_provincia || ' - ' || c.etiqueta_departamento || ' - Radio ' || c.valor_radio as label
                FROM '{census_url}' c
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


def preload_all_metadata(year="2022", progress_callback=None):
    """
    Cargar el archivo metadata.parquet completo una vez y cachear todas las categorías de variables.
    Esto hace que las búsquedas de categorías posteriores sean instantáneas. El archivo es solo ~1MB.

    Args:
        year: Año del censo ("2022" o "2010")
        progress_callback: Callback opcional(porcentaje, mensaje) para actualizaciones de progreso

    Returns:
        Diccionario mapeando códigos de variable a datos de categoría:
        {
            'VARIABLE_CODE': {
                'categories': [(valor, etiqueta), ...],
                'has_nulls': bool
            }
        }
    """
    cache_key = f"all_metadata_{year}"
    config = CENSUS_CONFIG[year]
    metadata_url = config["urls"]["metadata"]

    # Check if already cached
    cached = get_cached_data(cache_key)
    if cached is not None:
        if progress_callback:
            progress_callback(100, f"Metadatos {year} cargados desde caché")
        return cached

    if progress_callback:
        progress_callback(5, f"Cargando metadatos del censo {year}...")

    try:
        con = _connection_pool.get_connection(load_extensions=True)

        # Load entire metadata file - it's small (~1MB)
        # Don't cast to INTEGER since some categories are text (e.g., "12 de Octubre")
        query = f"""
            SELECT
                codigo_variable,
                valor_categoria,
                etiqueta_categoria
            FROM '{metadata_url}'
            ORDER BY codigo_variable, valor_categoria
        """

        result = con.execute(query).fetchall()

        # Build category map from raw results
        metadata_map = {}

        # Group results by variable code
        for row in result:
            var_code = row[0]
            valor_cat = row[1]
            etiqueta_cat = row[2]

            if var_code not in metadata_map:
                metadata_map[var_code] = {"categories": [], "has_nulls": False}

            if valor_cat is not None:
                metadata_map[var_code]["categories"].append((str(valor_cat), str(etiqueta_cat)))
            else:
                metadata_map[var_code]["has_nulls"] = True

        # Cache the entire map
        save_cached_data(cache_key, metadata_map)

        if progress_callback:
            progress_callback(100, f"Metadatos {year} cargados: {len(metadata_map)} variables")

        return metadata_map

    except Exception as e:
        raise Exception(f"Error al precargar metadatos: {str(e)}")


def get_variable_categories(year="2022", variable_code=None, progress_callback=None, retry_count=3):
    """
    Obtener categorías para una variable del caché de metadatos precargados.
    Recurre a consulta individual si la precarga aún no ha ocurrido.

    Args:
        year: Año del censo ("2022" o "2010")
        variable_code: Código de variable simple string (ej., 'EDUCACION')
        progress_callback: Callback opcional(porcentaje, mensaje) para actualizaciones de progreso
        retry_count: Número de intentos de reintento en caso de fallo (predeterminado 3)

    Returns:
        Dict con claves:
        - 'categories': Lista de tuplas [(valor, etiqueta), ...]
        - 'has_nulls': Booleano indicando si existen categorías NULL

        Ejemplo: {
            'categories': [('1', 'Sin instrucción'), ('2', 'Primario incompleto')],
            'has_nulls': True
        }
    """
    config = CENSUS_CONFIG[year]
    metadata_url = config["urls"]["metadata"]

    # Try to get from preloaded metadata first
    all_metadata = get_cached_data(f"all_metadata_{year}")
    if all_metadata and variable_code in all_metadata:
        return all_metadata[variable_code]

    # Fallback: individual cache check
    cache_key = f"categories_{year}_{variable_code}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached

    # Last resort: query individual variable (shouldn't happen if preload worked)
    if progress_callback:
        progress_callback(5, f"Fetching categories for {variable_code}...")

    for attempt in range(retry_count):
        try:
            con = _connection_pool.get_connection(load_extensions=True)

            query_categories = f"""
                SELECT DISTINCT
                    valor_categoria,
                    etiqueta_categoria
                FROM '{metadata_url}'
                WHERE codigo_variable = ?
                  AND valor_categoria IS NOT NULL
                ORDER BY CAST(valor_categoria AS INTEGER)
            """

            result = con.execute(query_categories, [variable_code]).fetchall()
            categories = [(str(row[0]), str(row[1])) for row in result]

            query_nulls = f"""
                SELECT COUNT(*) as null_count
                FROM '{metadata_url}'
                WHERE codigo_variable = ?
                  AND valor_categoria IS NULL
            """

            null_count = con.execute(query_nulls, [variable_code]).fetchone()[0]
            has_nulls = null_count > 0

            result_dict = {"categories": categories, "has_nulls": has_nulls}
            save_cached_data(cache_key, result_dict)
            return result_dict

        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2**attempt
                if progress_callback:
                    progress_callback(
                        5,
                        f"Retry {attempt + 1}/{retry_count} for {variable_code} in {wait_time}s...",
                    )
                time.sleep(wait_time)
            else:
                raise Exception(
                    f"Failed to fetch categories for {variable_code} after {retry_count} attempts: {str(e)}"
                )


def get_variables(year="2022", entity_type=None, progress_callback=None):
    """Consultar metadata.parquet y devolver lista de (codigo_variable, etiqueta_variable) para tipo de entidad (con caché)

    Args:
        year: Año del censo ("2022" o "2010")
        entity_type: Tipo de entidad (HOGAR, PERSONA, VIVIENDA) o None para todas
        progress_callback: Callback opcional para actualizaciones de progreso

    Returns:
        Lista de tuplas (codigo_variable, etiqueta_variable)
    """
    cache_key = f"variables_{year}_{entity_type if entity_type else 'all'}"
    config = CENSUS_CONFIG[year]
    metadata_url = config["urls"]["metadata"]

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
            query = f"""
                SELECT DISTINCT codigo_variable, etiqueta_variable
                FROM '{metadata_url}'
                WHERE entidad = ?
                ORDER BY codigo_variable
            """
            result = con.execute(query, [entity_type]).fetchall()
        else:
            query = f"""
                SELECT DISTINCT codigo_variable, etiqueta_variable
                FROM '{metadata_url}'
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


def calculate_column_count(year="2022", variable_codes=None, selected_categories=None):
    """Calcular el número total de columnas que se generarán.

    Args:
        year: Año del censo ("2022" o "2010")
        variable_codes: Lista de códigos de variables
        selected_categories: Dict opcional mapeando var_code a lista de categorías seleccionadas

    Returns:
        int: Número total de columnas que se generarán
    """
    if variable_codes is None:
        variable_codes = []
    if isinstance(variable_codes, str):
        variable_codes = [variable_codes]

    metadata_map = preload_all_metadata(year=year)
    total_columns = 0

    for var_code in variable_codes:
        cat_data = metadata_map.get(var_code, {"categories": [], "has_nulls": False})
        categories = cat_data["categories"]
        has_nulls = cat_data["has_nulls"]

        # Filter categories if selected_categories provided
        if selected_categories and var_code in selected_categories:
            selected = selected_categories[var_code]
            if selected:  # Only filter if non-empty list provided
                categories = [c for c in categories if c[0] in selected]

        if not categories and not has_nulls:
            total_columns += 1  # Total-only variable
        else:
            total_columns += (
                len(categories) + (1 if has_nulls else 0) + 1
            )  # Categories + NULL? + total

    return total_columns


def load_census_layer(
    year="2022",
    variable_codes=None,
    geo_level="RADIO",
    geo_filters=None,
    bbox=None,
    selected_categories=None,
    progress_callback=None,
):
    """Ejecutar join en DuckDB y devolver QgsVectorLayer con datos del censo para múltiples variables.

    Args:
        year: Año del censo ("2022" o "2010")
        variable_codes: Lista de códigos de variables del censo (o código único como string)
        geo_level: Nivel geográfico - "RADIO", "FRACC", "DEPTO", o "PROV"
        geo_filters: Lista opcional de códigos geográficos para filtrar
        bbox: Bounding box opcional (xmin, ymin, xmax, ymax) en EPSG:4326
        selected_categories: Dict opcional mapeando var_code a lista de valores de categoría seleccionados
                           Ejemplo: {"PERSONA_P11": ["1", "2"]}
                           Si es None o vacío para una variable, se incluyen todas las categorías
        progress_callback: Callback opcional para actualizaciones de progreso

    Returns:
        QgsVectorLayer con geometría y columnas de categorías expandidas

    Raises:
        Exception: Si la consulta falla
    """
    # Allow single variable as string
    if variable_codes is None:
        variable_codes = []
    if isinstance(variable_codes, str):
        variable_codes = [variable_codes]

    # Obtener configuración para el año
    config = CENSUS_CONFIG[year]
    geo_id_col = config["geo_id_column"]
    radios_url = config["urls"]["radios"]
    census_url = config["urls"]["census"]

    try:
        if progress_callback:
            progress_callback(2, "Inicializando conexión DuckDB...")

        con = _connection_pool.get_connection(load_extensions=True)

        # PHASE 4.1: Fetch categories for all variables with retry logic
        if progress_callback:
            progress_callback(5, f"Obteniendo categorías para {len(variable_codes)} variables...")

        # Import query_builders functions (try relative import first for QGIS plugin context)
        try:
            from .query_builders import build_geo_filter, build_pivot_columns, build_spatial_filter
        except ImportError:
            from query_builders import build_geo_filter, build_pivot_columns, build_spatial_filter

        variable_categories_map = {}
        failed_variables = []

        for idx, var_code in enumerate(variable_codes):
            try:
                result = get_variable_categories(
                    year=year, variable_code=var_code, progress_callback=progress_callback
                )

                # Filter categories based on selected_categories if provided
                if selected_categories and var_code in selected_categories:
                    selected_vals = selected_categories[var_code]
                    if selected_vals:  # If list is not empty, filter
                        filtered_cats = [
                            (val, label)
                            for val, label in result["categories"]
                            if val in selected_vals
                        ]
                        result = {"categories": filtered_cats, "has_nulls": result["has_nulls"]}

                variable_categories_map[var_code] = result

                if progress_callback:
                    cat_count = len(result["categories"])
                    progress_callback(
                        5 + int((idx / len(variable_codes)) * 5),
                        f"Variable {var_code}: {cat_count} categorías",
                    )
            except Exception as e:
                from qgis.core import Qgis, QgsMessageLog

                QgsMessageLog.logMessage(
                    f"ADVERTENCIA: No se pudieron obtener categorías para {var_code}: {e}",
                    "Censo Argentino",
                    Qgis.Warning,
                )
                failed_variables.append(var_code)
                # Continue with empty categories for this variable
                variable_categories_map[var_code] = {"categories": [], "has_nulls": False}

        # PHASE 4.2: Calculate total column count and validate limits
        total_columns = 0
        for _var_code, cat_data in variable_categories_map.items():
            categories = cat_data["categories"]
            has_nulls = cat_data["has_nulls"]

            if not categories and not has_nulls:
                # Total-only variable: 1 column
                total_columns += 1
            else:
                # Regular categories + optional NULL column + total column
                total_columns += len(categories) + (1 if has_nulls else 0) + 1

        # Log column count for monitoring
        from qgis.core import Qgis, QgsMessageLog

        QgsMessageLog.logMessage(
            f"Cargando {total_columns} columnas",
            "Censo Argentino",
            Qgis.Info,
        )

        if progress_callback:
            progress_callback(
                10, f"Preparando consulta para nivel {geo_level} ({total_columns} columnas)..."
            )

        # Define grouping columns and ID fields based on geographic level
        # Usar columna de ID dinámica según el año
        geo_config_map = {
            "RADIO": {
                "group_cols": "PROV, DEPTO, FRACC, RADIO",
                "id_field": geo_id_col,
                "id_alias": "geo_id",
                "dissolve": False,
            },
            "FRACC": {
                "group_cols": "PROV, DEPTO, FRACC",
                "id_field": "PROV || '-' || DEPTO || '-' || FRACC",
                "id_alias": "geo_id",
                "dissolve": True,
            },
            "DEPTO": {
                "group_cols": "PROV, DEPTO",
                "id_field": "PROV || '-' || DEPTO",
                "id_alias": "geo_id",
                "dissolve": True,
            },
            "PROV": {
                "group_cols": "PROV",
                "id_field": "PROV",
                "id_alias": "geo_id",
                "dissolve": True,
            },
        }

        geo_config_level = geo_config_map[geo_level]

        # PHASE 4.3: Build filters using query_builders functions
        geo_filter, geo_params = build_geo_filter(geo_level, geo_filters, geo_id_col=geo_id_col)
        spatial_filter = build_spatial_filter(bbox)

        # PHASE 4.4: Build CTE-based query (FIXES CARTESIAN PRODUCT BUG)
        # Step 1: Build pivot columns SQL using category expansion
        pivot_sql = build_pivot_columns(variable_codes, variable_categories_map)

        # Step 2: Build query parameters (variables first, then geo filters)
        query_params = list(variable_codes) + geo_params

        # Step 3: Build variable filter for CTE
        variable_placeholders = ", ".join(["?" for _ in variable_codes])
        census_where_clause = f"codigo_variable IN ({variable_placeholders})"

        # Step 4: Build list of all column names from the pivot
        # Extract column names from pivot_sql (format: "... as \"column_name\"")
        import re

        column_names = re.findall(r'as "([^"]+)"', pivot_sql)

        # Step 5: Build CTE that pivots census data FIRST (prevents cartesian product)
        # This is the critical fix - we aggregate census data at radio level in a CTE,
        # THEN join 1:1 with geometry. Old approach joined first, causing row multiplication.
        if geo_config_level["dissolve"]:
            # For dissolved geometries: CTE aggregates to target level, then joins
            # Build SUM aggregations for all pivoted columns
            sum_columns = ", ".join([f'SUM(cp."{col}") as "{col}"' for col in column_names])

            query = f"""
                WITH census_pivoted AS (
                    SELECT
                        r.PROV, r.DEPTO, r.FRACC, r.RADIO,
                        {pivot_sql}
                    FROM '{radios_url}' r
                    LEFT JOIN '{census_url}' c
                        ON r.{geo_id_col} = c.id_geo AND {census_where_clause}
                    GROUP BY r.PROV, r.DEPTO, r.FRACC, r.RADIO
                )
                SELECT
                    {geo_config_level["id_field"]} as geo_id,
                    ST_AsText(ST_MemUnion_Agg(g.geometry)) as wkt,
                    {sum_columns}
                FROM '{radios_url}' g
                JOIN census_pivoted cp
                    ON g.PROV = cp.PROV AND g.DEPTO = cp.DEPTO AND g.FRACC = cp.FRACC AND g.RADIO = cp.RADIO
                WHERE 1=1 {geo_filter} {spatial_filter}
                GROUP BY {geo_config_level["group_cols"]}
            """
        else:
            # For RADIO level: CTE pivots at radio level, simple 1:1 join
            # No need to re-aggregate, just select all columns
            select_columns = ", ".join([f'cp."{col}"' for col in column_names])

            query = f"""
                WITH census_pivoted AS (
                    SELECT
                        r.{geo_id_col},
                        {pivot_sql}
                    FROM '{radios_url}' r
                    LEFT JOIN '{census_url}' c
                        ON r.{geo_id_col} = c.id_geo AND {census_where_clause}
                    GROUP BY r.{geo_id_col}
                )
                SELECT
                    g.{geo_config_level["id_field"]} as geo_id,
                    ST_AsText(g.geometry) as wkt,
                    {select_columns}
                FROM '{radios_url}' g
                JOIN census_pivoted cp ON g.{geo_config_level["id_field"]} = cp.{geo_id_col}
                WHERE 1=1 {geo_filter} {spatial_filter}
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
            f"Total de columnas expandidas: {total_columns}", "Censo Argentino", Qgis.Info
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
        if failed_variables:
            QgsMessageLog.logMessage(
                f"Variables con errores de categoría: {failed_variables}",
                "Censo Argentino",
                Qgis.Warning,
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

        result = con.execute(query, query_params).fetchall()

        if progress_callback:
            progress_callback(60, f"La consulta devolvió {len(result)} filas...")

        # Don't close - keep connection alive in pool

        if not result:
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

        # Create layer name with variable list and year
        if len(variable_codes) == 1:
            layer_name = f"Censo {year} - {variable_codes[0]} ({geo_level})"
        else:
            layer_name = f"Censo {year} - {len(variable_codes)} variables ({geo_level})"

        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        # PHASE 4.5: Add fields for all expanded category columns
        fields = [QgsField("geo_id", QVariant.String)]

        # Add one field for each category column (not just one per variable)
        for col_name in column_names:
            fields.append(QgsField(col_name, QVariant.Double))

        provider.addAttributes(fields)
        layer.updateFields()

        if progress_callback:
            progress_callback(75, f"Procesando {len(result)} entidades...")

        # Add features
        features = []
        total_rows = len(result)
        for idx, row in enumerate(result):
            feature = QgsFeature()

            # Row format: (geo_id, wkt, col1, col2, col3, ...)
            geo_id = row[0]
            wkt = row[1]

            # Parse geometry from WKT (converted by ST_AsText)
            geom = QgsGeometry.fromWkt(wkt)

            if geom.isNull():
                raise Exception(f"Geometría inválida para entidad {geo_id}")

            feature.setGeometry(geom)

            # Set attributes: geo_id + all category column values
            attributes = [geo_id]
            # Column values start at index 2 (after geo_id and wkt)
            for col_idx in range(len(column_names)):
                val = row[2 + col_idx]
                # Handle NULL values
                attributes.append(float(val) if val is not None else None)

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
            f"Se cargaron exitosamente {len(features)} entidades con {len(variable_codes)} variables "
            f"({total_columns} columnas expandidas)",
            "Censo Argentino",
            Qgis.Info,
        )

        # Store query as custom property for Query Log tab
        layer.setCustomProperty("censo_query", query)

        return layer

    except Exception as e:
        raise Exception(f"Error cargando capa censal: {str(e)}")


def run_custom_query(sql, year="2022", progress_callback=None):
    """Ejecutar SQL arbitrario contra datos del censo, devolver QgsVectorLayer o result tuple

    Args:
        sql: Consulta SQL a ejecutar
        year: Año del censo ("2022" o "2010")
        progress_callback: Callback opcional para actualizaciones de progreso

    Tablas disponibles:
        radios    → geometry + COD_2022/COD_2010, PROV, DEPTO, FRACC, RADIO
        census    → id_geo, codigo_variable, conteo, valor_provincia, etc.
        metadata  → codigo_variable, etiqueta_variable, entidad

    Returns:
        (result, error) donde result es QgsVectorLayer, (columns, rows), o None
    """
    config = CENSUS_CONFIG[year]

    try:
        if progress_callback:
            progress_callback(10, "Conectando a fuente de datos...")

        con = _connection_pool.get_connection(load_extensions=True)

        if progress_callback:
            progress_callback(20, f"Creando vistas de tablas para censo {year}...")

        # Drop views if they exist (in case year changed)
        con.execute(
            "DROP VIEW IF EXISTS radios; DROP VIEW IF EXISTS census; DROP VIEW IF EXISTS metadata;"
        )

        con.execute(f"""
            CREATE VIEW radios AS SELECT * FROM '{config["urls"]["radios"]}';
            CREATE VIEW census AS SELECT * FROM '{config["urls"]["census"]}';
            CREATE VIEW metadata AS SELECT * FROM '{config["urls"]["metadata"]}';
        """)

        if progress_callback:
            progress_callback(30, "Ejecutando consulta...")

        result_rel = con.execute(sql)
        columns = [desc[0] for desc in result_rel.description]
        rows = result_rel.fetchall()
        # Don't close - keep connection alive in pool

        if not rows:
            return None, "La consulta no devolvió resultados"

        if progress_callback:
            progress_callback(50, "Procesando resultados...")

        # Check if result has geometry (wkt column)
        if "wkt" in columns:
            layer = _result_to_layer(columns, rows, progress_callback)
            return layer, None
        else:
            return (columns, rows), None

    except Exception as e:
        return None, str(e)


def _result_to_layer(columns, rows, progress_callback=None):
    """Convertir resultado de consulta con columna wkt a QgsVectorLayer"""
    from qgis.core import Qgis, QgsMessageLog

    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Resultado de Consulta SQL", "memory")
    provider = layer.dataProvider()

    # Find wkt column index
    wkt_idx = columns.index("wkt")

    # Build fields from non-geometry columns
    fields = []
    non_wkt_indices = []
    for idx, col in enumerate(columns):
        if col == "wkt":
            continue
        non_wkt_indices.append(idx)

        # Infer type from first non-NULL value
        sample_val = None
        for row in rows:
            if row[idx] is not None:
                sample_val = row[idx]
                break

        if sample_val is not None:
            if isinstance(sample_val, int):
                fields.append(QgsField(col, QVariant.LongLong))
            elif isinstance(sample_val, float):
                fields.append(QgsField(col, QVariant.Double))
            else:
                fields.append(QgsField(col, QVariant.String))
        else:
            # Default to String if all values are NULL
            fields.append(QgsField(col, QVariant.String))

    provider.addAttributes(fields)
    layer.updateFields()

    if progress_callback:
        progress_callback(60, f"Agregando {len(rows)} entidades...")

    features = []

    for idx, row in enumerate(rows):
        feature = QgsFeature()
        geom = QgsGeometry.fromWkt(row[wkt_idx])
        if not geom.isNull():
            feature.setGeometry(geom)
            feature.setAttributes([row[i] for i in non_wkt_indices])
            features.append(feature)

        # Update progress
        if progress_callback and idx % 50 == 0:
            percent = 60 + int((idx / len(rows)) * 35)
            progress_callback(percent, f"Procesando entidades: {idx + 1}/{len(rows)}")

    provider.addFeatures(features)
    layer.updateExtents()

    if progress_callback:
        progress_callback(100, "Listo")

    QgsMessageLog.logMessage(
        f"Consulta SQL creó capa con {len(features)} entidades", "Censo Argentino", Qgis.Info
    )

    return layer
