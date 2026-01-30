# Plugin Censo Argentino QGIS - Instrucciones para Claude

## Reglas Fundamentales

1. **Idioma**: Todo en español (documentación, commits, comentarios, mensajes)
2. **Sin pandas**: Usar solo DuckDB nativo (`.fetchall()`, no DataFrames)
3. **Testing**: SIEMPRE usar `.venv/bin/pytest` (NUNCA `pytest` directo)
4. **Linting**: SIEMPRE usar `.venv/bin/pre-commit` (NUNCA `pre-commit` directo)
5. **Commits**: Mensajes descriptivos en español, formato convencional

## Arquitectura del Plugin

### Flujo de Datos
```
plugin.py → dialog.py → query.py → DuckDB → Parquet (Source.Coop)
                            ↓
                      Caché local (JSON)
```

### Archivos Clave
- `metadata.txt`: Control de versión del plugin (actualizar antes de release)
- `query_builders.py`: Toda la lógica de construcción SQL (usar CTEs, no templates)
- `dialog.py`: Interacciones de interfaz de usuario
- `query.py`: Gestión de conexiones DuckDB y caché

### Decisiones de Diseño
- **Caché**: Metadatos en `~/.cache/qgis-censo-argentino/` para respuesta instantánea
- **SQL**: Usar CTEs para prevenir productos cartesianos
- **Pool de conexiones**: Una conexión DuckDB reutilizable

## Comandos Esenciales

### Testing
```bash
# Ejecutar todos los tests
.venv/bin/pytest tests/ -v

# Con cobertura
.venv/bin/pytest tests/ --cov=. --cov-report=term-missing

# Test específico
.venv/bin/pytest tests/test_query_builders.py -v
```

### Linting y Formateo
```bash
# Verificar y arreglar código
.venv/bin/pre-commit run --all-files

# Solo archivos staged
.venv/bin/pre-commit run
```

## Proceso de Release

1. Actualizar versión en `metadata.txt`
2. Crear tag: `git tag -a v0.X.Y -m "Descripción del release"`
3. Push: `git push && git push origin v0.X.Y`
4. CI publica automáticamente a repositorio QGIS

## Problemas Comunes

### Tests fallan localmente
Instalar extensiones DuckDB:
```bash
python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL spatial'); con.execute('INSTALL httpfs')"
```

### Plugin no carga en QGIS
Revisar: Ver → Paneles → Mensajes de registro

### Release falla en CI
Verificar secrets `OSGEO_USER` y `OSGEO_PASSWORD` configurados

## Estilo de Escritura

- **Todo en español**: Documentación, commits, comentarios, mensajes
- **Tono directo**: Sin florituras ni verbosidad excesiva
- **Ejemplos prácticos**: Código funcional, no teórico

## Convenciones de Código

```python
# Variables y funciones: snake_case
def load_census_layer(variable_codes, geo_level):
    total_rows = len(result)

# Constantes: UPPER_CASE
MAX_COLUMNS = 100

# Clases: PascalCase
class DuckDBConnectionPool:

# Imports: estándar → terceros → locales
import json
from pathlib import Path

import duckdb
from qgis.core import QgsVectorLayer

from .query_builders import build_pivot_columns
```

## Recursos

- **Repositorio**: https://github.com/nlebovits/censo-argentino-qgis
- **Documentación**: https://nlebovits.github.io/censo-argentino-qgis/
- **Plugin QGIS**: https://plugins.qgis.org/plugins/censo_argentino_qgis/
- **Datos**: https://source.coop/nlebovits/censo-argentino