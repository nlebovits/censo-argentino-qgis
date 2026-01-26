# Desarrollo

Guía para desarrolladores que desean modificar, probar o contribuir al plugin.

## Arquitectura del Plugin

### Estructura de Archivos

```
censo-argentino-qgis/
├── __init__.py           # Punto de entrada QGIS
├── plugin.py             # Ciclo de vida del plugin
├── dialog.py             # Interfaz de usuario (Qt)
├── dialog.ui             # Diseño de UI (Qt Designer)
├── query.py              # Lógica de consultas DuckDB
├── query_builders.py     # Construcción de queries SQL
├── validation.py         # Validación de SQL
├── metadata.txt          # Metadatos del plugin QGIS
└── tests/                # Suite de tests
```

### Componentes Principales

**query.py** - Núcleo de acceso a datos
- Pool de conexiones DuckDB (singleton)
- Consultas a archivos Parquet remotos vía httpfs
- Caché de metadatos local
- Transformación de DataFrames a capas QGIS

**dialog.py** - Interfaz de usuario
- Pestaña Explorar: selección visual de variables
- Pestaña SQL: consultas personalizadas
- Pestaña Registro: historial de consultas
- Carga asíncrona con progreso

**query_builders.py** - Construcción de queries
- Filtros geográficos (PROV, DEPTO, FRACC, RADIO)
- Filtros espaciales (bounding box)
- Generación de columnas pivot

**validation.py** - Seguridad SQL
- Detección de placeholders (VAR_A, NOMBRE_PROVINCIA)
- Prevención de inyección SQL

## Configuración de Desarrollo

### Requisitos

- Python 3.9+
- QGIS 3.0+
- uv (gestor de paquetes)

### Instalación para Desarrollo

```bash
# Clonar repositorio
git clone https://github.com/nlebovits/censo-argentino-qgis.git
cd censo-argentino-qgis

# Enlazar al directorio de plugins QGIS
# Linux
ln -s $(pwd) ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis

# macOS
ln -s $(pwd) ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis

# Instalar DuckDB en Python de QGIS
pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/
```

### Modificar el Plugin

1. **Hacer cambios** en los archivos Python
2. **Recargar el plugin** en QGIS:
   - Usar Plugin Reloader (recomendado)
   - O reiniciar QGIS
3. **Probar cambios** manualmente en QGIS
4. **Ejecutar tests** (ver abajo)

## Tests

### Ejecutar Tests

```bash
# Instalar dependencias de test
uv pip install -e ".[test]"

# Ejecutar todos los tests
uv run pytest

# Ejecutar con cobertura
uv run pytest --cov

# Ejecutar tests específicos
uv run pytest tests/test_cache.py
uv run pytest tests/test_validation.py -v

# Ver reporte de cobertura HTML
open htmlcov/index.html
```

### Suite de Tests

**48 tests** distribuidos en:

- `test_cache.py` (11 tests) - Operaciones de caché
- `test_validation.py` (11 tests) - Validación SQL
- `test_query_builders.py` (26 tests) - Construcción de queries

**Cobertura**: 38% general, 100% en módulos críticos

### Escribir Nuevos Tests

Los tests usan pytest con mocks de QGIS:

```python
# tests/conftest.py proporciona fixtures
def test_mi_funcion(temp_cache_dir):
    # temp_cache_dir es un directorio temporal
    result = mi_funcion(temp_cache_dir)
    assert result == expected
```

## Documentación

### Servidor de Desarrollo

```bash
# Instalar MkDocs
uv tool install mkdocs --with mkdocs-material --with pymdown-extensions

# Iniciar servidor (http://127.0.0.1:8000)
uv tool run mkdocs serve

# Construir sitio estático
uv tool run mkdocs build
```

### Estructura de Documentación

```
docs/
├── index.md           # Página principal
├── instalacion.md     # Guía de instalación
├── inicio-rapido.md   # Tutorial rápido
├── guia-usuario.md    # Guía completa
├── sql.md             # Modo SQL
├── desarrollo.md      # Esta página
├── contribuir.md      # Guía de contribución
└── CHANGELOG.md       # Historial de versiones
```

La documentación se despliega automáticamente a GitHub Pages en cada push a `main`.

## Proceso de Release

### 1. Actualizar Changelog

Editar `docs/CHANGELOG.md`:

