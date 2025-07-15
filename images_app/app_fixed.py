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

UPLOAD_FOLDER = "./temp_uploads"
STATIC_FOLDER = "./static/images"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tiff", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["STATIC_FOLDER"] = STATIC_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


class HeiderDBClient:
    def __init__(self, host="localhost", port=54321):
        self.host = host
        self.port = port

    def send_query(self, query):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
                s.sendall(query.encode())

                response = b""
                while True:
                    data = s.recv(1024)
                    if not data:
                        break
                    response += data
                    if b"\n" in data or len(response) > 8192:
                        break

                response_str = response.decode("utf-8").strip()
                print(f"Raw response: {response_str[:200]}...")

                if not response_str:
                    return {"status": "error", "message": "Empty response from server"}

                return json.loads(response_str)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(
                f"Response was: {response_str if 'response_str' in locals() else 'No response'}"
            )
            return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            print(f"Error conectando a HeiderDB: {e}")
            return {"status": "error", "message": str(e)}


db_client = HeiderDBClient()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_filename(filename):
    name, ext = os.path.splitext(filename)
    clean_name = "".join(
        c for c in name if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    return f"{clean_name}{ext}"


def copy_image_to_static(original_path, image_data):
    try:
        if not os.path.exists(original_path):
            print(f"Archivo no encontrado: {original_path}")
            return None

        print(f"Copiando archivo {original_path} a static...")
        unique_id = str(uuid.uuid4())[:8]
        original_filename = os.path.basename(original_path)
        clean_name = clean_filename(original_filename)

        new_filename = f"{unique_id}_{clean_name}"
        static_path = os.path.join(STATIC_FOLDER, new_filename)

        shutil.copy2(original_path, static_path)
        print(f"Archivo copiado a: {static_path}")

        web_path = f"/static/images/{new_filename}"
        return web_path

    except Exception as e:
        print(f"Error copiando archivo {original_path}: {e}")
        return None


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Flask image similarity server running"})


@app.route("/api/test-db", methods=["GET"])
def test_database():
    try:
        response = db_client.send_query("SELECT * FROM imagenes LIMIT 3;")
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/analyze-similarity", methods=["POST"])
def analyze_similarity():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No se encontró archivo de imagen"}), 400

        file = request.files["image"]

        if file.filename == "":
            return jsonify({"error": "No se seleccionó archivo"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de archivo no permitido"}), 400

        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        temp_filename = f"{unique_id}_{filename}"
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)

        file.save(temp_path)

        absolute_temp_path = os.path.abspath(temp_path)

        print(f"Archivo guardado en: {absolute_temp_path}")

        # Usamos la tabla 'imagenes' y la columna 'archivo' en lugar de 'imagen'
        similarity_query = f'SELECT * FROM imagenes WHERE archivo SIMILAR TO "{absolute_temp_path}" LIMIT 12;'

        print(f"Ejecutando query: {similarity_query}")

        db_response = db_client.send_query(similarity_query)

        if db_response.get("status") != "ok":
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return (
                jsonify(
                    {
                        "error": f"Error en base de datos: {db_response.get('message', 'Desconocido')}"
                    }
                ),
                500,
            )

        results = db_response.get("result", [[]])[0]

        if not results:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify(
                {
                    "status": "ok",
                    "results": [],
                    "message": "No se encontraron imágenes similares",
                }
            )

        processed_results = []

        for image_data in results:
            try:
                # Usamos 'archivo' en lugar de 'imagen'
                original_path = image_data.get("archivo", "")
                if isinstance(original_path, bytes):
                    original_path = original_path.decode("utf-8").rstrip("\x00")

                image_name = image_data.get("nombre", "Imagen Desconocida")
                similarity_score = float(image_data.get("_similarity_score", 0.0)) * 100

                web_path = copy_image_to_static(original_path, image_data)

                if web_path:
                    processed_result = {
                        "id": image_data.get("id"),
                        "name": image_name,
                        "similarity": round(similarity_score, 1),
                        "imagePath": web_path,
                        "originalPath": original_path,
                    }
                    processed_results.append(processed_result)

            except Exception as e:
                print(f"Error procesando resultado {image_data}: {e}")
                continue

        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify(
            {
                "status": "ok",
                "results": processed_results,
                "message": f"Se encontraron {len(processed_results)} imágenes similares",
            }
        )

    except Exception as e:
        print(f"Error en analyze_similarity: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/static/images/<filename>")
def serve_image(filename):
    try:
        return send_from_directory(app.config["STATIC_FOLDER"], filename)
    except Exception as e:
        return jsonify({"error": "Archivo no encontrado"}), 404


@app.route("/<path:filename>")
def serve_static_files(filename):
    try:
        return send_from_directory("./static", filename)
    except:
        return jsonify({"error": "Archivo no encontrado"}), 404


@app.route("/")
def serve_index():
    return send_from_directory("./static/html", "index.html")


@app.route("/api/list-images", methods=["GET"])
def list_all_images():
    try:
        response = db_client.send_query("SELECT * FROM imagenes;")
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Archivo demasiado grande"}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    print("=== Servidor Flask de Similitud de Imágenes ===")
    print(f"Carpeta de uploads temporales: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Carpeta static de imágenes: {os.path.abspath(STATIC_FOLDER)}")
    print("Endpoints disponibles:")
    print("  POST /api/analyze-similarity - Analizar similitud de imagen")
    print("  GET  /api/health - Estado del servidor")
    print("  GET  /api/test-db - Probar conexión BD")
    print("  GET  /api/list-images - Listar todas las imágenes")
    print("  GET  /static/images/<filename> - Servir archivos de imagen")
    print()

    try:
        test_response = db_client.send_query("SELECT COUNT(*) as count FROM imagenes;")
        if test_response.get("status") == "ok":
            count = test_response.get("result", [[{}]])[0][0].get("count", 0)
            print(f"Conexión con HeiderDB establecida. Imágenes en BD: {count}")
        else:
            print("Error conectando con HeiderDB:", test_response.get("message"))
    except Exception as e:
        print("No se pudo conectar con HeiderDB:", e)
        print("   Asegúrate de que el servidor de BD esté ejecutándose")

    print()
    print("Iniciando servidor Flask...")
    app.run(debug=True, host="0.0.0.0", port=5001)
