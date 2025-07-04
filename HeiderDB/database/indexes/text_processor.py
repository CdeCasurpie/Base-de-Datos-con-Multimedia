import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

class TextProcessor:
    """
    Procesador de texto para normalización, tokenización y limpieza.
    Integración con técnicas de NLP para búsqueda textual mejorada.
    """
    
    def __init__(self, language='english', use_stemming=True, remove_stopwords=True):
        self.language = language
        self.use_stemming = use_stemming
        self.remove_stopwords = remove_stopwords
        self.stopwords = set()
        self.load_stopwords(language)
        self.stemmer = PorterStemmer()
        
    def tokenize(self, text):
        return word_tokenize(text)
        
    def normalize(self, text):
        # Poner en minúsculas y eliminar puntuación :)
        text = text.lower()
        text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
        return text
        
    def remove_stopwords_from_tokens(self, tokens):
        if self.remove_stopwords:
            return [word for word in tokens if word not in self.stopwords]
        return tokens
        
    def stem_tokens(self, tokens):
        if self.use_stemming:
            return [self.stemmer.stem(word) for word in tokens]
        return tokens
    
    def process_text(self, text):
        normalized = self.normalize(text)
        tokens = self.tokenize(normalized)
        
        if not self.stopwords and self.remove_stopwords:
            self.load_stopwords(self.language)

        tokens_no_stop = self.remove_stopwords_from_tokens(tokens)
        stemmed_tokens = self.stem_tokens(tokens_no_stop)
        return stemmed_tokens

    def load_stopwords(self, language='english'):
        try:
            self.stopwords = set(stopwords.words(language))
        except:
            print(f"No se pudo cargar stopwords para el idioma '{language}'")
