from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    data = request.get_json()
    query = data.get('query', '')
    resultados = [
        {"id": 1, "titulo": "Política y Tecnología 1", "contenido": "Contenido 1...", "imagen": "/static/images/scroll.png"},
        {"id": 2, "titulo": "Política y Tecnología 2", "contenido": "Contenido 2...", "imagen": "/static/images/scroll.png"},
        {"id": 3, "titulo": "Política y Tecnología 3", "contenido": "Contenido 3...", "imagen": "/static/images/scroll.png"},
        {"id": 4, "titulo": "Política y Tecnología 4", "contenido": "Contenido 4...", "imagen": "/static/images/scroll.png"},
        {"id": 5, "titulo": "Política y Tecnología 5", "contenido": "Contenido 5...", "imagen": "/static/images/scroll.png"},
        {"id": 6, "titulo": "Política y Tecnología 6", "contenido": "Contenido 6...", "imagen": "/static/images/scroll.png"},
    ]
    return jsonify(resultados)

@app.route('/documento/<int:doc_id>')
def documento(doc_id):
    doc = {"id": doc_id, "titulo": f"Documento {doc_id}", "contenido": f"Este es el contenido completo del documento {doc_id}."}
    return render_template('documento.html', doc=doc)

if __name__ == '__main__':
    app.run(debug=True) 