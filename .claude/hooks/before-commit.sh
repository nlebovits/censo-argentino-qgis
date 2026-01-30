#!/bin/bash
# Hook para ejecutar antes de commits
# Auto-formatear y verificar código con ruff

echo "🔍 Ejecutando verificaciones pre-commit..."

# Verificar que el entorno virtual esté activo
if [ ! -f ".venv/bin/ruff" ]; then
    echo "⚠️  No se encontró ruff en .venv/bin/"
    echo "   Ejecuta: pip install -r requirements-dev.txt"
    exit 1
fi

# Verificar código con ruff
echo "📝 Verificando código con ruff..."
.venv/bin/ruff check censo_argentino_qgis/ --fix

# Formatear código con ruff
echo "✨ Formateando código..."
.venv/bin/ruff format censo_argentino_qgis/

echo "✅ Verificaciones pre-commit completadas"