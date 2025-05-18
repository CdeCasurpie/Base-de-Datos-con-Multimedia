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
        self.columns = []
    
    def update_results(self, result):
        self.current_data = result
        
        # Limpiar vistas
        self.table_view.clear()
        self.table_view.setRowCount(0)
        self.table_view.setColumnCount(0)
        self.text_view.clear()
        
        if not result or "error" in result:
            # Mostrar error
            error_message = result.get("error", "Error desconocido") if result else "No hay datos"
            self.text_view.setTextColor(Qt.red)
            self.text_view.setText(error_message)
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
            return
            
        # Actualizar vista de texto
        self.text_view.setTextColor(Qt.black)
        self.text_view.setText(json.dumps(result, indent=2))
        
        # Obtener datos para la tabla
        if "result" in result and "data" in result["result"]:
            data = result["result"]["data"]
            if "columns" in result["result"]:
                self.columns = result["result"]["columns"]
            else:
                # Intentar inferir columnas del primer registro
                if data and len(data) > 0 and isinstance(data[0], dict):
                    self.columns = list(data[0].keys())
                else:
                    self.columns = []
                    
            self.update_table_view(data)
            self.tabs.setCurrentIndex(0)  # Mostrar tab de tabla
        else:
            # Mostrar mensaje en la tabla
            message = result.get("message", "Operación completada")
            self.text_view.setText(message)
            self.tabs.setCurrentIndex(1)  # Mostrar tab de texto
    
    def update_table_view(self, data):
        if not data:
            return
            
        # Configurar tabla
        self.table_view.setColumnCount(len(self.columns))
        self.table_view.setRowCount(len(data))
        self.table_view.setHorizontalHeaderLabels(self.columns)
        
        # Llenar datos
        for row, record in enumerate(data):
            for col, field in enumerate(self.columns):
                value = record.get(field, "")
                item = QTableWidgetItem(str(value))
                self.table_view.setItem(row, col, item)
    
    def export_to_csv(self):
        if not self.current_data or "result" not in self.current_data or "data" not in self.current_data["result"]:
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar como CSV", "", "CSV (*.csv)")
        if not filename:
            return
            
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Escribir encabezados
                writer.writerow(self.columns)
                # Escribir datos
                for record in self.current_data["result"]["data"]:
                    row = [record.get(field, "") for field in self.columns]
                    writer.writerow(row)
        except Exception as e:
            print(f"Error al exportar a CSV: {e}")
    
    def export_to_json(self):
        if not self.current_data:
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar como JSON", "", "JSON (*.json)")
        if not filename:
            return
            
        try:
            with open(filename, 'w') as jsonfile:
                json.dump(self.current_data, jsonfile, indent=2)
        except Exception as e:
            print(f"Error al exportar a JSON: {e}")