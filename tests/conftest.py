"""Shared test fixtures for censo-argentino-qgis tests."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def pytest_addoption(parser):
    """Agregar opciones personalizadas de pytest."""
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Ejecutar benchmarks de rendimiento (requiere conexión a internet)",
    )


# Mock QGIS modules before any imports
sys.modules["qgis"] = MagicMock()
sys.modules["qgis.core"] = MagicMock()
sys.modules["qgis.PyQt"] = MagicMock()
sys.modules["qgis.PyQt.QtCore"] = MagicMock()
sys.modules["qgis.PyQt.QtWidgets"] = MagicMock()
sys.modules["qgis.PyQt.QtGui"] = MagicMock()


@pytest.fixture
def temp_cache_dir():
    """Temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_variables():
    """Sample variable data for testing."""
    return [
        ("POB_TOT_P", "Población total"),
        ("VIVIENDA_TOT", "Total de viviendas"),
        ("HOGAR_TOT", "Total de hogares"),
    ]


@pytest.fixture
def sample_geo_codes():
    """Sample geographic codes for testing."""
    return {
        "PROV": [("02", "CABA"), ("06", "Buenos Aires")],
        "DEPTO": [("02007", "Comuna 1"), ("06007", "Adolfo Alsina")],
    }
