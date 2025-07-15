<div style="background: #D7ECF5; border-radius: 5px; padding: 1rem; margin-bottom: 1rem">
<img src="https://www.prototypesforhumanity.com/wp-content/uploads/2022/11/LOGO_UTEC_.png" alt="Banner" height="70" />   
 <div style="font-weight: bold; color:rgb(50, 120, 252); float: right "><u style="font-size: 28px; height:70px; display:flex; flex-direction: column; justify-content: center;">Proyecto BD II | Multimedia BD</u></div>
</div>

**HeiderDB** es una base de datos modular con soporte para índices secuenciales, B+ Trees, índices espaciales (R-Tree), e índices invertidos para texto. Incluye un servidor TCP personalizado y una API de cliente.

---

<div style="margin: 2rem 0;">
<h2 style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem;">Integrantes del Proyecto</h2>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.5rem; margin: 1rem 0;">
<div style="padding: 0.5rem; background: #f8f9fa; border-radius: 3px; color: black">• Cesar Perales</div>
<div style="padding: 0.5rem; background: #f8f9fa; border-radius: 3px; color: black">• Fernando Usurin</div>
<div style="padding: 0.5rem; background: #f8f9fa; border-radius: 3px; color: black">• Fabryzzio Meza</div>
<div style="padding: 0.5rem; background: #f8f9fa; border-radius: 3px; color: black">• Yoselyn Miranda</div>
<div style="padding: 0.5rem; background: #f8f9fa; border-radius: 3px; color: black">• Flavio Tipula</div>
</div>
</div>


### Diagrama de Arquitectura
![Diagrama de Arquitectura](diagrama.jpeg)

## Instalación
### Opción 1: Docker (Recomendado)

#### 1. Clonar el repositorio
```bash
git clone https://github.com/usuario/HeiderDB.git
cd HeiderDB
```

#### 2. Construir imagen Docker
```bash
docker build -t heiderdb .
```

#### 3. Ejecutar servidor
**Linux/macOS:**
```bash
docker run --rm -v "$PWD:/app" -w /app -p 54321:54321 heiderdb
```

**Windows:**
```bash
docker run --rm -v "%cd%:/app" -w /app -p 54321:54321 heiderdb
```

### Opción 2: Instalación Local

**Requisitos:** Python 3.10+

```bash
git clone https://github.com/usuario/HeiderDB.git
cd HeiderDB
pip install -r requirements-base.txt
pip install -r requirements-tf.txt
```

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold;">Uso del Sistema</div>

### Servidor de Base de Datos

Para iniciar el servidor TCP:
```bash
python -m HeiderDB.server
```

El servidor escuchará en `localhost:54321` por defecto.

### Interfaces de Usuario

#### Interfaz Gráfica (GUI)
```bash
python -m HeiderDB.main
```

#### Interfaz de Línea de Comandos (CLI)
```bash
python -m HeiderDB.main --cli
```

### Cliente Programático

#### Usando el cliente desde línea de comandos:
```bash
python HeiderDB/client.py --query "SELECT * FROM usuarios;"
python HeiderDB/client.py --host 127.0.0.1 --port 54321 --query "CREATE TABLE docs (id INT KEY, content VARCHAR(1000));"
```

#### Usando el cliente en código Python:
```python
from HeiderDB.client import HeiderClient

client = HeiderClient()

# Crear tabla con índice de texto
response = client.send_query("""
    CREATE TABLE articulos (
        id INT KEY,
        titulo VARCHAR(200),
        contenido VARCHAR(1000) TEXT INDEX
    ) using index bplus_tree(id);
""")

# Búsqueda textual
response = client.send_query("SELECT * FROM articulos WHERE contenido CONTAINS 'python AND database'")
print(response)

# Búsqueda espacial
response = client.send_query("SELECT * FROM lugares WHERE ubicacion WITHIN ((10, 20), 5.0)")
print(response)
```

### Aplicación de Prueba

Para ejecutar la aplicación de demostración:
```bash
python -m TestApp.main
```

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold; margin-bottom:1rem">Ejecutar Tests</div>

**Nota:** Los tests requieren dependencias instaladas localmente (recomendado Python 3.10+)

## Implementación del Índice Invertido y Multimedial

Para esta implementación se desarrollaron dos nuevos tipos de índices junto con una clase adicional de almacenamiento de datos multimediales:

---

### `InvertedIndex`
Gestiona un índice invertido tradicional para realizar búsquedas eficientes por palabras clave.  
Es ideal para estructuras textuales o contenidos que requieren recuperación basada en términos.

---

### `MultimediaIndex`
Diseñado para manejar contenido multimedial como imágenes y audio. Este índice se divide en dos componentes principales:

##### `FeatureExtractor`
Clase **abstracta** que define la interfaz para la extracción de características.  
Su objetivo es trabajar con **vectores n-dimensionales grandes**, mejorando la calidad de las búsquedas por similitud (a diferencia de vectores pequeños poco representativos).  
Implementaciones concretas:
- `ImageExtractor`: procesa imágenes y extrae características visuales.
- `AudioExtractor`: procesa archivos de audio y extrae características relevantes.

