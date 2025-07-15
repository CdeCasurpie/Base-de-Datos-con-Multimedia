from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayuda - Sintaxis SQL")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Contenido de ayuda
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        self.help_browser.setHtml(self.get_help_content())
        
        # Botones
        button_layout = QHBoxLayout()
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        
        layout.addWidget(self.help_browser)
        layout.addLayout(button_layout)
    
    def get_help_content(self):
        """Devuelve el contenido HTML de la ayuda"""
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 15px; }
                h1 { color: #2c3e50; }
                h2 { color: #3498db; margin-top: 20px; }
                h3 { color: #2980b9; }
                pre { background-color: #f8f8f8; padding: 10px; border-radius: 5px; overflow: auto; }
                .table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .table th { background-color: #f2f2f2; }
                .note { background-color: #fef9e7; border-left: 4px solid #f1c40f; padding: 10px; margin: 10px 0; }
                .warning { background-color: #fdedec; border-left: 4px solid #e74c3c; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>Documentación de Sintaxis SQL</h1>
            <p>Esta documentación detalla la sintaxis SQL soportada por el sistema de base de datos multimodal.</p>
            
            <h2>Comandos básicos</h2>
            
            <h3>CREATE TABLE</h3>
            <p>Crea una nueva tabla con columnas y tipos definidos:</p>
            <pre>CREATE TABLE nombre_tabla (
    columna1 tipo1 [KEY] [INDEX tipo_indice] [SPATIAL INDEX],
    columna2 tipo2,
    ...
) [using index tipo_indice(columna_clave)];</pre>

            <p>Donde:</p>
            <ul>
                <li><strong>KEY</strong>: Designa la columna como clave primaria</li>
                <li><strong>INDEX tipo_indice</strong>: Especifica un tipo de índice para la columna</li>
                <li><strong>SPATIAL INDEX</strong>: Crea un índice espacial para la columna (solo tipos espaciales)</li>
                <li><strong>using index</strong>: Define el índice principal de la tabla</li>
            </ul>
            
            <p>Ejemplo:</p>
            <pre>CREATE TABLE clientes (
    id INT KEY,
    nombre VARCHAR(50),
    ubicacion POINT SPATIAL INDEX
) using index bplus_tree(id);</pre>

            <p>Tipos de índices soportados:</p>
            <ul>
                <li><strong>bplus_tree</strong>: Árbol B+ (búsquedas eficientes por rango)</li>
                <li><strong>sequential_file</strong>: Archivo secuencial con área de overflow</li>
                <li><strong>extendible_hash</strong>: Hash extensible (búsquedas rápidas por valor exacto)</li>
                <li><strong>isam_sparse</strong>: ISAM con índice disperso</li>
            </ul>
            
            <h3>CREATE TABLE FROM FILE</h3>
            <p>Crea una tabla importando datos desde un archivo:</p>
            <pre>CREATE TABLE nombre_tabla FROM FILE "ruta_al_archivo" USING INDEX tipo_indice(columna_clave);</pre>
            
            <p>Ejemplo:</p>
            <pre>CREATE TABLE productos FROM FILE "datos/productos.json" USING INDEX bplus_tree(id);</pre>
            
            <p>Formatos soportados: JSON y CSV</p>
            
            <h3>CREATE SPATIAL INDEX</h3>
            <p>Crea un índice espacial para una columna existente:</p>
            <pre>CREATE SPATIAL INDEX nombre_indice ON nombre_tabla (columna_espacial);</pre>
            
            <p>Ejemplo:</p>
            <pre>CREATE SPATIAL INDEX idx_ubicacion ON restaurantes (ubicacion);</pre>
            
            <h3>SELECT</h3>
            <p>Recupera registros de una tabla:</p>
            <pre>SELECT columna1, columna2, ... FROM nombre_tabla [WHERE condición];</pre>
            
            <p>Seleccionar todas las columnas:</p>
            <pre>SELECT * FROM nombre_tabla;</pre>
            
            <h3>INSERT</h3>
            <p>Inserta un nuevo registro en una tabla:</p>
            <pre>INSERT INTO nombre_tabla VALUES (valor1, valor2, ...);</pre>
            
            <p>Ejemplo:</p>
            <pre>INSERT INTO clientes VALUES (1, "Juan Pérez", "POINT(10 20)");</pre>
            
            <h3>DELETE</h3>
            <p>Elimina registros de una tabla:</p>
            <pre>DELETE FROM nombre_tabla WHERE columna = valor;</pre>
            
            <p>Ejemplo:</p>
            <pre>DELETE FROM clientes WHERE id = 1;</pre>
            
            <h2>Tipos de datos</h2>
            <table class="table">
                <tr>
                    <th>Tipo</th>
                    <th>Descripción</th>
                    <th>Ejemplo</th>
                </tr>
                <tr>
                    <td>INT</td>
                    <td>Números enteros</td>
                    <td>42, -7, 0</td>
                </tr>
                <tr>
                    <td>FLOAT</td>
                    <td>Números de punto flotante</td>
                    <td>3.14, -0.01, 2.5e3</td>
                </tr>
                <tr>
                    <td>VARCHAR(n)</td>
                    <td>Texto de longitud variable (máximo n)</td>
                    <td>"Hola mundo"</td>
                </tr>
                <tr>
                    <td>BOOLEAN</td>
                    <td>Valores verdadero/falso</td>
                    <td>true, false</td>
                </tr>
                <tr>
                    <td>DATE</td>
                    <td>Fecha</td>
                    <td>Representación interna</td>
                </tr>
                <tr>
                    <td>POINT</td>
                    <td>Punto espacial (x,y)</td>
                    <td>"POINT(10 20)"</td>
                </tr>
                <tr>
                    <td>POLYGON</td>
                    <td>Polígono definido por vértices</td>
                    <td>"POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))"</td>
                </tr>
                <tr>
                    <td>LINESTRING</td>
                    <td>Línea definida por puntos</td>
                    <td>"LINESTRING(0 0, 10 10, 20 20)"</td>
                </tr>
                <tr>
                    <td>GEOMETRY</td>
                    <td>Cualquier tipo de geometría</td>
                    <td>Varía según el tipo específico</td>
                </tr>
            </table>
            
            <h2>Condiciones WHERE</h2>
            
            <h3>Condiciones estándar</h3>
            <ul>
                <li><code>columna = valor</code>: Igualdad</li>
                <li><code>columna != valor</code>: Desigualdad</li>
                <li><code>columna > valor</code>: Mayor que</li>
                <li><code>columna >= valor</code>: Mayor o igual que</li>
                <li><code>columna < valor</code>: Menor que</li>
                <li><code>columna <= valor</code>: Menor o igual que</li>
                <li><code>columna BETWEEN valor1 AND valor2</code>: Rango inclusivo</li>
            </ul>
            
            <p>Ejemplo:</p>
            <pre>SELECT * FROM productos WHERE precio BETWEEN 10.0 AND 50.0;</pre>
            
            <h3>Condiciones espaciales</h3>
            <ul>
                <li><code>columna WITHIN (punto, radio)</code>: Dentro de un círculo</li>
                <li><code>columna INTERSECTS geometría</code>: Intersecta con geometría</li>
                <li><code>columna NEAREST punto [LIMIT n]</code>: n vecinos más cercanos</li>
                <li><code>columna IN_RANGE (punto_min, punto_max)</code>: Dentro de un rectángulo</li>
            </ul>
            
            <p>Ejemplos:</p>
            <pre>-- Búsqueda por radio (5 unidades desde el punto (10,20))
SELECT * FROM lugares WHERE ubicacion WITHIN ((10, 20), 5.0);

-- Búsqueda por intersección con un polígono
SELECT * FROM lugares WHERE area INTERSECTS "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))";

-- 3 ubicaciones más cercanas al punto (0,0)
SELECT * FROM lugares WHERE ubicacion NEAREST (0, 0) LIMIT 3;

-- Ubicaciones dentro del rectángulo definido por (0,0) y (100,100)
SELECT * FROM lugares WHERE ubicacion IN_RANGE ((0, 0), (100, 100));</pre>

            <div class="note">
                <strong>Nota:</strong> Las coordenadas espaciales se representan como tuplas (x, y) o como strings WKT (Well-Known Text).
            </div>
            
            <h2>Formatos de valores</h2>
            <ul>
                <li><strong>Números:</strong> Directamente sin comillas (10, 3.14)</li>
                <li><strong>Texto:</strong> Entre comillas dobles o simples ("texto", 'texto')</li>
                <li><strong>Punto:</strong> Como tupla (x, y) o WKT "POINT(x y)"</li>
                <li><strong>Polígono:</strong> Como WKT "POLYGON((x1 y1, x2 y2, ...))"</li>
                <li><strong>Booleanos:</strong> true, false (sin comillas)</li>
                <li><strong>Valores nulos:</strong> null (sin comillas)</li>
            </ul>
            
            <div class="warning">
                <strong>Importante:</strong> Las consultas deben terminar con punto y coma (;).
            </div>
        </body>
        </html>
        """

# Uso de ejemplo:
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = HelpDialog()
    dialog.exec_()
