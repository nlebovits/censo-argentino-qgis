import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QCoreApplication
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
        self.progressBar.hide()
        self.lblStatus.hide()

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

    def update_progress(self, percent, message):
        """Update progress bar and status"""
        self.progressBar.setValue(percent)
        self.lblStatus.setText(message)
        QCoreApplication.processEvents()

    def on_year_changed(self):
        """Load variables when year changes"""
        self.comboVariable.clear()
        self.lblDescription.setText("Loading variables...")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)

        try:
            variables = get_variables(progress_callback=self.update_progress)
            self.variables = {}

            for code, label in variables:
                self.comboVariable.addItem(f"{code} - {label}", code)
                self.variables[code] = label

            self.lblDescription.setText("")
            self.progressBar.hide()
            self.lblStatus.hide()

            if self.comboVariable.count() > 0:
                self.on_variable_changed()

        except Exception as e:
            self.lblDescription.setText(f"Error loading variables: {str(e)}")
            self.progressBar.hide()
            self.lblStatus.hide()
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

        self.lblDescription.setText("")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)
        self.btnLoad.setEnabled(False)

        try:
            layer = load_census_layer(current_code, progress_callback=self.update_progress)

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
            self.progressBar.hide()
            self.lblStatus.hide()
            self.btnLoad.setEnabled(True)
