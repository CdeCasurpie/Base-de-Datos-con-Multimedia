import os
import re

PROYECTO_RAIZ = "HeiderDB"
IGNORAR = {"venv", "__pycache__", ".git"}

def es_import_relativo(linea):
    return re.match(r"\s*from\s+\.+", linea)

def es_import_mal_resuelto(linea):
    return re.match(r"\s*from\s+database\.", linea)

def resolver_import_absoluto(archivo, linea):
    nivel = len(re.match(r"\s*from\s+(\.+)", linea).group(1))
    ruta_modulo = os.path.relpath(archivo, PROYECTO_RAIZ).replace("/", ".").replace("\\", ".")
    partes = ruta_modulo.split(".")[:-1]  # sin el .py
    if len(partes) < nivel:
        return None
    base = ".".join([PROYECTO_RAIZ] + partes[:len(partes) - nivel])
    resto = re.sub(r"\s*from\s+\.+", "", linea, count=1)
    return f"from {base}.{resto}"

def resolver_import_mal_resuelto(linea):
    return linea.replace("from database.", f"from {PROYECTO_RAIZ}.database.")

def procesar_archivo(path):
    with open(path, "r") as f:
        lineas = f.readlines()

    nuevas = []
    cambiado = False

    for linea in lineas:
        if es_import_relativo(linea):
            absoluto = resolver_import_absoluto(path, linea)
            if absoluto:
                nuevas.append(absoluto)
                cambiado = True
                continue
        elif es_import_mal_resuelto(linea):
            nuevas.append(resolver_import_mal_resuelto(linea))
            cambiado = True
            continue
        nuevas.append(linea)

    if cambiado:
        with open(path, "w") as f:
            f.writelines(nuevas)
        print(f"✔ Convertido: {path}")

def recorrer_directorio(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        for file in files:
            if file.endswith(".py"):
                procesar_archivo(os.path.join(root, file))

if __name__ == "__main__":
    recorrer_directorio(PROYECTO_RAIZ)
