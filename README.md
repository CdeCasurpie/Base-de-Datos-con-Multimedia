# Sistema de Base de Datos Multimodal

Sistema de gestión de base de datos con soporte para múltiples estructuras de indexación y tipos de datos, incluyendo datos numéricos, texto, espaciales y vectoriales. Implementado como un proyecto educativo.

## Características

- Interfaz gráfica para consultas SQL
- Creación de tablas y gestión de datos
- Soporte para múltiples estructuras de indexación:
  - Sequential/AVL File
  - B+ Tree
  - Hash (estático y dinámico)

- Soporte para índices avanzados:
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
./venv/Scripts/activate  # En Windows
```

3. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Ejecución

Para ejecutar la aplicación, simplemente use:

```bash
python src/main.py
```