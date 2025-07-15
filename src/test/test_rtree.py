#!/usr/bin/env python3
"""
Script de prueba para el índice R-Tree espacial
Demuestra el funcionamiento completo del RTreeIndex integrado con la clase Table
"""

import os
import sys
import random
import time
import json
from shapely.geometry import Point, Polygon, box
from shapely.wkt import dumps as wkt_dumps

# Añadir el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.table import Table  # Importar la clase Table modificada


def clear_screen():
    """Limpia la pantalla."""
    os.system("cls" if os.name == "nt" else "clear")


def clean_previous_data():
    """Limpia datos de ejecuciones anteriores."""
    import shutil

    data_dirs = ["data/tables", "data/indexes"]

    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            try:
                shutil.rmtree(data_dir)
                print(f"✓ Directorio limpio: {data_dir}")
            except Exception as e:
                print(f"Advertencia limpiando {data_dir}: {e}")


def create_spatial_table():
    """Crea una tabla con columnas espaciales."""
    print("Creando tabla con datos espaciales...")

    # Definir columnas de la tabla
    columns = {
        "id": "INT",
        "name": "VARCHAR(50)",
        "location": "POINT",
        "area": "POLYGON",
        "category": "VARCHAR(20)",
    }

    # Crear tabla con índice espacial
    table = Table(
        name="spatial_test",
        columns=columns,
        primary_key="id",
        page_size=4096,
        index_type="bplus_tree",
        spatial_columns=["location", "area"],  # Columnas para índices espaciales
    )

    print(f"Tabla '{table.name}' creada exitosamente")
    print(f"Columnas: {list(columns.keys())}")
    print(f"Índices espaciales en: {table.spatial_columns}")

    return table


def generate_random_point():
    """Genera un punto aleatorio con coordenadas redondeadas."""
    x = round(random.uniform(-100, 100), 2)
    y = round(random.uniform(-100, 100), 2)
    return Point(x, y)


def generate_random_polygon():
    """Genera un polígono rectangular aleatorio más simple."""
    x = random.uniform(-100, 90)
    y = random.uniform(-100, 90)
    width = random.uniform(2, 10)  # Reducir tamaño para WKT más corto
    height = random.uniform(2, 10)

    # Crear un polígono simple con 4 puntos (rectángulo)
    polygon = box(x, y, x + width, y + height)

    # Verificar que el WKT no sea demasiado largo
    wkt_str = polygon.wkt
    if len(wkt_str) > 450:  # Dejar margen de seguridad
        # Si es muy largo, crear un polígono más simple
        return box(round(x, 1), round(y, 1), round(x + width, 1), round(y + height, 1))

    return polygon


def insert_sample_data(table, num_records=50):
    """Inserta datos de muestra en la tabla."""
    print(f"Insertando {num_records} registros de muestra...")

    categories = ["Restaurant", "Hospital", "School", "Park", "Store"]

    for i in range(1, num_records + 1):
        # Generar geometrías aleatorias
        point = generate_random_point()
        polygon = generate_random_polygon()

        record = {
            "id": i,
            "name": f"Place_{i}",
            "location": wkt_dumps(point),  # Convertir a WKT
            "area": wkt_dumps(polygon),  # Convertir a WKT
            "category": random.choice(categories),
        }

        try:
            table.add(record)
        except Exception as e:
            print(f"Error insertando registro {i}: {e}")

    print(f"Datos insertados. Total de registros: {table.get_record_count()}")