##### `VectorIndex`
Encargado de almacenar los vectores generados por el `FeatureExtractor`, y de ejecutar operaciones de comparación y **búsqueda por similitud** entre vectores.

---

#### `MultimediaStore`
Clase que gestiona el almacenamiento de archivos multimediales.  
En lugar de guardar directamente los bits de los archivos en la base de datos o en memoria, se **mapean rutas absolutas** a los archivos (imágenes o audios) ubicados en una carpeta específica del proyecto.

Este enfoque permite un uso eficiente de los recursos y facilita la gestión de los datos sin sobrecargar la base de datos ni la memoria del sistema.

### Tests de estructuras de índices:
```bash
python -m HeiderDB.test.test_btree          # B+ Tree
python -m HeiderDB.test.test_extendible_hash # Hash Extensible
python -m HeiderDB.test.test_sequential_file # Archivo Secuencial
python -m HeiderDB.test.test_isam_sparse     # ISAM Disperso
python -m HeiderDB.test.test_rtree           # R-Tree (Espacial)
python -m HeiderDB.test.test_inverted_index  # Índice Invertido (Texto)
```

### Tests del sistema:
```bash
python -m HeiderDB.test.test_database        # Sistema completo
python -m HeiderDB.test.test_vector_index    # Índices vectoriales
```

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold;">Ejemplos de Consultas SQL</div>

### Creación de Tablas

```sql
-- Tabla básica con B+ Tree
CREATE TABLE usuarios (
    id INT KEY,
    nombre VARCHAR(50),
    email VARCHAR(100)
) using index bplus_tree(id);

-- Tabla con índice espacial
CREATE TABLE lugares (
    id INT KEY,
    nombre VARCHAR(100),
    ubicacion POINT SPATIAL INDEX,
    area POLYGON
) using index bplus_tree(id);

-- Tabla con índice de texto
CREATE TABLE documentos (
    id INT KEY,
    titulo VARCHAR(200),
    abstract VARCHAR(1000) TEXT INDEX,
    fecha DATE
) using index bplus_tree(id);
```

### Consultas Espaciales

```sql
-- Búsqueda por radio
SELECT * FROM lugares WHERE ubicacion WITHIN ((10, 20), 5.0);

-- Intersección geométrica
SELECT * FROM lugares WHERE area INTERSECTS "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))";

-- Vecinos más cercanos
SELECT * FROM lugares WHERE ubicacion NEAREST (0, 0) LIMIT 3;
```

### Consultas Textuales

```sql
-- Búsqueda de términos
SELECT * FROM documentos WHERE abstract CONTAINS 'machine learning';

-- Búsqueda booleana
SELECT * FROM documentos WHERE abstract CONTAINS 'python AND database';

-- Búsqueda con ranking
SELECT * FROM documentos WHERE abstract CONTAINS 'neural networks deep learning' RANKED LIMIT 10;
```

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold; margin-bottom:1rem">Arquitectura del Sistema</div>

- **Motor de almacenamiento**: Gestión de páginas y persistencia en disco
- **Índices primarios**: B+ Tree, Hash Extensible, ISAM, Archivo Secuencial
- **Índices secundarios**: R-Tree para datos espaciales, Índices Invertidos para texto
- **Parser SQL**: Análisis sintáctico de consultas con extensiones espaciales y textuales
- **Servidor TCP**: Protocolo binario personalizado para comunicación cliente-servidor
- **Gestión de memoria**: Paginación eficiente con buffer pools

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold; margin-bottom:1rem">Tipos de Datos Soportados</div>

- **Numéricos**: INT, FLOAT
- **Texto**: VARCHAR(n)
- **Lógicos**: BOOLEAN
- **Temporales**: DATE
- **Espaciales**: POINT, POLYGON, LINESTRING, GEOMETRY

<div style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; font-size: 1.5em; font-weight: bold; margin-bottom:1rem">Notas Técnicas</div>

- El sistema utiliza un protocolo TCP personalizado, no HTTP/REST
- Los archivos de datos se almacenan en el directorio `/data/`
- Cada tabla puede tener múltiples índices secundarios
- El sistema soporta transacciones básicas y recuperación de errores
- La implementación incluye optimizaciones de memoria secundaria y algoritmos de paginación

## Experimentación y Evaluación de Desempeño
| N       | MyIndex (ms) | PostgreSQL (ms) |
|---------|--------------|-----------------|
| 100     | 18.64        | 0.550           |
| 200     | 26.18        | 0.335           |
| 400     | 59.97        | 1.399           |
| 800     | 115.63       | 2.313           |
| 1600    | 139.56       | 6.573           |
| 3200    | 225.69       | 7.715           |
| 6400    | 462.24       | 15.009          |
| 12800   | 947.61       | 16.439          |
| 20000   | 1516.76      | 43.307          |
![Grafica comparativo](grafica1.png)
