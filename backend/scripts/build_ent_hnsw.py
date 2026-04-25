import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pickle
import hnswlib
from sentence_transformers import SentenceTransformer

def build_ent_hnsw():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tasks_path = os.path.join(base_dir, "data", "ent", "processed", "ent_tasks.json")
    
    if not os.path.exists(tasks_path):
        print("❌ Нет файла ent_tasks.json. Сначала запустите парсер.")
        return

    with open(tasks_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    print(f"📚 Загружено {len(tasks)} задач")

    # Тексты для эмбеддингов
    texts = [f"{t.get('topic', '')} {t.get('question', '')}" for t in tasks]
    
    # Загружаем мультиязычную модель
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("🔄 Генерация эмбеддингов...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    print(f"Эмбеддинги shape: {embeddings.shape}")

    # Сохраняем векторы
    vectors_path = os.path.join(base_dir, "data", "ent", "vectors.npy")
    np.save(vectors_path, embeddings)
    print(f"✅ Векторы сохранены в {vectors_path}")

    # Создаём HNSW индекс
    dim = embeddings.shape[1]
    index = hnswlib.Index(space='cosine', dim=dim)
    index.init_index(max_elements=len(embeddings), ef_construction=200, M=16)
    index.add_items(embeddings)

    index_path = os.path.join(base_dir, "data", "ent", "index_ent.hnsw")
    index.save_index(index_path)
    print(f"✅ HNSW индекс сохранён в {index_path}")

    # Сохраняем метаданные
    metadata_path = os.path.join(base_dir, "data", "ent", "metadata_ent.pkl")
    with open(metadata_path, 'wb') as f:
        pickle.dump(tasks, f)
    print(f"✅ Метаданные сохранены в {metadata_path}")

    # Также сохраняем тексты (для отладки)
    texts_path = os.path.join(base_dir, "data", "ent", "texts.npy")
    np.save(texts_path, np.array(texts))
    
    print("\n🎉 Готово! Теперь можно использовать семантический поиск.")

if __name__ == "__main__":
    build_ent_hnsw()