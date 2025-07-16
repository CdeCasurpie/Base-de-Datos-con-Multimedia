import socket
import json
import pandas as pd

class HeiderDBClient:
    def __init__(self, host='localhost', port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(query.encode())
                response = s.recv(8192).decode()
                return json.loads(response)
        except Exception as e:
            print(f"Error conectando a HeiderDB: {e}")
            return {"status": "error", "message": str(e)}

db = HeiderDBClient()

# 1. Borra la tabla si existe
print("Borrando tabla si existe...")
print(db.send_query("DROP TABLE documentos;"))

# 2. Crea la tabla
print("Creando tabla...")
print(db.send_query("""
CREATE TABLE documentos (
    id VARCHAR(100) KEY,
    contenido VARCHAR(20000)
);
"""))

# 3. Crea el índice invertido
print("Creando índice invertido...")
print(db.send_query("CREATE INVERTED INDEX idx_contenido ON documentos(contenido);"))

# 4. Carga el CSV generado
print("Cargando documentos_test.csv...")
df = pd.read_csv("documentos_test.csv")

for idx, row in df.iterrows():
    id_ = str(row['id']).replace("'", "''")
    contenido = str(row['article']).replace("'", "''")
    insert = f"INSERT INTO documentos VALUES ('{id_}', '{contenido}');"
    print(f"Insertando {id_}...")
    print(db.send_query(insert))

print("Carga completada.")