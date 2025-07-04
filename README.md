# HeiderDB | Multimedia y Textos

**HeiderDB** es una base de datos modular con soporte para índices secuenciales, B+ Trees, índices espaciales (R-Tree), e índices invertidos para texto. Incluye un servidor TCP personalizado y una API de cliente.

## 🚀 Requisitos

- Docker instalado (funciona en Windows, macOS y Linux)
- Python 3.10+ solo si deseas correrlo fuera de Docker (no recomendado)



## 📦 Instalación con Docker

### 1. Clona el proyecto

```bash
git clone https://github.com/tu_usuario/HeiderDB.git
cd HeiderDB
````

### 2. Construye la imagen de Docker

```bash
docker build -t heiderdb .
```

### 3. Ejecuta el servidor

#### En Linux / macOS:

```bash
docker run --rm -v "$PWD:/app" -w /app -p 54321:54321 heiderdb
```

#### En Windows (CMD o PowerShell):

```bash
docker run --rm -v "%cd%:/app" -w /app -p 54321:54321 heiderdb
```

El servidor escuchará en `localhost:54321`.


### ¿Qué hace?

* El servidor ejecuta `python -m HeiderDB.server`
* Se conecta con el cliente (`HeiderClient`) vía socket
* Guarda los archivos de datos en tu carpeta local (`/data/`)


## 💬 Ejecutar el cliente

Puedes usar el cliente en `HeiderDB/client.py` para enviar consultas SQL:

```bash
python HeiderDB/client.py --query "SELECT * FROM usuarios;"
```

O pasarle host y puerto:

```bash
python HeiderDB/client.py --host 127.0.0.1 --port 54321 --query "SELECT * FROM usuarios;"
```


##  Notas

* Este proyecto no usa HTTP ni REST, es un servidor TCP puro.
* Todos los archivos creados se guardan en tu carpeta local gracias al volumen Docker.