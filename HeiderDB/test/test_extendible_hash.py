import os
import sys
import random
import time

# Añadir el directorio padre al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from HeiderDB.database.table import Table

# Tamaño de página pequeño para probar la estructura del hash con divisiones frecuentes
PAGE_SIZE = 4096

def clear_screen():
    """Limpia la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def create_test_table():
    """Crear una tabla de prueba con un índice de hash extensible"""
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
    
    # Crear la tabla con un hash extensible como índice
    table = Table(
        name="test_hash",
        columns=columns,
        primary_key="id",
        page_size=PAGE_SIZE,
        index_type="extendible_hash"  # Usar hash extensible en lugar de B+ tree
    )
    
    print(f"Tabla 'test_hash' creada con tamaño de página: {PAGE_SIZE} bytes")
    print(f"Columnas: {table.get_column_names()}")
    print(f"Profundidad global inicial del hash: {table.index.global_depth}")
    print(f"Factor de bloque: {table.index.block_factor}")
    
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

def print_hash_info(table):
    """Mostrar información detallada del hash extensible"""
    index = table.index
    
    print("\n=== INFORMACIÓN DEL HASH EXTENSIBLE ===")
    print(f"Profundidad global: {index.global_depth}")
    print(f"Factor de bloque: {index.block_factor}")
    print(f"Tamaño de página: {table.page_size} bytes")
    print(f"Número de buckets: {len(set(index.directory.values()))}")
    print(f"Número de registros: {index.count()}")
    
    # Mostrar información del directorio
    print("\n--- Directorio ---")
    print(f"{'Índice binario':<15} | {'ID Bucket':<10}")
    print("-" * 30)
    
    # Limitar a mostrar solo los primeros 20 para no saturar la pantalla
    sorted_dir = sorted(index.directory.items())
    if len(sorted_dir) > 20:
        for bin_index, bucket_id in sorted_dir[:10]:
            print(f"{bin_index:<15} | {bucket_id:<10}")
        print("...")  # Indicar que hay más entradas
        for bin_index, bucket_id in sorted_dir[-10:]:
            print(f"{bin_index:<15} | {bucket_id:<10}")
        print(f"\nTotal de entradas en directorio: {len(sorted_dir)}")
    else:
        for bin_index, bucket_id in sorted_dir:
            print(f"{bin_index:<15} | {bucket_id:<10}")
    
    # Mostrar información de buckets
    print("\n--- Buckets ---")
    print(f"{'ID':<5} | {'Prof. local':<12} | {'Claves':<8} | {'Overflow':<8}")
    print("-" * 40)
    
    # Mostrar los primeros 10 buckets únicos
    unique_buckets = sorted(set(index.directory.values()))
    for bucket_id in unique_buckets[:min(10, len(unique_buckets))]:
        bucket = index._read_bucket(bucket_id)
        overflow = "Sí" if bucket.next != -1 else "No"
        print(f"{bucket_id:<5} | {bucket.local_depth:<12} | {len(bucket.keys):<8} | {overflow:<8}")
    
    if len(unique_buckets) > 10:
        print(f"... y {len(unique_buckets) - 10} buckets más")

def print_menu():
    """Mostrar el menú de opciones"""
    print("\n===== MENÚ DE PRUEBAS DEL HASH EXTENSIBLE =====")
    print("1. Insertar un registro")
    print("2. Insertar registros aleatorios en masa")
    print("3. Buscar registro por ID")
    print("4. Buscar registros por rango de IDs")
    print("5. Eliminar registro por ID")
    print("6. Mostrar todos los registros")
    print("7. Mostrar información del hash extensible")
    print("8. Ver distribución de buckets")
    print("9. Salir")
    print("===============================================")

def print_bucket_distribution(table):
    """Mostrar la distribución de claves en los buckets"""
    index = table.index
    
    # Obtener información de todos los buckets
    bucket_stats = {}
    unique_buckets = set(index.directory.values())
    
    # Recopilar estadísticas de buckets
    for bucket_id in unique_buckets:
        total_keys = 0
        overflow_count = 0
        
        # Contar claves en el bucket principal
        bucket = index._read_bucket(bucket_id)
        main_keys = len(bucket.keys)
        total_keys += main_keys
        
        # Contar claves y buckets de overflow
        current = bucket
        while current.next != -1:
            overflow_count += 1
            current = index._read_bucket(current.next)
            total_keys += len(current.keys)
        
        bucket_stats[bucket_id] = {
            "local_depth": bucket.local_depth,
            "main_keys": main_keys,
            "total_keys": total_keys,
            "overflow_buckets": overflow_count
        }
    
    # Mostrar estadísticas de los buckets
    print("\n=== DISTRIBUCIÓN DE BUCKETS ===")
    
    # Calcular estadísticas generales
    depths = [stats["local_depth"] for stats in bucket_stats.values()]
    keys_per_bucket = [stats["total_keys"] for stats in bucket_stats.values()]
    overflow_counts = [stats["overflow_buckets"] for stats in bucket_stats.values()]
    
    if bucket_stats:
        avg_depth = sum(depths) / len(depths)
        avg_keys = sum(keys_per_bucket) / len(keys_per_bucket)
        max_keys = max(keys_per_bucket) if keys_per_bucket else 0
        total_overflow = sum(overflow_counts)
        
        print(f"Profundidad global: {index.global_depth}")
        print(f"Profundidad local promedio: {avg_depth:.2f}")
        print(f"Claves por bucket (promedio): {avg_keys:.2f}")
        print(f"Buckets con overflow: {sum(1 for c in overflow_counts if c > 0)}")
        print(f"Total de buckets de overflow: {total_overflow}")
        
        # Mostrar histograma de distribución de claves
        print("\nDistribución de claves por bucket:")
        
        # Agrupar por cantidad de claves
        distribution = {}
        for keys in keys_per_bucket:
            if keys not in distribution:
                distribution[keys] = 0
            distribution[keys] += 1
        
        # Mostrar histograma
        for keys, count in sorted(distribution.items()):
            bar = "#" * min(count * 2, 40)  # Escalar para que no sea muy grande
            print(f"{keys:2} claves: {bar} ({count})")
    else:
        print("No hay buckets para analizar.")

def main():
    clear_screen()
    print("=== PRUEBA DEL HASH EXTENSIBLE ===")
    
    try:
        # Intentar cargar la tabla existente
        table = Table.from_table_name("test_hash", PAGE_SIZE)
        print("Tabla 'test_hash' cargada exitosamente")
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
                
                # Mostrar información del hash después de la inserción
                index = table.index
                bin_index = index.hashindex(id_value)
                bucket_id = index.directory[bin_index]
                
                print(f"\nInformación del hash:")
                print(f"- Índice binario de la clave: {bin_index}")
                print(f"- ID del bucket donde se almacenó: {bucket_id}")
                print(f"- Profundidad global actual: {index.global_depth}")
                
                bucket = index._read_bucket(bucket_id)
                print(f"- Profundidad local del bucket: {bucket.local_depth}")
                print(f"- Número de claves en el bucket: {len(bucket.keys)}")
            
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
                
                # Opcional: permitir especificar rango de IDs
                use_range = input("¿Desea especificar un rango para los IDs? (s/n): ").lower() == 's'
                if use_range:
                    min_id = int(input("ID mínimo: "))
                    max_id = int(input("ID máximo: "))
                    if max_id <= min_id:
                        raise ValueError("El ID máximo debe ser mayor al mínimo")
                else:
                    min_id = 1
                    max_id = 100000
                
                start_time = time.time()
                inserted = 0
                skipped = 0
                depth_increases = 0
                initial_depth = table.index.global_depth
                
                print("\nInsertando registros...")
                for _ in range(num_records):
                    try:
                        # Generar ID único para evitar colisiones
                        unique_id = random.randint(min_id, max_id)
                        while table.search("id", unique_id) is not None:
                            unique_id = random.randint(min_id, max_id)
                            skipped += 1
                        
                        record = generate_random_record(unique_id)
                        prev_depth = table.index.global_depth
                        table.add(record)
                        inserted += 1
                        
                        # Verificar si aumentó la profundidad global
                        if table.index.global_depth > prev_depth:
                            depth_increases += 1
                        
                        # Mostrar progreso cada 10 inserciones
                        if inserted % 10 == 0:
                            print(f"Insertados: {inserted}/{num_records}", end="\r")
                    
                    except Exception as e:
                        print(f"\nError en inserción {inserted+1}: {e}")
                
                elapsed_time = time.time() - start_time
                final_depth = table.index.global_depth
                
                print(f"\nSe insertaron {inserted} registros en {elapsed_time:.2f} segundos")
                print(f"Registros omitidos (colisiones): {skipped}")
                print(f"Velocidad: {inserted/elapsed_time:.2f} registros/segundo")
                print(f"Cambios en profundidad global: {initial_depth} → {final_depth}")
                print(f"Número de incrementos de profundidad: {depth_increases}")
                
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
                    
                    # Mostrar información de ubicación
                    index = table.index
                    bin_index = index.hashindex(id_value)
                    bucket_id = index.directory[bin_index]
                    
                    print("\nInformación de ubicación:")
                    print(f"Índice binario: {bin_index}")
                    print(f"ID del bucket: {bucket_id}")
                else:
                    print(f"No se encontró registro con ID={id_value}")
            
            except ValueError:
                print("El ID debe ser un número entero")
        
        elif option == "4":
            # Buscar registros por rango
            clear_screen()
            print("=== BÚSQUEDA POR RANGO ===")
            print("Nota: Las búsquedas por rango no son eficientes en hash")
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
                
                # Guardar información antes de eliminar para comparar después
                index = table.index
                before_global_depth = index.global_depth
                bin_index = index.hashindex(id_value)
                bucket_id = index.directory[bin_index]
                bucket = index._read_bucket(bucket_id)
                before_local_depth = bucket.local_depth
                
                # Eliminar el registro
                start_time = time.time()
                result = table.remove("id", id_value)
                elapsed_time = time.time() - start_time
                
                if result:
                    print(f"Registro con ID={id_value} eliminado en {elapsed_time*1000:.2f} ms")
                    
                    # Verificar si cambió la estructura del hash
                    after_global_depth = index.global_depth
                    bucket = index._read_bucket(bucket_id)
                    after_local_depth = bucket.local_depth
                    
                    if after_global_depth != before_global_depth or after_local_depth != before_local_depth:
                        print("\nCambios en la estructura del hash:")
                        if after_global_depth != before_global_depth:
                            print(f"- Profundidad global: {before_global_depth} → {after_global_depth}")
                        if after_local_depth != before_local_depth:
                            print(f"- Profundidad local del bucket: {before_local_depth} → {after_local_depth}")
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
            # Mostrar información del hash extensible
            clear_screen()
            print_hash_info(table)
        
        elif option == "8":
            # Ver distribución de buckets
            clear_screen()
            print_bucket_distribution(table)
        
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