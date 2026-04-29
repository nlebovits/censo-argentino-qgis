#!/usr/bin/env python3
"""
Regenerar archivos parquet empaquetados desde Source Coop remoto.

Uso:
    .venv/bin/python scripts/regenerate_bundled_data.py

Regenera:
    - censo_argentino_qgis/data/metadata.parquet (variables y categorías)
    - censo_argentino_qgis/data/geocodes.parquet (códigos geográficos)
"""

import os
from pathlib import Path

import duckdb

BASE_URL = "https://data.source.coop/nlebovits/censo-argentino"
YEARS = ["1991", "2001", "2010", "2022"]
OUTPUT_DIR = Path(__file__).parent.parent / "censo_argentino_qgis" / "data"


def regenerate_metadata():
    """Regenerar metadata.parquet desde archivos remotos."""
    print("=== Regenerando metadata.parquet ===")
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs")
    con.execute("SET enable_progress_bar = true")

    union_parts = []
    for year in YEARS:
        url = f"{BASE_URL}/{year}/metadata.parquet"
        union_parts.append(f"""
            SELECT
                '{year}' as year,
                codigo_variable,
                etiqueta_variable,
                valor_categoria,
                etiqueta_categoria,
                entidad
            FROM '{url}'
        """)

    query = " UNION ALL ".join(union_parts)
    output_path = OUTPUT_DIR / "metadata.parquet"

    print(f"Descargando metadata de {len(YEARS)} años...")
    con.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")

    result = con.execute(f"""
        SELECT year, COUNT(*) as rows, COUNT(etiqueta_variable) as with_labels
        FROM '{output_path}'
        GROUP BY year ORDER BY year
    """).fetchall()

    print("\nResultado:")
    for row in result:
        null_pct = ((row[1] - row[2]) / row[1] * 100) if row[1] > 0 else 0
        print(f"  {row[0]}: {row[1]:,} filas, {row[2]:,} con etiquetas ({null_pct:.1f}% NULL)")

    print(f"\nGuardado en: {output_path}")
    print(f"Tamaño: {output_path.stat().st_size / 1024:.1f} KB")


def regenerate_geocodes():
    """Regenerar geocodes.parquet desde archivos remotos."""
    print("\n=== Regenerando geocodes.parquet ===")
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial")
    con.execute("SET enable_progress_bar = true")

    geo_id_cols = {
        "1991": "COD_1991",
        "2001": "COD_2001",
        "2010": "COD_2010",
        "2022": "COD_2022",
    }

    union_parts = []
    for year in YEARS:
        radios_url = f"{BASE_URL}/{year}/radios.parquet"
        census_url = f"{BASE_URL}/{year}/census-data.parquet"
        geo_col = geo_id_cols[year]

        # Provincias - labels from census-data
        union_parts.append(f"""
            SELECT '{year}' as year, 'PROV' as level,
                   valor_provincia as code, FIRST(etiqueta_provincia) as label
            FROM '{census_url}' GROUP BY valor_provincia
        """)

        # Departamentos - labels from census-data
        union_parts.append(f"""
            SELECT '{year}' as year, 'DEPTO' as level,
                   valor_provincia || '-' || valor_departamento as code,
                   FIRST(etiqueta_departamento) as label
            FROM '{census_url}' GROUP BY valor_provincia, valor_departamento
        """)

        # Fracciones - from radios (no labels needed, use code as label)
        union_parts.append(f"""
            SELECT '{year}' as year, 'FRACC' as level,
                   PROV || '-' || DEPTO || '-' || FRACC as code,
                   PROV || '-' || DEPTO || '-' || FRACC as label
            FROM '{radios_url}' GROUP BY PROV, DEPTO, FRACC
        """)

        # Radios - from radios (use geo ID as both code and label)
        union_parts.append(f"""
            SELECT '{year}' as year, 'RADIO' as level,
                   {geo_col} as code, {geo_col} as label
            FROM '{radios_url}'
        """)

    query = " UNION ALL ".join(union_parts)
    output_path = OUTPUT_DIR / "geocodes.parquet"

    print(f"Descargando geocodes de {len(YEARS)} años...")
    con.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")

    result = con.execute(f"""
        SELECT year, level, COUNT(*) as count
        FROM '{output_path}'
        GROUP BY year, level ORDER BY year, level
    """).fetchall()

    print("\nResultado:")
    current_year = None
    for row in result:
        if row[0] != current_year:
            current_year = row[0]
            print(f"  {row[0]}:")
        print(f"    {row[1]}: {row[2]:,}")

    print(f"\nGuardado en: {output_path}")
    print(f"Tamaño: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    regenerate_metadata()
    regenerate_geocodes()
    print("\n✓ Regeneración completa")
