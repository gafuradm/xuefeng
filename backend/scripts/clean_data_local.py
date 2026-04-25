# scripts/clean_data_local.py
import numpy as np
import re
import os

def clean_gaokao_text():
    """Бесплатная очистка текста регулярными выражениями"""
    
    chunks_path = "data/gaokao/chunks.npy"
    texts = np.load(chunks_path, allow_pickle=True)
    
    cleaned = []
    for text in texts:
        if not isinstance(text, str):
            text = str(text)
        
        # Удаляем рекламу
        text = re.sub(r'【.*?淘.*?宝.*?】', '', text)
        text = re.sub(r'【.*?学.*?霸.*?】', '', text)
        text = re.sub(r'\(网络收集\)', '', text)
        
        # Убираем лишние пробелы между иероглифами
        text = re.sub(r'(?<=[\u4e00-\u9fff]) +(?=[\u4e00-\u9fff])', '', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        cleaned.append(text.strip())
    
    # Сохраняем очищенную версию
    np.save("data/gaokao/chunks_clean.npy", cleaned)
    print(f"Очищено {len(cleaned)} задач")

if __name__ == "__main__":
    clean_gaokao_text()