#!/bin/bash
# Hook para ejecutar antes de tests
# Asegura que las extensiones DuckDB estén instaladas

echo "🔧 Preparando entorno de pruebas..."

# Instalar extensiones DuckDB necesarias
echo "📦 Instalando extensiones DuckDB (spatial, httpfs)..."
python -c "
import duckdb
con = duckdb.connect(':memory:')
try:
    con.execute('INSTALL spatial')
    con.execute('INSTALL httpfs')
    print('✅ Extensiones DuckDB instaladas correctamente')
except Exception as e:
    print(f'⚠️  Error instalando extensiones: {e}')
"

# Verificar que pytest esté disponible
if [ ! -f ".venv/bin/pytest" ]; then
    echo "⚠️  No se encontró pytest en .venv/bin/"
    echo "   Ejecuta: pip install -r requirements-dev.txt"
    exit 1
fi

echo "✅ Entorno de pruebas listo"
