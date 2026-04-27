"""Vulture whitelist - falsos positivos para código QGIS.

Vulture detecta código "muerto" pero no entiende el contexto de plugins QGIS.
Estos identificadores son usados por QGIS en tiempo de ejecución.
"""

# === QGIS Plugin Entry Points ===
# Llamados por QGIS, no por nuestro código
classFactory  # __init__.py - punto de entrada del plugin
initGui  # plugin.py - inicialización de GUI por QGIS
unload  # plugin.py - descarga del plugin por QGIS

# === QGIS Plugin Lifecycle ===
# Métodos llamados por el framework QGIS
iface  # Interfaz principal de QGIS pasada al plugin
run  # Ejecutado cuando el usuario hace clic en el botón del plugin

# === PyQt Signals ===
# Señales conectadas dinámicamente
finished  # QThread.finished signal
progress  # Señal de progreso personalizada

# === Test Fixtures ===
# Usados por pytest, no llamados directamente
temp_cache_dir  # conftest.py fixture
sample_variables  # conftest.py fixture
sample_geo_codes  # conftest.py fixture
duckdb_connection  # test_benchmarks.py fixture
census_urls  # test_benchmarks.py fixture

# === pytest hooks ===
pytest_addoption  # conftest.py - agrega opciones CLI
