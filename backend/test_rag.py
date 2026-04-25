# backend/test_rag.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from app.rag.vector_store import VectorStore

def test_rag():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chunks_path = os.path.join(base_dir, "data", "gaokao", "chunks.npy")
    
    print("1. Загружаем данные...")
    chunks = np.load(chunks_path, allow_pickle=True)
    print(f"   Всего задач: {len(chunks)}")
    
    print("\n2. Создаём хранилище...")
    store = VectorStore()
    store.load_gaokao_data(chunks_path, None, None)
    
    print("\n3. Проверяем метаданные...")
    metadata = store.active_stores['gaokao']['metadata']
    print(f"   Метаданных: {len(metadata)}")
    
    print("\n4. Показываем первую задачу:")
    first = metadata[0]
    print(f"   Тема: {first.get('topic')}")
    print(f"   Текст: {first.get('text')[:200]}...")
    
    print("\n5. Ищем задачи по слову 'тригонометрия'...")
    results = store.search_similar('gaokao', 'тригонометрия', k=3)
    
    print(f"   Найдено: {len(results)}")
    for i, r in enumerate(results):
        print(f"\n   Результат {i+1}:")
        print(f"   Тема: {r.get('topic')}")
        print(f"   Текст: {r.get('text')[:150]}...")
        print(f"   Похожесть: {r.get('similarity', 'N/A')}")

if __name__ == "__main__":
    test_rag()