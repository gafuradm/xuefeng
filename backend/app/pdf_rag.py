import os
import uuid
import json
import pickle
from typing import List
import pypdf
import easyocr
import numpy as np
import cv2
import pypdfium2 as pdfium
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    return _ocr_reader

def preprocess_image(img_np):
    """Улучшает изображение для OCR"""
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    # Увеличение размера для лучшего распознавания мелких деталей
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    # Адаптивная бинаризация
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # Медианный фильтр для удаления шума
    denoised = cv2.medianBlur(binary, 3)
    return denoised

def extract_text_from_pdf(pdf_path: str) -> str:
    # 1. Пытаемся извлечь текст напрямую (для текстовых PDF)
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if text.strip():
            print(f"[PDF RAG] Текстовый PDF, извлечено {len(text)} символов.")
            return text
    except Exception as e:
        print(f"[PDF RAG] Ошибка pypdf: {e}")
    
    # 2. Если не получилось – используем OCR через pypdfium2
    print("[PDF RAG] Текст не найден, запускаем OCR с предобработкой...")
    pdf = pdfium.PdfDocument(pdf_path)
    reader = get_ocr_reader()
    full_text = ""
    for i in range(len(pdf)):
        page = pdf[i]
        # Рендерим страницу с масштабированием 2x (повышает качество)
        bitmap = page.render(scale=2)
        img_np = np.array(bitmap.to_pil())
        processed = preprocess_image(img_np)
        result = reader.readtext(processed, detail=0, paragraph=True, width_ths=0.7, height_ths=0.7)
        page_text = " ".join(result)
        full_text += page_text + "\n"
        print(f"[PDF RAG] Страница {i+1}: распознано {len(page_text)} символов.")
        # Если результат пустой, пробуем оригинал без предобработки
        if len(page_text) < 50:
            result2 = reader.readtext(np.array(bitmap.to_pil()), detail=0, paragraph=True)
            page_text2 = " ".join(result2)
            if len(page_text2) > len(page_text):
                full_text = full_text[:-len(page_text)-1] + page_text2 + "\n"
                print(f"[PDF RAG] Страница {i+1}: повторная попытка дала {len(page_text2)} символов.")
    print(f"[PDF RAG] Всего извлечено {len(full_text)} символов.")
    return full_text

def split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i+chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    print(f"[PDF RAG] Текст разбит на {len(chunks)} фрагментов.")
    return chunks

def create_tfidf_index(chunks: List[str]):
    if not chunks:
        raise ValueError("Нет фрагментов для индексации")
    vectorizer = TfidfVectorizer(lowercase=True, stop_words=None)
    tfidf_matrix = vectorizer.fit_transform(chunks)
    base_path = f"/tmp/tfidf_{uuid.uuid4().hex}"
    vec_path = base_path + "_vectorizer.pkl"
    mat_path = base_path + "_matrix.npy"
    chk_path = base_path + "_chunks.json"
    with open(vec_path, "wb") as f:
        pickle.dump(vectorizer, f)
    np.save(mat_path, tfidf_matrix.toarray())
    with open(chk_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    return vec_path, mat_path, chk_path

def search_tfidf_index(vectorizer_path: str, matrix_path: str, chunks_path: str, query: str, k: int = 3) -> List[str]:
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)
    tfidf_matrix = np.load(matrix_path)
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(similarities)[-k:][::-1]
    results = []
    for idx in top_indices:
        if similarities[idx] > 0:
            results.append(chunks[idx])
    return results