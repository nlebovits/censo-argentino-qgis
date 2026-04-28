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

## Requisito: Python 3.10 o superior

**Causa**: DuckDB >= 1.5.0 requiere Python 3.10 o superior. Si usa QGIS con Python 3.9, no podrá instalar la versión requerida de DuckDB.

**Solución**: Actualice a una versión de QGIS que incluya Python 3.10+. Las versiones recientes de QGIS (3.28+) generalmente incluyen Python 3.10 o superior.

Para verificar su versión de Python en QGIS:
1. Abra **Complementos → Consola de Python**
2. Ejecute: `import sys; print(sys.version)`

## Error: GeoParquet version 2.0.0 is not supported

**Causa**: Su versión de DuckDB es demasiado antigua. Los datos del censo usan GeoParquet 2.0, que requiere DuckDB >= 1.5.0.

**Solución**: Actualizar DuckDB desde la consola Python de QGIS:

1. Abra **Complementos → Consola de Python**
2. Pegue este código:

```python
import subprocess
import sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'duckdb'])
```

3. Presione Enter y espere a que termine
4. **Reinicie QGIS completamente**

Para verificar la versión instalada:
```python
import duckdb
print(duckdb.__version__)  # Debe ser >= 1.5.0
```

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
