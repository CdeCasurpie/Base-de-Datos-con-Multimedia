import os
import sys
import random
import time

# Añadir el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.table import Table

# Tamaño de página pequeño para probar la estructura del archivo secuencial con reorganizaciones frecuentes
PAGE_SIZE = 4096

def clear_screen():
    """Limpia la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def create_test_table():
    """Crear una tabla de prueba con un índice de archivo secuencial"""
    # Verificar y crear el directorio de datos si no existe
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)
    
    # Definir la estructura de la tabla: columnas y tipos
    columns = {
        "id": "INT",               # Clave primaria
        "name": "VARCHAR(30)",     # Nombre
        "age": "INT",              # Edad
        "score": "FLOAT"           # Puntuación
    }
    
    # Crear la tabla con un archivo secuencial como índice
    table = Table(
        name="test_seq",
        columns=columns,
        primary_key="id",
        page_size=PAGE_SIZE,
        index_type="sequential_file"
    )
    
    print(f"Tabla 'test_seq' creada con tamaño de página: {PAGE_SIZE} bytes")
    print(f"Columnas: {table.get_column_names()}")
    print(f"Registros por página: {table.index.entries_per_page}")
    
    return table

def generate_random_record(id_value=None):
    """Generar un registro aleatorio para pruebas"""
    if id_value is None:
        id_value = random.randint(1, 10000)
    
    names = ["Ana", "Juan", "Pedro", "María", "Carlos", "Lucía", "Pablo", "Elena", "Jorge", "Isabel"]
    
    return {
        "id": id_value,
        "name": random.choice(names) + " " + chr(random.randint(65, 90)) + ".",
        "age": random.randint(18, 80),
        "score": round(random.uniform(0, 100), 2)
    }

def print_record(record):
    """Imprimir un registro en formato legible"""
    if record is None:
        print("Registro no encontrado")
        return
    
    print("─" * 50)
    for field, value in record.items():
        print(f"│ {field.ljust(10)}: {str(value).ljust(35)} │")
    print("─" * 50)

def print_records(records):
    """Imprimir una lista de registros"""
    if not records:
        print("No se encontraron registros")
        return
    
    print(f"Registros encontrados: {len(records)}")
    print("─" * 50)
    print(f"│ {'ID'.ljust(6)}│ {'Nombre'.ljust(20)}│ {'Edad'.ljust(6)}│ {'Puntuación'.ljust(11)}│")
    print("─" * 50)
    for record in records:
        print(f"│ {str(record['id']).ljust(6)}│ {record['name'].ljust(20)}│ {str(record['age']).ljust(6)}│ {str(record['score']).ljust(11)}│")
    print("─" * 50)

def print_sequential_file_info(table):
    """Mostrar información detallada del archivo secuencial"""
    index = table.index
    
    print("\n=== INFORMACIÓN DEL ARCHIVO SECUENCIAL ===")
    print(f"Total de registros: {index.record_count}")
    print(f"Registros en overflow: {index.overflow_count}")
    print(f"Registros en archivo principal: {index.record_count - index.overflow_count}")
    print(f"Tamaño de entrada: {index.entry_size} bytes")
    print(f"Entradas por página: {index.entries_per_page}")
    
    try:
        # Calcular tamaño aproximado de los archivos
        main_file_size = os.path.getsize(index.index_file) if os.path.exists(index.index_file) else 0
        overflow_file_size = os.path.getsize(index.overflow_file) if os.path.exists(index.overflow_file) else 0
        
        print(f"Tamaño del archivo principal: {main_file_size} bytes")
        print(f"Tamaño del archivo overflow: {overflow_file_size} bytes")
        
        # Calcular densidad de ocupación
        if main_file_size > 0:
            density = ((index.record_count - index.overflow_count) * index.entry_size) / main_file_size * 100
            print(f"Densidad de ocupación del archivo principal: {density:.2f}%")
    except Exception as e:
        print(f"Error al calcular estadísticas de archivos: {e}")

def print_menu():
    """Mostrar el menú de opciones"""
    print("\n===== MENÚ DE PRUEBAS DEL ARCHIVO SECUENCIAL =====")
    print("1. Insertar un registro")
    print("2. Insertar registros aleatorios en masa")
    print("3. Buscar registro por ID")
    print("4. Buscar registros por rango de IDs")
    print("5. Eliminar registro por ID")
    print("6. Mostrar todos los registros")
    print("7. Mostrar información del archivo secuencial")
    print("8. Forzar reorganización del archivo (rebuild)")
    print("9. Salir")
    print("==================================================")

def main():
    clear_screen()
    print("=== PRUEBA DEL ÍNDICE DE ARCHIVO SECUENCIAL ===")
    
    try:
        # Intentar cargar la tabla existente
        table = Table.from_table_name("test_seq", PAGE_SIZE)
        print("Tabla 'test_seq' cargada exitosamente")
    except Exception as e:
        # Si no existe, crear una nueva tabla
        print(f"Error al cargar tabla: {e}")
        print("Creando nueva tabla de prueba...")
        table = create_test_table()
    
    while True:
        print_menu()
        option = input("Elija una opción (1-9): ")
        
        if option == "1":
            # Insertar un registro manualmente
            clear_screen()
            print("=== INSERTAR REGISTRO ===")
            
            try:
                id_value = int(input("ID (entero): "))
                
                # Verificar si ya existe el ID
                if table.search("id", id_value) is not None:
                    print(f"Error: Ya existe un registro con ID={id_value}")
                    continue
                    
                name = input("Nombre (máx 30 caracteres): ")
                age = int(input("Edad (entero): "))
                score = float(input("Puntuación (decimal): "))
                
                record = {
                    "id": id_value,
                    "name": name,
                    "age": age,
                    "score": score
                }
                
                # Medir tiempo de inserción
                start_time = time.time()
                table.add(record)
                elapsed_time = time.time() - start_time
                
                print(f"Registro con ID={id_value} insertado en {elapsed_time*1000:.2f} ms")
                
                # Verificar si hubo reorganización
                print("\nEstado del archivo secuencial:")
                print(f"Registros totales: {table.index.record_count}")
                print(f"Registros en overflow: {table.index.overflow_count}")
                
                # Si la proporción de overflow es alta, sugerir reorganización
                if table.index.overflow_count > table.index.record_count / 3:
                    print("\nSugerencia: La cantidad de registros en overflow es alta.")
                    print("Considere ejecutar una reorganización (opción 8).")
            
            except ValueError as e:
                print(f"Error de formato: {e}")
            except Exception as e:
                print(f"Error al insertar: {e}")
        
        elif option == "2":
            # Insertar registros aleatorios en masa
            clear_screen()
            print("=== INSERCIÓN MASIVA ===")
            try:
                num_records = int(input("Cantidad de registros a insertar: "))
                if num_records <= 0:
                    raise ValueError("La cantidad debe ser mayor a cero")
                
                # Opcional: permitir especificar orden de los datos
                data_order = input("¿En qué orden insertar los datos? (a)scendente, (d)escendente, (r)andom: ").lower()
                
                # Generar IDs según el orden especificado
                if data_order == "a":
                    ids = sorted([random.randint(1, 100000) for _ in range(num_records)])
                    print("Insertando en orden ascendente...")
                elif data_order == "d":
                    ids = sorted([random.randint(1, 100000) for _ in range(num_records)], reverse=True)
                    print("Insertando en orden descendente...")
                else:
                    ids = [random.randint(1, 100000) for _ in range(num_records)]
                    print("Insertando en orden aleatorio...")
                
                start_time = time.time()
                inserted = 0
                skipped = 0
                rebuild_count = 0
                prev_overflow_count = table.index.overflow_count
                
                print("\nInsertando registros...")
                for id_value in ids:
                    try:
                        # Evitar duplicados
                        if table.search("id", id_value) is not None:
                            skipped += 1
                            continue
                        
                        record = generate_random_record(id_value)
                        table.add(record)
                        inserted += 1
                        
                        # Detectar si hubo reorganización
                        if table.index.overflow_count < prev_overflow_count:
                            rebuild_count += 1
                            prev_overflow_count = table.index.overflow_count
                        else:
                            prev_overflow_count = table.index.overflow_count
                        
                        # Mostrar progreso cada 10 inserciones
                        if inserted % 10 == 0:
                            print(f"Insertados: {inserted}/{num_records}", end="\r")
                    
                    except Exception as e:
                        print(f"\nError en inserción {inserted+1}: {e}")
                
                elapsed_time = time.time() - start_time
                
                print(f"\nSe insertaron {inserted} registros en {elapsed_time:.2f} segundos")
                print(f"Registros omitidos (duplicados): {skipped}")
                print(f"Velocidad: {inserted/max(0.001, elapsed_time):.2f} registros/segundo")
                print(f"Reorganizaciones automáticas: {rebuild_count}")
                
                print("\nEstado final del archivo secuencial:")
                print(f"Registros totales: {table.index.record_count}")
                print(f"Registros en archivo principal: {table.index.record_count - table.index.overflow_count}")
                print(f"Registros en overflow: {table.index.overflow_count}")
                print(f"Proporción de overflow: {table.index.overflow_count/max(1, table.index.record_count)*100:.2f}%")
                
            except ValueError as e:
                print(f"Error: {e}")
        
        elif option == "3":
            # Buscar registro por ID
            clear_screen()
            print("=== BÚSQUEDA POR ID ===")
            try:
                id_value = int(input("ID a buscar: "))
                
                start_time = time.time()
                record = table.search("id", id_value)
                elapsed_time = time.time() - start_time
                
                if record:
                    print(f"Registro encontrado en {elapsed_time*1000:.2f} ms:")
                    print_record(record)
                else:
                    print(f"No se encontró registro con ID={id_value}")
            
            except ValueError:
                print("El ID debe ser un número entero")
        
        elif option == "4":
            # Buscar registros por rango
            clear_screen()
            print("=== BÚSQUEDA POR RANGO ===")
            try:
                start_id = int(input("ID inicial: "))
                end_id = int(input("ID final: "))
                
                if end_id < start_id:
                    raise ValueError("El ID final debe ser mayor o igual al ID inicial")
                
                start_time = time.time()
                records = table.range_search("id", start_id, end_id)
                elapsed_time = time.time() - start_time
                
                print(f"Búsqueda completada en {elapsed_time*1000:.2f} ms")
                print_records(records)
            
            except ValueError as e:
                print(f"Error: {e}")
        
        elif option == "5":
            # Eliminar registro
            clear_screen()
            print("=== ELIMINAR REGISTRO ===")
            try:
                id_value = int(input("ID del registro a eliminar: "))
                
                # Verificar si existe antes de eliminar
                if table.search("id", id_value) is None:
                    print(f"No existe registro con ID={id_value}")
                    continue
                
                # Guardar recuentos antes para comparar
                before_count = table.index.record_count
                before_overflow = table.index.overflow_count
                
                # Eliminar el registro
                start_time = time.time()
                result = table.remove("id", id_value)
                elapsed_time = time.time() - start_time
                
                if result:
                    after_count = table.index.record_count
                    after_overflow = table.index.overflow_count
                    
                    print(f"Registro con ID={id_value} eliminado en {elapsed_time*1000:.2f} ms")
                    
                    if before_overflow != after_overflow:
                        print(f"Registros de overflow reducidos: {before_overflow} → {after_overflow}")
                else:
                    print(f"No se pudo eliminar el registro con ID={id_value}")
            
            except ValueError:
                print("El ID debe ser un número entero")
            except Exception as e:
                print(f"Error al eliminar: {e}")
        
        elif option == "6":
            # Mostrar todos los registros
            clear_screen()
            print("=== TODOS LOS REGISTROS ===")
            
            start_time = time.time()
            records = table.get_all()
            elapsed_time = time.time() - start_time
            
            print(f"Recuperación completada en {elapsed_time*1000:.2f} ms")
            print_records(records)
            print(f"Total de registros: {len(records)}")
        
        elif option == "7":
            # Mostrar información del archivo secuencial
            clear_screen()
            print_sequential_file_info(table)
        
        elif option == "8":
            # Forzar reorganización del archivo
            clear_screen()
            print("=== REORGANIZACIÓN DEL ARCHIVO SECUENCIAL ===")
            
            before_records = table.index.record_count
            before_overflow = table.index.overflow_count
            
            print(f"Estado antes de reorganizar:")
            print(f"- Registros totales: {before_records}")
            print(f"- Registros en archivo principal: {before_records - before_overflow}")
            print(f"- Registros en overflow: {before_overflow}")
            print(f"- Proporción de overflow: {before_overflow/max(1, before_records)*100:.2f}%")
            
            print("\nReorganizando archivo secuencial...")
            start_time = time.time()
            table.index.rebuild()
            elapsed_time = time.time() - start_time
            
            after_records = table.index.record_count
            after_overflow = table.index.overflow_count
            
            print(f"\nReorganización completada en {elapsed_time*1000:.2f} ms")
            print(f"Estado después de reorganizar:")
            print(f"- Registros totales: {after_records}")
            print(f"- Registros en archivo principal: {after_records - after_overflow}")
            print(f"- Registros en overflow: {after_overflow}")
            print(f"- Proporción de overflow: {after_overflow/max(1, after_records)*100:.2f}%")
        
        elif option == "9":
            # Salir
            print("Saliendo del programa...")
            break
        
        else:
            print("Opción no válida. Intente nuevamente.")
        
        input("\nPresione Enter para continuar...")
        clear_screen()

if __name__ == "__main__":
    main()
