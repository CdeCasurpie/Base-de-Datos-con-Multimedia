#!/usr/bin/env python3

import os
import sys
import shutil
import uuid
import json
import socket
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuración
UPLOAD_FOLDER = './temp_uploads'
STATIC_FOLDER = './static/songs'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac'}

# Crear directorios si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

class HeiderDBClient:
    """Cliente para comunicarse con la base de datos HeiderDB"""
    
    def __init__(self, host='localhost', port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        """Envía una query a la base de datos y retorna la respuesta"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(query.encode())
                response = s.recv(8192).decode()  # Aumentamos el buffer para más datos
                return json.loads(response)
        except Exception as e:
            print(f"Error conectando a HeiderDB: {e}")
            return {"status": "error", "message": str(e)}

# Instancia global del cliente de BD
db_client = HeiderDBClient()

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_filename(filename):
    """Limpia el nombre del archivo para evitar caracteres problemáticos"""
    name, ext = os.path.splitext(filename)
    # Remover caracteres especiales y espacios
    clean_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    return f"{clean_name}{ext}"

def copy_song_to_static(original_path, song_data):
    """
    Copia una canción de su ubicación original a la carpeta static
    y retorna la ruta relativa para acceso web
    """
    try:
        if not os.path.exists(original_path):
            print(f"Archivo no encontrado: {original_path}")
            return None
            
        print(f"Copiando archivo {original_path} a static...")
        # Generar nombre único para evitar conflictos
        unique_id = str(uuid.uuid4())[:8]
        original_filename = os.path.basename(original_path)
        clean_name = clean_filename(original_filename)
        
        # Crear nombre único: id_nombre.mp3
        new_filename = f"{unique_id}_{clean_name}"
        static_path = os.path.join(STATIC_FOLDER, new_filename)
        
        # Copiar archivo
        shutil.copy2(original_path, static_path)

        # archivo
        print(f"Archivo copiado a: {static_path}")
        
        # Retornar ruta relativa para acceso web
        web_path = f"/static/songs/{new_filename}"
        return web_path
        
    except Exception as e:
        print(f"Error copiando archivo {original_path}: {e}")
        return None


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({"status": "ok", "message": "Flask audio similarity server running"})

@app.route('/api/test-db', methods=['GET'])
def test_database():
    """Endpoint para probar la conexión con la base de datos"""
    try:
        response = db_client.send_query("SELECT * FROM audios LIMIT 3;")
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/analyze-similarity', methods=['POST'])
def analyze_similarity():
    """
    Endpoint principal para analizar similitud de audio
    """
    try:
        # Verificar que se envió un archivo
        if 'audio' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        file = request.files['audio']
        
        if file.filename == '':
            return jsonify({"error": "No se seleccionó archivo"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de archivo no permitido"}), 400
        
        # Guardar archivo temporal
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        temp_filename = f"{unique_id}_{filename}"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        
        file.save(temp_path)
        
        # Obtener ruta absoluta para la query
        absolute_temp_path = os.path.abspath(temp_path)
        
        print(f"Archivo guardado en: {absolute_temp_path}")
        
        # Construir query de similitud
        similarity_query = f'SELECT * FROM audios WHERE archivo SIMILAR TO "{absolute_temp_path}" LIMIT 12;'
        
        print(f"Ejecutando query: {similarity_query}")
        
        # Ejecutar query en la base de datos
        db_response = db_client.send_query(similarity_query)
        
        if db_response.get("status") != "ok":
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"error": f"Error en base de datos: {db_response.get('message', 'Desconocido')}"}), 500
        
        # Procesar resultados
        results = db_response.get("result", [[]])[0]  # Primer elemento de la respuesta
        
        if not results:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "status": "ok", 
                "results": [],
                "message": "No se encontraron canciones similares"
            })
        
        # Procesar cada resultado y copiar archivos a static
        processed_results = []
        
        for song_data in results:
            try:
                original_path = song_data.get('archivo', '')
                song_name = song_data.get('nombre', 'Canción Desconocida')
                similarity_score = float(song_data.get('_similarity_score', 0.0)) * 100  # Convertir a porcentaje
                
                # Copiar archivo a carpeta static
                web_path = copy_song_to_static(original_path, song_data)
                
                if web_path:
                    processed_result = {
                        "id": song_data.get('id'),
                        "title": song_name,
                        "artist": "Artista Desconocido",  # Podrías agregar una columna 'artista' a tu BD
                        "similarity": round(similarity_score, 1),
                        "audioPath": web_path,
                        "originalPath": original_path  # Para debug, remover en producción
                    }
                    processed_results.append(processed_result)
                    
            except Exception as e:
                print(f"Error procesando resultado {song_data}: {e}")
                continue
        
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        print(f"Retornando {len(processed_results)} resultados procesados")
        
        return jsonify({
            "status": "ok",
            "results": processed_results,
            "total": len(processed_results),
            "message": f"Encontradas {len(processed_results)} canciones similares"
        })
        
    except Exception as e:
        print(f"Error en analyze_similarity: {e}")
        # Limpiar archivo temporal en caso de error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route('/static/songs/<filename>')
def serve_song(filename):
    """Servir archivos de audio desde la carpeta static"""
    try:
        return send_from_directory(app.config['STATIC_FOLDER'], filename)
    except Exception as e:
        print(f"Error sirviendo archivo {filename}: {e}")
        return jsonify({"error": "Archivo no encontrado"}), 404

@app.route('/<path:filename>')
def serve_static_files(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except:
        # Si el archivo no existe, devolver 404 o redirigir al index
        return send_from_directory(app.static_folder, 'index.html')



@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/list-songs', methods=['GET'])
def list_all_songs():
    """Endpoint para listar todas las canciones en la base de datos (para debug)"""
    try:
        response = db_client.send_query("SELECT * FROM audios;")
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Archivo demasiado grande. Máximo 50MB"}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    print("=== Servidor Flask de Similitud de Audio ===")
    print(f"Carpeta de uploads temporales: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Carpeta static de canciones: {os.path.abspath(STATIC_FOLDER)}")
    print("Endpoints disponibles:")
    print("  POST /api/analyze-similarity - Analizar similitud de audio")
    print("  GET  /api/health - Estado del servidor")
    print("  GET  /api/test-db - Probar conexión BD")
    print("  GET  /api/list-songs - Listar todas las canciones")
    print("  GET  /static/songs/<filename> - Servir archivos de audio")
    print()
    
    # Verificar conexión con la base de datos al inicio
    try:
        test_response = db_client.send_query("SELECT COUNT(*) as count FROM audios;")
        if test_response.get("status") == "ok":
            print("✅ Conexión con HeiderDB establecida correctamente")
        else:
            print("❌ Error conectando con HeiderDB:", test_response.get("message"))
    except Exception as e:
        print("❌ No se pudo conectar con HeiderDB:", e)
        print("   Asegúrate de que el servidor de BD esté ejecutándose")
    
    print()
    print("Iniciando servidor Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)