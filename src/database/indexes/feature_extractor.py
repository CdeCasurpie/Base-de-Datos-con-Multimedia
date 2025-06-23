from abc import ABC, abstractmethod
import numpy as np

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
        self.method = method
        
    def extract(self, file_path):
        return np.array([])
        
    def get_vector_dimension(self):
        return 0
        
    def _extract_sift(self, image_path):
        return np.array([])
        
    def _extract_cnn(self, image_path):
        return np.array([])


class AudioExtractor(FeatureExtractor):
    """
    Extractor de características para audio.
    Implementa métodos MFCC para caracterización.
    """
    
    def __init__(self):
        pass
        
    def extract(self, file_path):
        return np.array([])
        
    def get_vector_dimension(self):
        return 0
        
    def _extract_mfcc(self, audio_path):
        return np.array([])