from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, 
                            QPushButton, QHBoxLayout, QComboBox,
                            QLabel, QMessageBox, QApplication)
from PyQt5.QtCore import pyqtSignal, Qt
from database.database import Database

class QueryPanel(QWidget):
    query_executed = pyqtSignal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        layout = QVBoxLayout(self)

        # Tipo de consulta
        options_layout = QHBoxLayout()
        self.query_type_label = QLabel("Tipo de consulta:")
        self.query_type_combo = QComboBox()
        self.query_type_combo.addItems([
            "SQL Personalizado", "SELECT", "INSERT",
            "CREATE TABLE", "CREATE TABLE FROM FILE",
            "CREATE SPATIAL INDEX", "DELETE", "DROP TABLE"
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
        layout.addLayout(button_layout)

        # Conexiones
        self.execute_button.clicked.connect(self.execute_query)
        self.clear_button.clicked.connect(self.query_editor.clear)
        self.template_button.clicked.connect(self.show_templates)
        self.examples_button.clicked.connect(self.show_examples)
        self.query_type_combo.currentIndexChanged.connect(self.update_template)

    def execute_query(self):
        query = self.query_editor.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "Consulta vacía", "Por favor ingrese una consulta SQL.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            results, error = self.db.execute_query(query)
            self.query_executed.emit((results, error))
        except Exception as e:
            self.query_executed.emit((None, str(e)))
        finally:
            QApplication.restoreOverrideCursor()

    def set_query_text(self, text):
        self.query_editor.setText(text)

    def show_templates(self):
        templates = {
            "SELECT": 'SELECT * FROM nombre_tabla WHERE columna1 = valor;',
            "INSERT": 'INSERT INTO nombre_tabla VALUES (valor1, valor2, ...);',
            "CREATE TABLE": (
                'CREATE TABLE nombre_tabla (\n'
                '    columna1 TIPO [KEY] [INDEX tipo],\n'
                '    columna2 TIPO [SPATIAL INDEX]\n'
                ') using index tipo(columna1);'
            ),
            "CREATE TABLE FROM FILE": (
                'CREATE TABLE nombre_tabla FROM FILE "/ruta/archivo.ext" ' 
                'USING INDEX tipo("columna1");'
            ),
            "CREATE SPATIAL INDEX": 'CREATE SPATIAL INDEX idx_nombre ON nombre_tabla (columna_spatial);',
            "DELETE": 'DELETE FROM nombre_tabla WHERE columna1 = valor;',
            "DROP TABLE": 'DROP TABLE nombre_tabla;'
        }
        dialog = QMessageBox()
        dialog.setWindowTitle("Plantillas de consultas")
        content = ""
        for name, query in templates.items():
            content += f"--- {name} ---\n{query}\n\n"
        dialog.setStyleSheet("QLabel { min-width: 600px; }")
        dialog.setText(content)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def show_examples(self):
        examples = {
            "Ejemplo espacial": 'SELECT columna_spatial FROM nombre_tabla WHERE columna_spatial WITHIN ((X, Y), R);'
        }
        dialog = QMessageBox()
        dialog.setWindowTitle("Ejemplos prácticos")
        content = ""
        for name, query in examples.items():
            content += f"--- {name} ---\n{query}\n\n"
        dialog.setStyleSheet("QLabel { min-width: 600px; }")
        dialog.setText(content)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def update_template(self, index):
        templates = {
            0: "",  # SQL Personalizado
            1: 'SELECT * FROM nombre_tabla WHERE columna1 = valor;',  # SELECT
            2: 'INSERT INTO nombre_tabla VALUES (valor1, valor2, ...);',  # INSERT
            3: (
                'CREATE TABLE nombre_tabla (\n'
                '    columna1 TIPO [KEY] [INDEX tipo],\n'
                '    columna2 TIPO [SPATIAL INDEX]\n'
                ') using index tipo(columna1);'
            ),  # CREATE TABLE
            4: (
                'CREATE TABLE nombre_tabla FROM FILE "/ruta/archivo.ext" ' 
                'USING INDEX tipo("columna1");'
            ),  # CREATE TABLE FROM FILE
            5: 'CREATE SPATIAL INDEX idx_nombre ON nombre_tabla (columna_spatial);',  # CREATE SPATIAL INDEX
            6: 'DELETE FROM nombre_tabla WHERE columna1 = valor;',  # DELETE
            7: 'DROP TABLE nombre_tabla;'  # DROP TABLE
        }
        if index in templates:
            self.query_editor.setText(templates[index])
