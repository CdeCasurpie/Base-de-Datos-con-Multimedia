from abc import ABC, abstractmethod

class IndexBase(ABC):
    @abstractmethod
    def search(self, key):
        pass
    
    @abstractmethod
    def range_search(self, begin_key, end_key=None):
        pass
    
    @abstractmethod
    def add(self, record):
        pass
    
    @abstractmethod
    def remove(self, key):
        pass
    
    @abstractmethod
    def rebuild(self):
        pass
    
    @abstractmethod
    def get_all(self):
        pass
    
    @abstractmethod
    def count(self):
        pass