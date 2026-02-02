# Solución de Problemas

## Error: Módulo DuckDB no encontrado

**Causa**: El paquete Python `duckdb` no está instalado o no es accesible para QGIS.

**Solución recomendada**: Instalar el plugin [QDuckDB](https://plugins.qgis.org/plugins/qduckdb/) desde el repositorio oficial de QGIS y activarlo. Esto instala DuckDB automáticamente y evita problemas con pip.

**Solución alternativa**: Instalar DuckDB manualmente desde la consola Python de QGIS (funciona en Windows, Linux y macOS):

1. En QGIS, abra la consola de Python: **Complementos → Consola de Python**
2. Pegue este código:

```python
import subprocess
import sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'duckdb'])
```

3. Presione Enter y espere a que termine la instalación
4. Reinicie QGIS

Si el error persiste, verifique que DuckDB se instaló correctamente:

1. Abra nuevamente la consola Python de QGIS
2. Ejecute: `import duckdb`
3. Si no aparece error, la instalación fue exitosa

## Error de conexión

**Causa**: Sin acceso a Internet o Source.Coop no disponible.

**Solución**: Verifique su conexión. Los datos se consultan remotamente desde `data.source.coop`.

## Limpiar caché

Si los metadatos parecen desactualizados:

```bash
rm -rf ~/.cache/qgis-censo-argentino/
```

El caché se regenera automáticamente en el próximo uso.

## Carga lenta la primera vez

La primera vez que cargues un campo, tiene que descargarse y cachearse localmente. Esto toma aproximadamente un minuto o menos. Después de eso, debería cargar casi instantáneamente.

## Ver logs detallados

**Ver → Paneles → Mensajes de registro → "Censo Argentino"**

Ahí aparecen errores detallados y resultados de consultas sin geometría.
