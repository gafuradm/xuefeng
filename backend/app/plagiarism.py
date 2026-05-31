import hashlib
import re
from collections import defaultdict
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from .models import PlagiarismCorpus, TextReview

def get_shingles(text: str, k: int = 9) -> List[int]:
    """Разбивает текст на шинглы (k символов) и возвращает список их хешей (int)."""
    text = re.sub(r'\s+', ' ', text).lower()
    shingles = set()
    for i in range(len(text) - k + 1):
        shingle = text[i:i+k]
        hash_val = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
        shingles.add(hash_val)
    return list(shingles)

def compute_similarity(shingles1: List[int], shingles2: List[int]) -> float:
    """Коэффициент Жаккара между двумя наборами шинглов."""
    set1 = set(shingles1)
    set2 = set(shingles2)
    if not set1 or not set2:
        return 0.0
    intersect = len(set1 & set2)
    union = len(set1 | set2)
    return intersect / union if union > 0 else 0.0

def find_similar_fragments(text: str, all_texts: List[Dict]) -> List[Dict]:
    """
    Упрощённый поиск похожих фрагментов: разбиваем исходный текст на предложения
    и ищем их вхождение в другие тексты.
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    similar = []
    for s in sentences:
        for other in all_texts:
            if s in other['text']:
                similar.append({
                    "text": s,
                    "source_user_id": other.get('user_id'),
                    "source_title": other.get('title'),
                    "similarity": 0.9  # примерное значение
                })
                break
    return similar[:10]  # не более 10 фрагментов

def check_plagiarism(db: Session, user_id: int, title: str, text: str) -> Tuple[float, List[Dict]]:
    """
    Проверяет текст на плагиат:
    - Сравнивает с ранее проверенными работами (TextReview) и с корпусом PlagiarismCorpus.
    - Возвращает процент уникальности и список похожих фрагментов.
    - Сохраняет шинглы текущего текста в корпус для будущих сравнений.
    """
    # 1. Генерируем шинглы для текущего текста
    current_shingles = get_shingles(text)
    
    # 2. Собираем шинглы из корпуса (для ускорения)
    #    Загружаем все записи из PlagiarismCorpus
    corpus_entries = db.query(PlagiarismCorpus).filter(PlagiarismCorpus.user_id != user_id).all()
    
    similarities = []
    
    # Сравниваем с каждым документом в корпусе по сохранённым шинглам
    for entry in corpus_entries:
        if entry.shingles:
            sim = compute_similarity(current_shingles, entry.shingles)
            if sim > 0.05:
                similarities.append({
                    "source_user_id": entry.user_id,
                    "source_title": f"Корпус #{entry.id}",
                    "similarity": sim,
                    "text_excerpt": f"(шинглы из корпуса, хеш: {entry.text_hash[:16]}...)"
                })
    
    # 3. Также сравниваем с предыдущими рецензиями (TextReview) – на лету
    previous_reviews = db.query(TextReview).filter(TextReview.user_id != user_id).all()
    for rev in previous_reviews:
        rev_shingles = get_shingles(rev.text)
        sim = compute_similarity(current_shingles, rev_shingles)
        if sim > 0.05:
            similarities.append({
                "source_user_id": rev.user_id,
                "source_title": rev.title,
                "similarity": sim,
                "text_excerpt": rev.text[:200]
            })
    
    # 4. Вычисляем уникальность как 1 - максимальная схожесть
    max_sim = max([s["similarity"] for s in similarities]) if similarities else 0.0
    uniqueness = max(0.0, (1.0 - max_sim) * 100)
    
    # 5. Находим похожие фрагменты (расширенный поиск)
    similar_parts = find_similar_fragments(
        text,
        [{"text": r.text, "user_id": r.user_id, "title": r.title} for r in previous_reviews]
    )
    
    # 6. СОХРАНЯЕМ ШИНГЛЫ ТЕКУЩЕГО ТЕКСТА В КОРПУС
    text_hash = hashlib.md5(text.encode()).hexdigest()
    existing = db.query(PlagiarismCorpus).filter(PlagiarismCorpus.text_hash == text_hash).first()
    if not existing:
        corpus_entry = PlagiarismCorpus(
            user_id=user_id,
            text_hash=text_hash,
            shingles=current_shingles
        )
        db.add(corpus_entry)
        db.commit()
        print(f"[PLAGIARISM] Сохранены шинглы для текста с хешем {text_hash[:16]}, {len(current_shingles)} шинглов")
    
    return uniqueness, similar_parts