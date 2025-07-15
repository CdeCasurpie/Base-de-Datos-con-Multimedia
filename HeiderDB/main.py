#!/usr/bin/env python3

import sys
import os
import argparse
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon

# Asegurar que el directorio actual está en sys.path
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_gui():
    """Inicia la interfaz gráfica"""
    from ui.main_window import MainWindow
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo más moderno y consistente
    
    try:
        window = MainWindow()
        window.show()
        return app.exec_()
    except Exception as e:
        QMessageBox.critical(None, "Error al iniciar", 
                            f"No se pudo iniciar la aplicación: {str(e)}")
        return 1

def start_cli():
    """Inicia la versión de línea de comandos"""
    from test.test_database import DatabaseShell
    
    try:
        shell = DatabaseShell()
        shell.cmdloop()
        return 0
    except Exception as e:
        print(f"Error al iniciar el shell: {e}")
        return 1

def main():
    if not os.path.exists("./data"):
        os.makedirs("./data/tables", exist_ok=True)
        os.makedirs("./data/indexes", exist_ok=True)
    
    parser = argparse.ArgumentParser(description="Sistema de Base de Datos Multimodal")
    parser.add_argument('--cli', action='store_true', help='Iniciar en modo línea de comandos')
    parser.add_argument('--gui', action='store_true', help='Iniciar en modo interfaz gráfica (por defecto)')
    
    args = parser.parse_args()
    
    # Por defecto, usar GUI a menos que se especifique CLI
    if args.cli:
        sys.exit(start_cli())
    else:
        sys.exit(start_gui())

if __name__ == "__main__":
    main()