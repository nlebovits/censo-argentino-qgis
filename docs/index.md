# Censo Argentino

Plugin de QGIS para explorar datos del censo argentino directamente desde la nube.

## ¿Qué hace?

Consulta datos del [Censo Nacional 2022](https://source.coop/nlebovits/censo-argentino) alojados en Source.Coop y los carga como capas vectoriales en QGIS. No requiere descargar archivos — los datos se consultan remotamente mediante DuckDB.

## Características

- **Exploración visual**: Seleccione variables del censo desde una interfaz gráfica
- **Consultas SQL**: Acceso directo a DuckDB para análisis avanzados
- **Filtros geográficos**: Por provincia, departamento, o extensión del mapa
- **Sin descargas**: Los datos se consultan directamente desde Source.Coop
- **Caché local**: Los metadatos se guardan para cargas más rápidas

## Inicio rápido

1. [Instale el plugin](instalacion.md)
2. Abra **Complementos → Censo Argentino**
3. Seleccione una variable y haga clic en **Cargar Capa**

!!! info "Primera vez"
    La primera vez que abras el plugin tardará 5-15 segundos en cargar metadatos. Estos se cachean localmente y en usos posteriores todo carga instantáneamente. [Más info sobre rendimiento →](solucion-problemas.md#rendimiento-y-tiempos-de-carga)

## Fuente de datos

Los datos provienen del [INDEC](https://www.indec.gob.ar/) (Instituto Nacional de Estadística y Censos) y están disponibles bajo licencia CC-BY-4.0.

- [Dataset en Source.Coop](https://source.coop/nlebovits/censo-argentino)
- [Documentación del dataset](https://data.source.coop/nlebovits/censo-argentino/README.md)
