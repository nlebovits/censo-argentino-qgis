# Plugin de Censo Argentino para QGIS

Plugin de QGIS para cargar datos del [Censo Nacional 2022](https://source.coop/nlebovits/censo-argentino) del INDEC desde Source.Coop (licencia CC-BY-4.0).

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://nlebovits.github.io/censo-argentino-qgis/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

![](docs/imgs/ejemplo.png)

## 📚 Documentación

**[Documentación completa](https://nlebovits.github.io/censo-argentino-qgis/)**

- [Instalación](https://nlebovits.github.io/censo-argentino-qgis/instalacion/)
- [Inicio Rápido](https://nlebovits.github.io/censo-argentino-qgis/inicio-rapido/)
- [Modo SQL](https://nlebovits.github.io/censo-argentino-qgis/sql/)
- [Desarrollo](https://nlebovits.github.io/censo-argentino-qgis/desarrollo/)
- [Contribuir](https://nlebovits.github.io/censo-argentino-qgis/contribuir/)

## Instalación

**Método recomendado - Repositorio oficial de QGIS:**

1. Abrir QGIS
2. Ir a **Complementos → Administrar e instalar complementos**
3. En la pestaña **Todos**, buscar "Censo Argentino"
4. Hacer clic en **Instalar complemento**
5. El plugin aparecerá en **Complementos → Censo Argentino**

**Instalación manual desde ZIP:**

Si necesitas instalar una versión específica, puedes descargar el archivo ZIP desde [Releases](https://github.com/nlebovits/censo-argentino-qgis/releases) e instalar desde la pestaña **Instalar desde ZIP** en el administrador de complementos.

**Nota sobre dependencias:** El plugin requiere el paquete Python `duckdb`. Si encuentras errores, consulta la [Guía de Solución de Problemas](https://nlebovits.github.io/censo-argentino-qgis/solucion-problemas/#error-modulo-duckdb-no-encontrado) para instrucciones de instalación.

## Demo

![Demo del plugin](docs/imgs/ejemplo.gif)

## Desarrollo y Contribución

Ver la [guía de desarrollo](https://nlebovits.github.io/censo-argentino-qgis/desarrollo/) para:
- Arquitectura del plugin
- Configuración de entorno de desarrollo
- Ejecución de tests
- Proceso de release

¡Las contribuciones son bienvenidas! Ver la [guía de contribución](https://nlebovits.github.io/censo-argentino-qgis/contribuir/).

## Licencia

Apache 2.0 - Ver [LICENSE](LICENSE) para más detalles.

## Autor

Nissim Lebovits - [nlebovits@pm.me](mailto:nlebovits@pm.me)
