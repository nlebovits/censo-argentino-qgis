import os
from qgis.PyQt import uic, QtWidgets
from qgis.core import QgsProject, QgsMessageLog, Qgis
from .query import get_variables, load_census_layer

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog.ui'))


class CensoArgentinoDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CensoArgentinoDialog, self).__init__(parent)
        self.setupUi(self)

        self.variables = {}  # Store mapping of variable codes to labels

        # Initialize UI
        self.init_year_combo()
        self.comboYear.currentIndexChanged.connect(self.on_year_changed)
        self.comboVariable.currentIndexChanged.connect(self.on_variable_changed)
        self.btnLoad.clicked.connect(self.on_load_clicked)

        # Load initial data
        self.on_year_changed()

    def init_year_combo(self):
        """Initialize year dropdown (hardcoded to 2022 for now)"""
        self.comboYear.clear()
        self.comboYear.addItem("2022", "2022")

    def on_year_changed(self):
        """Load variables when year changes"""
        self.comboVariable.clear()
        self.lblDescription.setText("Loading variables...")

        try:
            variables = get_variables()
            self.variables = {}

            for code, label in variables:
                self.comboVariable.addItem(f"{code} - {label}", code)
                self.variables[code] = label

            self.lblDescription.setText("")

            if self.comboVariable.count() > 0:
                self.on_variable_changed()

        except Exception as e:
            self.lblDescription.setText(f"Error loading variables: {str(e)}")
            QgsMessageLog.logMessage(
                f"Error loading variables: {str(e)}",
                "Censo Argentino",
                Qgis.Critical
            )

    def on_variable_changed(self):
        """Update description when variable changes"""
        current_code = self.comboVariable.currentData()
        if current_code and current_code in self.variables:
            self.lblDescription.setText(self.variables[current_code])
        else:
            self.lblDescription.setText("")

    def on_load_clicked(self):
        """Load the selected census layer"""
        current_code = self.comboVariable.currentData()

        if not current_code:
            self.lblDescription.setText("Please select a variable")
            return

        self.lblDescription.setText("Loading layer...")
        self.btnLoad.setEnabled(False)

        try:
            layer = load_census_layer(current_code)

            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.lblDescription.setText("Layer loaded successfully!")
                QgsMessageLog.logMessage(
                    f"Layer loaded: {layer.name()}",
                    "Censo Argentino",
                    Qgis.Info
                )
            else:
                self.lblDescription.setText("Error: Invalid layer")
                QgsMessageLog.logMessage(
                    "Invalid layer created",
                    "Censo Argentino",
                    Qgis.Critical
                )

        except Exception as e:
            self.lblDescription.setText(f"Error: {str(e)}")
            QgsMessageLog.logMessage(
                f"Error loading layer: {str(e)}",
                "Censo Argentino",
                Qgis.Critical
            )

        finally:
            self.btnLoad.setEnabled(True)
