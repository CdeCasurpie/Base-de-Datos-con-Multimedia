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
    Extractor de características para audio optimizado.
    Extrae exactamente 40 vectores por archivo de audio usando ventanas fijas.
    """

    def __init__(self, method="mfcc", vectors_per_file=40, target_dimension=20):
        super().__init__()
        self._dimension = target_dimension  # 20 dimensiones por defecto
        self.media_type = "audio"
        self.method = method
        self.vectors_per_file = vectors_per_file  # 40 vectores por archivo
        
        print(f"🎵 AudioExtractor inicializado:")
        print(f"   - Método: {method}")
        print(f"   - Vectores por archivo: {vectors_per_file}")
        print(f"   - Dimensiones por vector: {target_dimension}")

    def extract(self, file_path):
        """Extrae exactamente vectors_per_file vectores del archivo de audio"""
        if self.method == "mfcc":
            return self._extract_mfcc_segments(file_path)
        elif self.method == "spectral":
            return self._extract_spectral_segments(file_path)
        else:
            return self._extract_mfcc_segments(file_path)  # Default a MFCC

    def get_vector_dimension(self):
        return self._dimension

    def _extract_mfcc_segments(self, audio_path):
        """
        Extrae MFCCs dividiendo el audio en segmentos fijos.
        Garantiza exactamente vectors_per_file vectores por archivo.
        """
        try:
            import librosa
            import numpy as np

            # Cargar audio
            y, sr = librosa.load(audio_path, sr=None)
            
            if len(y) == 0:
                print(f"⚠️ Archivo de audio vacío: {audio_path}")
                return self._generate_dummy_vectors()
            
            # Dividir audio en segmentos iguales
            segment_length = len(y) // self.vectors_per_file
            
            if segment_length < 512:  # Segmento muy pequeño
                print(f"⚠️ Audio muy corto ({len(y)/sr:.1f}s): {audio_path}")
                return self._extract_with_overlap(y, sr)
            
            vectors = []
            
            for i in range(self.vectors_per_file):
                start_idx = i * segment_length
                end_idx = start_idx + segment_length
                
                # Para el último segmento, tomar todo lo que queda
                if i == self.vectors_per_file - 1:
                    end_idx = len(y)
                
                segment = y[start_idx:end_idx]
                
                if len(segment) > 0:
                    vector = self._extract_mfcc_from_segment(segment, sr)
                    vectors.append(vector)
                else:
                    # Segmento vacío, usar vector dummy
                    vectors.append(np.zeros(self._dimension, dtype=np.float32))
            
            print(f"✅ Extraídos {len(vectors)} vectores de {audio_path}")
            return vectors

        except ImportError:
            print("⚠️ librosa no disponible, usando vectores dummy")
            return self._generate_dummy_vectors()
        
        except Exception as e:
            print(f"❌ Error procesando {audio_path}: {e}")
            return self._generate_dummy_vectors()

    def _extract_mfcc_from_segment(self, segment, sr):
        """
        Extrae un vector MFCC promedio de un segmento de audio.
        """
        import librosa
        import numpy as np
        
        # Extraer MFCCs del segmento
        n_mfcc = min(13, self._dimension)  # Máximo 13 MFCCs estándar
        
        mfccs = librosa.feature.mfcc(
            y=segment, 
            sr=sr, 
            n_mfcc=n_mfcc,
            hop_length=512,
            n_fft=min(2048, len(segment) // 2)
        )
        
        if mfccs.size == 0:
            return np.zeros(self._dimension, dtype=np.float32)
        
        # Promediar MFCCs sobre el tiempo
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # Si necesitamos más dimensiones, añadir características espectrales
        if self._dimension > 13:
            extra_features = self._extract_extra_features(segment, sr)
            # Combinar hasta alcanzar _dimension
            combined = np.concatenate([mfcc_mean, extra_features])
            vector = combined[:self._dimension]  # Truncar si es necesario
        else:
            vector = mfcc_mean[:self._dimension]
        
        # Rellenar con ceros si es muy corto
        if len(vector) < self._dimension:
            padding = np.zeros(self._dimension - len(vector))
            vector = np.concatenate([vector, padding])
        
        return vector.astype(np.float32)

    def _extract_extra_features(self, segment, sr):
        """
        Extrae características espectrales adicionales del segmento.
        """
        import librosa
        import numpy as np
        
        try:
            # Características espectrales básicas
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=segment, sr=sr))
            spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=segment, sr=sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=segment, sr=sr))
            zcr = np.mean(librosa.feature.zero_crossing_rate(segment))
            
            # Características de energía
            rms_energy = np.mean(librosa.feature.rms(y=segment))
            
            # Características tonales (solo primeras 2 para no sobrecargar)
            chroma = librosa.feature.chroma_stft(y=segment, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)[:2]  # Solo 2 primeras componentes
            
            # Combinar características extra (7 dimensiones)
            extra_features = np.array([
                spectral_centroid,
                spectral_bandwidth, 
                spectral_rolloff,
                zcr,
                rms_energy,
                chroma_mean[0] if len(chroma_mean) > 0 else 0.0,
                chroma_mean[1] if len(chroma_mean) > 1 else 0.0
            ])
            
            return extra_features
            
        except Exception as e:
            print(f"⚠️ Error extrayendo características extra: {e}")
            return np.zeros(7)  # 7 características extra

    def _extract_with_overlap(self, y, sr):
        """
        Para audios muy cortos, extrae con ventanas superpuestas.
        """
        import librosa
        import numpy as np
        
        vectors = []
        window_size = len(y) // 4  # Ventanas más pequeñas
        hop_size = window_size // 2  # 50% overlap
        
        for i in range(0, len(y) - window_size, hop_size):
            if len(vectors) >= self.vectors_per_file:
                break
                
            segment = y[i:i + window_size]
            vector = self._extract_mfcc_from_segment(segment, sr)
            vectors.append(vector)
        
        # Rellenar hasta vectors_per_file si es necesario
        while len(vectors) < self.vectors_per_file:
            if len(vectors) > 0:
                # Duplicar el último vector válido
                vectors.append(vectors[-1].copy())
            else:
                # Vector dummy
                vectors.append(np.zeros(self._dimension, dtype=np.float32))
        
        return vectors[:self.vectors_per_file]  # Asegurar exactamente vectors_per_file

    def _extract_spectral_segments(self, audio_path):
        """
        Extrae características espectrales por segmentos.
        """
        try:
            import librosa
            import numpy as np

            y, sr = librosa.load(audio_path, sr=None)
            
            if len(y) == 0:
                return self._generate_dummy_vectors()
            
            # Dividir en segmentos
            segment_length = len(y) // self.vectors_per_file
            vectors = []
            
            for i in range(self.vectors_per_file):
                start_idx = i * segment_length
                end_idx = start_idx + segment_length
                
                if i == self.vectors_per_file - 1:
                    end_idx = len(y)
                
                segment = y[start_idx:end_idx]
                
                if len(segment) > 0:
                    vector = self._extract_spectral_from_segment(segment, sr)
                    vectors.append(vector)
                else:
                    vectors.append(np.zeros(self._dimension, dtype=np.float32))
            
            return vectors

        except Exception as e:
            print(f"❌ Error en extracción espectral: {e}")
            return self._generate_dummy_vectors()

    def _extract_spectral_from_segment(self, segment, sr):
        """
        Extrae vector de características espectrales de un segmento.
        """
        import librosa
        import numpy as np
        
        try:
            # Características espectrales básicas
            spectral_features = []
            
            spectral_features.append(np.mean(librosa.feature.spectral_centroid(y=segment, sr=sr)))
            spectral_features.append(np.mean(librosa.feature.spectral_bandwidth(y=segment, sr=sr)))
            spectral_features.append(np.mean(librosa.feature.spectral_rolloff(y=segment, sr=sr)))
            spectral_features.append(np.mean(librosa.feature.zero_crossing_rate(segment)))
            spectral_features.append(np.mean(librosa.feature.rms(y=segment)))
            
            # Extender el vector replicando características hasta _dimension
            base_features = np.array(spectral_features)
            extended_vector = np.tile(base_features, (self._dimension // len(base_features)) + 1)
            
            return extended_vector[:self._dimension].astype(np.float32)
            
        except Exception as e:
            print(f"⚠️ Error en características espectrales: {e}")
            return np.zeros(self._dimension, dtype=np.float32)

    def _generate_dummy_vectors(self):
        """
        Genera vectors_per_file vectores dummy cuando hay errores.
        """
        import numpy as np
        
        return [
            np.random.normal(0, 0.1, self._dimension).astype(np.float32) 
            for _ in range(self.vectors_per_file)
        ]

    def get_extraction_stats(self, file_path):
        """
        Obtiene estadísticas de extracción para un archivo (útil para debugging).
        """
        try:
            import librosa
            
            y, sr = librosa.load(file_path, sr=None)
            duration = len(y) / sr
            segment_duration = duration / self.vectors_per_file
            
            return {
                "duration_seconds": duration,
                "sample_rate": sr,
                "total_samples": len(y),
                "vectors_extracted": self.vectors_per_file,
                "segment_duration": segment_duration,
                "samples_per_segment": len(y) // self.vectors_per_file
            }
        except Exception as e:
            return {"error": str(e)}

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