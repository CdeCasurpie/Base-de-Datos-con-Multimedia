import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import argparse
from HeiderDB.database.database import Database
import nltk


def run_server(host='0.0.0.0', port=54321):
    db = Database()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Servidor escuchando en {host}:{port}")
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096).decode()
                if not data:
                    continue
                try:
                    result = db.execute_query(data)
                    response = json.dumps({"status": "ok", "result": result})
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
