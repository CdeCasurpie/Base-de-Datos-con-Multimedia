from flask import Flask, render_template, request, jsonify
import socket
import json

app = Flask(__name__)

# Cliente para comunicarse con la base de datos HeiderDB
class HeiderDBClient:
    def __init__(self, host='localhost', port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(query.encode())
                response = s.recv(65536).decode()  # Aumenta el buffer
                print("[DEBUG] Respuesta cruda de la BD:")
                print(response)
                try:
                    return json.loads(response)
                except Exception as json_err:
                    print("[ERROR] Fallo al decodificar JSON:", json_err)
                    print("[ERROR] Respuesta cruda:", response)
                    return {"status": "error", "message": str(json_err), "raw": response}
        except Exception as e:
            print(f"Error conectando a HeiderDB: {e}")
            return {"status": "error", "message": str(e)}

# Instancia global del cliente de BD
heiderdb_client = HeiderDBClient()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    data = request.get_json()
    query_text = data.get('query', '')
    # Consulta principal
    sql_query = f"select * from documentos where contenido CONTAINS '{query_text}' LIMIT 10"
    db_response = heiderdb_client.send_query(sql_query)
    print("Consulta SQL:", sql_query)
    print("Respuesta de la BD:", db_response)

    # Prueba 1: SELECT simple
    select_simple = "SELECT * FROM documentos;"
    resp_simple = heiderdb_client.send_query(select_simple)
    print("SELECT simple:", select_simple)
    print("Respuesta:", resp_simple)

    # Prueba 2: CONTAINS
    contains_query = f"select * from documentos where contenido CONTAINS '{query_text}' LIMIT 10"
    resp_contains = heiderdb_client.send_query(contains_query)
    print("CONTAINS query:", contains_query)
    print("Respuesta:", resp_contains)

    # Prueba 3: RANKED BY palabra común
    ranked_common = "select * from documentos where contenido RANKED BY 'the' LIMIT 10"
    resp_ranked_common = heiderdb_client.send_query(ranked_common)
    print("RANKED BY común:", ranked_common)
    print("Respuesta:", resp_ranked_common)

    if db_response.get("status") != "ok":
        return jsonify({"error": db_response.get("message", "Error desconocido")}), 500
    results = db_response.get("result", [[]])[0]
    processed = [
        {
            "id": doc.get("id"),
            "titulo": doc.get("id"),
            "contenido": doc.get("contenido"),
            "imagen": "/static/images/scroll.png"
        }
        for doc in results
    ]
    return jsonify(processed)

@app.route('/documento/<doc_id>')
def documento(doc_id):
    print(f"[DEBUG] ID recibido: {doc_id}")
    # Consulta sin WHERE ni LIMIT por limitaciones del parser
    sql = "SELECT * FROM documentos;"
    resp = heiderdb_client.send_query(sql)
    print(f"[DEBUG] Resultado consulta: {resp}")
    doc = None
    if resp.get("status") == "ok":
        results = resp.get("result", [[]])[0]
        # Busca el documento por id en Python
        for row in results:
            if row.get("id") == doc_id:
                doc = row
                break
    if not doc:
        doc = {"id": doc_id, "titulo": doc_id, "contenido": "Documento no encontrado."}
    else:
        doc["titulo"] = doc["id"]
    return render_template('documento.html', doc=doc)

@app.route('/listar_ids')
def listar_ids():
    queries = [
        "SELECT * FROM documentos;",
        "select * from documentos;",
        "SELECT * FROM documentos",
        "select * from documentos"
    ]
    ids = []
    error_msg = None
    for sql in queries:
        resp = heiderdb_client.send_query(sql)
        if resp.get("status") == "ok":
            results = resp.get("result", [[]])[0]
            if results:
                ids = [row.get("id") for row in results if row and row.get("id")]
                break
            # Si el parser devuelve un mensaje de error, guárdalo
            if resp.get("result") and len(resp["result"]) > 1 and resp["result"][1]:
                error_msg = resp["result"][1]
        else:
            error_msg = resp.get("message")
    return render_template('listar_ids.html', ids=ids, error_msg=error_msg)

if __name__ == '__main__':
    app.run(debug=True) 