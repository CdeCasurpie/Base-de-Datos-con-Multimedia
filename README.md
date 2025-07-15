# HeiderDB: Sistema de Gestión de Base de Datos con Soporte Multimedia

## Descripción

HeiderDB es un sistema de gestión de base de datos (DBMS) orientado a datos estructurados, textuales y multimedia, desarrollado como proyecto de investigación y educativo. Ofrece una arquitectura modular con soporte para:

- Estructuras de datos avanzadas (B+Tree, Hash Extensible, ISAM, Sequential File)
- Índices espaciales (R-Tree)
- Búsqueda textual (Índices invertidos)
- Indexación multimedia (imágenes y audio)
- Interfaz CLI y GUI

## Características Principales

- **Estructuras de Indexación**:
  - B+ Tree: Para búsquedas eficientes por rango y exactas
  - Hash Extensible: Para búsquedas exactas de alta velocidad
  - ISAM: Para datos relativamente estáticos
  - Sequential File: Para pequeños conjuntos de datos
  - R-Tree: Para datos espaciales/geométricos
  - Índices Invertidos: Para búsqueda textual y por relevancia

- **Soporte de Tipos de Datos**:
  - Tipos básicos: INT, FLOAT, VARCHAR, DATE, BOOLEAN
  - Tipos espaciales: POINT, POLYGON, LINESTRING, GEOMETRY
  - Tipo multimedia: Almacenamiento e indexación de imágenes y audio

- **Búsquedas Avanzadas**:
  - Búsqueda textual: por términos individuales, booleana (AND/OR), rankeada por relevancia
  - Búsqueda espacial: por radio, intersección, vecino más cercano, rango
  - Búsqueda multimedia: por similitud visual o acústica

- **Interfaces**:
  - CLI: Interfaz de línea de comandos interactiva con soporte para SQL
  - GUI: Interfaz gráfica para exploración visual de datos y resultados
  - Cliente/Servidor: Modelo de comunicación mediante sockets

## Requisitos

- Python 3.8+
- Dependencias (instalables mediante `requirements.txt`):
  - PyQt5 (para GUI)
  - NumPy, SciPy (para cálculos)
  - OpenCV (para procesamiento de imágenes)
  - TensorFlow, Keras (para extracción de características)
  - librosa (para procesamiento de audio)
  - rtree (para indexación espacial)
  - nltk (para procesamiento de texto)

## Instalación

1. Clone el repositorio:
   ```bash
   git clone https://github.com/usuario/Base-de-Datos-con-Multimedia.git
   cd Base-de-Datos-con-Multimedia
   ```

2. Instale las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Asegúrese de descargar los recursos necesarios para NLTK:
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```

## Ejecución

El sistema se puede ejecutar de varias formas:

### Interfaz Gráfica (GUI)

```bash
python -m HeiderDB.main
# o simplemente
python -m HeiderDB.main --gui
```

### Interfaz de Línea de Comandos (CLI)

```bash
python -m HeiderDB.main --cli
```

### Aplicación de Prueba

```bash
python -m TestApp.main
```

### Pruebas Unitarias

```bash
python -m HeiderDB.test.test_btree
python -m HeiderDB.test.test_inverted_index
python -m HeiderDB.test.test_rtree
# etc...
```

### Modo Cliente/Servidor

1. Primero inicie el servidor:
   ```bash
   python -m HeiderDB.server
   ```

2. Luego, conéctese con el cliente:
   ```python
   from HeiderDB.client import HeiderClient
   
   client = HeiderClient()
   result = client.send_query("SELECT * FROM tabla")
   print(result)
   ```

## Guía de Uso

### Comandos SQL Básicos

#### Crear una tabla

```sql
CREATE TABLE personas (
  id INT,
  nombre VARCHAR(100),
  edad INT,
  ubicacion POINT
) USING INDEX bplus_tree(id);
```

#### Crear tabla desde archivo

```sql
CREATE TABLE documentos 
FROM FILE '/ruta/al/archivo.json'
USING INDEX bplus_tree(id);
```

#### Insertar datos

```sql
INSERT INTO personas VALUES (1, 'Juan Pérez', 30, 'POINT(10 20)');
```

#### Consultar datos

```sql
-- Consulta simple
SELECT * FROM personas WHERE id = 1;

