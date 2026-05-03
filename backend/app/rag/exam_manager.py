# backend/app/rag/exam_manager.py
from typing import Dict, List, Any, Optional
from .vector_store import VectorStore

class ExamManager:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.active_exams = {}
    
    def init_ent(self, index_path: str, vectors_path: str, metadata_path: str, exam_key: str = 'ent'):
        """Загружает базу под указанным ключом"""
        self.vector_store.load_ent_index(index_path, vectors_path, metadata_path, exam_key)
        self.active_exams[exam_key] = self.vector_store.active_stores[exam_key]

    def search_problems(self, exam_type: str, query: str, k: int = 5,
                        filters: Optional[Dict] = None) -> List[Dict]:
        """Поиск задач в указанном хранилище"""
        return self.vector_store.search_similar(exam_type, query, k, filters)

    def get_similar_for_generation(self, exam_type: str, topic: str,
                                    num_examples: int = 3) -> List[Dict]:
        """Получить похожие задачи для генерации"""
        return self.search_problems(exam_type, topic, k=num_examples)