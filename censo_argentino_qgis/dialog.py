import os
from datetime import datetime

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QCoreApplication, Qt, QThread, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.utils import iface

from .config import AVAILABLE_YEARS
from .query import (
    calculate_column_count,
    get_cached_data,
    get_geographic_codes,
    get_variable_categories,
    get_variables,
    load_census_layer,
    preload_all_metadata,
    run_custom_query,
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "dialog.ui"))


EXAMPLE_QUERIES = {
    "-- Seleccionar un ejemplo --": "",
    "Población total por radio": """-- Las vistas 'radios' y 'census' cambian según el año seleccionado
-- Para 2022 usa COD_2022, para 2010 usa COD_2010 automáticamente
SELECT
    c.id_geo as geo_id,
    ST_AsText(g.geometry) as wkt,
    c.conteo as total_pop
FROM census c
JOIN radios g ON c.id_geo = COALESCE(g.COD_2022, g.COD_2010)
WHERE c.codigo_variable LIKE '%POB_TOT%'
LIMIT 1000""",
    "Comparar dos variables (plantilla de ratio)": """-- Reemplazar VAR_A y VAR_B con códigos de variable reales
-- Las vistas cambian según el año seleccionado
SELECT
    a.id_geo as geo_id,
    ST_AsText(g.geometry) as wkt,
    (a.conteo::float / NULLIF(b.conteo, 0)) * 100 as ratio
FROM census a
JOIN census b ON a.id_geo = b.id_geo AND b.codigo_variable = 'VAR_B'
JOIN radios g ON a.id_geo = COALESCE(g.COD_2022, g.COD_2010)
WHERE a.codigo_variable = 'VAR_A'
LIMIT 1000""",
    "Agregar a nivel departamental": """SELECT
    c.valor_provincia || '-' || c.valor_departamento as geo_id,
    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
    SUM(c.conteo) as total
FROM census c
JOIN radios g ON c.id_geo = COALESCE(g.COD_2022, g.COD_2010)
WHERE c.codigo_variable LIKE '%POB_TOT%'
GROUP BY c.valor_provincia, c.valor_departamento""",
    "Filtrar por provincia": """-- Las vistas cambian según el año seleccionado
SELECT
    c.id_geo as geo_id,
    ST_AsText(g.geometry) as wkt,
    c.conteo as poblacion
FROM census c
JOIN radios g ON c.id_geo = COALESCE(g.COD_2022, g.COD_2010)
WHERE c.codigo_variable LIKE '%POB_TOT%'
  AND c.etiqueta_provincia LIKE '%Buenos Aires%'
LIMIT 1000""",
    "Listar variables disponibles": """SELECT DISTINCT
    entidad,
    codigo_variable,
    etiqueta_variable
FROM metadata
ORDER BY entidad, codigo_variable""",
    "Conteo por provincia": """-- Agrupa población total por provincia
SELECT
    c.etiqueta_provincia as provincia,
    SUM(c.conteo) as poblacion_total
FROM census c
WHERE c.codigo_variable LIKE '%POB_TOT%'
GROUP BY c.valor_provincia, c.etiqueta_provincia
ORDER BY poblacion_total DESC""",
}


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
        super().__init__(parent)
        self.setupUi(self)

        self.variables = {}  # Store mapping of variable codes to labels
        self.entity_types = []  # Store entity types
        self.loader_threads = []  # Track active threads
        self.last_query = ""  # Store last executed query for copying
        self.last_browse_query = ""  # Store last Browse tab query for error logging
        self.variable_categories = {}  # Store categories for each selected variable
        self.category_widgets = {}  # Store category UI widgets per variable

        # Search debounce timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)  # 200ms debounce
        self.search_timer.timeout.connect(self.perform_search)

        # Initialize UI
        self.progressBar.hide()
        self.lblStatus.hide()

        # Initialize category section (collapsed by default)
        self.groupBoxCategories.setChecked(False)

        # Initialize Browse tab
        self.init_year_combo()
        self.init_geo_level_combo()
        self.init_entity_type_combo()
        self.comboYear.currentIndexChanged.connect(self.on_year_changed)
        self.comboGeoLevel.currentIndexChanged.connect(self.on_geo_level_changed)
        self.comboEntityType.currentIndexChanged.connect(self.on_entity_type_changed)
        self.listVariables.itemChanged.connect(self.on_variable_changed)
        self.searchVariables.textChanged.connect(self.on_search_changed)
        self.btnSelectAllVars.clicked.connect(self.on_select_all_vars_clicked)
        self.btnClearAllVars.clicked.connect(self.on_clear_all_vars_clicked)
        self.btnLoad.clicked.connect(self.on_load_clicked)
        self.btnDocs.clicked.connect(self.on_docs_clicked)
        self.btnTroubleshooting.clicked.connect(self.on_troubleshooting_clicked)

        # Initialize SQL tab
        self.init_sql_tab()
        self.comboExamples.currentIndexChanged.connect(self.on_example_selected)
        self.btnRunSql.clicked.connect(self.on_run_sql_clicked)

        # Initialize Query Log tab
        self.init_query_log_tab()
        self.btnCopyQuery.clicked.connect(self.on_copy_query_clicked)
        self.btnClearLog.clicked.connect(self.on_clear_log_clicked)

        # Load initial data asynchronously
        self.load_data_async()

    def init_year_combo(self):
        """Initialize year dropdown with available census years"""
        self.comboYear.clear()
        for year in AVAILABLE_YEARS:
            self.comboYear.addItem(year, year)

    def init_geo_level_combo(self):
        """Initialize geographic level dropdown"""
        self.comboGeoLevel.clear()
        self.comboGeoLevel.addItem("Radio Censal", "RADIO")
        self.comboGeoLevel.addItem("Fracción", "FRACC")
        self.comboGeoLevel.addItem("Departamento", "DEPTO")
        self.comboGeoLevel.addItem("Provincia", "PROV")

    def init_entity_type_combo(self):
        """Initialize entity type dropdown with friendly labels"""
        self.comboEntityType.clear()
        # Add entity types with readable labels
        self.comboEntityType.addItem("Hogar", "HOGAR")
        self.comboEntityType.addItem("Persona", "PERSONA")
        self.comboEntityType.addItem("Vivienda", "VIVIENDA")

    def update_progress(self, percent, message):
        """Update progress bar and status"""
        # Capture query text if message starts with QUERY_TEXT:
        if message.startswith("QUERY_TEXT:"):
            self.last_browse_query = message[len("QUERY_TEXT:") :]
            return  # Don't show this as a status message

        self.progressBar.setValue(percent)
        self.lblStatus.setText(message)
        QCoreApplication.processEvents()

    def load_data_async(self):
        """Load initial data (geo codes, variables, and metadata) in background threads"""
        year = self.comboYear.currentData() or "2022"

        # Check if this is a first-time cache load (show special message)
        cache_key = f"all_metadata_{year}"
        is_first_load = get_cached_data(cache_key) is None

        if is_first_load:
            # Show caching dialog for first-time users
            self.show_caching_message(year)
        else:
            self.lblDescription.setText("Cargando datos...")

        # Preload all metadata in background (makes category lookups instant)
        metadata_thread = DataLoaderThread(preload_all_metadata, "metadata", year=year)
        metadata_thread.finished.connect(self.on_metadata_loaded)
        metadata_thread.error.connect(self.on_data_load_error)
        self.loader_threads.append(metadata_thread)
        metadata_thread.start()

        # Load geographic codes in background
        geo_level = self.comboGeoLevel.currentData()
        if geo_level:
            geo_thread = DataLoaderThread(
                get_geographic_codes, "geo_codes", year=year, geo_level=geo_level
            )
            geo_thread.finished.connect(self.on_geo_codes_loaded)
            geo_thread.error.connect(self.on_data_load_error)
            self.loader_threads.append(geo_thread)
            geo_thread.start()

        # Load variables in background
        entity_type = self.comboEntityType.currentData()
        if entity_type:
            var_thread = DataLoaderThread(
                get_variables, "variables", year=year, entity_type=entity_type
            )
            var_thread.finished.connect(self.on_variables_loaded)
            var_thread.error.connect(self.on_data_load_error)
            self.loader_threads.append(var_thread)
            var_thread.start()

    def show_caching_message(self, year):
        """Show a non-blocking message about first-time caching"""
        self.lblDescription.setText(f"⏳ Cacheando metadatos del censo {year} (operación única)...")
        # Also show a message box for visibility
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle("Cargando metadatos")
        msg.setText(
            f"Primera vez cargando datos del censo {year}.\n\n"
            "El plugin está descargando y cacheando los metadatos.\n"
            "Esto toma unos segundos y solo ocurre una vez por año censal.\n\n"
            "Las próximas cargas serán instantáneas."
        )
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        # Use a timer to auto-close after 3 seconds
        QTimer.singleShot(5000, msg.accept)
        msg.show()  # Non-blocking show

    def on_metadata_loaded(self, metadata_map, data_type):
        """Handle metadata preload completion"""
        # Metadata is now cached - all category lookups will be instant
        QgsMessageLog.logMessage(
            f"Metadata precargados: {len(metadata_map)} variables con categorías",
            "Censo Argentino",
            Qgis.Info,
        )
        self.check_loading_complete()

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
            f"Error loading {data_type}: {error_message}", "Censo Argentino", Qgis.Warning
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
        # Clear current data
        self.listVariables.clear()
        self.listGeoFilter.clear()
        self.clear_all_category_widgets()

        # Reload all data for the new year
        self.load_data_async()

    def clear_all_category_widgets(self):
        """Remove all category selection widgets"""
        for var_code in list(self.category_widgets.keys()):
            self.remove_category_widget(var_code)

    def on_geo_level_changed(self):
        """Load geographic codes when level changes (async)"""
        self.listGeoFilter.clear()
        geo_level = self.comboGeoLevel.currentData()
        year = self.comboYear.currentData() or "2022"

        if not geo_level:
            return

        self.lblDescription.setText("Cargando códigos geográficos...")

        # Load in background thread
        geo_thread = DataLoaderThread(
            get_geographic_codes, "geo_codes", year=year, geo_level=geo_level
        )
        geo_thread.finished.connect(self.on_geo_codes_loaded)
        geo_thread.error.connect(self.on_data_load_error)
        self.loader_threads.append(geo_thread)
        geo_thread.start()

    def on_entity_type_changed(self):
        """Load variables when entity type changes (async)"""
        self.listVariables.clear()
        self.clear_all_category_widgets()
        self.lblDescription.setText("Cargando variables...")

        entity_type = self.comboEntityType.currentData()
        year = self.comboYear.currentData() or "2022"

        if not entity_type:
            return

        # Load in background thread
        var_thread = DataLoaderThread(
            get_variables, "variables", year=year, entity_type=entity_type
        )
        var_thread.finished.connect(self.on_variables_loaded)
        var_thread.error.connect(self.on_data_load_error)
        self.loader_threads.append(var_thread)
        var_thread.start()

    def on_search_changed(self):
        """Debounce search input - restart timer on each keystroke"""
        self.search_timer.stop()
        self.search_timer.start()

    def perform_search(self):
        """Actually filter variables list based on search text (called after debounce)"""
        search_text = self.searchVariables.text().lower()

        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            item_text = item.text().lower()

            # Show item if search text is in the item text, hide otherwise
            item.setHidden(search_text not in item_text)

    def on_variable_changed(self):
        """Update description and category selection when variables are checked"""
        checked_count = 0
        last_checked_code = None
        currently_checked = set()

        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            if item.checkState() == Qt.Checked:
                checked_count += 1
                var_code = item.data(Qt.UserRole)
                last_checked_code = var_code
                currently_checked.add(var_code)

        # Update description
        if checked_count == 1 and last_checked_code in self.variables:
            self.lblDescription.setText(self.variables[last_checked_code])
        elif checked_count > 1:
            self.lblDescription.setText(f"{checked_count} variables seleccionadas")
        else:
            self.lblDescription.setText("")

        # Update category UI: remove unchecked variables, add newly checked ones
        for var_code in list(self.category_widgets.keys()):
            if var_code not in currently_checked:
                self.remove_category_widget(var_code)

        for var_code in currently_checked:
            if var_code not in self.category_widgets:
                self.add_category_widget(var_code)

    def on_select_all_vars_clicked(self):
        """Select all visible variables in the list"""
        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)

    def on_clear_all_vars_clicked(self):
        """Clear all variable selections"""
        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            item.setCheckState(Qt.Unchecked)

    def add_category_widget(self, var_code):
        """Add collapsible category selection widget for a variable"""
        year = self.comboYear.currentData() or "2022"

        # Fetch categories asynchronously
        try:
            cat_data = get_variable_categories(year=year, variable_code=var_code)
            categories = cat_data["categories"]

            if not categories:
                # No categories for this variable, skip UI
                return

            # Create group box for this variable
            group_box = QtWidgets.QGroupBox(f"{var_code} - {self.variables.get(var_code, '')}")
            group_box.setCheckable(True)
            group_box.setChecked(False)  # Collapsed by default
            layout = QtWidgets.QVBoxLayout()

            # Add Select All / Unselect All buttons
            button_layout = QtWidgets.QHBoxLayout()
            btn_select_all = QtWidgets.QPushButton("Seleccionar todos")
            btn_unselect_all = QtWidgets.QPushButton("Deseleccionar todos")

            def select_all_categories():
                for checkbox in group_box.findChildren(QtWidgets.QCheckBox):
                    checkbox.setChecked(True)

            def unselect_all_categories():
                for checkbox in group_box.findChildren(QtWidgets.QCheckBox):
                    checkbox.setChecked(False)

            btn_select_all.clicked.connect(select_all_categories)
            btn_unselect_all.clicked.connect(unselect_all_categories)
            button_layout.addWidget(btn_select_all)
            button_layout.addWidget(btn_unselect_all)
            layout.addLayout(button_layout)

            # Add checkbox for each category
            category_checkboxes = []
            for valor, etiqueta in categories:
                checkbox = QtWidgets.QCheckBox(f"{valor} - {etiqueta}")
                checkbox.setChecked(True)  # Default: all selected
                checkbox.setProperty("valor", valor)
                layout.addWidget(checkbox)
                category_checkboxes.append(checkbox)

            group_box.setLayout(layout)

            # Add to scroll area
            self.layoutCategories.addWidget(group_box)

            # Store widget and checkboxes for later retrieval
            self.category_widgets[var_code] = {
                "group_box": group_box,
                "checkboxes": category_checkboxes,
            }

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error loading categories for {var_code}: {e}", "Censo Argentino", Qgis.Warning
            )

    def remove_category_widget(self, var_code):
        """Remove category selection widget for a variable"""
        if var_code in self.category_widgets:
            widget_data = self.category_widgets[var_code]
            group_box = widget_data["group_box"]
            self.layoutCategories.removeWidget(group_box)
            group_box.deleteLater()
            del self.category_widgets[var_code]

    def get_selected_categories(self):
        """Get dictionary of selected categories per variable"""
        selected = {}
        for var_code, widget_data in self.category_widgets.items():
            checkboxes = widget_data["checkboxes"]
            selected_vals = [cb.property("valor") for cb in checkboxes if cb.isChecked()]
            selected[var_code] = selected_vals
        return selected

    def on_load_clicked(self):
        """Load layers for checked census variables"""
        # Get checked variables
        checked_variables = []
        for i in range(self.listVariables.count()):
            item = self.listVariables.item(i)
            if item.checkState() == Qt.Checked:
                checked_variables.append(item)

        if not checked_variables:
            self.lblDescription.setText("Por favor seleccione al menos una variable")
            return

        year = self.comboYear.currentData() or "2022"
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
                    f"Extensión original en {crs.authid()}: {extent.xMinimum()}, {extent.yMinimum()}, {extent.xMaximum()}, {extent.yMaximum()}",
                    "Censo Argentino",
                    Qgis.Info,
                )

                # Always transform to WGS84 (EPSG:4326) for querying
                if crs.authid() != "EPSG:4326":
                    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform

                    transform = QgsCoordinateTransform(
                        crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance()
                    )
                    extent = transform.transformBoundingBox(extent)

                    QgsMessageLog.logMessage(
                        f"Extensión transformada a EPSG:4326: {extent.xMinimum()}, {extent.yMinimum()}, {extent.xMaximum()}, {extent.yMaximum()}",
                        "Censo Argentino",
                        Qgis.Info,
                    )

                bbox = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error obteniendo extensión del mapa: {str(e)}",
                    "Censo Argentino",
                    Qgis.Warning,
                )
                bbox = None

        # Validate category selection
        selected_categories = self.get_selected_categories()
        for var_code in variable_codes:
            if var_code in selected_categories and len(selected_categories[var_code]) == 0:
                self.lblDescription.setText(
                    f"Error: No se seleccionaron categorías para {var_code}. "
                    f"Seleccione al menos una categoría o todas."
                )
                return

        self.lblDescription.setText("")
        self.progressBar.show()
        self.lblStatus.show()
        self.progressBar.setValue(0)
        self.btnLoad.setEnabled(False)

        try:
            # Check column count and warn if > 100
            column_count = calculate_column_count(
                year=year, variable_codes=variable_codes, selected_categories=selected_categories
            )
            if column_count > 100:
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "Muchas columnas",
                    f"Está a punto de cargar {column_count} columnas de datos.\n\n"
                    f"Esto puede causar que QGIS se vuelva lento o no responda.\n\n"
                    f"¿Está seguro de que desea continuar?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if reply == QtWidgets.QMessageBox.No:
                    self.lblDescription.setText("Carga cancelada")
                    self.progressBar.hide()
                    self.lblStatus.hide()
                    self.btnLoad.setEnabled(True)
                    return

            # Load single layer with all variables (filtered by selected categories)
            layer = load_census_layer(
                year=year,
                variable_codes=variable_codes,
                geo_level=geo_level,
                geo_filters=geo_filters,
                bbox=bbox,
                selected_categories=selected_categories,
                progress_callback=self.update_progress,
            )

            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)

                # Log the query to Query Log tab
                query_text = layer.customProperty("censo_query", "")
                if query_text:
                    self.log_query(query_text, "Browse")

                if len(variable_codes) == 1:
                    self.lblDescription.setText("¡Capa cargada exitosamente con 1 variable!")
                else:
                    self.lblDescription.setText(
                        f"¡Capa cargada exitosamente con {len(variable_codes)} variables!"
                    )
                QgsMessageLog.logMessage(
                    f"Capa cargada: {layer.name()} con {len(variable_codes)} variables",
                    "Censo Argentino",
                    Qgis.Info,
                )
            else:
                self.lblDescription.setText("Error: Capa inválida")
                QgsMessageLog.logMessage(
                    "Se creó una capa inválida", "Censo Argentino", Qgis.Critical
                )

        except Exception as e:
            self.lblDescription.setText(f"Error: {str(e)}")
            QgsMessageLog.logMessage(
                f"Error cargando capa: {str(e)}", "Censo Argentino", Qgis.Critical
            )
            # Log the query to Query Log tab even on error
            if self.last_browse_query:
                self.log_query(self.last_browse_query, f"Explorar (ERROR: {str(e)})")
            else:
                log_msg = f"-- ERROR: {str(e)}\n-- La consulta no fue capturada. Revise el panel de Mensajes de Registro de QGIS para más detalles.\n\n"
                self.txtQueryLog.appendPlainText(log_msg)

        finally:
            self.progressBar.hide()
            self.lblStatus.hide()
            self.btnLoad.setEnabled(True)

    def log_query(self, query, source="Explorar"):
        """Log query to the Query Log tab"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"-- Consulta de {source} a las {timestamp}\n{query}\n\n"
        self.txtQueryLog.appendPlainText(log_entry)
        self.last_query = query

    def init_sql_tab(self):
        """Initialize SQL tab UI"""
        self.progressBarSql.hide()
        self.lblSqlStatus.setText("")
        self.tblSqlResults.hide()  # Hide table initially

        # Set monospace font
        font = QFont("Consolas, Monaco, Courier New, monospace", 10)
        self.txtSql.setFont(font)

        # Populate examples dropdown
        self.comboExamples.clear()
        for name in EXAMPLE_QUERIES.keys():
            self.comboExamples.addItem(name)

        # Set placeholder text
        self.txtSql.setPlaceholderText(
            "-- Ingrese consulta SQL aquí\n"
            "-- Tablas: radios, census, metadata\n"
            "-- Incluya 'ST_AsText(g.geometry) as wkt' para cargar como capa"
        )

    def init_query_log_tab(self):
        """Initialize Query Log tab"""
        font = QFont("Consolas, Monaco, Courier New, monospace", 9)
        self.txtQueryLog.setFont(font)
        self.txtQueryLog.setPlainText(
            "-- El registro de consultas aparecerá aquí\n-- Consultas de las pestañas Explorar y SQL\n\n"
        )

    def on_example_selected(self):
        """Load selected example into SQL editor"""
        example_name = self.comboExamples.currentText()
        if example_name in EXAMPLE_QUERIES and EXAMPLE_QUERIES[example_name]:
            self.txtSql.setPlainText(EXAMPLE_QUERIES[example_name])

    def update_sql_progress(self, percent, message):
        """Update SQL tab progress"""
        self.progressBarSql.setValue(percent)
        self.lblSqlStatus.setText(message)
        QCoreApplication.processEvents()

    def on_run_sql_clicked(self):
        """Execute SQL query"""
        sql = self.txtSql.toPlainText().strip()
        year = self.comboYear.currentData() or "2022"

        if not sql:
            self.lblSqlStatus.setText("Por favor ingrese una consulta SQL")
            return

        # Check for placeholder variables that need replacement
        from validation import validate_sql_placeholders

        placeholders = validate_sql_placeholders(sql)

        if placeholders:
            self.lblSqlStatus.setText(
                f"⚠️ Error: La consulta contiene marcadores de posición que deben reemplazarse: {', '.join(placeholders)}\n\n"
                "Use la pestaña 'Explorar' para encontrar códigos de variables reales, o ejecute:\n"
                "SELECT DISTINCT codigo_variable, etiqueta_variable FROM metadata"
            )
            self.tblSqlResults.hide()
            return

        # Log the query
        self.log_query(sql, f"SQL ({year})")

        self.progressBarSql.show()
        self.lblSqlStatus.show()
        self.btnRunSql.setEnabled(False)

        try:
            result, error = run_custom_query(
                sql, year=year, progress_callback=self.update_sql_progress
            )

            if error:
                self.lblSqlStatus.setText(f"Error: {error}")
                QgsMessageLog.logMessage(f"Error SQL: {error}", "Censo Argentino", Qgis.Warning)
            elif result is None:
                self.lblSqlStatus.setText("La consulta no devolvió resultados")
            elif isinstance(result, QgsVectorLayer):
                if result.isValid():
                    QgsProject.instance().addMapLayer(result)
                    self.lblSqlStatus.setText(f"Capa agregada: {result.featureCount()} entidades")
                else:
                    self.lblSqlStatus.setText("Error: Se creó una capa inválida")
            else:
                # Tuple result (columns, rows) - no geometry - show in table
                columns, rows = result
                row_count = len(rows)
                col_count = len(columns)
                self.lblSqlStatus.setText(
                    f"La consulta devolvió {row_count} filas con {col_count} columnas"
                )

                # Populate table widget
                self.tblSqlResults.show()
                self.tblSqlResults.setRowCount(
                    min(row_count, 1000)
                )  # Limit to 1000 rows for display
                self.tblSqlResults.setColumnCount(col_count)
                self.tblSqlResults.setHorizontalHeaderLabels(columns)

                # Populate data (limit to first 1000 rows)
                for row_idx, row in enumerate(rows[:1000]):
                    for col_idx, value in enumerate(row):
                        self.tblSqlResults.setItem(
                            row_idx, col_idx, QtWidgets.QTableWidgetItem(str(value))
                        )

                # Resize columns to content
                self.tblSqlResults.resizeColumnsToContents()

                # Also log to QGIS log panel (show first 20 rows)
                log_lines = ["\t".join(columns)]  # Header
                for row in rows[:20]:
                    log_lines.append("\t".join(str(v) for v in row))
                log_output = "\n".join(log_lines)
                QgsMessageLog.logMessage(
                    f"Resultado de consulta SQL ({row_count} filas, {col_count} columnas):\n{log_output}",
                    "Censo Argentino",
                    Qgis.Info,
                )

        except Exception as e:
            self.lblSqlStatus.setText(f"Error: {str(e)}")
            QgsMessageLog.logMessage(
                f"Error de ejecución SQL: {str(e)}", "Censo Argentino", Qgis.Critical
            )

        finally:
            self.progressBarSql.hide()
            self.btnRunSql.setEnabled(True)

    def on_copy_query_clicked(self):
        """Copy last query to clipboard"""
        if self.last_query:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(self.last_query)
            QgsMessageLog.logMessage(
                "Consulta copiada al portapapeles", "Censo Argentino", Qgis.Info
            )
        else:
            QgsMessageLog.logMessage("No hay consulta para copiar", "Censo Argentino", Qgis.Warning)

    def on_clear_log_clicked(self):
        """Clear the query log"""
        self.txtQueryLog.setPlainText("-- Registro de consultas borrado\n\n")

    def on_docs_clicked(self):
        """Open documentation in browser"""
        import webbrowser

        docs_url = "https://nlebovits.github.io/censo-argentino-qgis/"
        webbrowser.open(docs_url)
        QgsMessageLog.logMessage(
            f"Abriendo documentación: {docs_url}", "Censo Argentino", Qgis.Info
        )

    def on_troubleshooting_clicked(self):
        """Open troubleshooting documentation in browser"""
        import webbrowser

        docs_url = "https://nlebovits.github.io/censo-argentino-qgis/solucion-problemas/"
        webbrowser.open(docs_url)
        QgsMessageLog.logMessage(
            f"Abriendo solución de problemas: {docs_url}", "Censo Argentino", Qgis.Info
        )
