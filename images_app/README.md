# Sistema de Similitud de Imágenes

Sistema web para búsqueda de imágenes similares usando la base de datos multimedia HeiderDB.

## Estructura del Proyecto

```
images_app/
├── app.py                     # Servidor Flask principal
├── requirements.txt           # Dependencias Python
├── temp_uploads/             # Archivos temporales
├── static/
│   ├── images/              # Imágenes servidas al frontend
│   ├── css/
│   │   ├── styles.css       # Estilos principales
│   │   └── image-interface.css  # Estilos de la interfaz
│   ├── html/
│   │   ├── index.html       # HTML original
│   │   └── index_new.html   # Nueva interfaz de similitud
│   └── js/
│       └── image-handler.js # Lógica de frontend
```

## Instalación

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Asegurar que HeiderDB esté ejecutándose en puerto 54321

3. Tener datos de imágenes en la tabla 'galeria' con índice multimedia

## Uso

1. Ejecutar el servidor:

```bash
python app.py
```

2. Abrir navegador en: http://localhost:5001

3. Usar la nueva interfaz en: http://localhost:5001/static/html/index_new.html

## API Endpoints

- `POST /api/analyze-similarity` - Analizar similitud de imagen
- `GET /api/health` - Estado del servidor
- `GET /api/test-db` - Probar conexión a BD
- `GET /api/list-images` - Listar imágenes en BD
- `GET /static/images/<filename>` - Servir archivos de imagen

## Características

- Interfaz moderna con animaciones CSS
- Drag & drop para subir imágenes
- Análisis de similitud en tiempo real
- Visualización de resultados con estadísticas
- Soporte para JPG, PNG, BMP, TIFF, WEBP
- Integración con base de datos HeiderDB
- Modo demostración sin conexión a BD

## Configuración de Base de Datos

El sistema espera una tabla 'galeria_messi' con:

- Campo 'id' (clave primaria)
- Campo 'imagen' (ruta del archivo)
- Campo 'nombre' (opcional, nombre descriptivo)
- Índice multimedia SIFT en el campo 'imagen'

Ejemplo de comandos HeiderDB:

```sql
CREATE TABLE galeria_messi (id INT KEY INDEX bplus_tree, nombre VARCHAR(100), imagen IMAGE);
INSERT INTO galeria_messi VALUES (1, 'Messi Principal', 'C:\Users\ASUS\OneDrive\Documentos\Base-de-Datos-con-Multimedia\HeiderDB\test_images\messi.jpg');
INSERT INTO galeria_messi VALUES (2, 'Messi 2', 'C:\Users\ASUS\OneDrive\Documentos\Base-de-Datos-con-Multimedia\HeiderDB\test_images\messi2.jpg');
CREATE MULTIMEDIA INDEX idx_messi_img ON galeria_messi (imagen) WITH TYPE image METHOD sift;
```

## Pasos para configurar los datos:

1. Ejecutar el servidor HeiderDB:

```bash
python -m HeiderDB.server
```

2. En otra terminal, conectar al CLI y ejecutar:

```bash
python -m HeiderDB.client
```

3. Crear la estructura y datos:

```sql
DROP TABLE galeria_messi;
CREATE TABLE galeria_messi (id INT KEY INDEX bplus_tree, nombre VARCHAR(100), imagen IMAGE);
INSERT INTO galeria_messi VALUES (1, 'Messi Principal', 'C:\Users\ASUS\OneDrive\Documentos\Base-de-Datos-con-Multimedia\HeiderDB\test_images\messi.jpg');
INSERT INTO galeria_messi VALUES (2, 'Messi 2', 'C:\Users\ASUS\OneDrive\Documentos\Base-de-Datos-con-Multimedia\HeiderDB\test_images\messi2.jpg');
INSERT INTO galeria_messi VALUES (3, 'Messi Calvo', 'C:\Users\ASUS\OneDrive\Documentos\Base-de-Datos-con-Multimedia\HeiderDB\test_images\messi_calvo.jpg');
CREATE MULTIMEDIA INDEX idx_messi_img ON galeria_messi (imagen) WITH TYPE image METHOD sift;
```
