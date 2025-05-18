from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from database.database import Database

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
        try:
            result = self.db.list_tables()
            
            self.clear()
            
            if "error" in result:
                error_item = QTreeWidgetItem(self)
                error_item.setText(0, f"Error: {result['error']}")
                return
                
            if not result.get("result") or not result["result"].get("tables"):
                empty_item = QTreeWidgetItem(self)
                empty_item.setText(0, "No hay tablas disponibles")
                return
            
            for table_name in result["result"]["tables"]:
                table_item = QTreeWidgetItem(self)
                table_item.setText(0, table_name)
                table_item.setData(0, 256, {"type": "table", "name": table_name})
                
                self._add_table_details(table_item, table_name)
        except Exception as e:
            print(f"Error al actualizar tablas: {e}")
            error_item = QTreeWidgetItem(self)
            error_item.setText(0, f"Error de conexión: {str(e)}")
    
    def _add_table_details(self, parent_item, table_name):
        try:
            result = self.db.get_table(table_name)
            
            if "error" in result:
                error_item = QTreeWidgetItem(parent_item)
                error_item.setText(0, f"Error: {result['error']}")
                return
            
            if "result" in result:
                structure_item = QTreeWidgetItem(parent_item)
                index_type = result["result"].get("index_type", "Unknown")
                structure_item.setText(0, f"Estructura: {index_type}")
                
                columns_item = QTreeWidgetItem(parent_item)
                columns_item.setText(0, "Columnas")
                
                if "columns" in result["result"]:
                    for column in result["result"]["columns"]:
                        col_item = QTreeWidgetItem(columns_item)
                        col_name = column.get("name", "")
                        col_type = column.get("type", "")
                        col_item.setText(0, f"{col_name} ({col_type})")
                        
        except Exception as e:
            print(f"Error al obtener detalles de la tabla {table_name}: {e}")
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Error: {str(e)}")
    
    def _on_item_double_clicked(self, item, column):
        data = item.data(0, 256)
        if data and data.get("type") == "table":
            table_name = data.get("name")
            self.table_selected.emit(table_name)