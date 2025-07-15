from abc import ABC, abstractmethod
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
        self.media_type = "image"  # Agregar atributo media_type
        self.cnn_model = None
        self.sift_detector = None

        if self.method == "sift":
            try:
                import cv2

                self.sift_detector = cv2.SIFT_create()
            except ImportError:
                print("Warning: OpenCV not available, using dummy SIFT")
                self.sift_detector = None
            self._dimension = 512  # 128 * 4 estadísticas

        elif self.method == "cnn":
            try:
                from tensorflow.keras.applications.inception_v3 import InceptionV3

                self.cnn_model = InceptionV3(
                    include_top=False, weights="imagenet", pooling=None
                )
            except ImportError:
                print("Warning: TensorFlow not available, using dummy CNN")
                self.cnn_model = None
            self._dimension = 2048

    def extract(self, file_path):
        if self.method == "sift":
            return self._extract_sift(file_path)
        elif self.method == "cnn":
            return self._extract_cnn(file_path)
        else:
            import numpy as np

            return np.array([0.0] * self._dimension, dtype=np.float32)

    def get_vector_dimension(self):
        return self._dimension

    def _extract_sift(self, image_path):
        """
        Extrae características SIFT y las agrega en un vector único de dimensión fija.
        """
        if self.sift_detector is None:
            import numpy as np

            return np.array([0.1] * 512, dtype=np.float32)

        try:
            import cv2
            import numpy as np

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"⚠ No se pudo cargar la imagen: {image_path}")
                return np.array([0.0] * 512, dtype=np.float32)

            _, descriptors = self.sift_detector.detectAndCompute(img, None)

            if descriptors is None or len(descriptors) == 0:
                print(f"⚠ No se encontraron características SIFT en {image_path}")
                return np.array([0.0] * 512, dtype=np.float32)

            # Calcular estadísticas agregadas de todos los descriptores
            features_aggregated = np.concatenate(
                [
                    np.mean(descriptors, axis=0),  # 128 dimensiones - promedio
                    np.std(
                        descriptors, axis=0
                    ),  # 128 dimensiones - desviación estándar
                    np.min(descriptors, axis=0),  # 128 dimensiones - mínimo
                    np.max(descriptors, axis=0),  # 128 dimensiones - máximo
                ]
            )

            # Resultado: vector de 512 dimensiones (128 * 4 estadísticas)
            return features_aggregated.astype(np.float32)

        except Exception as e:
            print(f"Error extrayendo SIFT de {image_path}: {e}")
            import numpy as np

            return np.array([0.0] * 512, dtype=np.float32)

    def _extract_cnn(self, image_path):
        if self.cnn_model is None:
            import numpy as np

            return np.array([0.1] * 2048, dtype=np.float32)

        try:
            import numpy as np
            from tensorflow.keras.preprocessing import image
            from tensorflow.keras.applications.inception_v3 import preprocess_input

            img = image.load_img(image_path, target_size=(299, 299))
            img_array = image.img_to_array(img)
            img_batch = np.expand_dims(img_array, axis=0)
            preprocessed_img = preprocess_input(img_batch)
            features = self.cnn_model.predict(preprocessed_img, verbose=0)
            features = features[0].flatten()  # Aplanar a vector 1D
            return features.astype(np.float32)
        except Exception as e:
            print(f"Error in CNN extraction: {e}")
            import numpy as np

            return np.array([0.1] * 2048, dtype=np.float32)


