# Solución de Problemas

## El plugin no aparece en QGIS

**Causa**: DuckDB no está instalado o está en la ubicación incorrecta.

**Solución**: Verifique la instalación de DuckDB:

1. Abra la consola Python de QGIS (**Complementos → Consola Python**)
2. Ejecute: `import duckdb`
3. Si falla, reinstale siguiendo las [instrucciones de instalación](instalacion.md)

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
