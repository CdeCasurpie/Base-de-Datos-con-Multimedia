import os
import json
import math
import pickle
import struct
from HeiderDB.database.index_base import IndexBase
from HeiderDB.database.indexes.text_processor import TextProcessor

class InvertedIndex(IndexBase):
    """
    Implementación de índice invertido para búsqueda textual.
    Implementa algoritmo SPIMI para indexación eficiente.
    """
    
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        
        # Definir rutas de archivos
        self.index_dir = os.path.dirname(data_path)
        self.dictionary_file = os.path.join(self.index_dir, f"{table_name}_{column_name}_inverted_dictionary.dat")
        self.postings_file = os.path.join(self.index_dir, f"{table_name}_{column_name}_inverted_postings.dat")
        self.metadata_file = os.path.join(self.index_dir, f"{table_name}_{column_name}_inverted_metadata.json")
        
        # Inicializar procesador de texto
        self.text_processor = TextProcessor()
        
        # Diccionario en memoria: término -> {offset, size, df}
        self.dictionary = {}
        
        # Contador de documentos indexados
        self.doc_count = 0
        
        # Cargar o crear índice
        self._load_or_create_index()
        
    def _load_or_create_index(self):
        """Carga el índice existente o crea uno nuevo"""
        if os.path.exists(self.metadata_file) and os.path.exists(self.dictionary_file):
            self._load_metadata()
            self._load_dictionary()
            print(f"Índice invertido cargado para {self.table_name}.{self.column_name}")
        else:
            self._create_new_index()
            print(f"Nuevo índice invertido creado para {self.table_name}.{self.column_name}")
    
    def _create_new_index(self):
        """Crea un nuevo índice vacío"""
        self.dictionary = {}
        self.doc_count = 0
        
        # Asegurar que el directorio existe
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Crear archivos vacíos
        with open(self.dictionary_file, 'wb') as f:
            f.write(struct.pack('!I', 0))  # 0 términos inicialmente
            
        with open(self.postings_file, 'wb') as f:
            pass  # Archivo vacío
            
        self._save_metadata()
    
    def _save_metadata(self):
        """Guarda metadatos del índice"""
        metadata = {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "doc_count": self.doc_count,
            "vocabulary_size": len(self.dictionary),
            "created_at": os.path.getmtime(self.data_path) if os.path.exists(self.data_path) else 0,
            "updated_at": os.path.getmtime(self.postings_file) if os.path.exists(self.postings_file) else 0
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self):
        """Carga metadatos del índice"""
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
            self.doc_count = metadata.get("doc_count", 0)
    
    def _load_dictionary(self):
        """Carga el diccionario completo en memoria"""
        self.dictionary = {}
        
        try:
            with open(self.dictionary_file, 'rb') as f:
                num_terms = struct.unpack('!I', f.read(4))[0]
                
                for _ in range(num_terms):
                    # Leer longitud del término
                    term_len = struct.unpack('!I', f.read(4))[0]
                    
                    # Leer término
                    term = f.read(term_len).decode('utf-8')
                    
                    # Leer offset, size y df
                    offset, size, df = struct.unpack('!QII', f.read(16))
                    
                    # Almacenar en el diccionario
                    self.dictionary[term] = {
                        'offset': offset,
                        'size': size,
                        'df': df
                    }
        except (EOFError, struct.error) as e:
            print(f"Error al cargar el diccionario: {e}")
            self.dictionary = {}
    
    def _save_dictionary(self):
        """Guarda el diccionario completo a disco"""
        with open(self.dictionary_file, 'wb') as f:
            # Escribir número de términos
            f.write(struct.pack('!I', len(self.dictionary)))
            
            # Escribir cada término con su offset, size y df
            for term, data in self.dictionary.items():
                term_bytes = term.encode('utf-8')
                
                # Escribir longitud del término
                f.write(struct.pack('!I', len(term_bytes)))
                
                # Escribir término
                f.write(term_bytes)
                
                # Escribir offset, size y df
                f.write(struct.pack('!QII', data['offset'], data['size'], data['df']))
    
    def _read_posting_list(self, term):
        """Lee la posting list para un término específico desde el archivo"""
        if term not in self.dictionary:
            return None
            
        try:
            with open(self.postings_file, 'rb') as f:
                f.seek(self.dictionary[term]['offset'])
                serialized = f.read(self.dictionary[term]['size'])
                return pickle.loads(serialized)
        except (EOFError, pickle.UnpicklingError) as e:
            print(f"Error al leer posting list para '{term}': {e}")
            return None
    
    def _write_posting_list(self, posting_list):
        """Escribe una posting list al archivo y retorna su offset y tamaño"""
        term = posting_list['term']
        serialized = pickle.dumps(posting_list)
        
        with open(self.postings_file, 'ab') as f:
            offset = f.tell()
            f.write(serialized)
            size = len(serialized)
        
        return offset, size
    
    def search(self, key):
        """
        Busca un registro usando la clave proporcionada.
        Para índice invertido, key es un término o frase de búsqueda.
        Retorna el primer registro que coincide o None.
        """
        query = key
        
        if isinstance(query, int) or isinstance(query, float):
            # Si es un valor numérico, buscar por ID primario directamente
            return self.table_ref.search(self.table_ref.primary_key, query)
        
        if not isinstance(query, str):
            return None
        
        # Detectar tipo de búsqueda
        if " AND " in query or " OR " in query:
            # Búsqueda booleana
            results = self.search_boolean(query)
            if results:
                return results
        elif " " in query:
            # Búsqueda rankeada (multi-término)
            results = self.search_ranked(query, k=100)
            if results:
                return results
        else:
            # Búsqueda simple de un término
            results = self.search_term(query)
            if results:
                return results
        return None
        
    def range_search(self, begin_key, end_key=None):
        """
        En índice invertido no aplica búsqueda por rango tradicional.
        """
        return []
        
    def add(self, record, key):
        """
        Añade un registro al índice invertido.
        key: ID primario del registro
        record: Registro completo con la columna de texto
        """
        if self.column_name not in record:
            return
            
        text = record[self.column_name]
        if not isinstance(text, str) or not text.strip():
            return
            
        # Procesar texto
        terms = self.text_processor.process_text(text)
        
        # Calcular frecuencias de términos
        term_freqs = {}
        term_positions = {}
        
        for pos, term in enumerate(terms):
            if term in term_freqs:
                term_freqs[term] += 1
                term_positions[term].append(pos)
            else:
                term_freqs[term] = 1
                term_positions[term] = [pos]
        
        # Para cada término, actualizar su posting list
        for term, tf in term_freqs.items():
            # Leer posting list actual
            posting_list = self._read_posting_list(term)
            
            if posting_list is None:
                # Crear nueva posting list
                posting_list = {
                    'term': term,
                    'df': 1,
                    'postings': [
                        {
                            'doc_id': key,
                            'tf': tf,
                            'positions': term_positions[term]
                        }
                    ]
                }
            else:
                # Actualizar posting list existente
                # Verificar si el documento ya está en la lista
                found = False
                for i, posting in enumerate(posting_list['postings']):
                    if posting['doc_id'] == key:
                        # Actualizar entrada existente
                        posting_list['postings'][i] = {
                            'doc_id': key,
                            'tf': tf,
                            'positions': term_positions[term]
                        }
                        found = True
                        break
                        
                if not found:
                    # Añadir nueva entrada
                    posting_list['postings'].append({
                        'doc_id': key,
                        'tf': tf,
                        'positions': term_positions[term]
                    })
                    posting_list['df'] += 1
            
            # Escribir posting list actualizada
            offset, size = self._write_posting_list(posting_list)
            
            # Actualizar diccionario
            self.dictionary[term] = {
                'offset': offset,
                'size': size,
                'df': posting_list['df']
            }
        
        # Actualizar contador de documentos
        self.doc_count += 1
        
        # Guardar cambios
        self._save_dictionary()
        self._save_metadata()
        
    def remove(self, key):
        """
        Elimina un documento del índice invertido.
        key: ID primario del documento a eliminar
        """
        removed = False
        terms_to_update = []
        
        # Identificar términos que contienen el documento
        for term, data in self.dictionary.items():
            posting_list = self._read_posting_list(term)
            if not posting_list:
                continue
                
            # Buscar y eliminar el documento de la posting list
            new_postings = [p for p in posting_list['postings'] if p['doc_id'] != key]
            
            # Si cambió la posting list
            if len(new_postings) < len(posting_list['postings']):
                removed = True
                
                if len(new_postings) == 0:
                    # Si no quedan documentos, eliminar el término
                    del self.dictionary[term]
                else:
                    # Actualizar posting list
                    posting_list['postings'] = new_postings
                    posting_list['df'] = len(new_postings)
                    
                    # Reescribir posting list
                    offset, size = self._write_posting_list(posting_list)
                    
                    # Actualizar diccionario
                    self.dictionary[term] = {
                        'offset': offset,
                        'size': size,
                        'df': posting_list['df']
                    }
        
        if removed:
            self.doc_count -= 1
            self._save_dictionary()
            self._save_metadata()
            
        return removed
        
    def rebuild(self):
        """
        Reconstruye el índice desde cero usando todos los registros de la tabla.
        """
        # Limpiar archivos existentes
        self._create_new_index()
        
        # Obtener todos los registros
        all_records = self.table_ref.get_all()
        
        # Reindexar cada registro
        for record in all_records:
            primary_key = record.get(self.table_ref.primary_key)
            if primary_key is not None:
                self.add(record, primary_key)
        
        print(f"Índice invertido reconstruido con {self.doc_count} documentos")
        
    def get_all(self):
        """
        Obtiene todos los registros de la tabla.
        """
        return self.table_ref.get_all()
        
    def count(self):
        """
        Retorna el número de documentos indexados.
        """
        return self.doc_count
        
    def compute_tf_idf(self, term, document):
        """
        Calcula el valor TF-IDF para un término en un documento.
        
        Args:
            term: Término a evaluar
            document: ID del documento o documento completo
        
        Returns:
            float: Valor TF-IDF
        """
        # Si term no está en el diccionario
        if term not in self.dictionary:
            return 0.0
        
        # Obtener ID del documento si se pasó el documento completo
        doc_id = document
        if isinstance(document, dict):
            doc_id = document.get(self.table_ref.primary_key)
        
        # Leer posting list
        posting_list = self._read_posting_list(term)
        if not posting_list:
            return 0.0
        
        # Buscar el documento en la posting list
        doc_posting = None
        for posting in posting_list['postings']:
            if posting['doc_id'] == doc_id:
                doc_posting = posting
                break
                
        if not doc_posting:
            return 0.0
            
        # Calcular TF (term frequency)
        tf = doc_posting['tf']
        
        # Normalizar TF (opcional)
        # En esta implementación usamos frecuencia bruta
        
        # Calcular IDF (inverse document frequency)
        idf = math.log(self.doc_count / posting_list['df'])
        
        return tf * idf
        
    def search_term(self, term):
        """
        Busca documentos que contienen un término específico.
        
        Args:
            term: Término a buscar
            
        Returns:
            list: Lista de documentos que contienen el término
        """
        # Procesar el término
        processed_terms = self.text_processor.process_text(term)

        print("Procesed terms:", processed_terms)  # Depuración     
        
        if not processed_terms:
            return []
            
        # Usar solo el primer término procesado
        processed_term = processed_terms[0]
        
        if processed_term not in self.dictionary:
            return []
            
        posting_list = self._read_posting_list(processed_term)
        if not posting_list:
            return []
            
        # Obtener IDs de documentos
        doc_ids = [posting['doc_id'] for posting in posting_list['postings']]
        
        # Recuperar documentos completos
        results = []
        for doc_id in doc_ids:
            # Corregir la llamada para pasar el nombre de la columna primaria
            doc = self.table_ref.search(self.table_ref.primary_key, doc_id)
            if doc:
                results.append(doc)
                
        return results
        
    def search_boolean(self, query):
        """
        Realiza búsqueda booleana (AND/OR) de términos.
        
        Args:
            query: Consulta con operadores AND/OR
            
        Returns:
            list: Lista de documentos que satisfacen la consulta
        """
        # Dividir consulta por operadores
        if " AND " in query:
            parts = query.split(" AND ")
            operator = "AND"
        elif " OR " in query:
            parts = query.split(" OR ")
            operator = "OR"
        else:
            # Sin operador, tratar como búsqueda simple
            return self.search_term(query)
            
        # Procesar cada parte
        results_sets = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Buscar documentos para esta parte
            part_results = self.search_term(part)
            
            # Extraer IDs
            doc_ids = set()
            for doc in part_results:
                doc_id = doc.get(self.table_ref.primary_key)
                if doc_id is not None:
                    doc_ids.add(doc_id)
                    
            results_sets.append(doc_ids)
            
        if not results_sets:
            return []
            
        # Aplicar operador
        if operator == "AND":
            # Intersección
            final_ids = results_sets[0]
            for s in results_sets[1:]:
                final_ids = final_ids.intersection(s)
        else:
            # Unión
            final_ids = results_sets[0]
            for s in results_sets[1:]:
                final_ids = final_ids.union(s)
                
        # Recuperar documentos completos
        results = []
        for doc_id in final_ids:
            # Corregir para incluir el nombre de la columna primaria
            doc = self.table_ref.search(self.table_ref.primary_key, doc_id)
            if doc:
                results.append(doc)
                
        return results
        
    def search_top_k(self, query, k=10):
        """
        Busca los k documentos más relevantes para una consulta.
        Alias de search_ranked para compatibilidad con otros índices.
        """
        return self.search_ranked(query, k)
        
    def search_ranked(self, query, k=10):
        """
        Realiza búsqueda rankeada por TF-IDF para múltiples términos.
        
        Args:
            query: Consulta de texto
            k: Número máximo de resultados
            
        Returns:
            list: Lista de documentos ordenados por relevancia
        """
        # Procesar consulta
        query_terms = self.text_processor.process_text(query)
        
        if not query_terms:
            return []
            
        # Mapear término -> documentos
        term_docs = {}
        
        # Para cada término, obtener documentos
        for term in set(query_terms):
            if term in self.dictionary:
                posting_list = self._read_posting_list(term)
                if posting_list:
                    term_docs[term] = posting_list['postings']
        
        if not term_docs:
            return []
            
        # Calcular puntuaciones TF-IDF para cada documento
        doc_scores = {}
        
        for term, postings in term_docs.items():
            for posting in postings:
                doc_id = posting['doc_id']
                
                # Calcular TF-IDF
                tf = posting['tf']
                df = self.dictionary[term]['df']
                idf = math.log(self.doc_count / df) if df > 0 else 0
                
                score = tf * idf
                
                # Acumular puntuación
                if doc_id in doc_scores:
                    doc_scores[doc_id] += score
                else:
                    doc_scores[doc_id] = score
        
        # Ordenar documentos por puntuación
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Limitar a k resultados
        top_k_docs = sorted_docs[:k]
        
        # Recuperar documentos completos
        results = []
        for doc_id, score in top_k_docs:
            # Corregir para incluir el nombre de la columna primaria
            doc = self.table_ref.search(self.table_ref.primary_key, doc_id)
            if doc:
                # Opcionalmente añadir la puntuación al documento
                doc['_score'] = score
                results.append(doc)
                
        return results
        
    def cosine_similarity(self, query_vector, document_vector):
        """
        Calcula similitud del coseno entre dos vectores.
        
        Args:
            query_vector: Vector de la consulta
            document_vector: Vector del documento
            
        Returns:
            float: Similitud del coseno (0-1)
        """
        # Producto punto
        dot_product = sum(query_vector.get(term, 0) * document_vector.get(term, 0) 
                          for term in set(query_vector) | set(document_vector))
        
        # Magnitudes
        query_magnitude = math.sqrt(sum(val ** 2 for val in query_vector.values()))
        doc_magnitude = math.sqrt(sum(val ** 2 for val in document_vector.values()))
        
        # Evitar división por cero
        if query_magnitude == 0 or doc_magnitude == 0:
            return 0.0
            
        return dot_product / (query_magnitude * doc_magnitude)
        
    def _save_index(self):
        """
        Guarda el índice completo (diccionario y metadatos).
        """
        self._save_dictionary()
        self._save_metadata()
        
    def _load_index(self):
        """
        Carga el índice completo.
        """
        self._load_metadata()
        self._load_dictionary()