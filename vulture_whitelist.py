"""Vulture whitelist - falsos positivos para código QGIS.

Vulture detecta código "muerto" pero no entiende el contexto de plugins QGIS.
Estos identificadores son usados por QGIS en tiempo de ejecución.

Formato: usar atributos de _ (underscore) para indicar nombres usados.
"""

# Objeto placeholder para whitelist
_ = type("_", (), {})()

# === QGIS Plugin Entry Points ===
_.classFactory  # __init__.py - punto de entrada del plugin
_.initGui  # plugin.py - inicialización de GUI por QGIS
_.unload  # plugin.py - descarga del plugin por QGIS

# === QGIS Plugin Lifecycle ===
_.iface  # Interfaz principal de QGIS pasada al plugin
_.run  # Ejecutado cuando el usuario hace clic en el botón del plugin

# === PyQt Signals ===
_.finished  # QThread.finished signal
_.progress  # Señal de progreso personalizada

# === Test Fixtures ===
_.temp_cache_dir  # conftest.py fixture
_.sample_variables  # conftest.py fixture
_.sample_geo_codes  # conftest.py fixture
_.duckdb_connection  # test_benchmarks.py fixture
_.census_urls  # test_benchmarks.py fixture

# === pytest hooks ===
_.pytest_addoption  # conftest.py - agrega opciones CLI
