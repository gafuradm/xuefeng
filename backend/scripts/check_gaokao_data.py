# backend/scripts/check_gaokao_data.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

def check_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunks_path = os.path.join(base_dir, "data", "gaokao", "chunks.npy")
    index_path = os.path.join(base_dir, "data", "gaokao", "index.hnsw")
    
    print("Проверка файлов:")
    print(f"chunks.npy существует: {os.path.exists(chunks_path)}")
    print(f"index.hnsw существует: {os.path.exists(index_path)}")
    
    if os.path.exists(chunks_path):
        chunks = np.load(chunks_path, allow_pickle=True)
        print(f"\nРазмер chunks: {chunks.shape}")
        print(f"Тип данных: {chunks.dtype}")
        
        if len(chunks.shape) == 2:
            print(f"Количество векторов: {chunks.shape[0]}")
            print(f"Размерность вектора: {chunks.shape[1]}")
        
        print(f"\nПервые 3 вектора (первые 10 значений):")
        for i in range(min(3, len(chunks))):
            vec = chunks[i]
            if isinstance(vec, np.ndarray):
                print(f"  Вектор {i}: {vec[:10]}")
            else:
                print(f"  Вектор {i}: {vec}")
    
    if os.path.exists(index_path):
        try:
            import hnswlib
            # Сначала загружаем векторы чтобы узнать размерность
            if os.path.exists(chunks_path):
                chunks = np.load(chunks_path, allow_pickle=True)
                if len(chunks.shape) == 2:
                    dim = chunks.shape[1]
                else:
                    dim = 384
            else:
                dim = 384
            
            index = hnswlib.Index(space='cosine', dim=dim)
            index.load_index(index_path)
            print(f"\nИндекс HNSW загружен")
            print(f"Элементов в индексе: {index.get_current_count()}")
        except Exception as e:
            print(f"\nОшибка загрузки индекса: {e}")
    
    print("\n✅ Проверка завершена")

if __name__ == "__main__":
    check_data()