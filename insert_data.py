#!/usr/bin/env python3
"""
Script para insertar datos multimedia automáticamente.
Crea tablas de imágenes y audios e inserta todos los archivos de las carpetas correspondientes.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HeiderDB.client import HeiderClient


def get_files_from_directory(directory, extensions):
    """
    Obtiene todos los archivos con las extensiones especificadas de un directorio.
    
    Args:
        directory (str): Ruta del directorio
        extensions (list): Lista de extensiones permitidas (ej: ['.jpg', '.png'])
    
    Returns:
        list: Lista de rutas de archivos
    """
    files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file)
                if ext.lower() in extensions:
                    files.append(file_path)
    return files


def get_filename_without_extension(file_path):
    """
    Obtiene el nombre del archivo sin la extensión.
    
    Args:
        file_path (str): Ruta completa del archivo
    
    Returns:
        str: Nombre del archivo sin extensión
    """
    return Path(file_path).stem


def create_and_populate_tables():
    """
    Función principal que crea las tablas e inserta los datos multimedia.
    """
    # Conectar al cliente HeiderDB
    client = HeiderClient()
    
    # Directorios de archivos multimedia
    images_dir = "./HeiderDB/test_images"
    audios_dir = "./HeiderDB/test_audios"
    
    # Extensiones permitidas
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
    audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    
    print("🎵 Script de inserción de datos multimedia")
    print("=" * 50)
    
    # ================================
    # TABLA DE IMÁGENES
    # ================================
    print("\n📸 Procesando tabla de imágenes...")
    
    # Crear tabla de imágenes (si no existe)
    create_images_query = """
    CREATE TABLE imagenes (
        id INT KEY,
        nombre VARCHAR(100),
        archivo IMAGE
    ) using index bplus_tree(id);
    """

    create_index = """
    CREATE MULTIMEDIA INDEX idx_image ON imagenes (archivo) WITH TYPE image METHOD sift;
    """
    
    try:
        response = client.send_query(create_images_query)
        response2 = client.send_query(create_index)
        if response['status'] == 'ok':
            print("✅ Tabla 'imagenes' creada exitosamente")
        else:
            print(f"⚠️  Tabla 'imagenes': {response.get('message', 'Ya existe o error')}")
    except Exception as e:
        print(f"❌ Error creando tabla 'imagenes': {e}")
    
    # Obtener archivos de imágenes
    image_files = get_files_from_directory(images_dir, image_extensions)
    print(f"📁 Encontradas {len(image_files)} imágenes en {images_dir}")
    
    # Insertar imágenes
    for i, image_path in enumerate(image_files, 1):
        nombre = get_filename_without_extension(image_path)
        # Convertir ruta relativa a absoluta
        absolute_path = os.path.abspath(image_path)
        
        insert_query = f"INSERT INTO imagenes VALUES ({i}, '{nombre}', '{absolute_path}');"
        
        try:
            response = client.send_query(insert_query)
            if response['status'] == 'ok':
                print(f"  ✅ [{i:2d}] {nombre} -> {os.path.basename(image_path)}")
            else:
                print(f"  ❌ [{i:2d}] Error insertando {nombre}: {response.get('message', 'Error desconocido')}")
        except Exception as e:
            print(f"  ❌ [{i:2d}] Excepción insertando {nombre}: {e}")
    
    # ================================
    # TABLA DE AUDIOS
    # ================================
    print(f"\n🎵 Procesando tabla de audios...")
    
    # Crear tabla de audios (si no existe)
    create_audios_query = """
    CREATE TABLE audios (
        id INT KEY,
        nombre VARCHAR(100),
        archivo AUDIO
    ) using index bplus_tree(id);
    """

    create_index = """
    CREATE MULTIMEDIA INDEX idx_audio ON audios (archivo) WITH TYPE audio METHOD mfcc;
    """
    
    try:
        response = client.send_query(create_audios_query)
        response2 = client.send_query(create_index)
        if response['status'] == 'ok':
            print("✅ Tabla 'audios' creada exitosamente")
        else:
            print(f"⚠️  Tabla 'audios': {response.get('message', 'Ya existe o error')}")
    except Exception as e:
        print(f"❌ Error creando tabla 'audios': {e}")
    
    # Obtener archivos de audio
    audio_files = get_files_from_directory(audios_dir, audio_extensions)
    print(f"📁 Encontrados {len(audio_files)} audios en {audios_dir}")
    
    # Insertar audios
    for i, audio_path in enumerate(audio_files, 1):
        nombre = get_filename_without_extension(audio_path)
        # Convertir ruta relativa a absoluta
        absolute_path = os.path.abspath(audio_path)
        
        insert_query = f"INSERT INTO audios VALUES ({i}, '{nombre}', '{absolute_path}');"
        
        try:
            response = client.send_query(insert_query)
            if response['status'] == 'ok':
                print(f"  ✅ [{i:2d}] {nombre} -> {os.path.basename(audio_path)}")
            else:
                print(f"  ❌ [{i:2d}] Error insertando {nombre}: {response.get('message', 'Error desconocido')}")
        except Exception as e:
            print(f"  ❌ [{i:2d}] Excepción insertando {nombre}: {e}")
    
    # ================================
    # VERIFICACIÓN FINAL
    # ================================
    print(f"\n🔍 Verificación final...")
    
    # Verificar tabla de imágenes
    try:
        response = client.send_query("SELECT COUNT(*) FROM imagenes;")
        if response['status'] == 'ok':
            print(f"📸 Tabla 'imagenes': registros insertados exitosamente")
        else:
            print(f"❌ Error verificando tabla 'imagenes': {response.get('message')}")
    except Exception as e:
        print(f"❌ Excepción verificando tabla 'imagenes': {e}")
    
    # Verificar tabla de audios
    try:
        response = client.send_query("SELECT COUNT(*) FROM audios;")
        if response['status'] == 'ok':
            print(f"🎵 Tabla 'audios': registros insertados exitosamente")
        else:
            print(f"❌ Error verificando tabla 'audios': {response.get('message')}")
    except Exception as e:
        print(f"❌ Excepción verificando tabla 'audios': {e}")
    
    print(f"\n🎉 ¡Proceso completado!")
    print("=" * 50)
    print("💡 Puedes verificar las tablas con:")
    print("   python HeiderDB/client.py --query \"SELECT * FROM imagenes;\"")
    print("   python HeiderDB/client.py --query \"SELECT * FROM audios;\"")


if __name__ == "__main__":
    try:
        create_and_populate_tables()
    except KeyboardInterrupt:
        print("\n⏹️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)