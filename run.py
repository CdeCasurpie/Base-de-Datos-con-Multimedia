#!/usr/bin/env python3
"""
Lanzador del Sistema de Base de Datos Multimodal.
Este script simplemente inicia la aplicación desde el directorio correcto.
"""

import os
import sys
import subprocess

def main():
    # Obtener el directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Cambiar al directorio del proyecto
    os.chdir(script_dir)
    
    # Construir el comando para ejecutar
    cmd = [sys.executable, "src/main.py"] + sys.argv[1:]
    
    try:
        # Ejecutar la aplicación
        print("Iniciando Sistema de Base de Datos Multimodal...")
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nEjecución cancelada por el usuario")
        return 1
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
