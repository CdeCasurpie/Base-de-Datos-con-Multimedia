import os
import sys
import random
import time

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.table import Table

PAGE_SIZE = 4096

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def create_isam_table():
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)

    columns = {
        "id": "INT",
        "name": "VARCHAR(30)",
        "age": "INT",
        "score": "FLOAT"
    }

    table = Table(
        name="test_isam",
        columns=columns,
        primary_key="id",
        page_size=PAGE_SIZE,
        index_type="isam_sparse"
    )

    print("Tabla 'test_isam' creada con índice ISAM sparse")
    return table


def insert_random_record(table, record_id=None):
    names = ["Ana", "Juan", "Pedro", "María", "Carlos"]
    record = {
        "id": record_id if record_id is not None else random.randint(1, 10000),
        "name": random.choice(names),
        "age": random.randint(18, 80),
        "score": round(random.uniform(0, 100), 2)
    }
    try:
        table.add(record)
        print(f"Registro insertado: {record}")
    except ValueError as e:
        print(f"Error al insertar registro: {e}")


def insert_bulk_records(table, num_records):
    for _ in range(num_records):
        insert_random_record(table)
    print(f"{num_records} registros insertados.")


def insert_with_custom_id(table):
    try:
        record_id = int(input("ID deseado (entero): "))
    except ValueError:
        print("ID inválido")
        return
    # resto de campos aleatorios
    insert_random_record(table, record_id=record_id)


def search_record_by_id(table):
    try:
        record_id = int(input("ID del registro a buscar: "))
    except ValueError:
        print("ID inválido")
        return
    record = table.search("id", record_id)
    if record:
        print(f"Registro encontrado: {record}")
    else:
        print(f"Registro con ID {record_id} no encontrado")


def search_records_by_range(table):
    try:
        start_id = int(input("ID inicial: "))
        end_id = int(input("ID final: "))
    except ValueError:
        print("IDs inválidos")
        return
    records = table.range_search("id", start_id, end_id)
    print(f"Registros encontrados entre IDs {start_id}-{end_id}: {len(records)}")
    for record in records:
        print(record)


def show_all_records(table):
    records = table.get_all()
    print(f"Total de registros: {len(records)}")
    for record in records:
        print(record)


def delete_record_by_id(table):
    try:
        record_id = int(input("ID del registro a eliminar: "))
    except ValueError:
        print("ID inválido")
        return
    deleted = table.remove("id", record_id)
    if deleted:
        print(f"Registro con ID {record_id} eliminado correctamente.")
    else:
        print(f"No se encontró el registro con ID {record_id} o ya fue eliminado.")


def print_menu():
    print("\n===== MENÚ INTERACTIVO ISAM SPARSE =====")
    print("1. Insertar registro aleatorio")
    print("2. Insertar registros aleatorios en masa")
    print("3. Buscar registro por ID")
    print("4. Buscar registros por rango")
    print("5. Mostrar todos los registros")
    print("6. Reconstruir índice")
    print("7. Eliminar registro por ID")
    print("8. Insertar registro con ID especificado (resto aleatorio)")
    print("9. Salir")


def main():
    clear_screen()
    table = create_isam_table()

    while True:
        print_menu()
        option = input("Elija una opción (1-9): ")

        if option == "1":
            insert_random_record(table)
        elif option == "2":
            raw = input("Cantidad de registros a insertar: ")
            try:
                num_records = int(raw)
            except ValueError:
                print("Número inválido")
            else:
                insert_bulk_records(table, num_records)
        elif option == "3":
            search_record_by_id(table)
        elif option == "4":
            search_records_by_range(table)
        elif option == "5":
            show_all_records(table)
        elif option == "6":
            table.index.rebuild()
            print("Índice reconstruido exitosamente.")
        elif option == "7":
            delete_record_by_id(table)
        elif option == "8":
            insert_with_custom_id(table)
        elif option == "9":
            print("Saliendo del programa...")
            break
        else:
            print("Opción no válida. Intente nuevamente.")

        input("\nPresione Enter para continuar...")
        clear_screen()


if __name__ == "__main__":
    main()
