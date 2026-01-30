#!/bin/bash
# Hook para ejecutar antes de editar archivos
# Proporciona recordatorios según el archivo a modificar

FILE_PATH="$1"

# Función para mostrar recordatorio
show_reminder() {
    echo "⚠️  $1"
}

# Verificar archivo metadata.txt
if [[ "$FILE_PATH" == *"metadata.txt"* ]]; then
    show_reminder "Editando metadata.txt - Recordatorios:"
    echo "   • Actualizar campo 'version'"
    echo "   • Mantener formato: X.Y.Z"
    echo "   • Después crear tag: git tag -a vX.Y.Z -m 'Descripción'"
    echo ""
fi

# Verificar archivos SQL/Query
if [[ "$FILE_PATH" == *"query_builders.py"* ]] || [[ "$FILE_PATH" == *"query.py"* ]]; then
    show_reminder "Editando lógica SQL - Recordatorios:"
    echo "   • Usar CTEs para evitar productos cartesianos"
    echo "   • No usar pandas, solo DuckDB nativo"
    echo "   • Mantener caché en ~/.cache/qgis-censo-argentino/"
    echo ""
fi

# Verificar archivos de test
if [[ "$FILE_PATH" == *"test_"* ]]; then
    show_reminder "Editando tests - Recordatorios:"
    echo "   • Ejecutar con: .venv/bin/pytest"
    echo "   • Marcar tests que requieren Internet con @pytest.mark.skip"
    echo ""
fi

# Verificar documentación
if [[ "$FILE_PATH" == *"docs/"* ]] && [[ "$FILE_PATH" == *".md" ]]; then
    show_reminder "Editando documentación - Recordatorios:"
    echo "   • Todo en español"
    echo "   • Tono directo y práctico"
    echo "   • Títulos con ## (no #)"
    echo ""
fi