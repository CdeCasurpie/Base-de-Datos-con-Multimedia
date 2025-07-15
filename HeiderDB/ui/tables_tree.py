from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from HeiderDB.database.database import Database

class TablesTree(QTreeWidget):
    table_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.db = Database()
        
        self.setHeaderLabel("Tablas y estructuras")
        self.setColumnCount(1)
        
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        self.refresh_tables()
    
    def refresh_tables(self):
        """Actualiza la lista de tablas disponibles en la base de datos"""
        self.clear()
        
        try:
            self.db._load_tables()
            table_names = self.db.list_tables()
            
            if not table_names:
                empty_item = QTreeWidgetItem(self)
                empty_item.setText(0, "No hay tablas disponibles")
                return
            
            # borrar elementos existentes
            self.clear()
            
            
            for table_name in table_names:
                table_item = QTreeWidgetItem(self)
                table_item.setText(0, table_name)
                table_item.setData(0, 256, {"type": "table", "name": table_name})


                self._add_table_details(table_item, table_name)

        except Exception as e:
            print(f"Error al actualizar tablas: {e}")
            error_item = QTreeWidgetItem(self)
            error_item.setText(0, f"Error: {str(e)}")
    
    def _add_table_details(self, parent_item, table_name):
        """Añade detalles de la tabla al elemento del árbol"""
        try:
            table_info = self.db.get_table_info(table_name)
            
            if not table_info:
                error_item = QTreeWidgetItem(parent_item)
                error_item.setText(0, "No se pudo obtener información")
                return
            
            # Añadir información sobre el índice
            index_item = QTreeWidgetItem(parent_item)
            index_type = table_info["index_type"]
            primary_key = table_info["primary_key"]
            index_item.setText(0, f"Índice: {index_type} ({primary_key})")
            
            # Columnas
            columns_item = QTreeWidgetItem(parent_item)
            columns_item.setText(0, f"Columnas ({len(table_info['columns'])})")
            
            for col_name, col_type in table_info["columns"].items():
                col_item = QTreeWidgetItem(columns_item)
                # Resaltar la columna primary key
                if col_name == primary_key:
                    col_item.setText(0, f"{col_name} ({col_type}) [PK]")
                # Resaltar columnas con índice espacial
                elif col_name in table_info.get("spatial_columns", []):
                    col_item.setText(0, f"{col_name} ({col_type}) [Espacial]")
                else:
                    col_item.setText(0, f"{col_name} ({col_type})")
            
            # Información de registros
            records_item = QTreeWidgetItem(parent_item)
            records_item.setText(0, f"Registros: {table_info['record_count']}")
            
            # Añadir información espacial si existe
            if table_info.get("spatial_columns"):
                spatial_item = QTreeWidgetItem(parent_item)
                spatial_item.setText(0, f"Índices espaciales: {len(table_info['spatial_columns'])}")
                
                for col in table_info["spatial_columns"]:
                    spatial_col_item = QTreeWidgetItem(spatial_item)
                    spatial_col_item.setText(0, f"{col} (R-Tree)")
            
        except Exception as e:
            print(f"Error al obtener detalles de la tabla {table_name}: {e}")
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Error: {str(e)}")
    
    def _on_item_double_clicked(self, item, column):
        """Maneja el evento de doble clic en un elemento del árbol"""
        data = item.data(0, 256)
        if data and data.get("type") == "table":
            table_name = data.get("name")
            self.table_selected.emit(table_name)