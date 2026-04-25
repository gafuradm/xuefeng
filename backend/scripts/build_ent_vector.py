# backend/scripts/build_ent_vector.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pickle
import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path

def build_vector_db():
    base_dir = Path(__file__).parent.parent
    processed_dir = base_dir / "data" / "ent" / "processed"
    vectors_dir = base_dir / "data" / "vector_stores" / "ent"
    vectors_dir.mkdir(parents=True, exist_ok=True)
    
    chunks_path = processed_dir / "chunks.npy"
    if not chunks_path.exists():
        print("❌ Нет файла chunks.npy. Сначала запустите парсер.")
        return
    
    texts = np.load(chunks_path, allow_pickle=True)
    print(f"📚 Загружено {len(texts)} текстов")
    
    print("🔄 Генерация эмбеддингов...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(texts.tolist(), show_progress_bar=True)
    
    vectors_path = vectors_dir / "vectors.npy"
    np.save(vectors_path, embeddings)
    print(f"✅ Векторы сохранены: {vectors_path}")
    
    print("🔨 Создание HNSW индекса...")
    dim = embeddings.shape[1]
    index = hnswlib.Index(space='cosine', dim=dim)
    index.init_index(max_elements=len(embeddings), ef_construction=200, M=16)
    index.add_items(embeddings)
    
    index_path = vectors_dir / "index.hnsw"
    index.save_index(str(index_path))
    print(f"✅ Индекс сохранён: {index_path}")
    
    metadata_path = processed_dir / "metadata.pkl"
    if metadata_path.exists():
        import shutil
        shutil.copy2(metadata_path, vectors_dir / "metadata.pkl")
        print(f"✅ Метаданные скопированы")
    
    print("\n🎉 ВЕКТОРНАЯ БАЗА ЕНТ ГОТОВА!")
    print(f"   Всего задач: {len(texts)}")
    print(f"   Размерность: {dim}")

if __name__ == "__main__":
    build_vector_db()