def test_spatial_searches(table):
    """Prueba diferentes tipos de búsquedas espaciales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE BÚSQUEDAS ESPACIALES")
    print("=" * 50)

    # 1. Búsqueda por intersección
    print("\n1. Búsqueda por intersección:")
    test_box = box(-50, -50, 50, 50)
    print(f"Buscando áreas que intersectan con: {test_box.bounds}")

    try:
        results = table.intersection_search("area", test_box)
        print(f"Encontrados {len(results)} resultados:")
        for i, result in enumerate(results[:5]):  # Mostrar solo los primeros 5
            print(f"  {i+1}. {result['name']} - {result['category']}")
    except Exception as e:
        print(f"Error en búsqueda por intersección: {e}")

    # 2. Búsqueda por radio
    print("\n2. Búsqueda por radio:")
    center_point = (0, 0)
    radius = 25
    print(f"Buscando ubicaciones dentro de {radius} unidades de {center_point}")

    try:
        results = table.spatial_search("location", center_point, radius)
        print(f"Encontrados {len(results)} resultados:")
        for i, result in enumerate(results[:5]):
            print(f"  {i+1}. {result['name']} - {result['category']}")
    except Exception as e:
        print(f"Error en búsqueda por radio: {e}")

    # 3. Búsqueda de vecinos más cercanos
    print("\n3. Búsqueda de vecinos más cercanos:")
    query_point = (10, 10)
    k = 3
    print(f"Buscando {k} ubicaciones más cercanas a {query_point}")

    try:
        results = table.nearest_search("location", query_point, k)
        print(f"Encontrados {len(results)} vecinos más cercanos:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['name']} - {result['category']}")
    except Exception as e:
        print(f"Error en búsqueda de vecinos: {e}")

    # 4. Búsqueda por rango espacial
    print("\n4. Búsqueda por rango espacial:")
    min_point = (-30, -30)
    max_point = (30, 30)
    print(f"Buscando ubicaciones en rango: {min_point} a {max_point}")

    try:
        results = table.range_search_spatial("location", min_point, max_point)
        print(f"Encontrados {len(results)} resultados en rango:")
        for i, result in enumerate(results[:5]):
            print(f"  {i+1}. {result['name']} - {result['category']}")
    except Exception as e:
        print(f"Error en búsqueda por rango: {e}")


def test_performance(table):
    """Prueba el rendimiento de las búsquedas espaciales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE RENDIMIENTO")
    print("=" * 50)

    num_tests = 100

    # Test 1: Búsquedas por intersección
    print(f"\n1. Rendimiento de búsquedas por intersección ({num_tests} pruebas):")
    start_time = time.time()

    for _ in range(num_tests):
        # Generar box aleatorio para prueba
        x = random.uniform(-80, 80)
        y = random.uniform(-80, 80)
        test_box = box(x, y, x + 20, y + 20)
        try:
            results = table.intersection_search("area", test_box)
        except:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000  # En milisegundos
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")

    # Test 2: Búsquedas por radio
    print(f"\n2. Rendimiento de búsquedas por radio ({num_tests} pruebas):")
    start_time = time.time()

    for _ in range(num_tests):
        center = (random.uniform(-50, 50), random.uniform(-50, 50))
        radius = random.uniform(10, 30)
        try:
            results = table.spatial_search("location", center, radius)
        except:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")

    # Test 3: Búsquedas de vecinos más cercanos
    print(f"\n3. Rendimiento de búsquedas de vecinos ({num_tests} pruebas):")
    start_time = time.time()

    for _ in range(num_tests):
        point = (random.uniform(-50, 50), random.uniform(-50, 50))
        try:
            results = table.nearest_search("location", point, 5)
        except:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")


def show_spatial_statistics(table):
    """Muestra estadísticas de los índices espaciales."""
    print("\n" + "=" * 50)
    print("ESTADÍSTICAS DE ÍNDICES ESPACIALES")
    print("=" * 50)

    try:
        stats = table.get_spatial_index_stats()

        for column, index_stats in stats.items():
            print(f"\nÍndice espacial para columna '{column}':")
            print(f"  - Total de entradas: {index_stats['total_entries']}")
            print(f"  - Dimensiones: {index_stats['dimension']}D")
            print(f"  - Capacidad de hoja: {index_stats['leaf_capacity']}")
            print(f"  - Capacidad de índice: {index_stats['index_capacity']}")
            print(f"  - Factor de llenado: {index_stats['fill_factor']}")
            if index_stats["bounds"]:
                bounds = index_stats["bounds"]
                print(
                    f"  - Límites espaciales: ({bounds[0]:.2f}, {bounds[1]:.2f}) a ({bounds[2]:.2f}, {bounds[3]:.2f})"
                )

    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")


