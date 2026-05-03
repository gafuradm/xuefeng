# backend/app/rag/vector_store.py
import os
import pickle
import numpy as np
import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Any, Optional

class VectorStore:
    def __init__(self, base_path: str = "data/vector_stores"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.active_stores = {}
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        return self._model

    def load_ent_index(self, index_path: str, vectors_path: str, metadata_path: str, store_key: str = 'ent'):
        """Загружает индекс с указанным ключом"""
        print(f"Загрузка HNSW индекса из {index_path}")
        index = hnswlib.Index(space='cosine', dim=384)
        index.load_index(index_path)
        vectors = np.load(vectors_path)
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        self.active_stores[store_key] = {
            'index': index,
            'vectors': vectors,
            'metadata': metadata,
            'dim': 384
        }
        print(f"✅ Загружено {len(metadata)} задач, индекс содержит {index.get_current_count()} векторов")

    def search_similar(self, exam_type: str, query: str, k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """Поиск похожих задач в указанном хранилище"""
        store = self.active_stores.get(exam_type)
        if not store:
            return []
        
        # Если есть индекс, используем семантический поиск
        if store.get('index') is not None:
            try:
                model = self._get_model()
                query_emb = model.encode([query])
                labels, distances = store['index'].knn_query(query_emb, k=k)
                results = []
                for idx, dist in zip(labels[0], distances[0]):
                    if idx >= 0 and idx < len(store['metadata']):
                        task = store['metadata'][idx].copy()
                        task['similarity'] = 1 - dist
                        if filters:
                            match = all(task.get(key) == val for key, val in filters.items())
                            if not match:
                                continue
                        results.append(task)
                return results[:k]
            except Exception as e:
                print(f"Ошибка поиска: {e}")
        
        # Fallback: текстовый поиск
        results = []
        query_lower = query.lower()
        for item in store['metadata']:
            text = (item.get('question', '') + ' ' + 
                    item.get('topic', '') + ' ' + 
                    item.get('subject', '')).lower()
            if query_lower in text:
                item_copy = item.copy()
                item_copy['text'] = item.get('question', '')[:500]
                results.append(item_copy)
                if len(results) >= k:
                    break
        return results