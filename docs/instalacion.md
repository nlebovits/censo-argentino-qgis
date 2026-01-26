# Instalación

## Requisitos

- QGIS 3.0 o superior
- Conexión a Internet

## Instalación desde archivo ZIP

1. **Descargar el plugin:**

   [Descargar censo-argentino-qgis-0.3.1.zip](https://github.com/nlebovits/censo-argentino-qgis/releases/download/v0.3.1/censo-argentino-qgis-0.3.1.zip)

2. **Abrir QGIS**

3. **Ir al administrador de complementos:**

   Menú → **Complementos** → **Administrar e instalar complementos**

4. **Instalar desde ZIP:**

   - Hacer clic en la pestaña **Instalar desde ZIP**
   - Hacer clic en el botón **...** para seleccionar el archivo
   - Navegar hasta el archivo ZIP descargado
   - Seleccionarlo y hacer clic en **Abrir**
   - Hacer clic en **Instalar complemento**

5. **Confirmar la instalación:**

   Aparecerá un mensaje confirmando que el plugin se instaló correctamente.

6. **Reiniciar QGIS** (recomendado)

7. **Verificar instalación:**

   El plugin debería aparecer en el menú **Complementos** → **Censo Argentino**

## Instalar DuckDB (si es necesario)

El plugin requiere el paquete Python `duckdb`. Si al ejecutar el plugin aparece un error sobre DuckDB faltante, instalarlo manualmente:

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
    # Abrir OSGeo4W Shell como administrador
    python -m pip install duckdb
    ```

## Repositorio oficial de QGIS

El plugin estará disponible próximamente en el repositorio oficial de QGIS, donde se podrá instalar directamente desde el administrador de complementos buscando "Censo Argentino".

## Solución de problemas

### El plugin no aparece en el menú

1. Verificar que el plugin esté habilitado:
   - **Complementos** → **Administrar e instalar complementos** → pestaña **Instalados**
   - Marcar la casilla junto a **Censo Argentino**

2. Reiniciar QGIS completamente

### Error al cargar el plugin

Revisar la consola Python de QGIS para ver mensajes de error:
- **Complementos** → **Consola de Python**
- Buscar mensajes relacionados con `censo-argentino-qgis`

### Errores de DuckDB

Si aparecen errores sobre DuckDB, seguir los pasos de instalación de DuckDB en la sección anterior.