```markdown
## [0.4.0] - 2025-01-27

### Agregado
- Nueva funcionalidad

### Mejorado
- Mejoras existentes
```

### 2. Incrementar Versión

```bash
# Versión específica
python3 scripts/bump_version.py 0.4.0

# O usar atajos semánticos
python3 scripts/bump_version.py --patch  # 0.3.0 -> 0.3.1
python3 scripts/bump_version.py --minor  # 0.3.0 -> 0.4.0
python3 scripts/bump_version.py --major  # 0.3.0 -> 1.0.0
```

Esto actualiza automáticamente:
- `metadata.txt`
- `pyproject.toml`
- `docs/CHANGELOG.md`

### 3. Commit y Tag

```bash
git add -A
git commit -m "Bump version to 0.4.0"
git tag v0.4.0
git push && git push --tags
```

### 4. Release Automático

El workflow de GitHub Actions (`.github/workflows/release.yml`) automáticamente:

1. Verifica consistencia de versiones
2. Extrae notas del changelog
3. Crea ZIP del plugin
4. Publica GitHub Release con el artefacto

Ver [RELEASING.md](../RELEASING.md) para más detalles.

## Convenciones de Código

### Estilo Python

- PEP 8 para estilo general
- Nombres descriptivos en español cuando sea apropiado
- Docstrings para funciones públicas
- Type hints opcionales pero bienvenidos

### Mensajes de Commit

```bash
# Formato
Acción breve en imperativo

Descripción detallada de cambios si es necesario.

- Bullet points para cambios múltiples
- Referencias a issues: #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Tests

- Un archivo de test por módulo
- Nombres descriptivos: `test_funcion_hace_algo()`
- Arrange-Act-Assert pattern
- Fixtures en `conftest.py`

## Arquitectura de Datos

### Fuente de Datos

Los datos provienen de [Source.Coop](https://source.coop/nlebovits/censo-argentino):

```
/nlebovits/censo-argentino/
├── geometrias/
│   ├── 2022/
│   │   ├── radios.parquet
│   │   ├── fracciones.parquet
│   │   ├── departamentos.parquet
│   │   └── provincias.parquet
└── datos/
    └── 2022/
        ├── censo_hogar.parquet
        ├── censo_persona.parquet
        ├── censo_vivienda.parquet
        └── metadata.parquet
```

### Flujo de Consultas

1. **Usuario selecciona variables** → dialog.py
2. **Construir query SQL** → query_builders.py
3. **Ejecutar en DuckDB** → query.py
4. **Transformar DataFrame** → query.py
5. **Crear capa QGIS** → query.py
6. **Agregar al proyecto** → dialog.py

### Caché

Metadatos se cachean en `~/.cache/qgis-censo-argentino/`:

- `entity_types.json` - Tipos de entidad
- `variables_*.json` - Variables por tipo
- `geo_codes_*.json` - Códigos geográficos

El caché se invalida al cambiar de año o nivel geográfico.

## Troubleshooting

### Plugin no aparece en QGIS

```bash
# Verificar enlace simbólico
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Verificar metadata.txt
cat metadata.txt
```

### Cambios no se reflejan

1. Usar Plugin Reloader
2. O reiniciar QGIS completamente
3. Verificar consola Python de QGIS para errores

### Tests fallan

```bash
# Reinstalar dependencias
uv pip install -e ".[test]" --force-reinstall

# Limpiar caché de pytest
rm -rf .pytest_cache

# Ejecutar con verbose
uv run pytest -vv
```

### DuckDB no funciona

```bash
# Verificar instalación
python3 -c "import duckdb; print(duckdb.__version__)"

# Reinstalar en directorio QGIS
pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/ --upgrade
```

## Recursos

- [Documentación de QGIS Plugin Development](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/)
- [DuckDB Python API](https://duckdb.org/docs/api/python/overview)
- [PyQt5 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [Source.Coop Data Browser](https://source.coop/nlebovits/censo-argentino)

## Obtener Ayuda

- **Issues**: [GitHub Issues](https://github.com/nlebovits/censo-argentino-qgis/issues)
- **Email**: [nlebovits@pm.me](mailto:nlebovits@pm.me)
- **Documentación**: [https://nlebovits.github.io/censo-argentino-qgis/](https://nlebovits.github.io/censo-argentino-qgis/)
