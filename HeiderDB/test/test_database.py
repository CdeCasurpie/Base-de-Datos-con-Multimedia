#!/usr/bin/env python3

import os
import sys
import readline  # Para historial de comandos
import cmd
import json
import shutil  # Para detectar tamaño de terminal


# Códigos de colores ANSI
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


# Añadir el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from HeiderDB.database.database import Database


class DatabaseShell(cmd.Cmd):
    intro = f"""
{Colors.CYAN}==========================================
=  {Colors.BLUE}{Colors.BOLD}Sistema de Gestión de Base de Datos{Colors.RESET}{Colors.CYAN}   =
=  {Colors.BLUE}{Colors.BOLD}con soporte para índices espaciales{Colors.RESET}{Colors.CYAN}   =
=========================================={Colors.RESET}
    
{Colors.WHITE}Escriba '{Colors.WHITE}help{Colors.WHITE}' para ver la lista de comandos.
Para salir, escriba '{Colors.WHITE}exit{Colors.WHITE}' o '{Colors.WHITE}quit{Colors.WHITE}'.{Colors.RESET}
"""
    prompt = f"{Colors.WHITE}DB>{Colors.RESET} "

    def __init__(self):
        super().__init__()
        self.db = Database()

    def print_status(self):
        """Muestra el estado actual de la base de datos"""
        tables = self.db.list_tables()
        if tables:
            print(
                f"{Colors.WHITE}Base de datos cargada con {Colors.BOLD}{len(tables)}{Colors.RESET}{Colors.WHITE} tablas:{Colors.RESET}"
            )
            for table in tables:
                print(f"  {Colors.CYAN}•{Colors.RESET} {table}")
        else:
            print(
                f"{Colors.YELLOW}Base de datos sin tablas. Use '{Colors.WHITE}CREATE TABLE{Colors.YELLOW}' para crear una nueva.{Colors.RESET}"
            )

    def emptyline(self):
        """No hacer nada en línea vacía."""
        pass

    def default(self, line):
        """Ejecutar consulta SQL si no coincide con otro comando."""
        if line.lower() in ("exit", "quit"):
            return self.do_exit(line)

        # Ejecutar como consulta SQL
        try:
            results, error = self.db.execute_query(line)
            if error:
                print(
                    f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}{error}{Colors.RESET}"
                )
            elif isinstance(results, list):
                self.print_results(results)
            else:
                print(f"{Colors.GREEN}✓ {results}{Colors.RESET}")
        except Exception as e:
            print(
                f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Error inesperado: {e}{Colors.RESET}"
            )

    def print_results(self, results):
        """Muestra resultados en formato de tabla."""
        if not results:
            print(f"{Colors.YELLOW}No se encontraron resultados{Colors.RESET}")
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

            # Determinar ancho total aproximado
            total_width = sum(column_widths.values()) + (len(columns) * 3) - 1

            # Imprimir cabecera con colores
            header_row = " | ".join(
                f"{Colors.BOLD}{col.ljust(column_widths[col])}{Colors.RESET}"
                for col in columns
            )
            print(f"{Colors.CYAN}{'=' * total_width}{Colors.RESET}")
            print(header_row)
            print(f"{Colors.WHITE}{'=' * total_width}{Colors.RESET}")

            # Imprimir datos con colores alternando filas
            for i, record in enumerate(results):
                row_style = ""
                row_values = []
                for col in columns:
                    val = str(record.get(col, ""))
                    # Truncar valores largos
                    if len(val) > column_widths[col]:
                        val = val[: column_widths[col] - 3] + "..."
                    row_values.append(val.ljust(column_widths[col]))
                print(f"{row_style}{' | '.join(row_values)}{Colors.RESET}")

            print(f"{Colors.WHITE}{'=' * total_width}{Colors.RESET}")
            print(f"{Colors.WHITE}Total de registros: {len(results)}{Colors.RESET}")
        else:
            # Mostrar resultado único
            print(results)

    def do_help(self, arg):
        """Muestra ayuda sobre comandos disponibles."""
        if not arg:
            print(f"\n{Colors.BOLD}{Colors.WHITE}Comandos disponibles:{Colors.RESET}")
            print(f"{Colors.WHITE}====================={Colors.RESET}")
            print(
                f"{Colors.WHITE}tables         {Colors.RESET}- Listar todas las tablas"
            )
            print(
                f"{Colors.WHITE}describe tabla {Colors.RESET}- Mostrar estructura de una tabla"
            )
            print(
                f"{Colors.WHITE}stats tabla    {Colors.RESET}- Mostrar estadísticas de una tabla"
            )
            print(f"{Colors.WHITE}exit, quit     {Colors.RESET}- Salir del programa")
            print(
                f"\n{Colors.CYAN}Puede ejecutar cualquier consulta SQL directamente:{Colors.RESET}"
            )
            print(
                f"{Colors.WHITE}- CREATE TABLE nombre (columnas) USING INDEX tipo(pk){Colors.RESET}"
            )
            print(f"{Colors.WHITE}- SELECT * FROM tabla WHERE condicion{Colors.RESET}")
            print(f"{Colors.WHITE}- INSERT INTO tabla VALUES (valores){Colors.RESET}")
            print(f"{Colors.WHITE}- DELETE FROM tabla WHERE condicion{Colors.RESET}")
            print(
                f"\n{Colors.CYAN}Uso: help comando - para más información sobre un comando específico{Colors.RESET}"
            )
        elif arg == "tables":
            print(f"{Colors.YELLOW}Uso: tables{Colors.RESET}")
            print(
                f"{Colors.WHITE}Lista todas las tablas disponibles en la base de datos.{Colors.RESET}"
            )
        elif arg == "describe":
            print(f"{Colors.YELLOW}Uso: describe nombre_tabla{Colors.RESET}")
            print(
                f"{Colors.WHITE}Muestra la estructura de la tabla especificada.{Colors.RESET}"
            )
        elif arg == "stats":
            print(f"{Colors.YELLOW}Uso: stats nombre_tabla{Colors.RESET}")
            print(
                f"{Colors.WHITE}Muestra estadísticas detalladas de la tabla y sus índices.{Colors.RESET}"
            )
        elif arg in ["exit", "quit"]:
            print(f"{Colors.YELLOW}Uso: exit | quit{Colors.RESET}")
            print(f"{Colors.WHITE}Sale del programa.{Colors.RESET}")
        else:
            # Fallback a la ayuda estándar
            super().do_help(arg)

    def do_tables(self, arg):
        """Lista todas las tablas en la base de datos."""
        tables = self.db.list_tables()

        if not tables:
            print(f"{Colors.YELLOW}No hay tablas en la base de datos{Colors.RESET}")
            return

        print(f"\n{Colors.WHITE}{Colors.BOLD}Tablas disponibles:{Colors.RESET}")
        print(f"{Colors.WHITE}==================={Colors.RESET}")

        for table_name in tables:
            try:
                # Obtener información básica directamente de la tabla
                if table_name in self.db.tables:
                    table = self.db.tables[table_name]
                    record_count = table.get_record_count()
                    index_type = table.index_type

                    # Verificar si tiene índices espaciales o multimedia
                    has_spatial = (
                        hasattr(table, "spatial_columns") and table.spatial_columns
                    )
                    has_multimedia = hasattr(table, "indexes") and table.indexes

                    if has_spatial:
                        print(
                            f"{Colors.WHITE}* {table_name} {Colors.RESET}- {record_count} registros - {Colors.MAGENTA}{index_type} + spatial{Colors.RESET}"
                        )
                    elif has_multimedia:
                        print(
                            f"{Colors.WHITE}* {table_name} {Colors.RESET}- {record_count} registros - {Colors.CYAN}{index_type} + multimedia{Colors.RESET}"
                        )
                    else:
                        print(
                            f"{Colors.WHITE}  {table_name} {Colors.RESET}- {record_count} registros - {Colors.YELLOW}{index_type}{Colors.RESET}"
                        )
                else:
                    print(
                        f"{Colors.WHITE}  {table_name} {Colors.RESET}- [información no disponible]"
                    )
            except Exception as e:
                print(f"{Colors.RED}  {table_name} - [error: {e}]{Colors.RESET}")

    def do_describe(self, arg):
        """Muestra la estructura detallada de una tabla."""
        if not arg:
            print(
                f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Debe especificar un nombre de tabla{Colors.RESET}"
            )
            print(f"{Colors.YELLOW}Uso: describe nombre_tabla{Colors.RESET}")
            return

        table_name = arg.strip()
        table_info = self.db.get_table_info(table_name)

        if not table_info:
            print(
                f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Tabla '{table_name}' no encontrada{Colors.RESET}"
            )
            return

        # CORREGIDO: get_table_info() retorna un string, no un dict
        # Simplemente imprimir el string formateado que ya contiene toda la información
        print(table_info)

    def do_stats(self, arg):
        """Muestra estadísticas de una tabla."""
        if not arg:
            print(
                f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Debe especificar un nombre de tabla{Colors.RESET}"
            )
            print(f"{Colors.YELLOW}Uso: stats nombre_tabla{Colors.RESET}")
            return

        table_name = arg.strip()
        table_info = self.db.get_table_info(table_name)

        if not table_info:
            print(
                f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Tabla '{table_name}' no encontrada{Colors.RESET}"
            )
            return

        # CORREGIDO: get_table_info() retorna un string formateado, no un dict
        # El método ya incluye estadísticas completas
        print(table_info)

    def do_exit(self, arg):
        """Sale del programa."""
        print(f"{Colors.YELLOW}¡Hasta pronto!{Colors.RESET}")
        return True

    def do_quit(self, arg):
        """Alias para salir del programa."""
        return self.do_exit(arg)

    # Añadir alias útiles
    do_ls = do_tables
    do_desc = do_describe


if __name__ == "__main__":
    try:
        # Comprobar soporte de colores en la terminal
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        if not is_tty:
            # Desactivar colores si no hay soporte
            for attr in dir(Colors):
                if not attr.startswith("__"):
                    setattr(Colors, attr, "")

        DatabaseShell().cmdloop()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Programa interrumpido por el usuario.{Colors.RESET}")
    except Exception as e:
        print(
            f"{Colors.BG_RED}{Colors.WHITE} ERROR {Colors.RESET} {Colors.RED}Error inesperado: {e}{Colors.RESET}"
        )
        import traceback

        traceback.print_exc()
