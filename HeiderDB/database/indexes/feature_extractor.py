from abc import ABC, abstractmethod
import os


class FeatureExtractor(ABC):
    """
    Clase base abstracta para extractores de características multimedia.
    Define la interfaz para extraer vectores locales de diferentes tipos de medios.
    """

    def __init__(self):
        pass

    @abstractmethod
    def extract(self, file_path):
        """
        Extrae lista de vectores de características locales del archivo multimedia

        Params:
            file_path: Ruta al archivo multimedia

        Returns:
            list[numpy.ndarray]: Lista de vectores de características locales
        """
        pass

    @abstractmethod
    def get_vector_dimension(self):
        """
        Retorna la dimensión de cada vector de características local

        Returns:
            int: Dimensión de cada vector local
        """
        pass


class ImageExtractor(FeatureExtractor):
    """
    Extractor de características para imágenes.
    Implementa métodos SIFT o CNN para extraer vectores locales.
    """

    def __init__(self, method="sift"):
        super().__init__()
        if method not in ["sift", "cnn"]:
            raise ValueError("Método no soportado. Elija 'sift' o 'cnn'.")

        self.method = method
        self.media_type = "image"
        self.cnn_model = None
        self.sift_detector = None

        if self.method == "sift":
            try:
                import cv2

                self.sift_detector = cv2.SIFT_create()
            except ImportError:
                print("Warning: OpenCV not available, using dummy SIFT")
                self.sift_detector = None
            self._dimension = 128  # Dimensión original de SIFT

        elif self.method == "cnn":
            try:
                from tensorflow.keras.applications.inception_v3 import InceptionV3

                # Usar modelo sin pooling global para extraer mapas de características
                self.cnn_model = InceptionV3(
                    include_top=False, weights="imagenet", pooling=None
                )
            except ImportError:
                print("Warning: TensorFlow not available, using dummy CNN")
                self.cnn_model = None
            self._dimension = 128  # Dimensión reducida para vectores locales CNN

    def extract(self, file_path):
        if self.method == "sift":
            return self._extract_sift_local(file_path)
        elif self.method == "cnn":
            return self._extract_cnn_local(file_path)
        else:
            import numpy as np
            # Retornar lista de vectores dummy
            return [np.array([0.0] * self._dimension, dtype=np.float32) for _ in range(10)]

    def get_vector_dimension(self):
        return self._dimension

    def _extract_sift_local(self, image_path):
        """
        Extrae características SIFT locales como lista de descriptores.
        """
        if self.sift_detector is None:
            import numpy as np
            # Retornar vectores dummy
            return [np.array([0.1] * 128, dtype=np.float32) for _ in range(10)]

        try:
            import cv2
            import numpy as np

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"⚠ No se pudo cargar la imagen: {image_path}")
                return [np.array([0.0] * 128, dtype=np.float32)]

            _, descriptors = self.sift_detector.detectAndCompute(img, None)

            if descriptors is None or len(descriptors) == 0:
                print(f"⚠ No se encontraron características SIFT en {image_path}")
                return [np.array([0.0] * 128, dtype=np.float32)]

            # Retornar lista de descriptores locales (cada uno de 128 dimensiones)
            return [desc.astype(np.float32) for desc in descriptors]

        except Exception as e:
            print(f"Error extrayendo SIFT de {image_path}: {e}")
            import numpy as np
            return [np.array([0.0] * 128, dtype=np.float32)]

    def _extract_cnn_local(self, image_path):
        """
        Extrae características CNN locales dividiendo la imagen en patches.
        """
        if self.cnn_model is None:
            import numpy as np
            return [np.array([0.1] * 128, dtype=np.float32) for _ in range(16)]

        try:
            import numpy as np
            from tensorflow.keras.preprocessing import image
            from tensorflow.keras.applications.inception_v3 import preprocess_input
            from sklearn.decomposition import PCA

            # Cargar y preparar imagen
            img = image.load_img(image_path, target_size=(299, 299))
            img_array = image.img_to_array(img)
            img_batch = np.expand_dims(img_array, axis=0)
            preprocessed_img = preprocess_input(img_batch)
            
            # Extraer mapa de características
            feature_map = self.cnn_model.predict(preprocessed_img, verbose=0)
            # feature_map shape: (1, H, W, 2048) donde H,W dependen de la arquitectura
            
            # Aplanar el mapa espacial para obtener vectores locales
            feature_map = feature_map[0]  # Remover batch dimension
            h, w, channels = feature_map.shape
            
            # Reshape para obtener vectores locales
            local_vectors = feature_map.reshape(h * w, channels)
            
            # Reducir dimensionalidad a 128 usando PCA si es necesario
            if channels > 128:
                try:
                    pca = PCA(n_components=128)
                    local_vectors = pca.fit_transform(local_vectors)
                except:
                    # Si PCA falla, tomar las primeras 128 dimensiones
                    local_vectors = local_vectors[:, :128]
            
            # Retornar lista de vectores locales
            return [vec.astype(np.float32) for vec in local_vectors]
            
        except Exception as e:
            print(f"Error in CNN local extraction: {e}")
            import numpy as np
            return [np.array([0.1] * 128, dtype=np.float32) for _ in range(16)]


