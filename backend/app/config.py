import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Основные настройки
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_teacher.db")
    
    # RAG настройки (ЕНТ)
    VECTOR_STORE_PATH: str = "data/vector_stores"
    ENT_VECTOR_STORE_PATH: str = "data/vector_stores/ent"
    ENT_CHUNKS_PATH: str = "data/ent/processed/chunks.npy"
    ENT_INDEX_PATH: str = "data/vector_stores/ent/index.hnsw"
    ENT_METADATA_PATH: str = "data/vector_stores/ent/metadata.pkl"
    
    # Если нужно сохранить старые пути (можно удалить)
    # GAOKAO_* больше не используются

settings = Settings()