class AudioExtractor(FeatureExtractor):
    """
    Extractor de características para audio.
    Implementa métodos MFCC para caracterización con una dimensión fija de 20.
    """

    def __init__(self, method="mfcc"):
        super().__init__()
        self._dimension = 20
        self.media_type = "audio"  # Agregar atributo media_type
        self.method = method  # Agregar atributo method

    def extract(self, file_path):
        return self._extract_mfcc(file_path)

    def get_vector_dimension(self):
        return self._dimension

    def _extract_mfcc(self, audio_path):
        try:
            import librosa
            import numpy as np

            y, sr = librosa.load(audio_path, sr=None)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self._dimension)

            # Calcular promedio a lo largo del tiempo para obtener vector fijo
            if mfccs.size > 0:
                mfcc_mean = np.mean(mfccs, axis=1)  # Promedio temporal
                return mfcc_mean.astype(np.float32)
            else:
                return np.array([0.0] * self._dimension, dtype=np.float32)

        except ImportError:
            print("Warning: librosa not available, using dummy MFCC")
            import numpy as np

            return np.array([0.1] * self._dimension, dtype=np.float32)  # Vector fijo

        except Exception as e:
            print(f"Error procesando el archivo de audio {audio_path}: {e}")
            import numpy as np

            return np.array([0.0] * self._dimension, dtype=np.float32)


def create_feature_extractor(media_type, method="sift"):
    """
    Factory function to create the appropriate feature extractor.

    Args:
        media_type (str): Type of media ("image" or "audio")
        method (str): Method for extraction ("sift"/"cnn" for images, "mfcc" for audio)

    Returns:
        FeatureExtractor: Appropriate feature extractor instance
    """
    if media_type == "image":
        return ImageExtractor(method=method)
    elif media_type == "audio":
        # Para audio, usar method si se especifica, sino usar "mfcc" por defecto
        audio_method = method if method in ["mfcc"] else "mfcc"
        return AudioExtractor(method=audio_method)
    else:
        raise ValueError(f"Unsupported media type: {media_type}")


if __name__ == "__main__":
    import sys

    image_path = "test_image.jpeg"
    audio_path = "test_audio.mp3"

    print("--- Verificando archivos de prueba ---")

    if not os.path.exists(image_path):
        print(f"ERROR: No se encontró el archivo '{image_path}'.")
        print(
            "Por favor, coloca una imagen con ese nombre en la misma carpeta que el script y vuelve a ejecutarlo."
        )
        sys.exit()

    if not os.path.exists(audio_path):
        print(f"ERROR: No se encontró el archivo '{audio_path}'.")
        print(
            "Por favor, coloca un archivo de audio con ese nombre en la misma carpeta y vuelve a ejecutarlo."
        )
        sys.exit()

    print(
        f"Archivos '{image_path}' y '{audio_path}' encontrados. Iniciando pruebas...\n"
    )

    print("--- Probando ImageExtractor (SIFT) ---")
    sift_extractor = create_feature_extractor("image", "sift")
    print(f"Dimensión de vector SIFT: {sift_extractor.get_vector_dimension()}")
    sift_features = sift_extractor.extract(image_path)
    print(
        f"Forma de descriptores SIFT: {sift_features.shape if hasattr(sift_features, 'shape') and sift_features is not None else 'Ninguno'}\n"
    )

    print("--- Probando ImageExtractor (CNN) ---")
    cnn_extractor = create_feature_extractor("image", "cnn")
    print(f"Dimensión de vector CNN: {cnn_extractor.get_vector_dimension()}")
    cnn_features = cnn_extractor.extract(image_path)
    print(
        f"Forma de vector CNN global: {cnn_features.shape if hasattr(cnn_features, 'shape') else len(cnn_features)}\n"
    )

    print("--- Probando AudioExtractor (MFCC) ---")
    audio_extractor = create_feature_extractor("audio")
    print(f"Dimensión de cada vector MFCC: {audio_extractor.get_vector_dimension()}")

    mfcc_features = audio_extractor.extract(audio_path)
    print(
        f"Forma de vectores locales MFCC: {mfcc_features.shape if hasattr(mfcc_features, 'shape') else len(mfcc_features)}"
    )

    if hasattr(mfcc_features, "size") and mfcc_features.size > 0:
        try:
            import numpy as np

            global_mfcc = np.mean(mfcc_features, axis=1)
            print(f"Forma del vector MFCC global (promediado): {global_mfcc.shape}\n")
        except:
            print("No se pudo calcular el vector global\n")
    else:
        print("\n")

    print("--- Pruebas completadas ---")
