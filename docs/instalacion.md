# Instalación

## Requisitos

- QGIS 3.0 o superior
- Conexión a Internet

## Instalación desde el repositorio oficial de QGIS (Recomendado)

El plugin está disponible en el repositorio oficial de QGIS.

1. **Abrir QGIS**

2. **Ir al administrador de complementos:**

   Menú → **Complementos** → **Administrar e instalar complementos**

3. **Buscar el plugin:**

   - En la pestaña **Todos**, escribir "Censo Argentino" en el buscador
   - El plugin debería aparecer en los resultados

4. **Instalar:**

   - Seleccionar "Censo Argentino"
   - Hacer clic en **Instalar complemento**
   - Esperar a que se complete la instalación

5. **Verificar instalación:**

   El plugin debería aparecer en el menú **Complementos** → **Censo Argentino**

**Página oficial del plugin:** [https://plugins.qgis.org/plugins/censo_argentino_qgis/](https://plugins.qgis.org/plugins/censo_argentino_qgis/)

## Instalación manual desde archivo ZIP

Si necesitas instalar una versión específica o el repositorio oficial no está disponible:

1. **Descargar el plugin:**

   Ir a [Releases](https://github.com/nlebovits/censo-argentino-qgis/releases) y descargar el archivo ZIP de la versión deseada

2. **Abrir QGIS**

3. **Ir al administrador de complementos:**

   Menú → **Complementos** → **Administrar e instalar complementos**

4. **Instalar desde ZIP:**

   - Hacer clic en la pestaña **Instalar desde ZIP**
   - Hacer clic en el botón **...** para seleccionar el archivo
   - Navegar hasta el archivo ZIP descargado
   - Seleccionarlo y hacer clic en **Abrir**
   - Hacer clic en **Instalar complemento**

5. **Reiniciar QGIS** (recomendado)

6. **Verificar instalación:**

   El plugin debería aparecer en el menú **Complementos** → **Censo Argentino**

## Instalar dependencias (si es necesario)

El plugin requiere el paquete Python `duckdb`.

**Recomendación:** Antes de instalar Censo Argentino, instale primero el plugin [QDuckDB](https://plugins.qgis.org/plugins/qduckdb/) desde el repositorio oficial de QGIS y actívelo. Esto evita problemas con `pip install duckdb`.

Si al abrir el plugin aparece un error de módulo faltante, consulte la sección [Error: Módulo DuckDB no encontrado](solucion-problemas.md#error-modulo-duckdb-no-encontrado) en Solución de Problemas.

## Problemas después de la instalación

Si encuentra errores al usar el plugin, consulte la [Guía de Solución de Problemas](solucion-problemas.md).