def interactive_search(table):
    """Permite al usuario realizar búsquedas interactivas."""
    print("\n" + "=" * 50)
    print("BÚSQUEDAS INTERACTIVAS")
    print("=" * 50)

    while True:
        print(
            """
Opciones de búsqueda:
1. Búsqueda por intersección (área)
2. Búsqueda por radio (ubicación)
3. Vecinos más cercanos (ubicación) 
4. Búsqueda por rango (ubicación)
5. Volver al menú principal
"""
        )

        choice = input("Selecciona una opción (1-5): ").strip()

        if choice == "1":
            try:
                print("Ingresa las coordenadas del rectángulo (xmin ymin xmax ymax):")
                coords = list(map(float, input().split()))
                if len(coords) == 4:
                    test_box = box(coords[0], coords[1], coords[2], coords[3])
                    results = table.intersection_search("area", test_box)
                    print(f"\nEncontrados {len(results)} resultados:")
                    for i, result in enumerate(results[:10]):
                        print(f"  {i+1}. {result['name']} - {result['category']}")
                else:
                    print("Error: Debes ingresar exactamente 4 números")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "2":
            try:
                print("Ingresa el punto central (x y) y el radio:")
                values = list(map(float, input().split()))
                if len(values) == 3:
                    center = (values[0], values[1])
                    radius = values[2]
                    results = table.spatial_search("location", center, radius)
                    print(f"\nEncontrados {len(results)} resultados:")
                    for i, result in enumerate(results[:10]):
                        print(f"  {i+1}. {result['name']} - {result['category']}")
                else:
                    print("Error: Debes ingresar exactamente 3 números (x y radio)")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "3":
            try:
                print("Ingresa el punto de consulta (x y) y número de vecinos:")
                values = list(map(float, input().split()))
                if len(values) >= 2:
                    point = (values[0], values[1])
                    k = int(values[2]) if len(values) > 2 else 5
                    results = table.nearest_search("location", point, k)
                    print(f"\nEncontrados {len(results)} vecinos más cercanos:")
                    for i, result in enumerate(results):
                        print(f"  {i+1}. {result['name']} - {result['category']}")
                else:
                    print("Error: Debes ingresar al menos 2 números")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "4":
            try:
                print("Ingresa el rango (xmin ymin xmax ymax):")
                coords = list(map(float, input().split()))
                if len(coords) == 4:
                    min_point = (coords[0], coords[1])
                    max_point = (coords[2], coords[3])
                    results = table.range_search_spatial(
                        "location", min_point, max_point
                    )
                    print(f"\nEncontrados {len(results)} resultados:")
                    for i, result in enumerate(results[:10]):
                        print(f"  {i+1}. {result['name']} - {result['category']}")
                else:
                    print("Error: Debes ingresar exactamente 4 números")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "5":
            break

        else:
            print("Opción inválida")

        input("\nPresiona Enter para continuar...")


