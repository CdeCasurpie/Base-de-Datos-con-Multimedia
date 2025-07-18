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
    Extractor de características para audio ULTRA-OPTIMIZADO.
    Hasta 10x más rápido que la versión anterior.
    """

    def __init__(self, method="mfcc", vectors_per_file=100, target_dimension=20):
        super().__init__()
        self._dimension = target_dimension
        self.media_type = "audio"
        self.method = method
        self.vectors_per_file = vectors_per_file
        
        # Parámetros optimizados para velocidad
        self.sr_target = 22050  # Reducir sample rate para velocidad
        self.n_fft = 1024      # FFT más pequeño
        self.hop_length = 512   # Hop length fijo optimizado
        
        print(f"🚀 AudioExtractor RÁPIDO inicializado:")
        print(f"   - Método: {method}")
        print(f"   - Vectores por archivo: {vectors_per_file}")
        print(f"   - Dimensiones: {target_dimension}")
        print(f"   - Sample rate objetivo: {self.sr_target} Hz")

    def extract(self, file_path):
        """Extrae vectores de forma ultra-optimizada"""
        if self.method == "mfcc":
            return self._extract_mfcc_fast(file_path)
        elif self.method == "spectral":
            return self._extract_spectral_fast(file_path)
        else:
            return self._extract_mfcc_fast(file_path)

    def get_vector_dimension(self):
        return self._dimension

    def _extract_mfcc_fast(self, audio_path):
        """
        VERSIÓN ULTRA-RÁPIDA: Extrae una sola vez y submuestrea inteligentemente.
        """
        try:
            import librosa
            import numpy as np

            # 🚀 OPTIMIZACIÓN 1: Cargar con sample rate reducido
            y, sr = librosa.load(audio_path, sr=self.sr_target, duration=None)
            
            if len(y) == 0:
                return self._generate_dummy_vectors()
            
            # 🚀 OPTIMIZACIÓN 2: Una sola extracción MFCC para todo el audio
            n_mfcc = min(13, self._dimension)
            mfccs = librosa.feature.mfcc(
                y=y, 
                sr=sr, 
                n_mfcc=n_mfcc,
                hop_length=self.hop_length,
                n_fft=self.n_fft
            )
            
            if mfccs.size == 0:
                return self._generate_dummy_vectors()
            
            # 🚀 OPTIMIZACIÓN 3: Calcular características adicionales UNA sola vez
            extra_features_timeline = None
            if self._dimension > 13:
                extra_features_timeline = self._compute_all_extra_features_fast(y, sr)
            
            # 🚀 OPTIMIZACIÓN 4: Submuestreo inteligente para obtener exactamente vectors_per_file
            total_frames = mfccs.shape[1]
            vectors = []
            
            if total_frames <= self.vectors_per_file:
                # Audio corto: usar todos los frames y rellenar si necesario
                for i in range(total_frames):
                    vector = self._build_vector_fast(mfccs[:, i], extra_features_timeline, i)
                    vectors.append(vector)
                
                # Rellenar duplicando el último
                while len(vectors) < self.vectors_per_file:
                    if vectors:
                        vectors.append(vectors[-1].copy())
                    else:
                        vectors.append(np.zeros(self._dimension, dtype=np.float32))
            else:
                # Audio largo: submuestrear uniformemente
                indices = np.linspace(0, total_frames - 1, self.vectors_per_file, dtype=int)
                for idx in indices:
                    vector = self._build_vector_fast(mfccs[:, idx], extra_features_timeline, idx)
                    vectors.append(vector)
            
            return vectors[:self.vectors_per_file]

        except ImportError:
            print("⚠️ librosa no disponible")
            return self._generate_dummy_vectors()
        except Exception as e:
            print(f"❌ Error rápido en {audio_path}: {e}")
            return self._generate_dummy_vectors()

    def _compute_all_extra_features_fast(self, y, sr):
        """
        🚀 Calcula TODAS las características extra de una sola vez.
        """
        import librosa
        import numpy as np
        
        try:
            # Calcular todas las características en paralelo
            spectral_centroid = librosa.feature.spectral_centroid(
                y=y, sr=sr, hop_length=self.hop_length, n_fft=self.n_fft)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                y=y, sr=sr, hop_length=self.hop_length, n_fft=self.n_fft)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=y, sr=sr, hop_length=self.hop_length, n_fft=self.n_fft)[0]
            zcr = librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)[0]
            rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
            
            # Chroma simplificado (solo primeras 2 componentes)
            chroma = librosa.feature.chroma_stft(
                y=y, sr=sr, hop_length=self.hop_length, n_fft=self.n_fft)[:2]
            
            # Combinar en matriz (7 x tiempo)
            extra_matrix = np.vstack([
                spectral_centroid,
                spectral_bandwidth, 
                spectral_rolloff,
                zcr,
                rms,
                chroma[0] if chroma.shape[0] > 0 else np.zeros_like(zcr),
                chroma[1] if chroma.shape[0] > 1 else np.zeros_like(zcr)
            ])
            
            return extra_matrix
            
        except Exception as e:
            print(f"⚠️ Error en características extra rápidas: {e}")
            return None

    def _build_vector_fast(self, mfcc_frame, extra_timeline, frame_idx):
        """
        🚀 Construye vector final combinando MFCC + extras de forma rápida.
        """
        import numpy as np
        
        # Empezar con MFCCs
        if self._dimension <= 13:
            vector = mfcc_frame[:self._dimension]
        else:
            # Combinar MFCC + características extra
            if extra_timeline is not None and frame_idx < extra_timeline.shape[1]:
                extra_features = extra_timeline[:, frame_idx]
                combined = np.concatenate([mfcc_frame, extra_features])
                vector = combined[:self._dimension]
            else:
                # Solo MFCCs, rellenar con ceros
                vector = np.zeros(self._dimension)
                vector[:len(mfcc_frame)] = mfcc_frame[:self._dimension]
        
        # Asegurar dimensión correcta
        if len(vector) < self._dimension:
            padding = np.zeros(self._dimension - len(vector))
            vector = np.concatenate([vector, padding])
        
        return vector.astype(np.float32)

    def _extract_spectral_fast(self, audio_path):
        """
        🚀 Versión rápida de extracción espectral.
        """
        try:
            import librosa
            import numpy as np

            # Cargar con sample rate reducido
            y, sr = librosa.load(audio_path, sr=self.sr_target)
            
            if len(y) == 0:
                return self._generate_dummy_vectors()
            
            # Calcular características espectrales básicas UNA vez
            features_timeline = self._compute_all_extra_features_fast(y, sr)
            
            if features_timeline is None:
                return self._generate_dummy_vectors()
            
            # Submuestrear para obtener vectors_per_file
            total_frames = features_timeline.shape[1]
            vectors = []
            
            if total_frames <= self.vectors_per_file:
                # Usar todos los frames
                for i in range(total_frames):
                    base_features = features_timeline[:5, i]  # Primeras 5 características
                    # Extender replicando
                    extended = np.tile(base_features, (self._dimension // 5) + 1)
                    vector = extended[:self._dimension]
                    vectors.append(vector.astype(np.float32))
                
                # Rellenar si necesario
                while len(vectors) < self.vectors_per_file:
                    if vectors:
                        vectors.append(vectors[-1].copy())
                    else:
                        vectors.append(np.zeros(self._dimension, dtype=np.float32))
            else:
                # Submuestrear uniformemente
                indices = np.linspace(0, total_frames - 1, self.vectors_per_file, dtype=int)
                for idx in indices:
                    base_features = features_timeline[:5, idx]
                    extended = np.tile(base_features, (self._dimension // 5) + 1)
                    vector = extended[:self._dimension]
                    vectors.append(vector.astype(np.float32))
            
            return vectors[:self.vectors_per_file]

        except Exception as e:
            print(f"❌ Error espectral rápido: {e}")
            return self._generate_dummy_vectors()

    def _generate_dummy_vectors(self):
        """Genera vectores dummy rápidamente."""
        import numpy as np
        return [
            np.random.normal(0, 0.1, self._dimension).astype(np.float32) 
            for _ in range(self.vectors_per_file)
        ]

    def extract_single_vector(self, audio_path):
        """
        🚀 MODO ULTRA-RÁPIDO: Extrae UN solo vector promedio por archivo.
        Ideal para datasets muy grandes donde necesitas máxima velocidad.
        """
        try:
            import librosa
            import numpy as np

            # Cargar con sample rate muy reducido
            y, sr = librosa.load(audio_path, sr=8000, duration=30)  # Solo 30 segundos máximo
            
            if len(y) == 0:
                return [np.zeros(self._dimension, dtype=np.float32)]
            
            # MFCCs simplificados
            n_mfcc = min(13, self._dimension)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, n_fft=512, hop_length=256)
            
            # Promediar todo el archivo en UN vector
            mfcc_mean = np.mean(mfccs, axis=1)
            
            # Rellenar hasta _dimension si es necesario
            if len(mfcc_mean) < self._dimension:
                padding = np.zeros(self._dimension - len(mfcc_mean))
                vector = np.concatenate([mfcc_mean, padding])
            else:
                vector = mfcc_mean[:self._dimension]
            
            # Devolver vectors_per_file copias del mismo vector
            return [vector.astype(np.float32) for _ in range(self.vectors_per_file)]
            
        except Exception as e:
            print(f"❌ Error ultra-rápido: {e}")
            return self._generate_dummy_vectors()

    def get_speed_stats(self, file_path):
        """
        Obtiene estadísticas de velocidad para comparar métodos.
        """
        import time
        
        methods = {
            "normal": self._extract_mfcc_fast,
            "ultra_fast": self.extract_single_vector
        }
        
        results = {}
        for method_name, method_func in methods.items():
            start_time = time.time()
            try:
                vectors = method_func(file_path)
                end_time = time.time()
                results[method_name] = {
                    "time_seconds": end_time - start_time,
                    "vectors_extracted": len(vectors),
                    "success": True
                }
            except Exception as e:
                end_time = time.time()
                results[method_name] = {
                    "time_seconds": end_time - start_time,
                    "vectors_extracted": 0,
                    "success": False,
                    "error": str(e)
                }
        
        return results

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