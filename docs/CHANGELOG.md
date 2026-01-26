# Changelog

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
