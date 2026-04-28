import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .dialog import CensoArgentinoDialog

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
            if current_version:
                msg = (
                    f"<b>DuckDB {current_version} es demasiado antiguo.</b><br><br>"
                    f"Este plugin requiere DuckDB >= {min_ver} para soporte de GeoParquet 2.0.<br><br>"
                    f"<b>Para actualizar, ejecute en la consola de Python de QGIS:</b><br>"
                    f"<code>import subprocess, sys<br>"
                    f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'duckdb'])</code><br><br>"
                    f"Luego reinicie QGIS."
                )
            else:
                msg = (
                    f"<b>DuckDB no está instalado.</b><br><br>"
                    f"Este plugin requiere DuckDB >= {min_ver}.<br><br>"
                    f"<b>Para instalar, ejecute en la consola de Python de QGIS:</b><br>"
                    f"<code>import subprocess, sys<br>"
                    f"subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'duckdb'])</code><br><br>"
                    f"Luego reinicie QGIS."
                )
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Censo Argentino - Versión de DuckDB Insuficiente",
                msg,
            )
            return

        if self.dialog is None:
            self.dialog = CensoArgentinoDialog()

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
