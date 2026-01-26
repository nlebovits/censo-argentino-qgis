import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.core import QgsProject, QgsMessageLog, Qgis
from .query import get_entity_types, get_variables, get_geographic_codes, load_census_layer

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog.ui'))


class CensoArgentinoDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CensoArgentinoDialog, self).__init__(parent)
        self.setupUi(self)

        self.variables = {}  # Store mapping of variable codes to labels
        self.entity_types = []  # Store entity types

        # Initialize UI
        self.progressBar.hide()
        self.lblStatus.hide()

        self.init_year_combo()
        self.init_geo_level_combo()
        self.init_entity_type_combo()
        self.comboYear.currentIndexChanged.connect(self.on_year_changed)
        self.comboGeoLevel.currentIndexChanged.connect(self.on_geo_level_changed)
        self.comboEntityType.currentIndexChanged.connect(self.on_entity_type_changed)
        self.listVariables.itemChanged.connect(self.on_variable_changed)
        self.searchVariables.textChanged.connect(self.on_search_changed)
        self.btnLoad.clicked.connect(self.on_load_clicked)

        # Load initial data
        self.on_geo_level_changed()  # Load geographic filters first
        self.on_year_changed()

    def init_year_combo(self):
        """Initialize year dropdown (hardcoded to 2022 for now)"""
        self.comboYear.clear()
        self.comboYear.addItem("2022", "2022")

    def init_geo_level_combo(self):
        """Initialize geographic level dropdown"""
        self.comboGeoLevel.clear()
        self.comboGeoLevel.addItem("Census Tract (Radio)", "RADIO")
        self.comboGeoLevel.addItem("Fraction (Fracción)", "FRACC")
        self.comboGeoLevel.addItem("Department (Departamento)", "DEPTO")
        self.comboGeoLevel.addItem("Province (Provincia)", "PROV")

    def init_entity_type_combo(self):
        """Initialize entity type dropdown with friendly labels"""
        self.comboEntityType.clear()
        # Add entity types with readable labels
        self.comboEntityType.addItem("Household (Hogar)", "HOGAR")
        self.comboEntityType.addItem("Person (Persona)", "PERSONA")
        self.comboEntityType.addItem("Dwelling (Vivienda)", "VIVIENDA")

    def update_progress(self, percent, message):
        """Update progress bar and status"""
        self.progressBar.setValue(percent)
        self.lblStatus.setText(message)
        QCoreApplication.processEvents()

    def on_year_changed(self):
        """Load entity types and variables when year changes"""
        self.on_entity_type_changed()

    def on_geo_level_changed(self):
        """Load geographic codes when level changes"""
        self.listGeoFilter.clear()
        geo_level = self.comboGeoLevel.currentData()

        if not geo_level:
            return

        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)

        try:
            geo_codes = get_geographic_codes(
                geo_level=geo_level,
                progress_callback=self.update_progress
            )

            for code, label in geo_codes:
                item = QtWidgets.QListWidgetItem(label)
                item.setData(Qt.UserRole, code)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.listGeoFilter.addItem(item)

            self.progressBar.hide()
            self.lblStatus.hide()

        except Exception as e:
            self.progressBar.hide()
            self.lblStatus.hide()
            QgsMessageLog.logMessage(
                f"Error loading geographic codes: {str(e)}",
                "Censo Argentino",
                Qgis.Warning
            )

    def on_entity_type_changed(self):
        """Load variables when entity type changes"""
        self.listVariables.clear()
        self.lblDescription.setText("Loading variables...")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)

        entity_type = self.comboEntityType.currentData()

        try:
            variables = get_variables(
                entity_type=entity_type,
                progress_callback=self.update_progress
            )
            self.variables = {}

            for code, label in variables:
                item = QtWidgets.QListWidgetItem(f"{code} - {label}")
                item.setData(Qt.UserRole, code)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.listVariables.addItem(item)
                self.variables[code] = label

            self.lblDescription.setText("")
            self.progressBar.hide()
            self.lblStatus.hide()

        except Exception as e:
            self.lblDescription.setText(f"Error loading variables: {str(e)}")
            self.progressBar.hide()
            self.lblStatus.hide()
            QgsMessageLog.logMessage(
                f"Error loading variables: {str(e)}",
                "Censo Argentino",
                Qgis.Critical
            )

    def on_search_changed(self):
        """Filter variables list based on search text"""
        search_text = self.searchVariables.text().lower()

        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            item_text = item.text().lower()

            # Show item if search text is in the item text, hide otherwise
            item.setHidden(search_text not in item_text)

    def on_variable_changed(self):
        """Update description when variables are checked"""
        checked_count = 0
        last_checked_code = None

        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            if item.checkState() == Qt.Checked:
                checked_count += 1
                last_checked_code = item.data(Qt.UserRole)

        if checked_count == 1 and last_checked_code in self.variables:
            self.lblDescription.setText(self.variables[last_checked_code])
        elif checked_count > 1:
            self.lblDescription.setText(f"{checked_count} variables selected")
        else:
            self.lblDescription.setText("")

    def on_load_clicked(self):
        """Load layers for checked census variables"""
        # Get checked variables
        checked_variables = []
        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            if item.checkState() == Qt.Checked:
                checked_variables.append(item)

        if not checked_variables:
            self.lblDescription.setText("Please check at least one variable")
            return

        geo_level = self.comboGeoLevel.currentData()
        variable_codes = [item.data(Qt.UserRole) for item in checked_variables]

        # Get checked geographic filters (optional)
        checked_geo_filters = []
        for i in range(self.listGeoFilter.count()):
            item = self.listGeoFilter.item(i)
            if item.checkState() == Qt.Checked:
                checked_geo_filters.append(item.data(Qt.UserRole))

        geo_filters = checked_geo_filters if checked_geo_filters else None

        self.lblDescription.setText("")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)
        self.btnLoad.setEnabled(False)

        loaded_count = 0
        error_count = 0

        try:
            for idx, var_code in enumerate(variable_codes):
                try:
                    # Update progress for multi-variable load
                    base_progress = int((idx / len(variable_codes)) * 100)

                    def progress_wrapper(percent, message):
                        adjusted_percent = base_progress + int((percent / 100) * (100 / len(variable_codes)))
                        self.update_progress(adjusted_percent, f"[{idx+1}/{len(variable_codes)}] {message}")

                    layer = load_census_layer(
                        var_code,
                        geo_level=geo_level,
                        geo_filters=geo_filters,
                        progress_callback=progress_wrapper
                    )

                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
                        loaded_count += 1
                        QgsMessageLog.logMessage(
                            f"Layer loaded: {layer.name()}",
                            "Censo Argentino",
                            Qgis.Info
                        )
                    else:
                        error_count += 1
                        QgsMessageLog.logMessage(
                            f"Invalid layer created for {var_code}",
                            "Censo Argentino",
                            Qgis.Critical
                        )

                except Exception as e:
                    error_count += 1
                    QgsMessageLog.logMessage(
                        f"Error loading {var_code}: {str(e)}",
                        "Censo Argentino",
                        Qgis.Critical
                    )

            # Summary message
            if error_count == 0:
                self.lblDescription.setText(f"Successfully loaded {loaded_count} layer(s)!")
            else:
                self.lblDescription.setText(f"Loaded {loaded_count} layer(s), {error_count} error(s)")

        except Exception as e:
            self.lblDescription.setText(f"Error: {str(e)}")
            QgsMessageLog.logMessage(
                f"Error in batch load: {str(e)}",
                "Censo Argentino",
                Qgis.Critical
            )

        finally:
            self.progressBar.hide()
            self.lblStatus.hide()
            self.btnLoad.setEnabled(True)
