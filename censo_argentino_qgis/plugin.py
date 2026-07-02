import os
import sys

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

# NOTA: No importar .dialog (ni .query) a nivel de módulo. Esos módulos
# importan `duckdb`, que puede no estar instalado (p. ej. en QGIS Flatpak).
# Un import eager haría fallar classFactory() con un traceback crudo y
# dejaría inalcanzable el chequeo amigable de abajo. El import se hace de
# forma perezosa en run(), recién después de verificar DuckDB.

MINIMUM_DUCKDB_VERSION = (1, 5, 0)


def check_duckdb_version():
    """Verificar que DuckDB >= 1.5.0 esté instalado (requerido para GeoParquet 2.0)"""
    try:
        import duckdb

        version_str = duckdb.__version__
        version_parts = tuple(int(x) for x in version_str.split(".")[:3])
        if version_parts < MINIMUM_DUCKDB_VERSION:
            return False, version_str
        return True, version_str
    except ImportError:
        return False, None


def _is_flatpak():
    """Detectar si QGIS corre dentro de un sandbox Flatpak."""
    return bool(os.environ.get("FLATPAK_ID")) or sys.prefix.startswith("/app")


class CensoArgentinoPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.action = None

    def initGui(self):
        """Initialize the plugin GUI"""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), "Censo Argentino", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.action.setStatusTip("Load Argentina census data from Source.Coop")

        # Add toolbar button
        self.iface.addToolBarIcon(self.action)
        # Add menu item
        self.iface.addPluginToMenu("&Censo Argentino", self.action)

    def unload(self):
        """Remove the plugin menu item and icon"""
        self.iface.removePluginMenu("&Censo Argentino", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Show the dialog"""
        # Verificar versión de DuckDB antes de abrir el diálogo
        version_ok, current_version = check_duckdb_version()
        if not version_ok:
            min_ver = ".".join(str(x) for x in MINIMUM_DUCKDB_VERSION)
            pip_flag = "--upgrade " if current_version else ""
            if current_version:
                encabezado = (
                    f"<b>DuckDB {current_version} es demasiado antiguo.</b><br><br>"
                    f"Este plugin requiere DuckDB >= {min_ver} para soporte de GeoParquet 2.0.<br><br>"
                )
            else:
                encabezado = (
                    f"<b>DuckDB no está instalado.</b><br><br>"
                    f"Este plugin requiere DuckDB >= {min_ver}.<br><br>"
                )

            if _is_flatpak():
                instrucciones = (
                    "<b>Está usando QGIS vía Flatpak.</b> El entorno Python de QGIS "
                    "es de solo lectura, así que debe instalar DuckDB en su carpeta "
                    "de usuario.<br><br>"
                    "<b>1) Abra una terminal y ejecute:</b><br>"
                    f"<code>flatpak run --command=python3 org.qgis.qgis \\<br>"
                    f"&nbsp;&nbsp;-m pip install --user {pip_flag}'duckdb>={min_ver}'</code><br><br>"
                    "<b>2) Reinicie QGIS.</b><br><br>"
                    "Si tras reiniciar sigue sin detectarse, es posible que la carpeta "
                    "de usuario no esté en el <code>sys.path</code> de QGIS; en ese caso "
                    "considere instalar QGIS desde el paquete oficial de su distribución."
                )
            else:
                instrucciones = (
                    "<b>Para instalar, ejecute en la consola de Python de QGIS:</b><br>"
                    "<code>import subprocess, sys<br>"
                    f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', "
                    f"{'--upgrade, ' if current_version else ''}'duckdb'])</code><br><br>"
                    "Luego reinicie QGIS."
                )

            QMessageBox.critical(
                self.iface.mainWindow(),
                "Censo Argentino - DuckDB no disponible",
                encabezado + instrucciones,
            )
            return

        # Import perezoso: recién ahora sabemos que DuckDB está disponible.
        from .dialog import CensoArgentinoDialog

        if self.dialog is None:
            self.dialog = CensoArgentinoDialog()

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
