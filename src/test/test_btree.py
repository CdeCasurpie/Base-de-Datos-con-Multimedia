import os
import sys
import random
import time

# Añadir el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.table import Table

# Tamaño de página muy pequeño para probar el comportamiento del B+ tree con divisiones frecuentes
PAGE_SIZE = 4096  # Tamaño de página pequeño para ver splits frecuentes

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def create_test_table():
    """Crear una tabla de prueba con un índice B+ tree"""
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
    
    # Crear la tabla con un pequeño tamaño de página para ver las divisiones del B+ tree
    table = Table(
        name="test_btree",
        columns=columns,
        primary_key="id",
        page_size=PAGE_SIZE,
        index_type="bplus_tree"
    )
    
    print(f"Tabla 'test_btree' creada con tamaño de página: {PAGE_SIZE} bytes")
    print(f"Columnas: {table.get_column_names()}")
    print(f"Orden del B+ tree: ~{table.index.order}")
    
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
    print(f"│ {"ID".ljust(6)}│ {"Nombre".ljust(20)}│ {"Edad".ljust(6)}│ {"Puntuación".ljust(11)}│")
    print("─" * 50)
    for record in records:
        print(f"│ {str(record['id']).ljust(6)}│ {record['name'].ljust(20)}│ {str(record['age']).ljust(6)}│ {str(record['score']).ljust(11)}│")
    print("─" * 50)

def print_menu():
    """Mostrar el menú de opciones"""
    print("\n===== MENÚ DE PRUEBAS DEL B+ TREE =====")
    print("1. Insertar un registro")
    print("2. Insertar registros aleatorios en masa")
    print("3. Buscar registro por ID")
    print("4. Buscar registros por rango de IDs")
    print("5. Eliminar registro por ID")
    print("6. Mostrar todos los registros")
    print("7. Mostrar información del B+ tree")
    print("8. Salir")
    print("======================================")

def main():
    clear_screen()
    print("=== PRUEBA DEL ÍNDICE B+ TREE ===")
    
    try:
        # Intentar cargar la tabla existente
        table = Table.from_table_name("test_btree", PAGE_SIZE)
        print("Tabla 'test_btree' cargada exitosamente")
    except:
        # Si no existe, crear una nueva tabla
        print("Creando nueva tabla de prueba...")
        table = create_test_table()
    
    while True:
        print_menu()
        option = input("Elija una opción (1-8): ")
        
        if option == "1":
            # Insertar un registro manualmente
            clear_screen()
            print("=== INSERTAR REGISTRO ===")
            
            try:
                id_value = int(input("ID (entero): "))
                name = input("Nombre (máx 30 caracteres): ")
                age = int(input("Edad (entero): "))
                score = float(input("Puntuación (decimal): "))
                
                record = {
                    "id": id_value,
                    "name": name,
                    "age": age,
                    "score": score
                }
                
                table.add(record)
                print(f"Registro con ID={id_value} insertado correctamente")
            
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
                
                start_time = time.time()
                inserted = 0
                for _ in range(num_records):
                    try:
                        # Generar ID único para evitar colisiones
                        unique_id = random.randint(1, 100000)
                        while table.index.search(unique_id) is not None:
                            unique_id = random.randint(1, 100000)
                        
                        record = generate_random_record(unique_id)
                        table.add(record)
                        inserted += 1
                        
                        # Mostrar progreso cada 10 inserciones
                        if inserted % 10 == 0:
                            print(f"Insertados: {inserted}/{num_records}", end="\r")
                    
                    except Exception as e:
                        print(f"\nError en inserción {inserted+1}: {e}")
                
                elapsed_time = time.time() - start_time
                print(f"\nSe insertaron {inserted} registros en {elapsed_time:.2f} segundos")
                print(f"Velocidad: {inserted/elapsed_time:.2f} registros/segundo")
            
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
                
                if table.remove("id", id_value):
                    print(f"Registro con ID={id_value} eliminado correctamente")
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
            # Mostrar información del B+ tree
            clear_screen()
            print("=== INFORMACIÓN DEL B+ TREE ===")
            
            index = table.index
            tree_info = {
                "Orden del árbol": index.order,
                "Altura del árbol": index.height,
                "Nodo raíz": index.root_page_id,
                "Número total de páginas": index.num_pages,
                "Registros indexados": index.count(),
                "Tamaño de página": table.page_size,
                "Columna indexada": index.column_name,
                "Archivo de índice": index.index_file,
                "Archivo de datos": index.data_path
            }
            
            max_key = max(len(key) for key in tree_info.keys())
            for key, value in tree_info.items():
                print(f"{key.ljust(max_key + 2)}: {value}")
        
        elif option == "8":
            # Salir
            print("Saliendo del programa...")
            break
        
        else:
            print("Opción no válida. Intente nuevamente.")
        
        input("\nPresione Enter para continuar...")
        clear_screen()

if __name__ == "__main__":
    main()