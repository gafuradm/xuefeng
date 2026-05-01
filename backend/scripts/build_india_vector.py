# backend/scripts/build_india_vector.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
import pickle
import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path

def build_india_vector_db():
    base_dir = Path(__file__).parent.parent
    tasks_path = base_dir / "data" / "india" / "india_tasks.json"
    if not tasks_path.exists():
        print("❌ Файл india_tasks.json не найден. Сначала запустите парсер.")
        return

    with open(tasks_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    print(f"📚 Загружено {len(tasks)} задач India")

    texts = [f"{t.get('subject', '')} {t.get('topic', '')} {t.get('question', '')}" for t in tasks]
    
    print("🔄 Генерация эмбеддингов...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    print(f"Эмбеддинги shape: {embeddings.shape}")

    vectors_dir = base_dir / "data" / "vector_stores" / "india"
    vectors_dir.mkdir(parents=True, exist_ok=True)
    vectors_path = vectors_dir / "vectors.npy"
    np.save(vectors_path, embeddings)
    print(f"✅ Векторы сохранены: {vectors_path}")

    dim = embeddings.shape[1]
    index = hnswlib.Index(space='cosine', dim=dim)
    index.init_index(max_elements=len(embeddings), ef_construction=200, M=16)
    index.add_items(embeddings)

    index_path = vectors_dir / "index.hnsw"
    index.save_index(str(index_path))
    print(f"✅ HNSW индекс сохранён: {index_path}")

    metadata_path = vectors_dir / "metadata.pkl"
    with open(metadata_path, 'wb') as f:
        pickle.dump(tasks, f)
    print(f"✅ Метаданные сохранены: {metadata_path}")

    print("\n🎉 ВЕКТОРНАЯ БАЗА INDIA ГОТОВА!")
    print(f"   Всего задач: {len(tasks)}")
    print(f"   Размерность: {dim}")

if __name__ == "__main__":
    build_india_vector_db()