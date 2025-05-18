from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, 
                            QPushButton, QHBoxLayout, QComboBox,
                            QLabel, QMessageBox)
from PyQt5.QtCore import pyqtSignal
from database.database import Database

class QueryPanel(QWidget):
    query_executed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.db = Database()
        
        layout = QVBoxLayout(self)
        
        options_layout = QHBoxLayout()
        
        self.query_type_label = QLabel("Tipo de consulta:")
        self.query_type_combo = QComboBox()
        self.query_type_combo.addItems(["SQL Personalizado", "SELECT", "INSERT", "CREATE TABLE", "DELETE"])
        options_layout.addWidget(self.query_type_label)
        options_layout.addWidget(self.query_type_combo)

        options_layout.addStretch(1)
        layout.addLayout(options_layout)
        
        self.query_editor = QTextEdit()
        self.query_editor.setPlaceholderText("Ingrese su consulta SQL aquí...")
        self.query_editor.setMinimumHeight(150)
        layout.addWidget(self.query_editor)
        
        button_layout = QHBoxLayout()
        self.execute_button = QPushButton("Ejecutar")
        self.execute_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.clear_button = QPushButton("Limpiar")
        self.template_button = QPushButton("Plantillas")
        button_layout.addWidget(self.execute_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.template_button)
        layout.addLayout(button_layout)
        
        self.execute_button.clicked.connect(self.execute_query)
        self.clear_button.clicked.connect(self.query_editor.clear)
        self.template_button.clicked.connect(self.show_templates)
        self.query_type_combo.currentIndexChanged.connect(self.update_template)
        
    def execute_query(self):
        query = self.query_editor.toPlainText()
        if not query.strip():
            QMessageBox.warning(self, "Consulta vacía", "Por favor ingrese una consulta SQL.")
            return
        
        try:
            result = self.db.execute_query(query)
            self.query_executed.emit(result)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al ejecutar la consulta: {str(e)}")
    
    def set_query_text(self, text):
        self.query_editor.setText(text)
    
    def show_templates(self):
        templates = {
            "CREATE TABLE": 'CREATE TABLE nombre_tabla (id INT KEY INDEX SEQ, nombre VARCHAR[20] INDEX BTree, valor FLOAT);',
            "CREATE TABLE con archivo": 'CREATE TABLE nombre_tabla FROM "ruta/archivo.csv" USING INDEX BTREE;',
            "SELECT simple": 'SELECT * FROM nombre_tabla;',
            "SELECT con WHERE": 'SELECT columna1, columna2 FROM nombre_tabla WHERE columna1 = valor;',
            "INSERT": 'INSERT INTO nombre_tabla VALUES (1, "texto", 10.5);',
            "DELETE": 'DELETE FROM nombre_tabla WHERE id = 1;'
        }
        
        dialog = QMessageBox()
        dialog.setWindowTitle("Plantillas de consultas")
        template_text = "\n\n".join([f"{name}:\n{query}" for name, query in templates.items()])
        dialog.setText(template_text)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
    
    def update_template(self, index):
        templates = {
            0: "",  # SQL Personalizado
            1: "SELECT * FROM nombre_tabla;",  # SELECT
            2: "INSERT INTO nombre_tabla VALUES (1, \"texto\", 10.5);",  # INSERT
            3: "CREATE TABLE nombre_tabla (id INT KEY INDEX SEQ, nombre VARCHAR[20], valor FLOAT);",  # CREATE TABLE
            4: "DELETE FROM nombre_tabla WHERE id = 1;"  # DELETE
        }
        
        if index > 0:
            self.query_editor.setText(templates.get(index, ""))