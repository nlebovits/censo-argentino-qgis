# Contribuir

## Reportar problemas

Abra un issue en [GitHub](https://github.com/nlebovits/censo-argentino-qgis/issues) con:

- Versión de QGIS
- Sistema operativo
- Pasos para reproducir el problema
- Mensaje de error (si aplica)

## Desarrollo local

1. Clone el repositorio
2. Cree un enlace simbólico a su carpeta de plugins de QGIS
3. Instale DuckDB en el entorno Python de QGIS

### Modificar la interfaz

1. Edite `dialog.ui` con Qt Designer
2. Reinicie QGIS para ver los cambios

### Estructura del código

```
censo-argentino-qgis/
├── __init__.py      # Inicialización del plugin
├── plugin.py        # Clase principal del plugin
├── dialog.py        # Lógica del diálogo
├── dialog.ui        # Interfaz Qt
├── query.py         # Consultas DuckDB
└── metadata.txt     # Metadatos del plugin
```

## Pull requests

1. Fork el repositorio
2. Cree una rama para su cambio
3. Envíe un PR con descripción clara del cambio

## Licencia

Las contribuciones se publican bajo [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).
