"""Benchmarks de rendimiento para consultas censales.

Estos tests requieren conexión a internet y se ejecutan solo con --run-benchmarks.

Uso:
    .venv/bin/pytest tests/test_benchmarks.py -v -s --run-benchmarks

Los benchmarks miden:
- Uso de memoria para diferentes tipos de consultas
- Efectividad del filtro espacial (bbox)
- Rendimiento de consultas con múltiples variables
"""

import resource
import time

import duckdb
import pytest

from censo_argentino_qgis.config import CENSUS_CONFIG
from censo_argentino_qgis.query import DUCKDB_MEMORY_LIMIT


def get_memory_mb():
    """Obtener uso máximo de memoria del proceso en MB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


@pytest.fixture
def duckdb_connection():
    """Conexión DuckDB configurada para benchmarks."""
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial")
    con.execute(f"SET memory_limit = '{DUCKDB_MEMORY_LIMIT}'")
    yield con
    con.close()


@pytest.fixture
def census_urls():
    """URLs de archivos censales."""
    return CENSUS_CONFIG["2022"]["urls"]


# Bbox de Pergamino (área pequeña para tests)
PERGAMINO_BBOX = "POLYGON((-60.8 -33.5, -60.3 -33.5, -60.3 -34.0, -60.8 -34.0, -60.8 -33.5))"


@pytest.mark.skipif(
    "not config.getoption('--run-benchmarks')",
    reason="Benchmarks solo con --run-benchmarks",
)
class TestMemoryBenchmarks:
    """Benchmarks de uso de memoria."""

    def test_radios_count_memory(self, duckdb_connection, census_urls):
        """Memoria para contar todos los radios."""
        baseline = get_memory_mb()

        result = duckdb_connection.execute(
            f"SELECT COUNT(*) FROM '{census_urls['radios']}'"
        ).fetchone()

        delta = get_memory_mb() - baseline
        print(f"\n  Radios: {result[0]:,}, Memory delta: {delta:.1f} MB")

        assert result[0] > 60000
        assert delta < 500, "Contar radios no debe usar >500 MB adicionales"

    def test_spatial_filter_reduces_data(self, duckdb_connection, census_urls):
        """Filtro espacial debe reducir datos procesados."""
        # Sin filtro
        all_count = duckdb_connection.execute(
            f"SELECT COUNT(*) FROM '{census_urls['radios']}'"
        ).fetchone()[0]

        # Con filtro
        filtered_count = duckdb_connection.execute(
            f"""
            SELECT COUNT(*)
            FROM '{census_urls["radios"]}'
            WHERE ST_Intersects(geometry, ST_GeomFromText('{PERGAMINO_BBOX}'))
            """
        ).fetchone()[0]

        reduction = (1 - filtered_count / all_count) * 100
        print(
            f"\n  Total: {all_count:,}, Filtered: {filtered_count:,}, Reduction: {reduction:.1f}%"
        )

        assert filtered_count < all_count * 0.1, "Bbox pequeño debe filtrar >90% de radios"

    def test_query_with_early_filter_memory(self, duckdb_connection, census_urls):
        """Query con filtro temprano debe usar menos memoria."""
        baseline = get_memory_mb()

        # Simula la query optimizada con filtro temprano
        query = f"""
            WITH filtered_radios AS (
                SELECT COD_2022, geometry
                FROM '{census_urls["radios"]}'
                WHERE ST_Intersects(geometry, ST_GeomFromText('{PERGAMINO_BBOX}'))
            ),
            census_pivoted AS (
                SELECT
                    r.COD_2022,
                    SUM(CASE WHEN codigo_variable = 'PERSONA_SEXO' AND valor_categoria = '1'
                        THEN conteo ELSE 0 END) as varon,
                    SUM(CASE WHEN codigo_variable = 'PERSONA_SEXO' AND valor_categoria = '2'
                        THEN conteo ELSE 0 END) as mujer
                FROM filtered_radios r
                LEFT JOIN '{census_urls["census"]}' c
                    ON r.COD_2022 = c.id_geo AND codigo_variable = 'PERSONA_SEXO'
                GROUP BY r.COD_2022
            )
            SELECT g.COD_2022, ST_AsText(g.geometry), cp.varon, cp.mujer
            FROM filtered_radios g
            JOIN census_pivoted cp ON g.COD_2022 = cp.COD_2022
        """

        start = time.time()
        result = duckdb_connection.execute(query).fetchall()
        elapsed = time.time() - start
        delta = get_memory_mb() - baseline

        print(f"\n  Rows: {len(result)}, Time: {elapsed:.1f}s, Memory delta: {delta:.1f} MB")

        assert len(result) > 0
        assert delta < 500, "Query filtrada no debe usar >500 MB adicionales"


@pytest.mark.skipif(
    "not config.getoption('--run-benchmarks')",
    reason="Benchmarks solo con --run-benchmarks",
)
class TestQueryPerformance:
    """Benchmarks de rendimiento de queries."""

    def test_single_variable_performance(self, duckdb_connection, census_urls):
        """Rendimiento para una variable simple."""
        start = time.time()

        result = duckdb_connection.execute(
            f"""
            SELECT c.id_geo, SUM(c.conteo) as total
            FROM '{census_urls["census"]}' c
            WHERE c.codigo_variable = 'PERSONA_SEXO'
            GROUP BY c.id_geo
            """
        ).fetchall()

        elapsed = time.time() - start
        print(f"\n  Rows: {len(result):,}, Time: {elapsed:.1f}s")

        assert len(result) > 60000
        assert elapsed < 30, "Query simple debe completar en <30s"

    def test_dissolve_performance(self, duckdb_connection, census_urls):
        """Rendimiento para dissolve a nivel DEPTO."""
        start = time.time()

        result = duckdb_connection.execute(
            f"""
            SELECT
                PROV || '-' || DEPTO as depto_id,
                ST_AsText(ST_MemUnion_Agg(geometry)) as wkt
            FROM '{census_urls["radios"]}'
            WHERE ST_Intersects(geometry, ST_GeomFromText('{PERGAMINO_BBOX}'))
            GROUP BY PROV, DEPTO
            """
        ).fetchall()

        elapsed = time.time() - start
        print(f"\n  Departamentos: {len(result)}, Time: {elapsed:.1f}s")

        assert len(result) > 0
        assert elapsed < 60, "Dissolve con bbox debe completar en <60s"