def test_crud_operations(table):
    """Prueba operaciones CRUD con datos espaciales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE OPERACIONES CRUD")
    print("=" * 50)

    # CREATE - Insertar nuevo registro
    print("\n1. Insertando nuevo registro...")
    new_record = {
        "id": 999,
        "name": "Test_Location",
        "location": "POINT(25.5 30.2)",
        "area": "POLYGON((20 25, 30 25, 30 35, 20 35, 20 25))",
        "category": "Test",
    }

    try:
        table.add(new_record)
        print("✓ Registro insertado exitosamente")
    except Exception as e:
        print(f"✗ Error insertando: {e}")

    # READ - Buscar el registro insertado
    print("\n2. Buscando el registro insertado...")
    try:
        result = table.search("id", 999)
        if result:
            print(f"✓ Registro encontrado: {result}")
        else:
            print("✗ Registro no encontrado")
    except Exception as e:
        print(f"✗ Error buscando: {e}")

    # UPDATE - Simular actualización (eliminar y reinsertar)
    print("\n3. Simulando actualización del registro...")
    try:
        # Primero eliminar
        table.remove("id", 999)
        print("✓ Registro original eliminado")

        # Luego insertar versión actualizada
        updated_record = {
            "id": 999,
            "name": "Updated_Test_Location",
            "location": "POINT(35.5 40.2)",
            "area": "POLYGON((30 35, 40 35, 40 45, 30 45, 30 35))",
            "category": "Updated_Test",
        }
        table.add(updated_record)
        print("✓ Registro actualizado exitosamente")
    except Exception as e:
        print(f"✗ Error actualizando: {e}")

    # DELETE - Eliminar el registro
    print("\n4. Eliminando el registro de prueba...")
    try:
        table.remove("id", 999)
        print("✓ Registro eliminado exitosamente")

        # Verificar eliminación
        result = table.search("id", 999)
        if not result:
            print("✓ Eliminación verificada - registro no encontrado")
        else:
            print("✗ El registro aún existe después de eliminación")
    except Exception as e:
        print(f"✗ Error eliminando: {e}")


def main():
    """Función principal del script de prueba."""
    clear_screen()
    print("=" * 60)
    print("SCRIPT DE PRUEBA PARA ÍNDICES R-TREE ESPACIALES")
    print("=" * 60)

    # Preguntar si limpiar datos anteriores
    clean_choice = (
        input("\n¿Limpiar datos de ejecuciones anteriores? (s/n): ").strip().lower()
    )
    if clean_choice in ["s", "si", "y", "yes"]:
        clean_previous_data()

    # Crear tabla con datos espaciales
    table = create_spatial_table()


    while True:
        print("\n" + "=" * 50)
        print("MENÚ PRINCIPAL")
        print("=" * 50)
        print(
            """
1. Ejecutar pruebas de búsquedas espaciales
2. Ejecutar pruebas de rendimiento
3. Mostrar estadísticas de índices
4. Búsquedas interactivas
5. Probar operaciones CRUD
6. Insertar más datos de muestra
7. Mostrar todos los registros
8. Salir
"""
        )

        choice = input("Selecciona una opción (1-8): ").strip()

        if choice == "1":
            test_spatial_searches(table)

        elif choice == "2":
            test_performance(table)

        elif choice == "3":
            show_spatial_statistics(table)

        elif choice == "4":
            interactive_search(table)

        elif choice == "5":
            test_crud_operations(table)

        elif choice == "6":
            try:
                num = int(input("¿Cuántos registros adicionales? "))
                current_count = table.get_record_count()
                # cronometro
                start_time = time.time()
                insert_sample_data(table, num)
                end_time = time.time()
                print(f"✓ Datos insertados. Total: {table.get_record_count()}")
            except ValueError:
                print("Error: Ingresa un número válido")

        elif choice == "7":
            print("\nTodos los registros en la tabla:")
            try:
                all_records = table.get_all()
                for i, record in enumerate(
                    all_records[:20]
                ):  # Mostrar solo primeros 20
                    print(
                        f"  {i+1}. ID: {record['id']}, Nombre: {record['name']}, Categoría: {record['category']}"
                    )
                if len(all_records) > 20:
                    print(f"  ... y {len(all_records) - 20} registros más")
                print(f"\nTotal de registros: {len(all_records)}")
            except Exception as e:
                print(f"Error obteniendo registros: {e}")

        elif choice == "8":
            print("\n¡Gracias por usar el script de prueba!")
            print("Cerrando índices...")
            try:
                # Cerrar índices espaciales
                for spatial_index in table.spatial_indexes.values():
                    spatial_index.close()
                print("✓ Índices cerrados correctamente")
            except Exception as e:
                print(f"Advertencia: Error cerrando índices: {e}")
            break

        else:
            print("Opción inválida. Por favor selecciona 1-8.")

        if choice in ["1", "2", "3", "5"]:
            input("\nPresiona Enter para continuar...")
            clear_screen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrumpido por el usuario.")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        import traceback

        traceback.print_exc()
