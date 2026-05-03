# backend/scripts/parse_ege_improved.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from docx import Document

RAW_DIR = Path(__file__).parent.parent / "data" / "ege" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "ege" / "ege_tasks.json"

def extract_text_from_pdf(filepath):
    """Улучшенное извлечение текста из PDF"""
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                # Пробуем извлечь таблицы (часто содержат задачи)
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell) for cell in row if cell])
                        if row_text:
                            text += row_text + "\n"
    except Exception as e:
        print(f"  Ошибка PDF: {e}")
    return text

def extract_text_from_docx(filepath):
    try:
        doc = Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return ""

def split_into_tasks(text):
    """Разбивает текст на отдельные задачи"""
    lines = text.split('\n')
    tasks = []
    current_task = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Признак начала задачи: номер с точкой или скобкой
        if re.match(r'^(\d+)[\.\)]', line) or re.match(r'^Задание\s*\d+', line):
            if current_task:
                tasks.append('\n'.join(current_task))
                current_task = []
        current_task.append(line)
    
    if current_task:
        tasks.append('\n'.join(current_task))
    
    return tasks

def is_real_task(block):
    """Проверяет, похож ли блок на реальную задачу, а не на инструкцию"""
    if len(block) < 80:
        return False
    
    # Исключаем инструкции
    if re.search(r'Инструкция|Экзаменационная работа|Часть \d|Открытый вариант', block[:200]):
        return False
    
    # Должны быть цифры или математические символы
    if not re.search(r'\d', block):
        return False
    
    # Для математики: должны быть цифры или операторы
    if re.search(r'[+\-=×÷]', block):
        return True
    
    # Для текстовых предметов: должны быть вопросы
    if re.search(r'[?？]', block):
        return True
    
    # Для языка: должны быть варианты ответов (A, B, C, D)
    if re.search(r'[A-D][\.\)]', block):
        return True
    
    return False

def extract_answer(block):
    """Пытается извлечь ответ из текста"""
    patterns = [
        r'Ответ[:\s]*([A-D]|\d+|[-\d.]+)',
        r'ответ[:\s]*([A-D]|\d+|[-\d.]+)',
        r'Правильный ответ[:\s]*([A-D]|\d+|[-\d.]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""

def detect_subject(filename):
    """Определяет предмет по имени файла"""
    name = filename.lower()
    if "математик" in name or "math" in name:
        return "математика"
    if "физик" in name or "physics" in name:
        return "физика"
    if "хими" in name or "chemistry" in name:
        return "химия"
    if "биологи" in name or "biology" in name:
        return "биология"
    if "история" in name or "history" in name:
        return "история"
    if "обществ" in name or "society" in name:
        return "обществознание"
    if "географ" in name or "geography" in name:
        return "география"
    if "информатика" in name or "informatics" in name:
        return "информатика"
    if "литератур" in name or "literature" in name:
        return "литература"
    if "английск" in name or "english" in name:
        return "английский язык"
    if "русский" in name:
        return "русский язык"
    return "математика"

def detect_topic(block, subject):
    """Определяет тему задачи"""
    block_lower = block.lower()
    # Для математики
    if subject == "математика":
        if any(w in block_lower for w in ["уравнени", "неравенств"]):
            return "алгебра"
        if any(w in block_lower for w in ["функци", "график"]):
            return "функции"
        if any(w in block_lower for w in ["геометри", "треугольник", "окружност", "плоскост"]):
            return "геометрия"
        if any(w in block_lower for w in ["вероятност", "статистик"]):
            return "вероятность и статистика"
        if any(w in block_lower for w in ["производн", "интеграл"]):
            return "математический анализ"
    return "general"

def parse_task(block, subject, source):
    number_match = re.search(r'^(\d+)[\.\)]', block)
    number = int(number_match.group(1)) if number_match else 0
    
    # Очищаем вопрос
    question = block[:1500]
    
    # Извлекаем варианты ответов (для тестов)
    options = re.findall(r'([A-D])[\.\)]\s*([^\n]+)', block)
    options_dict = {opt[0]: opt[1].strip() for opt in options}
    
    # Извлекаем ответ
    answer = extract_answer(block)
    
    # Определяем сложность
    difficulty = "medium"
    if len(block) < 300:
        difficulty = "easy"
    elif len(block) > 800:
        difficulty = "hard"
    
    # Определяем тему
    topic = detect_topic(block, subject)
    
    return {
        "id": f"ege_{subject}_{number}_{source[:15]}",
        "source": source,
        "number": number,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "options": options_dict,
        "solution": "",
        "full_text": block[:2000]
    }

def main():
    files = list(RAW_DIR.glob("*.pdf")) + list(RAW_DIR.glob("*.docx"))
    print(f"📁 Найдено файлов: {len(files)}")
    all_tasks = []
    
    for filepath in files:
        print(f"\n📄 Обработка: {filepath.name}")
        subject = detect_subject(filepath.name)
        
        if filepath.suffix == ".pdf":
            text = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_docx(filepath)
        
        if not text:
            print(f"   ⚠️ Не удалось извлечь текст")
            continue
        
        blocks = split_into_tasks(text)
        print(f"   📝 Найдено блоков: {len(blocks)}")
        
        tasks_in_file = 0
        for block in blocks:
            if not is_real_task(block):
                continue
            task = parse_task(block, subject, filepath.name)
            if task:
                all_tasks.append(task)
                tasks_in_file += 1
        
        print(f"   ✅ Извлечено задач: {tasks_in_file}")
    
    # Удаляем дубликаты по тексту вопроса
    unique = {}
    for t in all_tasks:
        q = t.get("question", "")[:200]
        if q not in unique:
            unique[q] = t
    
    final = list(unique.values())
    print(f"\n📊 Всего извлечено задач: {len(final)}")
    
    # Сохраняем
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено в {OUTPUT_JSON}")

if __name__ == "__main__":
    main()