# Censo Argentino QGIS Plugin

A QGIS plugin to load Argentina census data from Source.Coop. The plugin queries parquet files via DuckDB and loads results as vector layers directly in QGIS.

## Data Source

Data is loaded from: `https://data.source.coop/nlebovits/censo-argentino/2022/`

Files:
- `radios.parquet` — GeoParquet with geometries
- `census-data.parquet` — Census variables in long format
- `metadata.parquet` — Variable codes and labels

## Installation

### 1. Install the plugin

Copy this directory to your QGIS plugins folder:
- **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`

Or use a symlink:
```bash
ln -s ~/Documents/dev/censo-argentino-qgis ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis
```

### 2. Install DuckDB dependency

The plugin requires the DuckDB Python package. Install it into QGIS's Python environment:

#### Linux/macOS
```bash
# For system QGIS
pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/

# For Flatpak QGIS
pip3 install duckdb --target ~/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/
```

#### Windows
```bash
# Open OSGeo4W Shell as administrator, then:
python -m pip install duckdb
```

### 3. Enable the plugin

1. Open QGIS
2. Go to **Plugins > Manage and Install Plugins**
3. Click **Installed**
4. Find **Censo Argentino** and check the box to enable it

## Usage

1. Click the **Censo Argentino** toolbar icon or go to **Plugins > Censo Argentino**
2. Select year (currently only 2022 available)
3. Select geographic level (Census Tract, Fraction, Department, or Province)
4. (Optional) Filter by specific geographic areas by checking them in the list
5. Select entity type (Household, Person, or Dwelling)
6. Search and check one or more census variables
7. (Optional) Check "Filter by current map extent" to load only visible data
8. Click **Load Layer**

The census data will be loaded as a single polygon layer with all selected variables as attribute columns.

### Caching

Metadata (variables and geographic codes) is automatically cached in `~/.cache/qgis-censo-argentino/` after the first load. This makes subsequent dialog opens nearly instant. The cache is safe to delete - it will be rebuilt on next use.

## SQL Query Mode

For advanced users, the plugin provides direct SQL access to the census data via DuckDB.

### Available Tables

| Table | Description |
|-------|-------------|
| `radios` | Census tract geometries (COD_2022, PROV, DEPTO, FRACC, RADIO, geometry) |
| `census` | Census data in long format (id_geo, codigo_variable, conteo, valor_provincia, etiqueta_provincia, etc.) |
| `metadata` | Variable definitions (codigo_variable, etiqueta_variable, entidad) |

### Creating Map Layers from SQL

To load query results as a map layer, your query must include geometry as WKT with the column name `wkt`:

```sql
SELECT
    g.COD_2022 as geo_id,
    ST_AsText(g.geometry) as wkt,  -- Required for map layer
    c.conteo as population
FROM radios g
JOIN census c ON g.COD_2022 = c.id_geo
WHERE c.codigo_variable = 'POB_TOT_P'
```

Queries without a `wkt` column will return results to the QGIS log panel (View → Panels → Log Messages → "Censo Argentino").

### Example: Calculate a Ratio

```sql
-- Percentage of variable A relative to variable B
SELECT
    g.COD_2022 as geo_id,
    ST_AsText(g.geometry) as wkt,
    (a.conteo::float / NULLIF(b.conteo, 0)) * 100 as percentage
FROM radios g
JOIN census a ON g.COD_2022 = a.id_geo AND a.codigo_variable = 'VAR_A'
JOIN census b ON g.COD_2022 = b.id_geo AND b.codigo_variable = 'VAR_B'
```

### Example: Aggregate to Department Level

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

### Finding Variable Codes

Use the "List available variables" example query or run:

```sql
SELECT DISTINCT entidad, codigo_variable, etiqueta_variable
FROM metadata
ORDER BY entidad, codigo_variable
```

### Query Log Tab

All queries (from Browse tab and SQL tab) are automatically logged to the Query Log tab. You can:
- View the generated SQL from Browse tab selections
- Copy queries to clipboard for reuse or debugging
- Clear the log at any time

This is invaluable for learning DuckDB SQL syntax and debugging filter issues.

## Features

- **Direct access** to Source.Coop hosted census data
- **No local data download** required for actual census data
- **Automatic caching** of metadata (variables and geographic codes) for faster subsequent loads
- **Multi-variable support** - load multiple variables in a single layer
- **Geographic level selection** - Census Tract, Fraction, Department, or Province
- **Entity type filtering** - Filter by Household, Person, or Dwelling variables
- **Geographic filtering** - Optionally filter by specific provinces/departments
- **Viewport filtering** - Load only data visible in current map extent
- **Variable search** - Quick search through hundreds of census variables
- **Async loading** - Background data loading keeps UI responsive
- **Automatic geometry aggregation** for higher geographic levels
- **SQL Query Mode** - Direct DuckDB SQL access for advanced queries, ratios, and custom aggregations
- **Query Log** - View and copy generated SQL from both Browse and SQL tabs for learning and debugging

## Requirements

- QGIS 3.0 or higher
- DuckDB Python package
- Internet connection

## Development

To modify the UI:
1. Edit `dialog.ui` with Qt Designer
2. Restart QGIS to see changes

## License

MIT

## Author

Nissim Lebovits