class AudioExtractor(FeatureExtractor):
    """
    Extractor de características para audio.
    Implementa métodos MFCC para extraer vectores locales por ventanas temporales.
    """

    def __init__(self, method="mfcc"):
        super().__init__()
        self._dimension = 128  # Dimensión de cada vector MFCC local
        self.media_type = "audio"
        self.method = method

    def extract(self, file_path):
        if self.method == "mfcc":
            return self._extract_mfcc_local(file_path)
        else:
            return self._extract_spectral_local(file_path)

    def get_vector_dimension(self):
        return self._dimension

    def _extract_mfcc_local(self, audio_path):
        """
        Extrae características MFCC locales por ventanas temporales.
        REtorna: list[numpy.ndarray] de vectores MFCC locales 
        """
        try:
            import librosa
            import numpy as np

            y, sr = librosa.load(audio_path, sr=None)
            
            # Extraer MFCCs con más frames para tener más vectores locales
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self._dimension, 
                                       hop_length=512, n_fft=2048)

            if mfccs.size > 0:
                # Transponer para tener (time_frames, n_mfcc)
                mfcc_frames = mfccs.T
                
                # Retornar lista de vectores MFCC locales (uno por frame temporal)
                return [frame.astype(np.float32) for frame in mfcc_frames]
            else:
                return [np.array([0.0] * self._dimension, dtype=np.float32)]

        except ImportError:
            print("Warning: librosa not available, using dummy MFCC")
            import numpy as np
            return [np.array([0.1] * self._dimension, dtype=np.float32) for _ in range(10)]

        except Exception as e:
            print(f"Error procesando el archivo de audio {audio_path}: {e}")
            import numpy as np
            return [np.array([0.0] * self._dimension, dtype=np.float32)]

    def _extract_spectral_local(self, audio_path):
        """
        Extrae características espectrales locales por ventanas temporales.
        """
        try:
            import librosa
            import numpy as np

            y, sr = librosa.load(audio_path, sr=None)
            
            # Extraer diferentes características espectrales
            hop_length = 512
            
            # Spectral centroid, bandwidth, rolloff
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
            
            # Combinar características para cada frame
            features_per_frame = []
            min_length = min(len(spectral_centroids), len(spectral_bandwidth), 
                           len(spectral_rolloff), len(zcr))
            
            for i in range(min_length):
                # Crear vector de características espectrales (extender a 20 dimensiones)
                frame_features = np.array([
                    spectral_centroids[i], spectral_bandwidth[i], spectral_rolloff[i], zcr[i]
                ])
                
                # Extender a 20 dimensiones con repetición controlada
                extended_features = np.tile(frame_features, 5)[:self._dimension]
                features_per_frame.append(extended_features.astype(np.float32))
            
            return features_per_frame if features_per_frame else [np.array([0.0] * self._dimension, dtype=np.float32)]

        except Exception as e:
            print(f"Error en extracción espectral de {audio_path}: {e}")
            import numpy as np
            return [np.array([0.0] * self._dimension, dtype=np.float32)]


def create_feature_extractor(media_type, method="sift"):
    """
    Factory function to create the appropriate feature extractor.

    Args:
        media_type (str): Type of media ("image" or "audio")
        method (str): Method for extraction ("sift"/"cnn" for images, "mfcc"/"spectral" for audio)

    Returns:
        FeatureExtractor: Appropriate feature extractor instance
    """
    if media_type == "image":
        return ImageExtractor(method=method)
    elif media_type == "audio":
        # Para audio, usar method si se especifica, sino usar "mfcc" por defecto
        audio_method = method if method in ["mfcc", "spectral"] else "mfcc"
        return AudioExtractor(method=audio_method)
    else:
        raise ValueError(f"Unsupported media type: {media_type}")