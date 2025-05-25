#!/usr/bin/env python3

import os
import sys
import json
import readline  # Para historial de comandos
import cmd
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel
from rich.syntax import Syntax

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
        self.console = Console()
        self.db = Database()
        self.print_banner()
    
    def print_banner(self):
        banner = Panel("[bold blue]Sistema de Gestión de Base de Datos[/bold blue]\n"
                       "[green]Con soporte para índices espaciales[/green]", 
                       expand=False)
        self.console.print(banner)
        
        # Mostrar tablas cargadas
        tables = self.db.list_tables()
        if tables:
            self.console.print(f"[green]✓[/green] Base de datos cargada con {len(tables)} tablas")
            self.console.print(", ".join([f"[yellow]{t}[/yellow]" for t in tables]))
        else:
            self.console.print("[yellow]Base de datos sin tablas. Use 'CREATE TABLE' para crear una nueva.[/yellow]")
    
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
                self.console.print(f"[bold red]Error:[/bold red] {error}")
            elif isinstance(results, list):
                self.print_results(results)
            else:
                self.console.print(f"[green]✓[/green] {results}")
        except Exception as e:
            self.console.print(f"[bold red]Error inesperado:[/bold red] {e}")
    
    def print_results(self, results):
        """Mostrar resultados en formato de tabla."""
        if not results:
            self.console.print("[yellow]No se encontraron resultados[/yellow]")
            return
        
        # Crear tabla enriquecida
        if isinstance(results, list) and results:
            # Obtener columnas del primer resultado
            columns = list(results[0].keys())
            
            table = RichTable(title=f"Resultados ({len(results)} registros)")
            
            # Añadir columnas
            for col in columns:
                table.add_column(col, style="cyan")
            
            # Añadir filas
            for record in results:
                row = []
                for col in columns:
                    value = record.get(col, "")
                    # Formatear según tipo de dato
                    if isinstance(value, (int, float)):
                        row.append(str(value))
                    elif isinstance(value, bool):
                        row.append("true" if value else "false")
                    elif value is None:
                        row.append("NULL")
                    else:
                        # Truncar strings largos
                        if len(str(value)) > 50:
                            row.append(str(value)[:47] + "...")
                        else:
                            row.append(str(value))
                
                table.add_row(*row)
            
            self.console.print(table)
        else:
            # Mostrar resultado único
            self.console.print(results)
    
    def do_help(self, arg):
        """Muestra ayuda sobre comandos disponibles."""
        if not arg:
            self.console.print(Panel("[bold]Comandos Disponibles:[/bold]", title="Ayuda"))
            self.console.print("""
[bold]Comandos SQL básicos:[/bold]
- CREATE TABLE nombre_tabla (columna1 tipo1, columna2 tipo2, ...) using index tipo_indice(primary_key)
- CREATE TABLE nombre_tabla FROM FILE 'ruta_archivo' USING INDEX tipo_indice(primary_key) 
- CREATE SPATIAL INDEX nombre_indice ON nombre_tabla (columna)
- SELECT columnas FROM tabla WHERE condición
- INSERT INTO tabla VALUES (valor1, valor2, ...)
- DELETE FROM tabla WHERE columna = valor

[bold]Tipos de índices disponibles:[/bold]
- [green]bplus_tree[/green]: Árbol B+ balanceado
- [green]sequential_file[/green]: Archivo secuencial con overflow
- [green]extendible_hash[/green]: Hash extensible
- [green]isam_sparse[/green]: ISAM con índice disperso

[bold]Tipos de datos espaciales:[/bold]
- [cyan]POINT[/cyan]: Punto 2D - Ejemplo: 'POINT(10.5 20.3)'
- [cyan]POLYGON[/cyan]: Polígono - Ejemplo: 'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))'
- [cyan]LINESTRING[/cyan]: Línea - Ejemplo: 'LINESTRING(0 0, 10 10, 20 20)'
- [cyan]GEOMETRY[/cyan]: Cualquier geometría

[bold]Consultas espaciales:[/bold]
- SELECT * FROM tabla WHERE columna_espacial WITHIN (punto, radio)
- SELECT * FROM tabla WHERE columna_espacial INTERSECTS geometría
- SELECT * FROM tabla WHERE columna_espacial NEAREST punto LIMIT n
- SELECT * FROM tabla WHERE columna_espacial IN_RANGE (punto_min, punto_max)

[bold]Comandos del shell:[/bold]
- [yellow]tables[/yellow]: Listar todas las tablas
- [yellow]describe tabla[/yellow]: Mostrar estructura de una tabla
- [yellow]exit[/yellow] o [yellow]quit[/yellow]: Salir del programa
            """)
        else:
            # Mostrar ayuda para un comando específico
            if arg == 'create':
                self.console.print(Panel("""
[bold]CREATE TABLE nombre_tabla (columna1 tipo1 [KEY] [INDEX tipo_indice], ...)[/bold]
    Crea una nueva tabla con las columnas especificadas.

[bold]CREATE TABLE nombre_tabla FROM FILE 'ruta_archivo' USING INDEX tipo_indice(primary_key)[/bold]
    Crea una tabla cargando datos desde un archivo JSON o CSV.

[bold]CREATE SPATIAL INDEX nombre_indice ON nombre_tabla (columna)[/bold]
    Crea un índice espacial para una columna existente.

[bold]Ejemplos:[/bold]
    CREATE TABLE Usuarios (id INT KEY INDEX btree, nombre VARCHAR(50), edad INT);
    CREATE TABLE Restaurantes (id INT KEY, nombre VARCHAR(50), ubicacion POINT SPATIAL INDEX);
                """, title="CREATE - Ayuda"))
            elif arg == 'select':
                self.console.print(Panel("""
[bold]SELECT columnas FROM tabla [WHERE condición][/bold]
    Consulta registros en una tabla.

[bold]Consultas espaciales:[/bold]
    SELECT * FROM tabla WHERE columna WITHIN (punto, radio)
    SELECT * FROM tabla WHERE columna INTERSECTS geometría
    SELECT * FROM tabla WHERE columna NEAREST punto LIMIT n
    SELECT * FROM tabla WHERE columna IN_RANGE (punto_min, punto_max)

[bold]Ejemplos:[/bold]
    SELECT * FROM Usuarios WHERE edad >= 18;
    SELECT nombre, direccion FROM Restaurantes WHERE ubicacion WITHIN ((40.7, -74.0), 5.0);
                """, title="SELECT - Ayuda"))
            else:
                # Llamar a la implementación original para otros comandos
                super().do_help(arg)
    
    def do_tables(self, arg):
        """Lista todas las tablas en la base de datos."""
        tables = self.db.list_tables()
        
        if not tables:
            self.console.print("[yellow]No hay tablas en la base de datos[/yellow]")
            return
        
        table = RichTable(title="Tablas")
        table.add_column("Nombre", style="cyan")
        table.add_column("Registros", style="green")
        table.add_column("Índice", style="yellow")
        table.add_column("Columnas", style="blue")
        
        for table_name in tables:
            table_obj = self.db.get_table(table_name)
            record_count = table_obj.get_record_count()
            index_type = table_obj.index_type
            column_count = len(table_obj.columns)
            
            # Destacar tablas con índices espaciales
            if table_obj.spatial_columns:
                table.add_row(
                    f"[bold]{table_name}[/bold]", 
                    str(record_count),
                    f"{index_type} + [cyan]spatial[/cyan]",
                    f"{column_count} ({', '.join(table_obj.spatial_columns)})"
                )
            else:
                table.add_row(table_name, str(record_count), index_type, str(column_count))
        
        self.console.print(table)
    
    def do_describe(self, arg):
        """Muestra la estructura detallada de una tabla."""
        if not arg:
            self.console.print("[bold red]Error: Debe especificar un nombre de tabla[/bold red]")
            self.console.print("Uso: [yellow]describe nombre_tabla[/yellow]")
            return
        
        table_name = arg.strip()
        table_info = self.db.get_table_info(table_name)
        
        if not table_info:
            self.console.print(f"[bold red]Error: Tabla '{table_name}' no encontrada[/bold red]")
            return
        
        # Panel de información general
        general_info = f"""[bold]Tabla:[/bold] {table_info['name']}
[bold]Registros:[/bold] {table_info['record_count']}
[bold]Índice primario:[/bold] {table_info['index_type']} en columna '{table_info['primary_key']}'
[bold]Columnas espaciales:[/bold] {', '.join(table_info['spatial_columns']) if table_info['spatial_columns'] else 'Ninguna'}
"""

        if 'index_info' in table_info:
            for key, value in table_info['index_info'].items():
                general_info += f"[bold]{key}:[/bold] {value}\n"
        
        self.console.print(Panel(general_info, title=f"Información de {table_name}"))
        
        # Tabla de columnas
        columns_table = RichTable(title="Estructura")
        columns_table.add_column("Columna", style="cyan")
        columns_table.add_column("Tipo", style="green")
        columns_table.add_column("Clave", style="yellow")
        columns_table.add_column("Índice", style="blue")
        
        for col_name, col_type in table_info['columns'].items():
            is_primary = "PRIMARY" if col_name == table_info['primary_key'] else ""
            has_index = table_info['index_type'] if col_name == table_info['primary_key'] else ""
            
            # Destacar columnas espaciales
            if col_name in table_info.get('spatial_columns', []):
                columns_table.add_row(
                    f"[bold]{col_name}[/bold]", 
                    f"[cyan]{col_type}[/cyan]",
                    is_primary,
                    f"{has_index} [cyan]R-Tree[/cyan]" if has_index else "[cyan]R-Tree[/cyan]"
                )
            else:
                columns_table.add_row(col_name, col_type, is_primary, has_index)
        
        self.console.print(columns_table)
        
        # Información de índices espaciales
        if 'spatial_indexes' in table_info and table_info['spatial_indexes']:
            self.console.print("\n[bold]Índices espaciales:[/bold]")
            for column, stats in table_info['spatial_indexes'].items():
                spatial_info = f"""[bold]Columna:[/bold] {column}
[bold]Dimensiones:[/bold] {stats.get('dimension', 'N/A')}D
[bold]Entradas:[/bold] {stats.get('total_entries', 'N/A')}
[bold]Capacidad de nodo hoja:[/bold] {stats.get('leaf_capacity', 'N/A')}"""
                
                if 'bounds' in stats and stats['bounds']:
                    bounds = stats['bounds']
                    spatial_info += f"\n[bold]Límites:[/bold] ({bounds[0]:.1f}, {bounds[1]:.1f}) a ({bounds[2]:.1f}, {bounds[3]:.1f})"
                
                self.console.print(Panel(spatial_info, title=f"R-Tree {column}"))
    
    def do_exit(self, arg):
        """Salir del programa."""
        self.console.print("[green]¡Hasta pronto![/green]")
        return True
    
    def do_quit(self, arg):
        """Alias para salir del programa."""
        return self.do_exit(arg)
    
    # Añadir alias útiles
    do_ls = do_tables
    do_desc = do_describe

if __name__ == "__main__":
    try:
        # Intentar importar rich para interfaz más agradable
        from rich import print as rprint
    except ImportError:
        # Si no está instalado rich
        print("Nota: Instala el paquete 'rich' para una mejor experiencia:")
        print("    pip install rich")
    
    try:
        DatabaseShell().cmdloop()
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
