import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialog import CensoArgentinoDialog


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
        if self.dialog is None:
            self.dialog = CensoArgentinoDialog()

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
