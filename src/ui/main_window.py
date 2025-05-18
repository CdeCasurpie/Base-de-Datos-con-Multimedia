import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QSplitter, QStatusBar)
from PyQt5.QtCore import Qt
from ui.result_panel import ResultPanel
from ui.tables_tree import TablesTree
from ui.query_panel import QueryPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Base de Datos Multimodal")
        self.resize(1200, 800)
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Splitter horizontal para dividir la pantalla
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo (Tablas y estructura)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Tablas y Estructuras"))
        
        # Árbol de tablas
        self.tables_tree = TablesTree()
        left_layout.addWidget(self.tables_tree)
        
        # Panel derecho (Consultas y resultados)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Pestañas para las funcionalidades
        tabs = QTabWidget()
        
        # Tab de consulta SQL
        query_tab = QWidget()
        query_layout = QVBoxLayout(query_tab)
        
        # Panel de consultas
        self.query_panel = QueryPanel()
        query_layout.addWidget(self.query_panel)
        
        # Panel de resultados
        self.result_panel = ResultPanel()
        query_layout.addWidget(self.result_panel)
        
        tabs.addTab(query_tab, "Consulta SQL")
        

        right_layout.addWidget(tabs)
        
        # Añadir widgets al splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])  # Tamaños iniciales
        
        main_layout.addWidget(splitter)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Configurar conexiones
        self.query_panel.query_executed.connect(self.result_panel.update_results)
        self.query_panel.query_executed.connect(self._on_query_executed)
        self.tables_tree.table_selected.connect(self._on_table_selected)
        
    def _on_query_executed(self, result):
        if "error" in result:
            self.status_bar.showMessage(f"Error: {result['error']}")
        else:
            self.status_bar.showMessage("Consulta ejecutada correctamente")
            self.tables_tree.refresh_tables()
            
    def _on_table_selected(self, table_name):
        query = f"SELECT * FROM {table_name};"
        self.query_panel.set_query_text(query)