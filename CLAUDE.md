# Guía de Desarrollo - Plugin Censo Argentino QGIS

Documentación para Claude y desarrolladores sobre la estructura y filosofía del proyecto.

## Filosofía de Diseño

**YAGNI (You Aren't Gonna Need It)**: No agregar funcionalidad hasta que sea necesaria.

**DRY (Don't Repeat Yourself)**: Eliminar duplicación, extraer lógica común.

**Mantenibilidad primero**: Código simple y directo sobre optimizaciones prematuras.

## Estructura del Proyecto

```
censo-argentino-qgis/
├── censo_argentino_qgis/  # Módulos principales del plugin
│   ├── __init__.py        # Inicialización del plugin
│   ├── plugin.py          # Punto de entrada QGIS
│   ├── dialog.py          # Interfaz gráfica
│   ├── dialog.ui          # Archivo Qt Designer (interfaz)
│   ├── query.py           # Consultas DuckDB y caché
│   ├── query_builders.py  # Construcción SQL dinámica
│   ├── validation.py      # Validación SQL
│   ├── metadata.txt       # Metadatos del plugin (versión, descripción)
│   └── icon.png          # Icono del plugin
├── tests/                 # Tests con pytest
├── docs/                  # Documentación MkDocs
│   ├── *.md              # Páginas de documentación
│   └── imgs/             # Imágenes y screenshots
├── .github/workflows/     # CI/CD
│   ├── ci.yml            # Tests y linting
│   ├── release.yml       # Publicación automática
│   └── deploy-docs.yml   # Despliegue de docs
└── .qgis-plugin-ci       # Config para publicación en QGIS repo
```

## Gestión de Entorno

### Desarrollo Local

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

### Dependencias

- **Runtime**: Solo `duckdb>=0.9.0` (sin pandas)
- **Dev**: pytest, ruff, coverage (ver `requirements-dev.txt`)

### Testing

**IMPORTANTE**: Los tests DEBEN ejecutarse usando el entorno virtual `.venv`:

```bash
# Ejecutar todos los tests
.venv/bin/pytest tests/ -v

# Con cobertura
.venv/bin/pytest tests/ --cov=. --cov-report=term-missing

# Tests específicos
.venv/bin/pytest tests/test_query_builders.py -v
```

**NO usar**:
- `pytest` (sin ruta al venv)
- `python -m pytest` (usa el Python del sistema)
- `uv run pytest` (el proyecto no tiene `[project]` en pyproject.toml)

**Nota**: Algunos tests requieren conexión a Internet (marcados como `@pytest.mark.skip`).

### Pre-commit Hooks

**IMPORTANTE**: Los hooks DEBEN ejecutarse usando el entorno virtual `.venv`:

```bash
# Ejecutar hooks en todos los archivos
.venv/bin/pre-commit run --all-files

# Ejecutar solo en archivos staged
.venv/bin/pre-commit run

# Instalar hooks para que corran automáticamente
.venv/bin/pre-commit install
```

**NO usar**:
- `pre-commit` (sin ruta al venv)
- Hooks configurados: `ruff` (linting) y `ruff-format` (formateo)

## Releases

### Proceso Manual

1. Actualizar `metadata.txt` con nueva versión
2. Crear tag: `git tag -a v0.4.1 -m "Descripción"`
3. Push: `git push && git push origin v0.4.1`
4. GitHub Actions publica automáticamente a:
   - GitHub Releases (ZIP del plugin)
   - Repositorio oficial de QGIS

### Publicación Automática

El workflow `.github/workflows/release.yml` usa `qgis-plugin-ci` para:
- Empaquetar el plugin (excluye tests, docs, etc.)
- Crear GitHub Release
- Publicar en plugins.qgis.org

**Requiere secrets**:
- `OSGEO_USER`: Usuario OSGeo
- `OSGEO_PASSWORD`: Contraseña OSGeo

## Documentación

### Ubicación y Estructura

Documentación en `docs/` usando MkDocs + Material theme:

```
docs/
├── index.md              # Página principal
├── instalacion.md        # Guía de instalación
├── inicio-rapido.md      # Tutorial básico
├── sql.md               # Modo SQL avanzado
├── solucion-problemas.md # Troubleshooting
└── CHANGELOG.md         # Historial de cambios
```

### Estilo de Escritura

**Todo en español**: Docs, commits, comentarios, README.

**Tono**: Directo y práctico. Sin florituras.

**Formato**:
- Títulos con `##` (no `#`)
- Ejemplos de código con sintaxis highlighting
- Capturas de pantalla en `docs/imgs/`
- Enlaces relativos entre páginas

**Ejemplo bueno**:
```markdown
## Instalar dependencias

El plugin requiere DuckDB. Instala el plugin QDuckDB primero:

1. Complementos → Administrar complementos
2. Buscar "QDuckDB"
3. Instalar
```

**Ejemplo malo** (demasiado verboso):
```markdown
## Cómo Instalar las Dependencias Necesarias para el Correcto Funcionamiento

Es importante destacar que nuestro maravilloso plugin requiere...
```

### Despliegue

GitHub Pages se actualiza automáticamente al hacer push a `main`:
- Workflow: `.github/workflows/deploy-docs.yml`
- URL: https://nlebovits.github.io/censo-argentino-qgis/

## Arquitectura del Plugin

### Principios Clave

1. **Sin pandas**: Usamos métodos nativos de DuckDB (`.fetchall()`)
2. **Caché inteligente**: Metadatos en `~/.cache/qgis-censo-argentino/`
3. **Connection pool**: Una conexión DuckDB reutilizable (`DuckDBConnectionPool`)
4. **Queries dinámicas**: Construcción SQL en `query_builders.py`, no string templates

### Flujo de Datos

```
Usuario → dialog.py → query.py → DuckDB → Parquet remoto (Source.Coop)
                         ↓
                    Cache local (JSON)
```

### Decisiones de Diseño

**¿Por qué no pandas?**
- Elimina dependencia pesada
- QGIS no siempre tiene pandas instalado
- DuckDB nativo es suficiente

**¿Por qué caché?**
- Metadata.parquet es ~1MB, carga rápido
- Evita consultas repetidas
- Mejora UX (respuesta instantánea)

**¿Por qué CTE en queries?**
- Previene productos cartesianos (bug histórico)
- SQL más legible
- Mejor performance

## Convenciones de Código

### Naming

```python
# Variables y funciones: snake_case
def load_census_layer(variable_codes, geo_level):
    total_rows = len(result)

# Constantes: UPPER_CASE
MAX_COLUMNS = 100

# Clases: PascalCase
class DuckDBConnectionPool:
```

### Imports

```python
# Estándar → Terceros → Locales
import json
from pathlib import Path

import duckdb
from qgis.core import QgsVectorLayer

from .query_builders import build_pivot_columns
```

### Docstrings

```python
def get_variable_categories(variable_code, progress_callback=None):
    """Obtener categorías para una variable del caché de metadatos.

    Args:
        variable_code: Código de variable (ej: 'PERSONA_CONASI')
        progress_callback: Callback opcional para progreso

    Returns:
        Dict con 'categories' y 'has_nulls'
    """
```

## CI/CD

### Workflows

1. **Integración Continua** (`ci.yml`):
   - Ejecuta en push/PR a `main`
   - Linting con `ruff`
   - Tests en Ubuntu, macOS, Windows × Python 3.9-3.12
   - Cobertura a Codecov

2. **Publicar Release** (`release.yml`):
   - Ejecuta en tags `v*.*.*`
   - Verifica versión en `metadata.txt`
   - Publica a GitHub + QGIS repo

3. **Publicar Documentación** (`deploy-docs.yml`):
   - Ejecuta en push a `main`
   - Construye con MkDocs
   - Despliega a GitHub Pages

### Disparadores Manuales

Todos los workflows tienen `workflow_dispatch` para ejecutar desde GitHub UI:
- Actions → [workflow] → Run workflow

## Solución de Problemas Comunes

### Tests fallan localmente

```bash
# Pre-instalar extensiones de DuckDB
python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL spatial'); con.execute('INSTALL httpfs')"
```

### Plugin no carga en QGIS

1. Verificar estructura de directorios
2. Revisar logs: Ver → Paneles → Mensajes de registro
3. Comprobar `metadata.txt` tiene todos los campos requeridos

### Release falla en CI

- Verificar secrets `OSGEO_USER` y `OSGEO_PASSWORD` configurados
- Confirmar versión en `metadata.txt` coincide con tag

## Recursos

- **Repositorio**: https://github.com/nlebovits/censo-argentino-qgis
- **Documentación**: https://nlebovits.github.io/censo-argentino-qgis/
- **QGIS Plugin Repo**: https://plugins.qgis.org/plugins/censo_argentino_qgis/
- **Datos**: https://source.coop/nlebovits/censo-argentino
