# Plugin de Censo Argentino para QGIS

Un plugin de QGIS para cargar datos del censo argentino desde Source.Coop. El plugin consulta archivos parquet mediante DuckDB y carga resultados como capas vectoriales directamente en QGIS.

## Fuente de Datos

Los datos se cargan desde: `https://data.source.coop/nlebovits/censo-argentino/2022/`

Archivos:
- `radios.parquet` — GeoParquet con geometrías
- `census-data.parquet` — Variables del censo en formato largo
- `metadata.parquet` — Códigos y etiquetas de variables

## Instalación

### 1. Instalar el plugin

Copie este directorio a su carpeta de plugins de QGIS:
- **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- **Windows**: `C:\Users\<usuario>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`

O use un enlace simbólico:
```bash
ln -s ~/Documents/dev/censo-argentino-qgis ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis
```

### 2. Instalar la dependencia DuckDB

El plugin requiere el paquete Python de DuckDB. Instálelo en el entorno Python de QGIS:

#### Linux/macOS
```bash
# Para QGIS del sistema
pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/

# Para QGIS Flatpak
pip3 install duckdb --target ~/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/
```

#### Windows
```bash
# Abra OSGeo4W Shell como administrador, luego:
python -m pip install duckdb
```

### 3. Habilitar el plugin

1. Abra QGIS
2. Vaya a **Complementos > Administrar e instalar complementos**
3. Haga clic en **Instalados**
4. Encuentre **Censo Argentino** y marque la casilla para habilitarlo

## Uso

1. Haga clic en el ícono de **Censo Argentino** en la barra de herramientas o vaya a **Complementos > Censo Argentino**
2. Seleccione el año (actualmente solo está disponible 2022)
3. Seleccione el nivel geográfico (Radio Censal, Fracción, Departamento o Provincia)
4. (Opcional) Filtre por áreas geográficas específicas marcándolas en la lista
5. Seleccione el tipo de entidad (Hogar, Persona o Vivienda)
6. Busque y marque una o más variables del censo
7. (Opcional) Marque "Filtrar por extensión actual del mapa" para cargar solo datos visibles
8. Haga clic en **Cargar Capa**

Los datos del censo se cargarán como una única capa de polígonos con todas las variables seleccionadas como columnas de atributos.

### Caché

Los metadatos (variables y códigos geográficos) se almacenan automáticamente en caché en `~/.cache/qgis-censo-argentino/` después de la primera carga. Esto hace que las aperturas posteriores del diálogo sean casi instantáneas. Es seguro eliminar el caché: se reconstruirá en el próximo uso.

## Modo de Consulta SQL

Para usuarios avanzados, el plugin proporciona acceso SQL directo a los datos del censo mediante DuckDB.

### Tablas Disponibles

| Tabla | Descripción |
|-------|-------------|
| `radios` | Geometrías de radios censales (COD_2022, PROV, DEPTO, FRACC, RADIO, geometry) |
| `census` | Datos del censo en formato largo (id_geo, codigo_variable, conteo, valor_provincia, etiqueta_provincia, etc.) |
| `metadata` | Definiciones de variables (codigo_variable, etiqueta_variable, entidad) |

### Crear Capas de Mapa desde SQL

Para cargar resultados de consultas como capa de mapa, su consulta debe incluir la geometría como WKT con el nombre de columna `wkt`:

```sql
SELECT
    g.COD_2022 as geo_id,
    ST_AsText(g.geometry) as wkt,  -- Requerido para capa de mapa
    c.conteo as poblacion
FROM radios g
JOIN census c ON g.COD_2022 = c.id_geo
WHERE c.codigo_variable = 'POB_TOT_P'
```

Las consultas sin una columna `wkt` devolverán resultados al panel de registro de QGIS (Ver → Paneles → Mensajes de registro → "Censo Argentino").

### Ejemplo: Calcular un Ratio

```sql
-- Porcentaje de variable A relativo a variable B
SELECT
    g.COD_2022 as geo_id,
    ST_AsText(g.geometry) as wkt,
    (a.conteo::float / NULLIF(b.conteo, 0)) * 100 as porcentaje
FROM radios g
JOIN census a ON g.COD_2022 = a.id_geo AND a.codigo_variable = 'VAR_A'
JOIN census b ON g.COD_2022 = b.id_geo AND b.codigo_variable = 'VAR_B'
```

### Ejemplo: Agregar a Nivel Departamental

```sql
SELECT
    c.valor_provincia || '-' || c.valor_departamento as geo_id,
    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
    SUM(c.conteo) as total
FROM radios g
JOIN census c ON g.COD_2022 = c.id_geo
WHERE c.codigo_variable = 'POB_TOT_P'
GROUP BY c.valor_provincia, c.valor_departamento
```

### Encontrar Códigos de Variables

Use la consulta de ejemplo "Listar variables disponibles" o ejecute:

```sql
SELECT DISTINCT entidad, codigo_variable, etiqueta_variable
FROM metadata
ORDER BY entidad, codigo_variable
```

### Pestaña de Registro de Consultas

Todas las consultas (de las pestañas Explorar y SQL) se registran automáticamente en la pestaña Registro de Consultas. Puede:
- Ver el SQL generado desde las selecciones de la pestaña Explorar
- Copiar consultas al portapapeles para reutilizarlas o depurarlas
- Borrar el registro en cualquier momento

Esto es invaluable para aprender la sintaxis SQL de DuckDB y depurar problemas de filtros.

## Características

- **Acceso directo** a datos del censo alojados en Source.Coop
- **No se requiere descarga local** de datos del censo
- **Caché automático** de metadatos (variables y códigos geográficos) para cargas posteriores más rápidas
- **Soporte multi-variable** - cargue múltiples variables en una sola capa
- **Selección de nivel geográfico** - Radio Censal, Fracción, Departamento o Provincia
- **Filtrado por tipo de entidad** - Filtre por variables de Hogar, Persona o Vivienda
- **Filtrado geográfico** - Opcionalmente filtre por provincias/departamentos específicos
- **Filtrado por ventana** - Cargue solo datos visibles en la extensión actual del mapa
- **Búsqueda de variables** - Búsqueda rápida entre cientos de variables del censo
- **Carga asíncrona** - La carga de datos en segundo plano mantiene la interfaz receptiva
- **Agregación automática de geometría** para niveles geográficos superiores
- **Modo de Consulta SQL** - Acceso SQL directo de DuckDB para consultas avanzadas, ratios y agregaciones personalizadas
- **Registro de Consultas** - Vea y copie SQL generado desde las pestañas Explorar y SQL para aprender y depurar

## Requisitos

- QGIS 3.0 o superior
- Paquete Python de DuckDB
- Conexión a Internet

## Desarrollo

Para modificar la interfaz:
1. Edite `dialog.ui` con Qt Designer
2. Reinicie QGIS para ver los cambios

## Licencia

MIT

## Autor

Nissim Lebovits
