#!/usr/bin/env python3

import os
import sys
import readline  # Para historial de comandos
import cmd
import json

# Añadir el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Database

class DatabaseShell(cmd.Cmd):
    intro = """
==========================================
=  Sistema de Gestión de Base de Datos   =
=  con soporte para índices espaciales   =
==========================================
    
Escriba 'help' para ver la lista de comandos.
Para salir, escriba 'exit' o 'quit'.
"""
    prompt = "DB> "
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        print(self.intro)
        self.print_status()
    
    def print_status(self):
        """Muestra el estado actual de la base de datos"""
        tables = self.db.list_tables()
        if tables:
            print(f"Base de datos cargada con {len(tables)} tablas:")
            for table in tables:
                print(f"  - {table}")
        else:
            print("Base de datos sin tablas. Use 'CREATE TABLE' para crear una nueva.")
    
    def emptyline(self):
        """No hacer nada en línea vacía."""
        pass
    
    def default(self, line):
        """Ejecutar consulta SQL si no coincide con otro comando."""
        if line.lower() in ('exit', 'quit'):
            return self.do_exit(line)
        
        # Ejecutar como consulta SQL
        try:
            results, error = self.db.execute_query(line)
            if error:
                print(f"ERROR: {error}")
            elif isinstance(results, list):
                self.print_results(results)
            else:
                print(f"✓ {results}")
        except Exception as e:
            print(f"Error inesperado: {e}")
    
    def print_results(self, results):
        """Muestra resultados en formato de tabla."""
        if not results:
            print("No se encontraron resultados")
            return
        
        if isinstance(results, list) and results:
            # Obtener columnas del primer registro
            columns = list(results[0].keys())
            
            # Calcular ancho para cada columna
            column_widths = {}
            for col in columns:
                # Inicializar con el ancho del nombre de columna
                column_widths[col] = len(str(col))
                
                # Actualizar con el ancho máximo de los valores
                for record in results:
                    val = str(record.get(col, ""))
                    if len(val) > column_widths[col]:
                        # Limitar a 30 caracteres
                        column_widths[col] = min(30, len(val))
            
            # Imprimir cabecera
            header_row = " | ".join(col.ljust(column_widths[col]) for col in columns)
            print("=" * len(header_row))
            print(header_row)
            print("=" * len(header_row))
            
            # Imprimir datos
            for record in results:
                row_values = []
                for col in columns:
                    val = str(record.get(col, ""))
                    # Truncar valores largos
                    if len(val) > column_widths[col]:
                        val = val[:column_widths[col]-3] + "..."
                    row_values.append(val.ljust(column_widths[col]))
                print(" | ".join(row_values))
            
            print("=" * len(header_row))
            print(f"Total de registros: {len(results)}")
        else:
            # Mostrar resultado único
            print(results)
    
    def do_help(self, arg):
        """Muestra ayuda sobre comandos disponibles."""
        if not arg:
            print("\nComandos disponibles:")
            print("=====================")
            print("tables         - Listar todas las tablas")
            print("describe tabla - Mostrar estructura de una tabla")
            print("stats tabla    - Mostrar estadísticas de una tabla")
            print("exit, quit     - Salir del programa")
            print("\nPuede ejecutar cualquier consulta SQL directamente:")
            print("- CREATE TABLE nombre (columnas) USING INDEX tipo(pk)")
            print("- SELECT * FROM tabla WHERE condicion")
            print("- INSERT INTO tabla VALUES (valores)")
            print("- DELETE FROM tabla WHERE condicion")
            print("\nUso: help comando - para más información sobre un comando específico")
        elif arg == 'tables':
            print("Uso: tables")
            print("Lista todas las tablas disponibles en la base de datos.")
        elif arg == 'describe':
            print("Uso: describe nombre_tabla")
            print("Muestra la estructura de la tabla especificada.")
        elif arg == 'stats':
            print("Uso: stats nombre_tabla")
            print("Muestra estadísticas detalladas de la tabla y sus índices.")
        elif arg in ['exit', 'quit']:
            print("Uso: exit | quit")
            print("Sale del programa.")
        else:
            # Fallback a la ayuda estándar
            super().do_help(arg)
    
    def do_tables(self, arg):
        """Lista todas las tablas en la base de datos."""
        tables = self.db.list_tables()
        
        if not tables:
            print("No hay tablas en la base de datos")
            return
        
        print("\nTablas disponibles:")
        print("===================")
        
        for table_name in tables:
            try:
                table_info = self.db.get_table_info(table_name)
                record_count = table_info.get('record_count', 0)
                index_type = table_info.get('index_type', 'unknown')
                
                # Destacar tablas con índices espaciales
                if table_info.get('spatial_columns'):
                    print(f"* {table_name} - {record_count} registros - {index_type} + spatial")
                else:
                    print(f"  {table_name} - {record_count} registros - {index_type}")
            except:
                print(f"  {table_name} - [error al obtener información]")
    
    def do_describe(self, arg):
        """Muestra la estructura detallada de una tabla."""
        if not arg:
            print("ERROR: Debe especificar un nombre de tabla")
            print("Uso: describe nombre_tabla")
            return
        
        table_name = arg.strip()
        table_info = self.db.get_table_info(table_name)
        
        if not table_info:
            print(f"ERROR: Tabla '{table_name}' no encontrada")
            return
        
        print(f"\nEstructura de tabla: {table_name}")
        print("=" * 50)
        
        print(f"Registros: {table_info['record_count']}")
        print(f"Índice primario: {table_info['index_type']} en '{table_info['primary_key']}'")
        
        if table_info.get('spatial_columns'):
            print(f"Columnas espaciales: {', '.join(table_info['spatial_columns'])}")
        
        print("\nColumnas:")
        print("-" * 50)
        print(f"{'Nombre':<20} | {'Tipo':<15} | {'Clave':<5} | {'Índice':<10}")
        print("-" * 50)
        
        for col_name, col_type in table_info['columns'].items():
            is_pk = "PK" if col_name == table_info['primary_key'] else ""
            index_type = table_info['index_type'] if col_name == table_info['primary_key'] else ""
            
            # Añadir indicador espacial
            if col_name in table_info.get('spatial_columns', []):
                index_type = (index_type + " + R-Tree") if index_type else "R-Tree"
                
            print(f"{col_name:<20} | {col_type:<15} | {is_pk:<5} | {index_type:<10}")
    
    def do_stats(self, arg):
        """Muestra estadísticas de una tabla."""
        if not arg:
            print("ERROR: Debe especificar un nombre de tabla")
            print("Uso: stats nombre_tabla")
            return
        
        table_name = arg.strip()
        table_info = self.db.get_table_info(table_name)
        
        if not table_info:
            print(f"ERROR: Tabla '{table_name}' no encontrada")
            return
        
        print(f"\nEstadísticas de tabla: {table_name}")
        print("=" * 50)
        
        # Información básica
        print(f"Total de registros: {table_info['record_count']}")
        
        # Información del índice primario
        print(f"\nÍndice primario ({table_info['index_type']}):")
        print("-" * 50)
        
        idx_info = table_info.get('index_info', {})
        for key, value in idx_info.items():
            print(f"{key}: {value}")
        
        # Información de índices espaciales
        if 'spatial_indexes' in table_info and table_info['spatial_indexes']:
            print("\nÍndices espaciales:")
            print("-" * 50)
            
            for col, stats in table_info['spatial_indexes'].items():
                print(f"Columna: {col}")
                for stat_name, stat_value in stats.items():
                    if stat_name == 'bounds' and stat_value:
                        b = stat_value
                        print(f"  límites: ({b[0]:.1f}, {b[1]:.1f}) a ({b[2]:.1f}, {b[3]:.1f})")
                    else:
                        print(f"  {stat_name}: {stat_value}")
                print()
    
    def do_exit(self, arg):
        """Sale del programa."""
        print("¡Hasta pronto!")
        return True
    
    def do_quit(self, arg):
        """Alias para salir del programa."""
        return self.do_exit(arg)
    
    # Añadir alias útiles
    do_ls = do_tables
    do_desc = do_describe

if __name__ == "__main__":
    try:
        DatabaseShell().cmdloop()
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
