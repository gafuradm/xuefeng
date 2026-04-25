# backend/scripts/build_vector_db.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pickle
import json
from tqdm import tqdm
import hnswlib

def build_gaokao_vector_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunks_path = os.path.join(base_dir, "data", "gaokao", "chunks.npy")
    
    print("1. Загрузка текстов задач...")
    texts = np.load(chunks_path, allow_pickle=True)
    print(f"   Загружено {len(texts)} задач")
    
    # Парсим тексты и извлекаем метаданные
    print("\n2. Парсинг метаданных...")
    problems = []
    for i, text in enumerate(tqdm(texts, desc="Парсинг")):
        # Извлекаем год из текста
        year = 2024
        if "2024" in text:
            year = 2024
        elif "2023" in text:
            year = 2023
        
        # Определяем тему
        topic = "unknown"
        if "三角" in text or "sin" in text or "cos" in text:
            topic = "тригонометрия"
        elif "几何" in text or "直线" in text or "圆" in text:
            topic = "геометрия"
        elif "函数" in text or "导数" in text:
            topic = "матанализ"
        elif "概率" in text or "统计" in text:
            topic = "вероятность"
        elif "数列" in text:
            topic = "алгебра"
        
        problems.append({
            'id': f"gaokao_{i}",
            'exam_type': 'gaokao',
            'year': year,
            'topic': topic,
            'difficulty': 'medium',  # будем определять позже
            'text': text,
            'solution': extract_solution(text),
            'answer': extract_answer(text),
            'score': 0,
            'metadata': {'source': 'original'}
        })
    
    # Сохраняем метаданные
    metadata_path = os.path.join(base_dir, "data", "gaokao", "metadata.pkl")
    with open(metadata_path, 'wb') as f:
        pickle.dump(problems, f)
    print(f"   Сохранено {len(problems)} записей метаданных")
    
    # Генерируем эмбеддинги
    print("\n3. Генерация эмбеддингов...")
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # Генерируем эмбеддинги для всех текстов
    embeddings = []
    batch_size = 32
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Эмбеддинги"):
        batch = texts[i:i+batch_size]
        # Берем только первые 500 символов для скорости
        batch_texts = [t[:500] if isinstance(t, str) else str(t)[:500] for t in batch]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=False)
        embeddings.append(batch_embeddings)
    
    embeddings = np.vstack(embeddings)
    print(f"   Размерность эмбеддингов: {embeddings.shape}")
    
    # Сохраняем векторы
    vectors_path = os.path.join(base_dir, "data", "gaokao", "vectors.npy")
    np.save(vectors_path, embeddings)
    print(f"   Сохранено векторов: {vectors_path}")
    
    # Создаём HNSW индекс
    print("\n4. Создание HNSW индекса...")
    dim = embeddings.shape[1]
    index = hnswlib.Index(space='cosine', dim=dim)
    index.init_index(max_elements=len(embeddings), ef_construction=200, M=16)
    index.add_items(embeddings)
    
    # Сохраняем индекс
    index_path = os.path.join(base_dir, "data", "gaokao", "index_new.hnsw")
    index.save_index(index_path)
    print(f"   Индекс сохранён: {index_path}")
    
    # Копируем в vector_stores
    vector_store_path = os.path.join(base_dir, "data", "vector_stores", "gaokao")
    os.makedirs(vector_store_path, exist_ok=True)
    
    import shutil
    shutil.copy2(vectors_path, os.path.join(vector_store_path, "vectors.npy"))
    shutil.copy2(index_path, os.path.join(vector_store_path, "index.hnsw"))
    shutil.copy2(metadata_path, os.path.join(vector_store_path, "metadata.pkl"))
    
    print("\n✅ База данных создана успешно!")
    print(f"   Всего задач: {len(problems)}")
    print(f"   Размерность: {dim}")
    print(f"   Темы: {set(p['topic'] for p in problems)}")

def extract_solution(text):
    """Извлечь решение из текста"""
    if "【详细解析】" in text:
        solution = text.split("【详细解析】")[1].split("【")[0][:500]
        return solution.strip()
    return ""

def extract_answer(text):
    """Извлечь ответ из текста"""
    if "【参考答案】" in text:
        answer = text.split("【参考答案】")[1].split("【")[0][:100]
        return answer.strip()
    return ""

if __name__ == "__main__":
    build_gaokao_vector_db()