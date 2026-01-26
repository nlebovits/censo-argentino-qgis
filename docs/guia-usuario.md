# Guía de Usuario

## Pestaña Explorar

Interfaz visual para seleccionar y cargar datos del censo.

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

### Filtros geográficos

**Por región:**
Marque provincias o departamentos en la lista. Solo se cargarán datos de las áreas seleccionadas.

**Por extensión del mapa:**
Active "Filtrar por extensión actual del mapa" para cargar únicamente los datos visibles en el canvas. Útil para trabajar con áreas específicas sin cargar todo el país.

### Resultado

El plugin genera una capa de polígonos con:

- Columna `geo_id` con el código del censo
- Una columna por cada variable seleccionada con el conteo

## Caché

Los metadatos (variables y códigos geográficos) se almacenan en `~/.cache/qgis-censo-argentino/` tras la primera carga. Puede eliminar esta carpeta para forzar una recarga.
