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

    def load_ent_index(self, index_path: str, vectors_path: str, metadata_path: str):
        """Загружает HNSW индекс и метаданные для ЕНТ"""
        print(f"Загрузка HNSW индекса из {index_path}")
        index = hnswlib.Index(space='cosine', dim=384)  # размерность модели
        index.load_index(index_path)
        vectors = np.load(vectors_path)
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        print(f"✅ Загружено {len(metadata)} задач, индекс содержит {index.get_current_count()} векторов")
        self.active_stores['ent'] = {
            'index': index,
            'vectors': vectors,
            'metadata': metadata,
            'dim': 384
        }

    def search_similar(self, exam_type: str, query: str, k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """Семантический поиск по индексу"""
        store = self.active_stores.get(exam_type)
        if not store or not store.get('index'):
            print(f"Индекс для {exam_type} не загружен, используем текстовый поиск (fallback)")
            # Fallback на простой текстовый поиск (можно оставить старый код)
            return self._text_search(store, query, k, filters)

        # Генерируем эмбеддинг запроса
        model = self._get_model()
        query_emb = model.encode([query])
        
        # Поиск
        labels, distances = store['index'].knn_query(query_emb, k=k)
        results = []
        for idx, dist in zip(labels[0], distances[0]):
            if idx >= 0 and idx < len(store['metadata']):
                task = store['metadata'][idx].copy()
                task['similarity'] = 1 - dist  # косинусное расстояние -> похожесть
                # Применяем фильтры (если нужны)
                if filters:
                    match = True
                    for key, val in filters.items():
                        if task.get(key) != val:
                            match = False
                            break
                    if not match:
                        continue
                results.append(task)
        return results[:k]

    def _text_search(self, store, query: str, k: int, filters=None):
        """Fallback: текстовый поиск по ключевым словам"""
        if not store or not store.get('metadata'):
            return []
        results = []
        query_lower = query.lower()
        for item in store['metadata']:
            text = (item.get('question', '') + ' ' + item.get('topic', '') + ' ' + item.get('subject', '')).lower()
            if query_lower in text:
                item_copy = item.copy()
                item_copy['text'] = item.get('question', '')[:500]
                results.append(item_copy)
                if len(results) >= k:
                    break
        return results