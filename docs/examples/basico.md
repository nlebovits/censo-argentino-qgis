# Ejemplos Básicos

## Población total por radio censal

1. Abra el plugin
2. Seleccione **Tipo de entidad**: Persona
3. Busque "POB_TOT" y marque la variable
4. Haga clic en **Cargar Capa**

## Comparar dos provincias

1. Seleccione **Nivel geográfico**: Provincia
2. En filtros geográficos, marque las provincias a comparar
3. Seleccione una variable y cargue

## Análisis de un área específica

1. Haga zoom en QGIS al área de interés
2. Abra el plugin
3. Active "Filtrar por extensión actual del mapa"
4. Seleccione variables y cargue

Solo se descargan los radios visibles.

## Múltiples variables

1. Marque varias variables de la lista
2. Cargue la capa

Cada variable aparece como columna en la tabla de atributos.

## Ratio con SQL

Para calcular porcentajes entre dos variables:

```sql
SELECT
    g.COD_2022 as geo_id,
    ST_AsText(g.geometry) as wkt,
    (a.conteo::float / NULLIF(b.conteo, 0)) * 100 as ratio
FROM radios g
JOIN census a ON g.COD_2022 = a.id_geo AND a.codigo_variable = 'VARIABLE_NUMERADOR'
JOIN census b ON g.COD_2022 = b.id_geo AND b.codigo_variable = 'VARIABLE_DENOMINADOR'
```

Reemplace `VARIABLE_NUMERADOR` y `VARIABLE_DENOMINADOR` con códigos reales del censo.
