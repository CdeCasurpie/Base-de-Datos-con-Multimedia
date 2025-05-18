# Sistema de Base de Datos Multimodal

Sistema de gestión de base de datos con soporte para múltiples estructuras de indexación y tipos de datos, incluyendo datos numéricos, texto, espaciales y vectoriales. Implementado como un proyecto educativo para el curso de Bases de Datos II.

## Características

- Interfaz gráfica intuitiva para consultas SQL
- Soporte para múltiples estructuras de indexación:
  - Sequential/AVL File
  - B+ Tree
  - Hash (estático y dinámico)
  - ISAM-Sparse
  - R-Tree (para datos espaciales)
  - GIN (para texto)
  - IVF (para vectores)
  - LSH (para alta dimensionalidad)
- Operaciones CRUD completas
- Importación/exportación de datos a CSV y JSON

## Requisitos

- Python 3.7 o superior
- PyQt5 para la interfaz gráfica

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/yourusername/BD-II-Project.git
cd BD-II-Project
```

2. Crear un entorno virtual (opcional pero recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows
```

3. Instalar las dependencias:
```bash
pip install PyQt5
```

## Ejecución

Para ejecutar la aplicación, simplemente use:

```bash
python src/main.py
```

## Uso básico

1. **Crear una tabla**: Utilice la pestaña "Consulta SQL" y escriba una consulta CREATE TABLE, seleccionando el tipo de índice deseado.
2. **Consultar datos**: Use la sintaxis SQL estándar con SELECT para recuperar datos.
3. **Insertar datos**: Utilice INSERT INTO para agregar registros a las tablas.
4. **Eliminar datos**: Use DELETE FROM para eliminar registros según criterios específicos.

## Ejemplos de consultas

```sql
-- Crear una tabla con índice secuencial para la clave primaria
CREATE TABLE usuarios (id INT KEY INDEX SEQ, nombre VARCHAR[50], edad INT);

-- Crear una tabla desde un archivo CSV usando B-Tree
CREATE TABLE productos FROM "datos/productos.csv" USING INDEX BTREE;

-- Seleccionar todos los registros
SELECT * FROM usuarios;

-- Insertar un registro
INSERT INTO usuarios VALUES (1, "Juan Pérez", 30);

-- Eliminar un registro
DELETE FROM usuarios WHERE id = 1;
```
