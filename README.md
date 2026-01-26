# Plugin de Censo Argentino para QGIS

Plugin de QGIS para cargar datos del censo argentino desde Source.Coop. Consulta archivos parquet mediante DuckDB y carga resultados como capas vectoriales directamente en QGIS.

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://nlebovits.github.io/censo-argentino-qgis/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Características

- 🗺️ **Acceso directo** a datos del censo alojados en Source.Coop
- 🚀 **Sin descargas** - consulta datos remotamente con DuckDB
- 🔍 **Interfaz visual** para explorar variables del censo
- 💾 **Caché automático** de metadatos para cargas rápidas
- 🎯 **Filtros geográficos** por provincia, departamento o extensión del mapa
- 🔧 **Modo SQL** para consultas avanzadas y análisis personalizados

## Instalación Rápida

### 1. Instalar el plugin

Copie este directorio a su carpeta de plugins de QGIS:

```bash
# Linux
ln -s ~/ruta/censo-argentino-qgis ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis

# macOS
ln -s ~/ruta/censo-argentino-qgis ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis
```

### 2. Instalar DuckDB

```bash
# Linux/macOS
pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/

# Windows (OSGeo4W Shell como administrador)
python -m pip install duckdb
```

### 3. Habilitar en QGIS

**Complementos > Administrar e instalar complementos > Instalados** → Marcar "Censo Argentino"

## Uso Básico

1. Abrir **Complementos > Censo Argentino**
2. Seleccionar año (2022), nivel geográfico y tipo de entidad
3. Marcar variables del censo
4. Hacer clic en **Cargar Capa**

## Documentación Completa

📚 **[Documentación completa](https://nlebovits.github.io/censo-argentino-qgis/)** - Guías detalladas, ejemplos SQL y solución de problemas

- [Guía de Instalación](https://nlebovits.github.io/censo-argentino-qgis/instalacion/)
- [Inicio Rápido](https://nlebovits.github.io/censo-argentino-qgis/inicio-rapido/)
- [Modo SQL](https://nlebovits.github.io/censo-argentino-qgis/sql/)
- [Ejemplos](https://nlebovits.github.io/censo-argentino-qgis/examples/basico/)

## Fuente de Datos

Datos del [Censo Nacional 2022](https://source.coop/nlebovits/censo-argentino) del INDEC, disponibles en Source.Coop bajo licencia CC-BY-4.0.

## Desarrollo

### Documentación

```bash
# Instalar MkDocs como herramienta uv
uv tool install mkdocs --with mkdocs-material --with pymdown-extensions

# Servidor de desarrollo
uv tool run mkdocs serve

# Construir sitio
uv tool run mkdocs build
```

Consulte [DOCS.md](DOCS.md) para más detalles.

## Licencia

Apache 2.0 - Consulte [LICENSE](LICENSE) para más detalles.

## Autor

Nissim Lebovits - [nlebovits@pm.me](mailto:nlebovits@pm.me)

## Contribuir

¡Las contribuciones son bienvenidas! Consulte la [guía de contribución](https://nlebovits.github.io/censo-argentino-qgis/contribuir/) para comenzar.
