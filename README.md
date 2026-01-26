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
3. Select a census variable from the dropdown
4. Click **Load Layer**

The census data will be loaded as a polygon layer with the selected variable joined to census tracts (radios).

## Features

- Direct access to Source.Coop hosted census data
- No local data download required
- Automatic geometry and attribute joining
- Simple variable selection interface

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
