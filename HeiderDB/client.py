import socket
import json
import argparse

class HeiderClient:
    def __init__(self, host='127.0.0.1', port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(query.encode())
            response = s.recv(4096).decode()
            return json.loads(response)