-- Consulta por rango
SELECT * FROM personas WHERE edad BETWEEN 20 AND 30;

-- Consulta espacial
SELECT * FROM personas WHERE ubicacion WITHIN 5 OF POINT(10 20);
```

### Índices Textuales

#### Crear un índice invertido

```sql
CREATE INVERTED INDEX idx_nombre ON personas (nombre);
```

#### Consultas textuales

```sql
-- Búsqueda por término
SELECT * FROM personas WHERE nombre CONTAINS 'Juan';

-- Búsqueda booleana
SELECT * FROM personas WHERE nombre CONTAINS 'Juan AND Pérez';
SELECT * FROM personas WHERE nombre CONTAINS 'Juan OR Pedro';

-- Búsqueda por relevancia
SELECT * FROM personas WHERE nombre RANKED BY 'Juan programador';
```

### Índices Espaciales

#### Crear un índice espacial

```sql
CREATE SPATIAL INDEX ON personas (ubicacion);
```

#### Consultas espaciales

```sql
-- Búsqueda por radio
SELECT * FROM personas WHERE ubicacion WITHIN 5 OF POINT(10 20);

-- Búsqueda por intersección
SELECT * FROM personas WHERE ubicacion INTERSECTS POLYGON((0 0, 10 0, 10 10, 0 10, 0 0));

-- Vecinos más cercanos
SELECT * FROM personas WHERE ubicacion NEAREST POINT(10 20) LIMIT 5;

-- Búsqueda por rango espacial
SELECT * FROM personas WHERE ubicacion IN RANGE(POINT(0 0), POINT(20 20));
```

### Comandos de Administración

```sql
-- Listar tablas
TABLES;

-- Mostrar estructura de tabla
DESCRIBE personas;

-- Estadísticas de índices
STATS personas;

-- Eliminar tabla
DROP TABLE personas;
```

## Arquitectura del Sistema

HeiderDB está organizado en los siguientes componentes principales:

1. **Núcleo de Base de Datos (`database/`)**
   - `database.py`: Coordinador principal
   - `table.py`: Manejo de tablas y registros
   - `parser.py`: Procesador de consultas SQL
   - `index_base.py`: Clase base para todos los índices

2. **Estructuras de Indexación (`database/indexes/`)**
   - Estructuras clásicas: B+Tree, Hash Extensible, ISAM, Sequential File
   - Índices espaciales: R-Tree
   - Índices textuales: Inverted Index
   - Índices multimedia: Vector Index con clustering

3. **Componentes Multimedia**
   - `feature_extractor.py`: Extracción de características de imágenes y audio
   - `vector_index.py`: Indexación de vectores de características
   - `multimedia_storage.py`: Almacenamiento de archivos multimedia
   - `text_processor.py`: Procesamiento de texto para búsqueda

4. **Interfaces de Usuario**
   - CLI: Interfaz interactiva en `test_database.py`
   - GUI: Interfaz gráfica basada en PyQt5 en `ui/`

5. **Cliente/Servidor**
   - `server.py`: Servidor TCP para procesar consultas remotas
   - `client.py`: Cliente para envío de consultas al servidor

## Limitaciones y Consideraciones

- El sistema está diseñado principalmente con fines educativos y de investigación
- No se recomienda para datos críticos o en entornos de producción
- El rendimiento puede variar significativamente dependiendo del tamaño de los datos
- La indexación multimedia requiere espacio adicional para almacenar vectores de características
- La extracción de características para multimedia puede ser intensiva en CPU y memoria

## Licencia

Este proyecto está licenciado bajo [su licencia aquí].

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abra un issue o pull request para mejoras o correcciones.