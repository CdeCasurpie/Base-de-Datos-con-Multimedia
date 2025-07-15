from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, 
                            QPushButton, QHBoxLayout, QComboBox,
                            QLabel, QMessageBox, QApplication)
from PyQt5.QtCore import pyqtSignal, Qt
from database.database import Database

class QueryPanel(QWidget):
    query_executed = pyqtSignal(tuple)  # Signal emits (results, error)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.db = Database()
        
        layout = QVBoxLayout(self)
        
        # Panel superior con opciones
        options_layout = QHBoxLayout()
        
        self.query_type_label = QLabel("Tipo de consulta:")
        self.query_type_combo = QComboBox()
        self.query_type_combo.addItems([
            "SQL Personalizado", 
            "SELECT", 
            "INSERT", 
            "CREATE TABLE", 
            "CREATE TABLE FROM FILE",
            "CREATE SPATIAL INDEX",
            "DELETE"
        ])
        options_layout.addWidget(self.query_type_label)
        options_layout.addWidget(self.query_type_combo)

        options_layout.addStretch(1)
        layout.addLayout(options_layout)
        
        # Editor de consulta
        self.query_editor = QTextEdit()
        self.query_editor.setPlaceholderText("Ingrese su consulta SQL aquí...")
        self.query_editor.setMinimumHeight(150)
        layout.addWidget(self.query_editor)
        
        # Botones
        button_layout = QHBoxLayout()
        self.execute_button = QPushButton("Ejecutar")
        self.execute_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.clear_button = QPushButton("Limpiar")
        self.template_button = QPushButton("Plantillas")
        self.examples_button = QPushButton("Ejemplos")
        
        button_layout.addWidget(self.execute_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.template_button)
        button_layout.addWidget(self.examples_button)
        layout.addLayout(button_layout)
        
        # Conectar señales
        self.execute_button.clicked.connect(self.execute_query)
        self.clear_button.clicked.connect(self.query_editor.clear)
        self.template_button.clicked.connect(self.show_templates)
        self.examples_button.clicked.connect(self.show_examples)
        self.query_type_combo.currentIndexChanged.connect(self.update_template)
        
    def execute_query(self):
        """Ejecuta la consulta actual y emite el resultado"""
        query = self.query_editor.toPlainText()
        if not query.strip():
            QMessageBox.warning(self, "Consulta vacía", "Por favor ingrese una consulta SQL.")
            return
        
        # Mostrar cursor de espera
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            results, error = self.db.execute_query(query)
            self.query_executed.emit((results, error))
        except Exception as e:
            self.query_executed.emit((None, str(e)))
        finally:
            # Restaurar cursor normal
            QApplication.restoreOverrideCursor()
    
    def set_query_text(self, text):
        """Establece el texto de la consulta"""
        self.query_editor.setText(text)
    
    def show_templates(self):
        """Muestra una ventana con plantillas de consultas"""
        templates = {
            "CREATE TABLE": (
                'CREATE TABLE nombre_tabla (\n'
                '    id INT KEY INDEX bplus_tree,\n'
                '    nombre VARCHAR(30),\n'
                '    edad INT,\n'
                '    puntuacion FLOAT\n'
                ') using index bplus_tree(id);'
            ),
            "CREATE TABLE con archivo": (
                'CREATE TABLE nombre_tabla FROM FILE "/ruta/archivo.json"\n'
                'USING INDEX bplus_tree("id");'
            ),
            "CREATE TABLE con geometría": (
                'CREATE TABLE lugares (\n'
                '    id INT KEY,\n'
                '    nombre VARCHAR(50),\n'
                '    ubicacion POINT SPATIAL INDEX,\n'
                '    area POLYGON\n'
                ') using index bplus_tree(id);'
            ),
            "CREATE SPATIAL INDEX": (
                'CREATE SPATIAL INDEX idx_ubicacion ON lugares (ubicacion);'
            ),
            "SELECT simple": 'SELECT * FROM nombre_tabla;',
            "SELECT con WHERE": 'SELECT columna1, columna2 FROM nombre_tabla WHERE columna1 = valor;',
            "SELECT espacial": (
                '-- Buscar por radio\n'
                'SELECT * FROM lugares WHERE ubicacion WITHIN ((10.5, 20.3), 5.0);\n\n'
                '-- Buscar por intersección\n'
                'SELECT * FROM lugares WHERE area INTERSECTS "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))";\n\n'
                '-- Buscar vecinos cercanos\n'
                'SELECT * FROM lugares WHERE ubicacion NEAREST (0, 0) LIMIT 5;\n\n'
                '-- Buscar por rango espacial\n'
                'SELECT * FROM lugares WHERE ubicacion IN_RANGE ((0, 0), (100, 100));'
            ),
            "INSERT": 'INSERT INTO nombre_tabla VALUES (1, "texto", 25, 95.5);',
            "INSERT espacial": 'INSERT INTO lugares VALUES (1, "Parque Central", "POINT(10.5 20.3)", "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))");',
            "DELETE": 'DELETE FROM nombre_tabla WHERE id = 1;'
        }
        
        dialog = QMessageBox()
        dialog.setWindowTitle("Plantillas de consultas")
        
        # Crea un texto con las plantillas formateadas
        template_text = ""
        for name, query in templates.items():
            template_text += f"--- {name} ---\n{query}\n\n"
            
        dialog.setStyleSheet("QLabel { min-width: 600px; }")
        dialog.setText(template_text)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
    
    def show_examples(self):
        """Muestra ejemplos prácticos de consultas"""
        examples = {
            "Crear tabla de usuarios": (
                'CREATE TABLE usuarios (\n'
                '    id INT KEY,\n'
                '    nombre VARCHAR(50),\n'
                '    email VARCHAR(100),\n'
                '    edad INT\n'
                ') using index bplus_tree(id);'
            ),
            "Crear tabla con ubicaciones": (
                'CREATE TABLE restaurantes (\n'
                '    id INT KEY,\n'
                '    nombre VARCHAR(50),\n'
                '    direccion VARCHAR(100),\n'
                '    ubicacion POINT SPATIAL INDEX,\n'
                '    area_servicio POLYGON\n'
                ') using index bplus_tree(id);'
            ),
            "Insertar usuario": 'INSERT INTO usuarios VALUES (1, "Juan Pérez", "juan@example.com", 28);',
            "Insertar restaurante": (
                'INSERT INTO restaurantes VALUES (\n'
                '    1,\n'
                '    "Pizzería Roma",\n'
                '    "Calle Principal 123",\n'
                '    "POINT(34.0522 -118.2437)",\n'
                '    "POLYGON((34.05 -118.25, 34.06 -118.25, 34.06 -118.24, 34.05 -118.24, 34.05 -118.25))"\n'
                ');'
            ),
            "Buscar restaurantes cercanos": 'SELECT * FROM restaurantes WHERE ubicacion WITHIN ((34.0522, -118.2437), 5.0);',
            "Buscar por rango de edad": 'SELECT * FROM usuarios WHERE edad BETWEEN 20 AND 30;'
        }
        
        # Selecciona un ejemplo
        example_keys = list(examples.keys())
        
        dialog = QMessageBox()
        dialog.setWindowTitle("Ejemplos prácticos")
        
        # Crea un texto con los ejemplos formateados
        example_text = ""
        for name, query in examples.items():
            example_text += f"--- {name} ---\n{query}\n\n"
            
        dialog.setStyleSheet("QLabel { min-width: 600px; }")
        dialog.setText(example_text)
        dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Apply)
        dialog.setButtonText(QMessageBox.Apply, "Usar primer ejemplo")
        
        result = dialog.exec_()
        if result == QMessageBox.Apply and example_keys:
            # Cargar el primer ejemplo
            self.set_query_text(examples[example_keys[0]])
    
    def update_template(self, index):
        """Actualiza el editor con una plantilla según el tipo seleccionado"""
        templates = {
            0: "",  # SQL Personalizado
            1: "SELECT * FROM nombre_tabla WHERE condicion;",  # SELECT
            2: "INSERT INTO nombre_tabla VALUES (1, \"texto\", 25);",  # INSERT
            3: (  # CREATE TABLE
                "CREATE TABLE nombre_tabla (\n"
                "    id INT KEY,\n"
                "    nombre VARCHAR(50),\n"
                "    valor FLOAT\n"
                ") using index bplus_tree(id);"
            ),
            4: (  # CREATE TABLE FROM FILE
                "CREATE TABLE nombre_tabla FROM FILE \"/ruta/archivo.json\"\n"
                "USING INDEX bplus_tree(\"id\");"
            ),
            5: "CREATE SPATIAL INDEX idx_ubicacion ON lugares (ubicacion);",  # CREATE SPATIAL INDEX
            6: "DELETE FROM nombre_tabla WHERE id = 1;"  # DELETE
        }
        
        if index in templates:
            self.query_editor.setText(templates[index])