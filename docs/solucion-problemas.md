# Solución de Problemas

## Error: Módulo DuckDB no encontrado

**Causa**: El paquete Python `duckdb` no está instalado o no es accesible para QGIS.

**Solución**: Instalar DuckDB desde la consola Python de QGIS (funciona en Windows, Linux y macOS):

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

## Carga lenta

**Causa**: Consulta de muchos datos a nivel de radio censal.

**Soluciones**:

- Use un nivel geográfico mayor (Departamento o Provincia)
- Active el filtro por extensión del mapa
- Filtre por provincias específicas

## La capa no tiene geometría

**Causa** (modo SQL): La consulta no incluye columna `wkt`.

**Solución**: Agregue `ST_AsText(g.geometry) as wkt` a su SELECT.

## Variables no encontradas

**Causa**: El tipo de entidad no coincide con la variable buscada.

**Solución**: Cambie el tipo de entidad (Hogar, Persona, Vivienda). Las variables están asociadas a un tipo específico.

## Limpiar caché

Si los metadatos parecen desactualizados:

```bash
rm -rf ~/.cache/qgis-censo-argentino/
```

El caché se regenera automáticamente en el próximo uso.

## Ver logs detallados

**Ver → Paneles → Mensajes de registro → "Censo Argentino"**

Ahí aparecen errores detallados y resultados de consultas sin geometría.
