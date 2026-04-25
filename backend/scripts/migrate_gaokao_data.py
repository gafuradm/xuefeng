# backend/scripts/migrate_gaokao_data.py
import sys
import os

# Добавляем путь к корневой директории
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Теперь можно импортировать
from app.rag import VectorStore, ExamManager

def migrate():
    # Указываем пути к вашим файлам (относительно backend)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunks_path = os.path.join(base_dir, "data", "gaokao", "chunks.npy")
    index_path = os.path.join(base_dir, "data", "gaokao", "index.hnsw")
    
    print(f"Загрузка из:")
    print(f"  chunks: {chunks_path}")
    print(f"  index: {index_path}")
    
    if not os.path.exists(chunks_path):
        print(f"❌ Файл не найден: {chunks_path}")
        return
    
    if not os.path.exists(index_path):
        print(f"❌ Файл не найден: {index_path}")
        return
    
    # Создаём хранилище
    vector_store_path = os.path.join(base_dir, "data", "vector_stores")
    vector_store = VectorStore(vector_store_path)
    exam_manager = ExamManager(vector_store)
    
    # Загружаем существующие данные
    store = exam_manager.init_gaokao(chunks_path, index_path)
    
    print(f"✅ Данные гаокао загружены успешно!")
    print(f"   Всего векторов: {len(store['vectors'])}")
    print(f"   Размерность: {store['dim']}")
    
    # Сохраняем в новом формате
    vector_store.active_stores['gaokao'] = store
    
    # Создаем метаданные если их нет
    if not store['metadata']:
        print("\n⚠️ Метаданные не найдены. Создаем пустые...")
        metadata = []
        for i in range(len(store['vectors'])):
            metadata.append({
                'id': f"gaokao_{i}",
                'exam_type': 'gaokao',
                'year': 2023,
                'topic': 'unknown',
                'difficulty': 'medium',
                'text': f"Задача из архива #{i}",
                'solution': '',
                'answer': '',
                'score': 0,
                'metadata': {}
            })
        
        store['metadata'] = metadata
        
        # Сохраняем метаданные
        metadata_path = os.path.join(base_dir, "data", "gaokao", "metadata.pkl")
        import pickle
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        print(f"✅ Создано {len(metadata)} записей метаданных")
    
    print("\n✅ Миграция завершена!")

if __name__ == "__main__":
    migrate()