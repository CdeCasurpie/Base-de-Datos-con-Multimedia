import socket
import json
import argparse

class HeiderClient:
    def __init__(self, host='localhost', port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(query.encode())
            response = s.recv(4096).decode()
            return json.loads(response)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente HeiderDB")
    parser.add_argument("--host", default="localhost", help="Host del servidor")
    parser.add_argument("--port", type=int, default=54321, help="Puerto del servidor")
    parser.add_argument("--query", type=str, help="Consulta SQL a enviar al servidor")

    args = parser.parse_args()

    if not args.query:
        print("Por favor, proporciona una consulta SQL con --query")
        exit(1)

    client = HeiderClient(host=args.host, port=args.port)

    res = client.send_query(args.query)
    print("Respuesta del servidor:", res)
