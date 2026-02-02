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

## Rendimiento y Tiempos de Carga

### "Los metadatos tardan en cargar" / "Los campos se pueblan lentamente"

**Esto es normal la primera vez** que usas el plugin o cambias de año censal. Aquí está lo que sucede:

#### Primera carga (5-15 segundos)
El plugin debe descargar metadatos del censo desde Source.Coop:
- `metadata.parquet` (~1 MB) - Diccionario de variables y categorías
- `radios.parquet` (headers) - Lista de códigos geográficos
- `census-data.parquet` (metadata) - Estructura de datos

Verás mensajes como:
- "Cargando metadatos del censo 2022..."
- "Cargando códigos de PROV..."
- "Variables cargadas"

#### Cargas subsecuentes (instantáneas)
El plugin **cachea todos los metadatos localmente** en `~/.cache/qgis-censo-argentino/`:
- ✅ Variables y categorías: **instantáneo** (desde caché)
- ✅ Códigos geográficos: **instantáneo** (desde caché)
- ✅ Tipos de entidad: **instantáneo** (desde caché)

#### Carga de datos censales (30-60 segundos)
Cuando haces clic en "Cargar Capa":
- El plugin consulta archivos Parquet remotos (100-500 MB de geometrías + datos)
- **El 80-90% del tiempo es descarga de red**, no procesamiento
- Esto es inevitable - los datos son remotos y grandes

**Tiempos típicos por nivel geográfico:**
- **PROV** (24 provincias): 5-10 segundos
- **DEPTO** (~500 departamentos): 15-25 segundos
- **FRACC** (~5,000 fracciones): 30-45 segundos
- **RADIO** (~50,000 radios): 45-90 segundos

### ¿Por qué es lento?

**No es el plugin - es física de red:**

1. **Descarga de Parquet** (80-90% del tiempo)
   - Geometrías de radios censales: 100-500 MB según nivel
   - Datos censales: 2-5 GB (DuckDB descarga solo lo necesario)
   - Limitado por tu velocidad de Internet

2. **Procesamiento DuckDB** (5-10% del tiempo)
   - Joins y pivots de categorías
   - Ya optimizado con CTEs y connection pooling

3. **Creación de capa QGIS** (2-3% del tiempo)
   - Parsing de geometrías WKT
   - Creación de features con atributos

### Cómo mejorar el rendimiento

✅ **Primera vez:** Sé paciente - el caché se construye automáticamente

✅ **Consultas grandes:** Usa filtros geográficos para reducir datos:
- Selecciona solo provincias/departamentos necesarios
- Limita el número de variables (cada una agrega columnas)

✅ **Buen Internet:** Conexión rápida = consultas rápidas (la mayoría del tiempo es I/O de red)

❌ **No es tu computadora:** Más RAM o CPU no ayuda mucho - el bottleneck es red

### Verificar que el caché funciona

1. **Primera carga:** Espera 5-15 segundos para que se pueblen los campos
2. **Cierra y reabre el plugin**
3. **Segunda carga:** Debe ser **instantánea** (<1 segundo)

Si la segunda carga no es instantánea:
- Verifica que existe `~/.cache/qgis-censo-argentino/`
- Revisa los logs (Ver → Paneles → Mensajes de registro)
- El caché puede estar corrupto - [límpialo](#limpiar-caché)

### Mensaje de caché

Cuando el plugin usa caché, verás:

> ℹ️ **Usando datos cacheados.** Los metadatos se cargan instantáneamente desde caché local. Si necesitas actualizar, limpia el caché manualmente.

Si ves este mensaje y aún es lento, el problema está en la **descarga de datos censales** (paso normal, no hay bug).

## Ver logs detallados

**Ver → Paneles → Mensajes de registro → "Censo Argentino"**

Ahí aparecen errores detallados y resultados de consultas sin geometría.
