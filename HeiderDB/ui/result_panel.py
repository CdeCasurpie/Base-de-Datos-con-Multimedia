from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget,
                             QTextEdit, QHBoxLayout, QPushButton, QFileDialog)
from PyQt5.QtCore import Qt
import json
import csv

class ResultPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Tabs para diferentes vistas
        self.tabs = QTabWidget()
        
        # Tab de datos en tabla
        self.table_view = QTableWidget()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Tab de resultados en texto
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        
        self.tabs.addTab(self.table_view, "Tabla")
        self.tabs.addTab(self.text_view, "Texto")
        
        layout.addWidget(self.tabs)
        
        # Botones de exportación
        export_layout = QHBoxLayout()
        self.export_csv_button = QPushButton("Exportar a CSV")
        self.export_json_button = QPushButton("Exportar a JSON")
        export_layout.addWidget(self.export_csv_button)
        export_layout.addWidget(self.export_json_button)
        export_layout.addStretch(1)
        
        layout.addLayout(export_layout)
        
        # Conectar señales
        self.export_csv_button.clicked.connect(self.export_to_csv)
        self.export_json_button.clicked.connect(self.export_to_json)
        
        # Datos actuales
        self.current_data = None
    
    def update_results(self, result_data):
        """
        Actualiza los resultados mostrados en el panel.
        
        Args:
            result_data: Tupla (results, error) de la ejecución de la consulta
        """
        self.current_data = result_data
        
        # Limpiar vistas
        self.table_view.clear()
        self.table_view.setRowCount(0)
        self.table_view.setColumnCount(0)
        self.text_view.clear()
        
        # Desempaquetar resultado
        results, error = result_data if isinstance(result_data, tuple) else (None, str(result_data))
        
        if error:
            # Mostrar error
            self.text_view.setTextColor(Qt.red)
            self.text_view.setText(f"ERROR: {error}")
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
            return
            
        if isinstance(results, list) and results:
            # Mostrar resultados en la vista de tabla
            self.update_table_view(results)
            # También mostrar como texto
            self.text_view.setTextColor(Qt.black)
            self.text_view.setText(json.dumps(results, indent=2, default=str))
            self.tabs.setCurrentIndex(0)  # Mostrar tab de tabla
        elif isinstance(results, str):
            # Es solo un mensaje, mostrarlo como texto
            self.text_view.setTextColor(Qt.darkGreen)
            self.text_view.setText(results)
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
        elif results is not None:
            # Otro tipo de resultado, intentar mostrarlo como texto
            self.text_view.setTextColor(Qt.black)
            self.text_view.setText(str(results))
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
        else:
            # No hay resultados
            self.text_view.setTextColor(Qt.black)
            self.text_view.setText("No hay resultados para mostrar.")
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
    
    def update_table_view(self, data):
        """Actualiza la vista de tabla con los datos proporcionados"""
        if not data or not isinstance(data, list):
            return
            
        # Obtener columnas del primer registro
        if isinstance(data[0], dict):
            columns = list(data[0].keys())
        else:
            # No podemos mostrar datos que no sean diccionarios
            self.text_view.setText(str(data))
            self.tabs.setCurrentIndex(1)
            return
            
        # Configurar tabla
        self.table_view.setColumnCount(len(columns))
        self.table_view.setRowCount(len(data))
        self.table_view.setHorizontalHeaderLabels(columns)
        
        # Llenar datos
        for row, record in enumerate(data):
            for col, field in enumerate(columns):
                value = record.get(field, "")
                # Formatear valores especiales
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                item = QTableWidgetItem(str(value))
                self.table_view.setItem(row, col, item)
    
    def export_to_csv(self):
        """Exporta los resultados actuales a un archivo CSV"""
        if not self.current_data or not isinstance(self.current_data, tuple):
            return
            
        results, error = self.current_data
        if error or not results or not isinstance(results, list):
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar como CSV", "", "CSV (*.csv)")
        if not filename:
            return
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if isinstance(results[0], dict):
                    # Obtener todas las columnas del primer registro
                    fieldnames = list(results[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Manejar valores no serializables
                    for row in results:
                        for key, value in row.items():
                            if not isinstance(value, (str, int, float, bool, type(None))):
                                row[key] = str(value)
                    
                    writer.writerows(results)
                else:
                    # Fallback para datos no estructurados
                    writer = csv.writer(csvfile)
                    for item in results:
                        writer.writerow([item])
        except Exception as e:
            print(f"Error al exportar a CSV: {e}")
    
    def export_to_json(self):
        """Exporta los resultados actuales a un archivo JSON"""
        if not self.current_data:
            return
            
        results, error = self.current_data if isinstance(self.current_data, tuple) else (None, None)
        if error:
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar como JSON", "", "JSON (*.json)")
        if not filename:
            return
            
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(results, jsonfile, indent=2, default=str)
        except Exception as e:
            print(f"Error al exportar a JSON: {e}")