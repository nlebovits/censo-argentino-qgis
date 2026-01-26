import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QCoreApplication, Qt, QThread, pyqtSignal
from qgis.core import QgsProject, QgsMessageLog, Qgis
from qgis.utils import iface
from .query import get_entity_types, get_variables, get_geographic_codes, load_census_layer

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog.ui'))


class DataLoaderThread(QThread):
    """Thread for loading data asynchronously"""
    finished = pyqtSignal(object, str)  # (result, data_type)
    error = pyqtSignal(str, str)  # (error_message, data_type)

    def __init__(self, load_func, data_type, *args, **kwargs):
        super().__init__()
        self.load_func = load_func
        self.data_type = data_type
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.load_func(*self.args, **self.kwargs)
            self.finished.emit(result, self.data_type)
        except Exception as e:
            self.error.emit(str(e), self.data_type)


class CensoArgentinoDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CensoArgentinoDialog, self).__init__(parent)
        self.setupUi(self)

        self.variables = {}  # Store mapping of variable codes to labels
        self.entity_types = []  # Store entity types
        self.loader_threads = []  # Track active threads

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

        # Load initial data asynchronously
        self.load_data_async()

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

    def load_data_async(self):
        """Load initial data (geo codes and variables) in background threads"""
        # Show loading state
        self.lblDescription.setText("Loading data...")

        # Load geographic codes in background
        geo_level = self.comboGeoLevel.currentData()
        if geo_level:
            geo_thread = DataLoaderThread(get_geographic_codes, "geo_codes", geo_level=geo_level)
            geo_thread.finished.connect(self.on_geo_codes_loaded)
            geo_thread.error.connect(self.on_data_load_error)
            self.loader_threads.append(geo_thread)
            geo_thread.start()

        # Load variables in background
        entity_type = self.comboEntityType.currentData()
        if entity_type:
            var_thread = DataLoaderThread(get_variables, "variables", entity_type=entity_type)
            var_thread.finished.connect(self.on_variables_loaded)
            var_thread.error.connect(self.on_data_load_error)
            self.loader_threads.append(var_thread)
            var_thread.start()

    def on_geo_codes_loaded(self, geo_codes, data_type):
        """Handle geographic codes loaded in background"""
        self.listGeoFilter.clear()
        for code, label in geo_codes:
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.listGeoFilter.addItem(item)
        self.check_loading_complete()

    def on_variables_loaded(self, variables, data_type):
        """Handle variables loaded in background"""
        self.listVariables.clear()
        self.variables = {}
        for code, label in variables:
            item = QtWidgets.QListWidgetItem(f"{code} - {label}")
            item.setData(Qt.UserRole, code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.listVariables.addItem(item)
            self.variables[code] = label
        self.check_loading_complete()

    def on_data_load_error(self, error_message, data_type):
        """Handle errors during background data loading"""
        QgsMessageLog.logMessage(
            f"Error loading {data_type}: {error_message}",
            "Censo Argentino",
            Qgis.Warning
        )
        self.check_loading_complete()

    def check_loading_complete(self):
        """Check if all loading threads are complete"""
        all_complete = all(not thread.isRunning() for thread in self.loader_threads)
        if all_complete:
            self.lblDescription.setText("")
            # Clean up finished threads
            self.loader_threads = [t for t in self.loader_threads if t.isRunning()]

    def on_year_changed(self):
        """Load entity types and variables when year changes"""
        self.on_entity_type_changed()

    def on_geo_level_changed(self):
        """Load geographic codes when level changes (async)"""
        self.listGeoFilter.clear()
        geo_level = self.comboGeoLevel.currentData()

        if not geo_level:
            return

        self.lblDescription.setText("Loading geographic codes...")

        # Load in background thread
        geo_thread = DataLoaderThread(get_geographic_codes, "geo_codes", geo_level=geo_level)
        geo_thread.finished.connect(self.on_geo_codes_loaded)
        geo_thread.error.connect(self.on_data_load_error)
        self.loader_threads.append(geo_thread)
        geo_thread.start()

    def on_entity_type_changed(self):
        """Load variables when entity type changes (async)"""
        self.listVariables.clear()
        self.lblDescription.setText("Loading variables...")

        entity_type = self.comboEntityType.currentData()

        if not entity_type:
            return

        # Load in background thread
        var_thread = DataLoaderThread(get_variables, "variables", entity_type=entity_type)
        var_thread.finished.connect(self.on_variables_loaded)
        var_thread.error.connect(self.on_data_load_error)
        self.loader_threads.append(var_thread)
        var_thread.start()

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

        # Get current map extent if checkbox is checked
        bbox = None
        if self.chkFilterViewbox.isChecked():
            try:
                canvas = iface.mapCanvas()
                extent = canvas.extent()
                crs = canvas.mapSettings().destinationCrs()

                QgsMessageLog.logMessage(
                    f"Original extent in {crs.authid()}: {extent.xMinimum()}, {extent.yMinimum()}, {extent.xMaximum()}, {extent.yMaximum()}",
                    "Censo Argentino",
                    Qgis.Info
                )

                # Always transform to WGS84 (EPSG:4326) for querying
                if crs.authid() != 'EPSG:4326':
                    from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem
                    transform = QgsCoordinateTransform(
                        crs,
                        QgsCoordinateReferenceSystem('EPSG:4326'),
                        QgsProject.instance()
                    )
                    extent = transform.transformBoundingBox(extent)

                    QgsMessageLog.logMessage(
                        f"Transformed extent to EPSG:4326: {extent.xMinimum()}, {extent.yMinimum()}, {extent.xMaximum()}, {extent.yMaximum()}",
                        "Censo Argentino",
                        Qgis.Info
                    )

                bbox = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error getting map extent: {str(e)}",
                    "Censo Argentino",
                    Qgis.Warning
                )
                bbox = None

        self.lblDescription.setText("")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)
        self.btnLoad.setEnabled(False)

        try:
            # Load single layer with all variables
            layer = load_census_layer(
                variable_codes,
                geo_level=geo_level,
                geo_filters=geo_filters,
                bbox=bbox,
                progress_callback=self.update_progress
            )

            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if len(variable_codes) == 1:
                    self.lblDescription.setText(f"Successfully loaded layer with 1 variable!")
                else:
                    self.lblDescription.setText(f"Successfully loaded layer with {len(variable_codes)} variables!")
                QgsMessageLog.logMessage(
                    f"Layer loaded: {layer.name()} with {len(variable_codes)} variables",
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
