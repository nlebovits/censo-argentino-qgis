# Guía de Usuario

!!! tip "Primera vez usando el plugin"
    **¿Los campos tardan en aparecer?** Es normal la primera vez. El plugin descarga metadatos del censo (5-15 segundos) y los cachea localmente. En usos posteriores, todo carga instantáneamente.

    [Ver más sobre rendimiento →](#rendimiento-y-caché)

## Pestaña Explorar

Interfaz visual para seleccionar y cargar datos del censo.

![Interfaz de la pestaña Explorar](imgs/interfaz.png)

### Opciones

| Opción | Descripción |
|--------|-------------|
| **Año** | Año del censo (actualmente solo 2022) |
| **Nivel geográfico** | Radio Censal, Fracción, Departamento o Provincia |
| **Tipo de entidad** | Filtra las variables disponibles: Hogar, Persona o Vivienda |

### Niveles geográficos

- **Radio Censal**: Máximo detalle (~52,000 polígonos)
- **Fracción**: Agrupación de radios
- **Departamento**: Partidos/departamentos provinciales
- **Provincia**: 24 jurisdicciones

Los niveles superiores agregan automáticamente las geometrías y suman los conteos.

### Seleccionar variables

1. Escriba en el buscador para filtrar (ej: "educacion", "vivienda")
2. Marque una o más variables
3. La descripción de la variable aparece debajo de la lista

### Seleccionar categorías (opcional)

Muchas variables del censo tienen **categorías** — por ejemplo, la variable de nivel educativo tiene categorías como "Sin instrucción", "Primaria", "Secundaria", etc.

Por defecto, todas las categorías se incluyen. Para filtrar categorías específicas:

1. Active la casilla **"Categorías (seleccionar por variable)"**
2. Expanda la variable deseada haciendo clic en el título
3. Seleccione/deseleccione categorías según necesite
4. Use los botones "Seleccionar todos" / "Deseleccionar todos" para control rápido

**Importante**: Cada combinación de variable+categoría genera una columna separada en la capa resultante. Por ejemplo, si selecciona "educación" con 5 categorías, obtendrá 6 columnas: una para cada categoría más una columna `_total` con la suma de todas.

!!! warning "Límite de columnas"
    - **50+ columnas**: Aparecerá una advertencia (puede continuar)
    - **100+ columnas**: Se bloqueará la carga para evitar problemas de rendimiento

    Considere reducir el número de variables o usar filtros de categorías.

### Filtros geográficos

**Por región:**
Marque provincias o departamentos en la lista. Solo se cargarán datos de las áreas seleccionadas.

**Por extensión del mapa:**
Active "Filtrar por extensión actual del mapa" para cargar únicamente los datos visibles en el canvas. Útil para trabajar con áreas específicas sin cargar todo el país.

### Resultado

El plugin genera una capa de polígonos con:

- Columna `geo_id` con el código del censo
- Para variables **con categorías**: una columna por categoría (ej: `educacion_primaria`, `educacion_secundaria`) más una columna `_total`
- Para variables **sin categorías**: una sola columna con el conteo total

**Nombres de columnas**: Las columnas se generan automáticamente con formato `variable_categoria` en minúsculas, sin espacios ni acentos. Por ejemplo:
- `PERSONA_P11` (categoría "Sí") → `persona_p11_si`
- `PERSONA_P19` (categoría "0-14 años") → `persona_p19_cat_0_14_anos`

![Ejemplo de visualización en QGIS](imgs/ejemplo.png)

## Rendimiento y Caché

### Primera vez usando el plugin

**Espere 5-15 segundos** la primera vez que abre el plugin o cambia de año censal. El plugin descarga y cachea metadatos del censo:

- Variables disponibles y sus categorías
- Códigos geográficos (provincias, departamentos, etc.)
- Tipos de entidad

Verá mensajes de progreso como "Cargando metadatos..." mientras se construye el caché local.

### Usos posteriores

Después de la primera carga, **los metadatos cargan instantáneamente** (< 1 segundo) desde el caché local en `~/.cache/qgis-censo-argentino/`.

**Si algo parece lento en usos posteriores**, el problema está en la **descarga de datos censales** (geometrías + valores), no en metadatos. Esto es normal - ver [Solución de Problemas](solucion-problemas.md#rendimiento-y-tiempos-de-carga) para detalles.

### Tiempos esperados

| Operación | Primera vez | Usos posteriores |
|-----------|-------------|------------------|
| **Cargar metadatos** (listas de variables) | 5-15 segundos | < 1 segundo ✅ |
| **Cargar capa RADIO** (52K polígonos) | 45-90 segundos | 45-90 segundos* |
| **Cargar capa PROV** (24 polígonos) | 5-10 segundos | 5-10 segundos* |

*Los datos censales (geometrías + valores) se consultan remotamente cada vez - no se cachean debido al tamaño (GBs).

### Limpiar el caché

Si necesita forzar una recarga de metadatos:

```bash
rm -rf ~/.cache/qgis-censo-argentino/
```

El caché se regenera automáticamente en el próximo uso.
