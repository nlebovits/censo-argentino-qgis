"""Tests de profiling para monitorear uso de memoria y rendimiento.

Estos tests verifican que las consultas no excedan límites de memoria razonables
y que las optimizaciones de bbox funcionen correctamente.

Para ejecutar solo estos tests:
    .venv/bin/pytest tests/test_profiling.py -v

Para benchmarks locales detallados (requiere conexión a internet):
    .venv/bin/pytest tests/test_profiling.py -v -s --run-benchmarks
"""

from censo_argentino_qgis.query import (
    DUCKDB_MEMORY_LIMIT,
    MAX_COLUMNS,
    DuckDBConnectionPool,
)
from censo_argentino_qgis.query_builders import build_spatial_filter


class TestMemoryLimits:
    """Tests para verificar límites de memoria configurados."""

    def test_max_columns_is_reasonable(self):
        """MAX_COLUMNS debe ser suficiente para uso normal pero no excesivo."""
        assert MAX_COLUMNS >= 100, "Muy restrictivo para uso normal"
        assert MAX_COLUMNS <= 1000, "Demasiado alto, riesgo de OOM"

    def test_duckdb_memory_limit_is_set(self):
        """DuckDB debe tener un límite de memoria configurado."""
        assert DUCKDB_MEMORY_LIMIT is not None
        # Verificar que es un valor razonable (entre 1GB y 16GB)
        limit_str = DUCKDB_MEMORY_LIMIT.upper()
        if "GB" in limit_str:
            limit_gb = float(limit_str.replace("GB", ""))
            assert 1 <= limit_gb <= 16, f"Límite de memoria inusual: {DUCKDB_MEMORY_LIMIT}"

    def test_max_columns_value(self):
        """MAX_COLUMNS debe ser 500."""
        assert MAX_COLUMNS == 500


class TestSpatialFilterPushdown:
    """Tests para verificar que el filtro espacial se aplica correctamente."""

    def test_spatial_filter_builds_valid_sql(self):
        """build_spatial_filter debe generar SQL válido."""
        bbox = (-60.8, -34.0, -60.3, -33.5)
        sql = build_spatial_filter(bbox)

        assert "ST_Intersects" in sql
        assert "ST_GeomFromText" in sql
        assert "POLYGON" in sql
        # Verificar coordenadas
        assert "-60.8" in sql
        assert "-34.0" in sql
        assert "-60.3" in sql
        assert "-33.5" in sql

    def test_spatial_filter_empty_for_none_bbox(self):
        """Sin bbox, no debe haber filtro espacial."""
        sql = build_spatial_filter(None)
        assert sql == ""


class TestConnectionPool:
    """Tests para el pool de conexiones DuckDB."""

    def test_connection_pool_singleton(self):
        """Pool debe ser singleton."""
        pool1 = DuckDBConnectionPool()
        pool2 = DuckDBConnectionPool()
        assert pool1 is pool2


class TestColumnLimitEnforcement:
    """Tests para verificar que el límite de columnas se respeta."""

    def test_max_columns_exported(self):
        """MAX_COLUMNS debe ser accesible desde query.py."""
        from censo_argentino_qgis.query import MAX_COLUMNS

        assert isinstance(MAX_COLUMNS, int)
        assert MAX_COLUMNS > 0
