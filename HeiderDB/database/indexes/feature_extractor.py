from abc import ABC, abstractmethod
import numpy as np
import cv2
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.inception_v3 import InceptionV3, preprocess_input
import librosa
import os
class FeatureExtractor(ABC):
    """
    Clase base abstracta para extractores de características multimedia.
    Define la interfaz para extraer vectores de diferentes tipos de medios.
    """
    
    def __init__(self):
        pass
    
    @abstractmethod
    def extract(self, file_path):
        """
        Extrae vector de características del archivo multimedia
        
        Params:
            file_path: Ruta al archivo multimedia
            
        Returns:
            numpy.ndarray: Vector de características
        """
        pass
    
    @abstractmethod
    def get_vector_dimension(self):
        """
        Retorna la dimensión del vector de características
        
        Returns:
            int: Dimensión del vector
        """
        pass


class ImageExtractor(FeatureExtractor):
    """
    Extractor de características para imágenes.
    Implementa métodos SIFT o CNN para caracterización.
    """
    
    def __init__(self, method="sift"):
        super().__init__()
        if method not in ["sift", "cnn"]:
            raise ValueError("Método no soportado. Elija 'sift' o 'cnn'.")
        
        self.method = method
        self.cnn_model = None
        self.sift_detector = None

        if self.method == "sift":
            self.sift_detector = cv2.SIFT_create()
            self._dimension = 128
        
        elif self.method == "cnn":
            self.cnn_model = InceptionV3(
                include_top=False, 
                weights="imagenet",
                pooling= None 
            )
            self._dimension = 2048

        
    def extract(self, file_path):
        feature_vector = []
        if self.method == "sift":
            feature_vector = self._extract_sift(file_path)
        elif self.method == "cnn":
            feature_vector = self._extract_cnn(file_path)
        return feature_vector
        
    def get_vector_dimension(self):
        return self._dimension
        
    def _extract_sift(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        _, descriptor = self.sift_detector.detectAndCompute(img,None)
        return descriptor
        
    def _extract_cnn(self, image_path):
        img = image.load_img(image_path, target_size = (299,299))
        img_array = image.img_to_array(img)
        img_batch = np.expand_dims(img_array, axis=0)
        preprocessed_img = preprocess_input(img_batch)        
        features = self.cnn_model.predict(preprocessed_img, verbose=0)
        features = features[0]
        features = features.reshape(-1, 2048)
        return features


class AudioExtractor(FeatureExtractor):
    """
    Extractor de características para audio.
    Implementa métodos MFCC para caracterización con una dimensión fija de 20.
    """
    def __init__(self):
        super().__init__()
        self._dimension = 20

    def extract(self, file_path):
        return self._extract_mfcc(file_path)

    def get_vector_dimension(self):
        return self._dimension

    def _extract_mfcc(self, audio_path):
        try:
            y, sr = librosa.load(audio_path, sr=None)            
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self._dimension)
            return mfccs
        except Exception as e:
            print(f"Error procesando el archivo de audio {audio_path}: {e}")
            return np.array([])

# if __name__ == '__main__':
#     import sys # Necesario para sys.exit()

#     # --- 1. PREPARACIÓN: Definir nombres de archivo y verificar su existencia ---
    
#     # Nombres de archivo que el script esperará encontrar
#     image_path = "test_image.jpeg"
#     audio_path = "test_audio.mp3"

#     print("--- Verificando archivos de prueba ---")

#     # Verificar si el archivo de imagen existe
#     if not os.path.exists(image_path):
#         print(f"ERROR: No se encontró el archivo '{image_path}'.")
#         print("Por favor, coloca una imagen con ese nombre en la misma carpeta que el script y vuelve a ejecutarlo.")
#         sys.exit() # Detiene la ejecución del script

#     # Verificar si el archivo de audio existe
#     if not os.path.exists(audio_path):
#         print(f"ERROR: No se encontró el archivo '{audio_path}'.")
#         print("Por favor, coloca un archivo de audio con ese nombre en la misma carpeta y vuelve a ejecutarlo.")
#         sys.exit() # Detiene la ejecución del script

#     print(f"Archivos '{image_path}' y '{audio_path}' encontrados. Iniciando pruebas...\n")

#     # --- 2. PRUEBA: ImageExtractor con SIFT ---
#     print("--- Probando ImageExtractor (SIFT) ---")
#     sift_extractor = ImageExtractor(method="sift")
#     print(f"Dimensión de vector SIFT: {sift_extractor.get_vector_dimension()}")
#     sift_features = sift_extractor.extract(image_path)
#     print(f"Forma de descriptores SIFT: {sift_features.shape if sift_features is not None and sift_features.size > 0 else 'Ninguno'}\n")

#     # --- 3. PRUEBA: ImageExtractor con CNN ---
#     print("--- Probando ImageExtractor (CNN) ---")
#     cnn_extractor = ImageExtractor(method="cnn")
#     print(f"Dimensión de vector CNN: {cnn_extractor.get_vector_dimension()}")
#     cnn_features = cnn_extractor.extract(image_path)
#     print(f"Forma de vector CNN global: {cnn_features.shape}\n")


#     # --- 4. PRUEBA: AudioExtractor con MFCC ---
#     print("--- Probando AudioExtractor (MFCC) ---")
#     audio_extractor = AudioExtractor()
#     print(f"Dimensión de cada vector MFCC: {audio_extractor.get_vector_dimension()}")
    
#     mfcc_features = audio_extractor.extract(audio_path)
#     print(f"Forma de vectores locales MFCC: {mfcc_features.shape}")
    
#     # Opcional: Crear un vector global promediando los locales
#     if mfcc_features.size > 0:
#         global_mfcc = np.mean(mfcc_features, axis=1)
#         print(f"Forma del vector MFCC global (promediado): {global_mfcc.shape}\n")
#     else:
#         print("\n")

#     print("--- Pruebas completadas ---")