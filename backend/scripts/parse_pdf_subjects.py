# backend/scripts/parse_pdf_subjects.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from typing import List, Dict

# Папка с PDF-файлами
RAW_DIR = Path(__file__).parent.parent / "data" / "ent" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "ent" / "ent_tasks.json"

# Предметы по именам файлов (можно расширить)
SUBJECT_KEYWORDS = {
    "физика": "физика",
    "математика": "математика",
    "химия": "химия",
    "биология": "биология",
    "история": "история казахстана",
    "всемирная": "всемирная история",
    "английский": "английский язык",
    "русский": "русский язык",
    "казахский": "казахский язык",
    "география": "география"
}

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Извлечение текста из PDF (с возможными искажениями формул)"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Ошибка при чтении {pdf_path.name}: {e}")
    return text

def split_into_tasks(text: str) -> List[str]:
    """Пытаемся разбить текст на отдельные задачи по номерам"""
    # Ищем паттерны типа "1.", "2)", "№ 1" и т.д.
    # Простой вариант: разбиваем по строкам, начинающимся с цифры и точки/скобки
    lines = text.split('\n')
    tasks = []
    current_task = []
    for line in lines:
        if re.match(r'^\s*\d+[\.\)\-]', line):
            if current_task:
                tasks.append('\n'.join(current_task))
                current_task = []
        current_task.append(line)
    if current_task:
        tasks.append('\n'.join(current_task))
    return tasks

def detect_subject(filename: str) -> str:
    """Определить предмет по имени файла"""
    name_lower = filename.lower()
    for key, subject in SUBJECT_KEYWORDS.items():
        if key in name_lower:
            return subject
    return "математика"  # по умолчанию

def parse_task_block(block: str, subject: str, source_file: str) -> Dict:
    """Извлекаем из блока вопрос, ответ (если есть) и т.д."""
    # Очистим от лишних пробелов
    block = block.strip()
    if len(block) < 50:
        return None
    
    # Ищем номер задачи
    num_match = re.search(r'^\s*(\d+)[\.\)\-]', block)
    number = int(num_match.group(1)) if num_match else 0
    
    # Ищем варианты ответов (A) ... B) ...)
    options = {}
    opt_pattern = r'([A-D])[\.\)]\s*([^\n]+)'
    for match in re.finditer(opt_pattern, block):
        options[match.group(1)] = match.group(2).strip()
    
    # Вопрос – всё, что до первого варианта или до конца
    question = block
    if options:
        first_opt = min([block.find(f"{l})") for l in options.keys() if f"{l})" in block] + [len(block)])
        question = block[:first_opt].strip()
    else:
        # Обрезаем по словам "Ответ:" или "Решение:"
        cut_pos = re.search(r'(Ответ|Решение|Объяснение)', question)
        if cut_pos:
            question = question[:cut_pos.start()].strip()
    
    # Ответ
    answer_match = re.search(r'Ответ[:\s]*([A-D]|\d+|[-0-9.]+)', block, re.IGNORECASE)
    answer = answer_match.group(1) if answer_match else ""
    
    # Решение (если есть)
    sol_match = re.search(r'(?:Решение|Объяснение|Разбор)[:\s]*(.+?)(?=\n\n|\Z)', block, re.DOTALL | re.IGNORECASE)
    solution = sol_match.group(1).strip() if sol_match else ""
    
    # Определяем тему (можно упрощённо – из контекста)
    topic = "general"
    if "кинематик" in block.lower(): topic = "кинематика"
    elif "динамик" in block.lower(): topic = "динамика"
    # можно добавить другие ключевые слова
    
    # Сложность (грубая)
    difficulty = "medium"
    if len(block) < 300:
        difficulty = "easy"
    elif len(block) > 800:
        difficulty = "hard"
    
    return {
        "id": f"{subject}_{number}_{source_file[:10]}",
        "source_file": source_file,
        "number": number,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "question": question[:2000],
        "options": options,
        "answer": answer,
        "solution": solution[:1000],
        "full_text": block[:2000]
    }

def main():
    pdf_files = list(RAW_DIR.glob("*.pdf"))
    print(f"Найдено PDF-файлов: {len(pdf_files)}")
    
    all_tasks = []
    # Если уже есть старый JSON, загрузим чтобы добавить новые задачи
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            all_tasks = existing
            print(f"Загружено существующих задач: {len(all_tasks)}")
    
    for pdf_path in pdf_files:
        print(f"\nОбработка: {pdf_path.name}")
        subject = detect_subject(pdf_path.name)
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("   Не удалось извлечь текст")
            continue
        blocks = split_into_tasks(text)
        print(f"   Найдено блоков: {len(blocks)}")
        for block in blocks:
            task = parse_task_block(block, subject, pdf_path.name)
            if task:
                all_tasks.append(task)
    
    # Сохраняем
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Всего задач в базе: {len(all_tasks)}")
    print(f"✅ Сохранено в {OUTPUT_JSON}")

if __name__ == "__main__":
    main()