import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QSplitter, QStatusBar, QMessageBox, QPushButton, QTextEdit)
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
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_header = QLabel("Tablas y Estructuras")
        left_header.setStyleSheet("font-weight: bold; padding: 5px;")
        left_layout.addWidget(left_header)
        
        # Árbol de tablas
        self.tables_tree = TablesTree()
        left_layout.addWidget(self.tables_tree)
        
        # Botón para refrescar tablas
        refresh_button = QPushButton("Refrescar tablas")
        refresh_button.clicked.connect(self.tables_tree.refresh_tables)
        left_layout.addWidget(refresh_button)
        
        # Panel derecho (Consultas y resultados)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pestañas para las funcionalidades
        tabs = QTabWidget()
        
        # Tab de consulta SQL
        query_tab = QWidget()
        query_layout = QVBoxLayout(query_tab)
        query_layout.setContentsMargins(5, 5, 5, 5)
        
        # Panel de consultas
        self.query_panel = QueryPanel()
        query_layout.addWidget(self.query_panel)
        
        # Panel de resultados
        self.result_panel = ResultPanel()
        query_layout.addWidget(self.result_panel)
        
        tabs.addTab(query_tab, "Consulta SQL")
        
        # Tab de información
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml(self._get_info_html())
        
        info_layout.addWidget(info_text)
        tabs.addTab(info_tab, "Información")
        
        right_layout.addWidget(tabs)
        
        # Añadir widgets al splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])  # Tamaños iniciales
        
        main_layout.addWidget(splitter)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sistema iniciado correctamente")
        
        # Configurar conexiones
        self.query_panel.query_executed.connect(self.result_panel.update_results)
        self.query_panel.query_executed.connect(self._on_query_executed)
        self.tables_tree.table_selected.connect(self._on_table_selected)
        
    def _on_query_executed(self, result):
        """Maneja el resultado de la ejecución de una consulta"""
        results, error = result
        
        if error:
            self.status_bar.showMessage(f"Error: {error}")
        else:
            if isinstance(results, list):
                item_text = "registros" if len(results) != 1 else "registro"
                self.status_bar.showMessage(f"Consulta completada: {len(results)} {item_text} encontrados")
            else:
                self.status_bar.showMessage("Consulta ejecutada correctamente")
            
            # Refrescar el árbol de tablas
            self.tables_tree.refresh_tables()
            
    def _on_table_selected(self, table_name):
        """Maneja la selección de una tabla en el árbol"""
        query = f"SELECT * FROM {table_name};"
        self.query_panel.set_query_text(query)

    def _get_info_html(self):
        """Retorna HTML con información del sistema con tema oscuro"""
        return """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #2c2c2c;
                    color: #ecf0f1;
                }
                h1 { color: #ecf0f1; }
                h2 { color: #3498db; }
                h3 { color: #bdc3c7; }
                .feature { margin-left: 20px; }
                code {
                    background-color: #34495e;
                    color: #ecf0f1;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                pre {
                    background-color: #34495e;
                    color: #ecf0f1;
                    padding: 10px;
                    border-radius: 5px;
                    overflow: auto;
                }
                ul {
                    margin-top: 0;
                }
                ul li {
                    margin-bottom: 4px;
                }
            </style>
        </head>
        <body>
            <h1>Sistema de Base de Datos Multimodal</h1>
            <p>Este sistema implementa una base de datos con soporte para múltiples estructuras de índices y tipos de datos espaciales.</p>

            <h2>Características principales</h2>
            <div class="feature">
                <h3>Estructuras de índices soportadas</h3>
                <ul>
                    <li><strong>bplus_tree</strong> - Árbol B+ para búsquedas eficientes por rango y valor</li>
                    <li><strong>sequential_file</strong> - Archivo secuencial con área de overflow</li>
                    <li><strong>extendible_hash</strong> - Hash dinámico con directorio extensible</li>
                    <li><strong>isam_sparse</strong> - Índice disperso basado en ISAM</li>
                    <li><strong>R-Tree</strong> - Índice espacial para datos geométricos</li>
                </ul>
            </div>

            <div class="feature">
                <h3>Tipos de datos soportados</h3>
                <ul>
                    <li><strong>INT</strong> - Números enteros</li>
                    <li><strong>FLOAT</strong> - Números de punto flotante</li>
                    <li><strong>VARCHAR(n)</strong> - Cadenas de caracteres de longitud variable</li>
                    <li><strong>DATE</strong> - Fechas</li>
                    <li><strong>BOOLEAN</strong> - Valores booleanos (true/false)</li>
                    <li><strong>POINT</strong> - Puntos espaciales (x, y)</li>
                    <li><strong>POLYGON</strong> - Polígonos definidos por vértices</li>
                    <li><strong>LINESTRING</strong> - Líneas definidas por puntos</li>
                    <li><strong>GEOMETRY</strong> - Geometrías genéricas</li>
                </ul>
            </div>

            <div class="feature">
                <h3>Operaciones espaciales soportadas</h3>
                <ul>
                    <li><strong>WITHIN</strong> - Búsqueda por radio alrededor de un punto</li>
                    <li><strong>INTERSECTS</strong> - Búsqueda por intersección geométrica</li>
                    <li><strong>NEAREST</strong> - Búsqueda de vecinos más cercanos</li>
                    <li><strong>IN_RANGE</strong> - Búsqueda en un rango espacial rectangular</li>
                </ul>
            </div>

            <h2>Ejemplos de consultas válidas</h2>
            <div class="feature">
                <h3>Creación de tablas</h3>
                <pre><code>CREATE TABLE usuarios (
    id INT KEY,
    nombre VARCHAR(50),
    email VARCHAR(100),
    activo BOOLEAN
) using index bplus_tree(id);</code></pre>

                <h3>Tabla con datos espaciales</h3>
                <pre><code>CREATE TABLE lugares (
    id INT KEY,
    nombre VARCHAR(50),
    ubicacion POINT SPATIAL INDEX,
    area POLYGON
) using index bplus_tree(id);</code></pre>

                <h3>Creación de índice espacial</h3>
                <pre><code>CREATE SPATIAL INDEX idx_ubicacion ON lugares (ubicacion);</code></pre>

                <h3>Consultas espaciales</h3>
                <pre><code>-- Búsqueda por radio
SELECT * FROM lugares WHERE ubicacion WITHIN ((10, 20), 5.0);

-- Búsqueda por intersección
SELECT * FROM lugares WHERE area INTERSECTS "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))";

-- Búsqueda de vecinos cercanos
SELECT * FROM lugares WHERE ubicacion NEAREST (0, 0) LIMIT 3;

-- Búsqueda por rango espacial
SELECT * FROM lugares WHERE ubicacion IN_RANGE ((0, 0), (10, 10));</code></pre>

                <h3>Inserción de datos espaciales</h3>
                <pre><code>INSERT INTO lugares VALUES (
    1, 
    "Parque Central", 
    "POINT(10.5 20.3)",
    "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))"
);</code></pre>
            </div>
        </body>
        </html>
        """


        
    def closeEvent(self, event):
        """Maneja el cierre de la ventana principal"""
        reply = QMessageBox.question(self, 'Confirmación', 
                                    '¿Está seguro de que desea salir?',
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


# Código para iniciar la aplicación
if __name__ == "__main__":
    from database.database import Database
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Usar estilo Fusion para mejor apariencia
    
    # Mostrar ventana principal
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())