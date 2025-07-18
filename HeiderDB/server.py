import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import argparse
from HeiderDB.database.database import Database
import nltk


def convert_bytes_to_string(obj):
    """
    Convierte recursivamente objetos bytes a string para serialización JSON
    """
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore').rstrip('\x00')
    elif isinstance(obj, dict):
        return {key: convert_bytes_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_string(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_bytes_to_string(item) for item in obj)
    else:
        return obj


def json_serializer(obj):
    """
    Serializador JSON personalizado para manejar tipos no serializables
    """
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore').rstrip('\x00')
    # Para otros tipos no serializables, convertir a string
    return str(obj)


def run_server(host='0.0.0.0', port=54321):
    db = Database()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Servidor escuchando en {host}:{port}")
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096).decode(errors='ignore')
                if not data:
                    continue
                try:
                    # Detectar si es una solicitud get_len
                    if data.strip().startswith('get_len(') and data.strip().endswith(')'):
                        # Extraer el nombre de la tabla de get_len(table_name)
                        table_name = data.strip()[8:-1].strip().strip('"').strip("'")
                        count = db.get_record_count(table_name)
                        if count is not None:
                            result = (count, None)
                        else:
                            result = (None, f"Tabla '{table_name}' no encontrada")
                    else:
                        # Ejecutar consulta SQL normal
                        result = db.execute_query(data)
                    
                    # Convertir bytes a string antes de serializar
                    clean_result = convert_bytes_to_string(result)
                    response = json.dumps({"status": "ok", "result": clean_result}, default=json_serializer)
                except Exception as e:
                    response = json.dumps({"status": "error", "message": str(e)})
                conn.sendall(response.encode())

if __name__ == "__main__":
    nltk.download('punkt_tab')
    
    parser = argparse.ArgumentParser(description="Servidor HeiderDB")
    parser.add_argument("--host", default="0.0.0.0", help="Host para escuchar")
    parser.add_argument("--port", type=int, default=54321, help="Puerto para escuchar")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
