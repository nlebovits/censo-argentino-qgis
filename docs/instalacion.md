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

## Instalar dependencias (si es necesario)

El plugin requiere el paquete Python `duckdb`. Si al abrir el plugin aparece un error de módulo faltante, consulte la sección [Error: Módulo DuckDB no encontrado](solucion-problemas.md#error-modulo-duckdb-no-encontrado) en Solución de Problemas.

## Repositorio oficial de QGIS

El plugin estará disponible próximamente en el repositorio oficial de QGIS, donde se podrá instalar directamente desde el administrador de complementos buscando "Censo Argentino".

## Problemas después de la instalación

Si encuentra errores al usar el plugin, consulte la [Guía de Solución de Problemas](solucion-problemas.md).
