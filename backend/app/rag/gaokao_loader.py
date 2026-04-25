# backend/app/rag/gaokao_loader.py
import json
import numpy as np
from typing import List, Dict, Any
from .vector_store import VectorStore, ExamProblem

class GaokaoLoader:
    """
    Загрузчик и обработчик данных гаокао
    Работает с существующими chunks.npy и index.hnsw
    """
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.metadata_cache = {}
    
    def load_existing_data(self, chunks_path: str, index_path: str):
        """
        Загрузить существующие файлы
        chunks.npy и index.hnsw
        """
        store = self.vector_store.load_gaokao_data(chunks_path, index_path)
        
        # Извлекаем метаданные из векторов (если они закодированы)
        self._extract_metadata_from_vectors(store)
        
        return store
    
    def _extract_metadata_from_vectors(self, store: Dict):
        """
        Если метаданные не сохранены отдельно,
        извлекаем их из структуры векторов или загружаем из JSON
        """
        # Ищем JSON файлы с задачами рядом
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        gaokao_json_path = os.path.join(base_dir, 'data', 'gaokao_problems.json')
        
        if os.path.exists(gaokao_json_path) and not store['metadata']:
            with open(gaokao_json_path, 'r', encoding='utf-8') as f:
                problems = json.load(f)
                
            # Создаём метаданные для каждой задачи
            metadata = []
            for i, problem in enumerate(problems):
                if i < len(store['vectors']):
                    metadata.append({
                        'id': problem.get('id', f"gaokao_{i}"),
                        'exam_type': 'gaokao',
                        'year': problem.get('year', 2023),
                        'topic': problem.get('topic', ''),
                        'difficulty': problem.get('difficulty', 'medium'),
                        'text': problem.get('text', ''),
                        'solution': problem.get('solution', ''),
                        'answer': problem.get('answer', ''),
                        'score': problem.get('score', 0),
                        'metadata': problem.get('metadata', {})
                    })
            
            store['metadata'] = metadata
            
            # Сохраняем метаданные
            metadata_path = os.path.join(os.path.dirname(chunks_path), 'metadata.pkl')
            import pickle
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
    
    def add_new_gaokao_problems(self, problems: List[Dict]):
        """Добавить новые задачи гаокао"""
        exam_problems = []
        for p in problems:
            exam_problems.append(ExamProblem(
                id=p.get('id', f"gaokao_new_{len(exam_problems)}"),
                exam_type='gaokao',
                year=p.get('year', 2024),
                topic=p.get('topic', ''),
                difficulty=p.get('difficulty', 'medium'),
                text=p.get('text', ''),
                solution=p.get('solution', ''),
                answer=p.get('answer', ''),
                score=p.get('score', 0),
                metadata=p.get('metadata', {})
            ))
        
        self.vector_store.add_exam_problems('gaokao', exam_problems)
    
    def search_gaokao_problems(self, query: str, k: int = 5, 
                                year: int = None, topic: str = None) -> List[Dict]:
        """Поиск задач гаокао"""
        filters = {}
        if year:
            filters['year'] = year
        if topic:
            filters['topic'] = topic
        
        return self.vector_store.search_similar('gaokao', query, k, filters)