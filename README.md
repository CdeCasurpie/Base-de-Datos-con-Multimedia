# Sistema de Base de Datos Multimodal - Proyecto 1

## Tabla de Contenidos

1. [Guía de Instalación y Ejecución](#1-guía-de-instalación-y-ejecución)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Análisis de Rendimiento](#3-análisis-de-rendimiento)
4. [Implementación de la Clase Table](#4-implementación-de-la-clase-table)
5. [Implementación de Índices](#5-implementación-de-índices)
   - [5.1 B+ Tree](#51-b-tree)
   - [5.2 Hash Extensible](#52-hash-extensible)
   - [5.3 Archivo Secuencial](#53-archivo-secuencial)
   - [5.4 ISAM Sparse](#54-isam-sparse)
   - [5.5 R-Tree](#55-r-tree)
6. [Parser SQL](#6-parser-sql)
7. [Interfaz Gráfica](#7-interfaz-gráfica)

## 1. Guía de Instalación y Ejecución

### Requisitos
```
Python 3.7+
PyQt5
rtree
shapely
```

### Instalación
```bash
git clone https://github.com/Fabryzzio-Meza-Torres/Sistema-de-Base-de-Datos-Multimodal.git
cd Sistema-de-Base-de-Datos-Multimodal
pip install -r requirements.txt
```

### Ejecución
```bash
# Aplicación principal con GUI
python run.py

# Shell interactivo de base de datos
python src/test/test_database.py

# Pruebas individuales de índices
python src/test/test_btree.py
python src/test/test_extendible_hash.py
python src/test/test_sequential_file.py
python src/test/test_isam_sparse.py
python src/test/test_rtree.py
```

### Uso Básico
```sql
-- Crear tabla con índice espacial
CREATE TABLE restaurantes (
    id INT KEY,
    nombre VARCHAR(50),
    ubicacion POINT SPATIAL INDEX
) using index bplus_tree(id);

-- Insertar datos
INSERT INTO restaurantes VALUES (1, "Pizza Hut", "POINT(10.5 20.3)");

-- Consultas espaciales
SELECT * FROM restaurantes WHERE ubicacion WITHIN ((10, 20), 5.0);
```

## 2. Estructura del Proyecto

```
src/
├── database/
│   ├── database.py          # Gestor principal de BD
│   ├── table.py             # Clase Table principal
│   ├── parser.py            # Parser SQL personalizado
│   ├── index_base.py        # Interfaz base para índices
│   └── indexes/
│       ├── b_plus.py        # Árbol B+
│       ├── extendible_hash.py # Hash Extensible
│       ├── sequential_file.py # Archivo Secuencial
│       ├── isam_sparse.py   # ISAM Sparse
│       └── r_tree.py        # R-Tree Espacial
├── ui/
│   ├── main_window.py       # Ventana principal GUI
│   ├── query_panel.py       # Panel consultas SQL
│   ├── result_panel.py      # Panel resultados
│   └── tables_tree.py       # Árbol navegación tablas
└── test/
    └── test_*.py            # Scripts prueba individuales
```

### Descripción de Componentes

**database/**: Contiene el núcleo del sistema de base de datos. La clase `Database` coordina todas las operaciones, mientras que `Table` maneja la estructura y datos de cada tabla individual.

**indexes/**: Implementaciones de las cinco técnicas de indexación requeridas. Cada índice hereda de `IndexBase` y implementa las operaciones fundamentales.

**ui/**: Interfaz gráfica desarrollada en PyQt5 con patrón MVC. Separa la lógica de presentación del núcleo de la base de datos.

**test/**: Scripts interactivos para probar cada componente individualmente con datos sintéticos y métricas de rendimiento.

## 3. Análisis de Rendimiento

### Metodología de Pruebas

Las pruebas se realizaron con datasets de 10, 100, 1,000, 10,000 y 100,000 registros, midiendo tiempo de inserción promedio por registro y operaciones de búsqueda.

### Resultados de Inserción (ms por registro)

| Registros | Hash Extensible | Sequential File | B+ Tree | ISAM Sparse | R-Tree |
|-----------|-----------------|-----------------|---------|-------------|--------|
| 10        | 0.1             | 0.0 5           | 0.05    | 0.04        |0.45    |
| 100       | 0.95            | 0.44            | 0.59    | 0.13        |1.80    |
| 1,000     | 8.2             | 5.2             | 5.89    | 4.71        |45.65   |
| 10,000    | 101.06          | 136.15          | 69.26   | 174.51      |2960.05 |
| 100,000   | 1001.05         | 1798.6          | 796.30  | 6328.5      |18112.05|

![Extendible Hash, Sequential File, Btree y ISAM (INSERCCIÓN)](https://github.com/user-attachments/assets/c36666a4-d9b8-43f9-bb2a-b40fbed71da5)


### Análisis por Técnica

**B+ Tree**: Tiene la mejor complejidad entre todas las operaciones, con complejidad **O(log n)** para inserciones. Su estructura auto-balanceada garantiza un rendimiento logarítmico consistente, independientemente del patrón de datos, permitiéndole escalar eficientemente incluso con grandes volúmenes (como se observa en las pruebas con 100,000 registros). La jerarquía en la organización de los nodos y el mantenimiento automático del equilibrio minimizan la degradación, incluso durante inserciones masivas.

**Hash Extensible**: Presenta un rendimiento escalable y consistente, con complejidad **O(1)** en el caso promedio para inserciones. Su crecimiento prácticamente lineal se debe al manejo dinámico de colisiones mediante la división de buckets al alcanzar su capacidad. La capacidad de duplicar el directorio cuando es necesario le permite adaptarse a conjuntos de datos crecientes sin comprometer significativamente el rendimiento, aunque puede experimentar algunos picos de latencia durante las operaciones de reorganización.

**Sequential File**: Muestra un rendimiento variable según el patrón de inserción, con complejidad **O(n)** en el peor caso. Es altamente eficiente para datos que llegan en orden (cercano a **O(1)**), pero muy costoso para inserciones aleatorias debido a las reconstrucciones frecuentes del archivo principal cuando el área de overflow se satura. La degradación observada con volúmenes grandes (136ms/registro en 10,000) refleja este comportamiento, donde las reconstrucciones se vuelven cada vez más costosas.

**ISAM Sparse**: Ofrece un rendimiento inicial excelente debido a su estructura estática de dos niveles, con complejidad **O(1)** para las primeras inserciones. Sin embargo, empeora rápidamente con volúmenes grandes (6328ms/registro en 100,000) debido a la acumulación de overflow pages. A diferencia del B+ Tree, el índice ISAM es estático y no se reorganiza automáticamente, lo que provoca un deterioro progresivo del rendimiento a medida que las cadenas de overflow crecen y requieren búsquedas lineales adicionales.

**R-Tree**: Muestra el rendimiento más lento en inserciones generales, con complejidad **O(log n)** en el mejor caso, pero **O(n)** en escenarios de división frecuente. Esta ineficiencia relativa (18112ms/registro en 100,000) se debe a las complejas operaciones geométricas necesarias para calcular y actualizar los rectángulos envolventes mínimos (MBRs) en cada nivel. Sin embargo, este costo adicional se justifica al realizar consultas espaciales, donde el R-Tree supera significativamente a otras estructuras gracias a su capacidad para podar rápidamente zonas de búsqueda irrelevantes.

### Búsquedas Espaciales (R-Tree)

Pruebas con 1,000 registros espaciales:
- Búsqueda por radio: 2.3ms promedio
- Intersección geométrica: 1.8ms promedio  
- K-vecinos cercanos: 3.1ms promedio (k=5)

## 4. Implementación de la Clase Table

### Arquitectura General

La clase `Table` actúa como coordinador central que encapsula la estructura de datos, esquema de la tabla y el índice primario seleccionado. Implementa el patrón Strategy para intercambiar técnicas de indexación dinámicamente.

### Tipos de Datos Soportados

```python
DATA_TYPES = {
    "INT": {"size": 4, "format": "i"},
    "FLOAT": {"size": 8, "format": "d"}, 
    "VARCHAR": {"variable": True},
    "DATE": {"size": 8, "format": "q"},
    "BOOLEAN": {"size": 1, "format": "?"},
    "POINT": {"variable": True, "spatial": True},
    "POLYGON": {"variable": True, "spatial": True},
    "LINESTRING": {"variable": True, "spatial": True},
    "GEOMETRY": {"variable": True, "spatial": True}
}
```

### Serialización y Deserialización

El sistema implementa serialización binaria optimizada que calcula automáticamente el pack string basado en los tipos de columna definidos. Los tipos espaciales se serializan como strings WKT con tamaño fijo de 500 bytes.

### Gestión de Índices

Cada tabla mantiene un índice primario obligatorio y opcionalmente múltiples índices espaciales secundarios. La selección del tipo de índice se realiza durante la creación mediante el parámetro `index_type`.

### Operaciones Fundamentales

**add()**: Valida estructura del registro, verifica unicidad de clave primaria, serializa datos y delega inserción al índice seleccionado.

**search()**: Distingue entre búsquedas en clave primaria (usa índice) y columnas secundarias (full scan).

**remove()**: Elimina registro del índice primario y todos los índices espaciales asociados.

**range_search()**: Aprovecha capacidades de búsqueda por rango del índice primario cuando está disponible.

## 5. Implementación de Índices

### 5.1 B+ Tree

#### Estructura de Nodos

Implementa nodos internos con solo claves y punteros, mientras que nodos hoja contienen claves, punteros a registros y enlaces horizontales para recorrido secuencial eficiente.

#### Algoritmo de Inserción

1. Navegación desde raíz hasta hoja apropiada siguiendo comparaciones de clave
2. Inserción ordenada manteniendo invariante de orden
3. División de nodo cuando se excede capacidad máxima (orden del árbol)
4. Promoción de clave mediana hacia nodo padre
5. Propagación de divisiones hasta raíz si es necesario

#### Algoritmo de División

**Nodos Hoja**: División equitativa promoviendo primera clave del nuevo nodo, manteniendo enlace horizontal.

**Nodos Internos**: División promoviendo clave mediana, distribuyendo punteros equitativamente entre nodos resultantes.

#### Algoritmo de Eliminación

1. Localización y eliminación de clave en nodo hoja
2. Detección de underflow (menos de orden/2 claves)
3. Redistribución con hermanos si es posible
4. Fusión de nodos cuando redistribución no es viable
5. Propagación de cambios hacia raíz

#### Gestión de Memoria Secundaria

Utiliza páginas de tamaño fijo con serialización binaria optimizada. Implementa lista de páginas libres para reutilización de espacio tras eliminaciones.

### 5.2 Hash Extensible

#### Estructura del Directorio

Mantiene un directorio global como arreglo de punteros a buckets, donde cada entrada se indexa mediante los primeros d bits del hash de la clave (d = profundidad global).

#### Algoritmo de Hash

Implementa función hash simple: suma de códigos ASCII para strings, multiplicación por 1000 para floats, identidad para enteros. El resultado se modula por 2^d para obtener índice de directorio.

#### Algoritmo de Inserción

1. Cálculo de hash y extracción de índice binario
2. Localización de bucket correspondiente
3. Inserción directa si hay espacio disponible
4. División de bucket si está lleno y profundidad local < global
5. Duplicación de directorio si profundidad local = global

#### División de Buckets

1. Incremento de profundidad local del bucket original
2. Creación de nuevo bucket con misma profundidad
3. Redistribución de claves basada en bit adicional
4. Actualización de punteros en directorio global

#### Manejo de Overflow

Cuando un bucket se llena y no puede dividirse, se crean buckets de overflow encadenados que se recorren secuencialmente durante búsquedas.

### 5.3 Archivo Secuencial

#### Estructura de Almacenamiento

Mantiene archivo principal con registros ordenados físicamente y archivo de overflow para nuevas inserciones que no pueden ubicarse en posición correcta.

#### Algoritmo de Búsqueda Binaria

Implementa búsqueda binaria en archivo principal considerando entradas marcadas como eliminadas. Si no encuentra registro, recorre área de overflow secuencialmente.

#### Algoritmo de Inserción

1. Búsqueda binaria para localizar posición de inserción
2. Inserción en posición vacía si está disponible
3. Inserción en overflow si archivo principal está lleno
4. Reconstrucción completa cuando overflow excede umbral

#### Proceso de Reconstrucción

1. Lectura de todos los registros válidos de ambos archivos
2. Ordenamiento por clave primaria
3. Reescritura completa del archivo principal
4. Limpieza del archivo de overflow
5. Actualización de metadatos

### 5.4 ISAM Sparse

#### Estructura Jerárquica

Implementa exactamente dos niveles de indexación:
- **Root**: Punteros dispersos a bloques de nivel 1
- **Level 1**: Punteros dispersos a páginas de datos físicas
- **Data Pages**: Páginas con overflow encadenado

#### Algoritmo de Navegación

1. Búsqueda binaria en nivel root para localizar bloque de nivel 1
2. Búsqueda binaria en nivel 1 para localizar página de datos
3. Búsqueda lineal en página de datos y sus overflows

#### Manejo de Inserciones

Las nuevas inserciones se colocan en páginas de overflow encadenadas sin modificar la estructura de índice estática. Esto preserva el carácter estático del ISAM pero puede degradar rendimiento.

#### Proceso de Reconstrucción

Reconstruye completamente los dos niveles de índice basándose en todos los registros válidos, redistribuyendo datos para minimizar overflow pages.

### 5.5 R-Tree

#### Estructura Espacial

Organiza objetos geométricos en rectángulos envolventes mínimos (MBR) jerárquicamente. Cada nodo interno contiene MBRs de sus hijos, mientras que hojas contienen MBRs de objetos reales.

#### Algoritmo de Inserción

1. Cálculo del MBR del objeto espacial
2. Selección de hoja que requiere menor expansión de MBR
3. Inserción del objeto actualizando MBRs ancestrales
4. División de nodo si excede capacidad máxima

#### Búsquedas Espaciales

**Por Radio**: Conversión a consulta rectangular aproximada seguida de filtrado por distancia euclidiana exacta.

**Intersección**: Verificación de solapamiento entre MBR de consulta y MBRs de nodos, descendiendo recursivamente en nodos que intersectan.

**K-Vecinos**: Utiliza cola de prioridad ordenada por distancia, expandiendo nodos más prometedores primero.

#### Integración con Shapely

Utiliza biblioteca Shapely para parsing de geometrías WKT y cálculos geométricos precisos. La integración permite soporte completo para tipos POINT, POLYGON, LINESTRING y GEOMETRY.

## 6. Parser SQL

### Arquitectura del Parser

Implementa parser descendente recursivo utilizando expresiones regulares complejas para reconocer patrones sintácticos. Cada tipo de consulta tiene su patrón específico con grupos de captura para extraer componentes.

### Gramática Soportada

El parser reconoce construcciones SQL extendidas incluyendo:
- Definiciones de tabla con especificación de índices
- Consultas SELECT con condiciones espaciales
- Operaciones de inserción y eliminación
- Importación desde archivos externos

### Procesamiento de Condiciones Espaciales

Parsea condiciones espaciales complejas como `WITHIN`, `INTERSECTS`, `NEAREST` y `IN_RANGE`, extrayendo parámetros geométricos y convirtiendo representaciones de coordenadas.

### Manejo de Tipos de Datos

El parser infiere tipos de datos automáticamente durante importación de archivos, detectando patrones WKT para tipos espaciales y estimando tamaños apropiados para VARCHAR.

## 7. Interfaz Gráfica

### Arquitectura MVC

La interfaz utiliza patrón Model-View-Controller con PyQt5, separando lógica de negocio (clases de base de datos) de presentación (widgets Qt) mediante señales y slots.

### Componentes Principales

**QueryPanel**: Editor SQL con resaltado sintáctico, plantillas predefinidas y validación en tiempo real.

**ResultPanel**: Visualización dual (tabular y textual) con capacidades de exportación a CSV/JSON.

**TablesTree**: Navegación jerárquica mostrando estructura de tablas, tipos de columnas e información de índices.

**MainWindow**: Coordinador principal que maneja comunicación entre componentes mediante sistema de señales Qt.

### Funcionalidades Avanzadas

El sistema incluye plantillas contextuales, ejemplos interactivos, manejo robusto de errores y retroalimentación visual del estado de operaciones mediante barra de estado integrada.


--- 
Para más documentación visitar
[https://deepwiki.com/Fabryzzio-Meza-Torres/Sistema-de-Base-de-Datos-Multimodal/1-overview#system-architecture](https://deepwiki.com/Fabryzzio-Meza-Torres/Sistema-de-Base-de-Datos-Multimodal/1-overview#system-architecture)
