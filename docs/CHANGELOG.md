# Changelog

## [0.6.0] - 2025-02-02

### Agregado
- **Soporte para Censo 2010**: Plugin ahora accede a datos del Censo Nacional 2010 además del 2022
- **Selector de año censal**: Dropdown en la interfaz para elegir entre Censo 2010 y 2022
- **Configuración centralizada**: Nueva arquitectura en `config.py` con URLs y parámetros por año
- **Tests de configuración**: Suite de 84 tests para validar configuración de censos
- **Documentación mejorada**: Secciones actualizadas sobre caché y rendimiento con datos reales

### Mejorado
- **Rendimiento de caché**: Documentación detallada sobre tiempos (~50ms) y tamaños (~1.3MB)
- **Tolerancia de columnas**: Sistema de advertencia confirmable para >100 columnas
- **Diálogos informativos**: Mejor UX con confirmación visual antes de cargas grandes

### Técnico
- Refactor de query builders para soporte multi-censo
- Sistema de configuración CENSUS_CONFIG extensible
- Tests de integración ampliados (77 → 159 tests)

## [0.5.0] - 2025-01-27

### Cambiado
- **Límite de columnas ahora es advertencia confirmable**: Eliminado límite duro de 100 columnas
- **Diálogo de confirmación**: Cuando se cargan >100 columnas, se pregunta al usuario si desea continuar
- **Mejor UX**: Usuario decide si proceder con cargas grandes en lugar de bloqueo automático

### Agregado
- Función `calculate_column_count()` para calcular columnas antes de cargar

### Eliminado
- Límite duro de 100 columnas que bloqueaba cargas
- Advertencia automática a 50 columnas

## [0.4.2] - 2025-01-27

### Corregido
- **Estructura de directorios del plugin**: Reestructurado a subdirectorio `censo_argentino_qgis/` para compatibilidad con qgis-plugin-ci
- **Publicación automática**: Resuelve error de generación de archivos ZIP con nombres inválidos (ej. `..0.4.1.zip`)
- **Imports relativos**: Actualizados todos los imports en tests para usar el nuevo namespace `censo_argentino_qgis.*`

### Mejorado
- **Documentación de desarrollo**: CLAUDE.md ahora incluye instrucciones específicas para ejecutar tests y pre-commit hooks
- **Configuración CI/CD**: `.qgis-plugin-ci` actualizado con `plugin_path` correcto

### Técnico
- Estructura de plugin conforme a estándares de QGIS
- 77 tests pasando tras reestructuración
- Mock paths actualizados en suite de tests

## [0.4.1] - 2025-01-27

### Corregido
- **Dependencia pandas eliminada**: Reemplazado `.df()` por `.fetchall()` en DuckDB para evitar error "'pandas' is required"
- **Compatibilidad Ubuntu**: Plugin ahora funciona sin pandas instalado en QGIS

### Mejorado
- **Documentación de instalación**: Recomienda instalar QDuckDB plugin primero para evitar problemas con pip
- **Solución de problemas**: Sección expandida con troubleshooting para dependencias

## [0.4.0] - 2025-01-27

### Agregado
- **Expansión de categorías**: Variables categóricas ahora se expanden en columnas separadas (ej. `educacion_primaria`, `educacion_secundaria`)
- **UI de selección de categorías**: Secciones colapsables por variable con checkboxes para filtrar categorías específicas
- **Columnas _total automáticas**: Cada variable genera una columna de total además de las categorías individuales
- **Precarga de metadatos**: Todos los metadatos (~1MB) se cargan al iniciar para lookups instantáneos
- **Botones de ayuda**: Links directos a Documentación y Solución de Problemas en la UI
- **Tooltips completos**: Todos los elementos de UI tienen tooltips explicativos
- **Tests de integración**: 17 nuevos tests para expansión de categorías y corrección de producto cartesiano

### Corregido
- **Bug crítico de producto cartesiano**: JOIN entre geometría y censo antes de filtrar causaba totales inflados incorrectamente
- **Implementación CTE-based**: Pivotea datos ANTES de hacer JOIN, garantizando relación 1:1 y totales correctos

### Mejorado
- **Rendimiento de categorías**: Lookups instantáneos vs ~1s por variable anteriormente
- **Validación de columnas**: Advertencia en 50 columnas, bloqueo en 100 para evitar crashes de QGIS
- **Nombres de columnas**: Sanitización completa (sin acentos, minúsculas, formato consistente)
- **Documentación DuckDB**: Método universal de instalación que funciona en Windows/Linux/macOS
- **Código 100% español**: Todas las docstrings, mensajes de error y logs traducidos

### Técnico
- Extracción de `query_builders.py` para testabilidad
- Manejo de categorías NULL
- Soporte para categorías de texto (no solo numéricas)
- Caché consistente con formato de tuplas

## [0.3.0] - 2025-01-26

### Agregado
- Suite de tests con pytest (48 tests, 38% cobertura)
- Validación de marcadores de posición en SQL
- Botones "Seleccionar Todo" / "Limpiar Selección" para variables
- Vista de tabla para resultados SQL sin geometría
- Debounce de búsqueda (200ms) para reducir lag

### Mejorado
- Pool de conexiones DuckDB (singleton) para mejor rendimiento (~150ms por consulta)
- Carga de extensiones una sola vez (~75ms ahorrados)
- Eliminado LIMIT 100 en filtros geográficos
- Traducción completa al español (UI, mensajes, documentación)
- README consolidado con enlaces a documentación
- Documentación desplegada automáticamente a GitHub Pages

### Técnico
- Módulo `validation.py` extraído para SQL placeholder detection
- Módulo `query_builders.py` extraído con funciones testeables
- Configuración de pytest con cobertura
- GitHub Actions para despliegue de documentación

## [0.2.0] - 2025-01-26

### Agregado
- Modo de consulta SQL con acceso directo a DuckDB
- Pestaña de registro de consultas
- Ejemplos de consultas SQL predefinidos
- Logging de consultas para depuración

### Mejorado
- Barra de progreso más granular durante la carga

## [0.1.0] - 2025-01-26

### Agregado
- Interfaz de exploración visual de variables
- Soporte para múltiples variables en una capa
- Filtrado por provincia y departamento
- Filtrado por extensión del mapa
- Caché local de metadatos
- Carga asíncrona de datos
- Agregación automática de geometrías por nivel geográfico
