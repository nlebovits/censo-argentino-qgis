# Instalación

## Requisitos

- QGIS 3.0 o superior
- Conexión a Internet

## 1. Copiar el plugin

Copie la carpeta del plugin a su directorio de plugins de QGIS:

=== "Linux"
    ```bash
    ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
    ```

=== "macOS"
    ```bash
    ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
    ```

=== "Windows"
    ```
    C:\Users\<usuario>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
    ```

**Alternativa con enlace simbólico (Linux/macOS):**
```bash
ln -s /ruta/a/censo-argentino-qgis ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/censo-argentino-qgis
```

## 2. Instalar DuckDB

El plugin requiere el paquete Python `duckdb`.

=== "Linux/macOS (QGIS sistema)"
    ```bash
    pip3 install duckdb --target ~/.local/share/QGIS/QGIS3/profiles/default/python/
    ```

=== "Linux (QGIS Flatpak)"
    ```bash
    pip3 install duckdb --target ~/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/
    ```

=== "Windows"
    ```bash
    # Abra OSGeo4W Shell como administrador
    python -m pip install duckdb
    ```

## 3. Habilitar el plugin

1. Abra QGIS
2. Vaya a **Complementos → Administrar e instalar complementos**
3. Seleccione la pestaña **Instalados**
4. Marque la casilla junto a **Censo Argentino**
