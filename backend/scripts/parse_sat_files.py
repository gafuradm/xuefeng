# backend/scripts/parse_sat_files.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from docx import Document

RAW_DIR = Path(__file__).parent.parent / "data" / "sat" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "sat" / "sat_tasks.json"

def extract_text(filepath):
    """Извлечение текста из DOCX или PDF"""
    text = ""
    try:
        if filepath.suffix == ".pdf":
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        elif filepath.suffix == ".docx":
            doc = Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Ошибка при извлечении: {e}")
    return text

def clean_text(text):
    """Очистка текста от мусора"""
    # Убираем повторяющиеся пустые строки
    text = re.sub(r'\n\s*\n', '\n', text)
    # Убираем строки с номерами страниц
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    return text

def extract_options(question_text):
    """Извлекает варианты ответов A) B) C) D)"""
    options = {}
    # Ищем варианты вида "A) текст" или "A. текст"
    pattern = r'([A-D])[\.\)]\s*([^\n]+)'
    matches = re.findall(pattern, question_text)
    for letter, opt_text in matches:
        options[letter] = opt_text.strip()
    return options

def determine_difficulty(question_text):
    """Определяет сложность задачи"""
    text_len = len(question_text)
    if text_len < 300:
        return "easy"
    elif text_len > 800:
        return "hard"
    return "medium"

def determine_topic(question_text):
    """Определяет тему задачи"""
    text_lower = question_text.lower()
    if any(word in text_lower for word in ['equation', 'function', 'graph', 'solve', 'x', 'y']):
        return "алгебра"
    elif any(word in text_lower for word in ['circle', 'triangle', 'angle', 'area', 'volume', 'perimeter']):
        return "геометрия"
    elif any(word in text_lower for word in ['probability', 'average', 'median', 'mean', 'percent']):
        return "статистика и вероятность"
    elif any(word in text_lower for word in ['reading', 'passage', 'author', 'paragraph']):
        return "чтение"
    elif any(word in text_lower for word in ['grammar', 'sentence', 'tense', 'pronoun']):
        return "грамматика"
    return "general"

def parse_math_question(text, idx):
    """Парсит математический вопрос"""
    options = extract_options(text)
    
    # Очищаем текст вопроса от вариантов ответов
    question_clean = text
    for letter in ['A', 'B', 'C', 'D']:
        question_clean = re.sub(rf'{letter}[\.\)]\s*[^\n]+', '', question_clean)
    question_clean = re.sub(r'\s+', ' ', question_clean).strip()
    
    # Определяем тип вопроса
    q_type = 'multiple_choice' if options else 'grid_in'
    
    # Для grid-in вопросов ищем число в конце
    answer = ""
    if not options:
        num_match = re.search(r'(\d+(?:\.\d+)?)\s*$', question_clean)
        if num_match:
            answer = num_match.group(1)
            question_clean = re.sub(r'\s*\d+(?:\.\d+)?\s*$', '', question_clean)
    
    return {
        "id": f"sat_math_{idx}",
        "source": "sat_file",
        "number": idx,
        "subject": "математика",
        "topic": determine_topic(text),
        "difficulty": determine_difficulty(text),
        "question_type": q_type,
        "question": question_clean[:2000],
        "passage": "",
        "answer": answer,
        "options": options,
        "solution": "",
        "full_text": text[:3000]
    }

def parse_reading_question(text, idx):
    """Парсит вопрос чтения/письма"""
    # Извлекаем пассаж (текст до вопроса)
    passage = ""
    question_text = text
    
    # Ищем маркеры начала вопроса
    question_markers = ['Which choice', 'Based on the text', 'According to the text', 
                        'The student wants', 'Which finding', 'Which quotation']
    
    for marker in question_markers:
        if marker in text:
            parts = text.split(marker, 1)
            if len(parts) == 2:
                passage = parts[0].strip()
                question_text = marker + parts[1]
                break
    
    options = extract_options(question_text)
    
    # Очищаем текст вопроса от вариантов
    question_clean = question_text
    for letter in ['A', 'B', 'C', 'D']:
        question_clean = re.sub(rf'{letter}[\.\)]\s*[^\n]+', '', question_clean)
    question_clean = re.sub(r'\s+', ' ', question_clean).strip()
    
    return {
        "id": f"sat_reading_{idx}",
        "source": "sat_file",
        "number": idx,
        "subject": "чтение и письмо",
        "topic": determine_topic(text),
        "difficulty": determine_difficulty(text),
        "question_type": "multiple_choice",
        "question": question_clean[:2000],
        "passage": passage[:3000],
        "answer": "",
        "options": options,
        "solution": "",
        "full_text": text[:3000]
    }

def extract_questions_by_numbers(text):
    """Извлекает вопросы по номерам (1., 2., 3. и т.д.)"""
    lines = text.split('\n')
    questions = []
    current_q = []
    current_number = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Проверяем, начинается ли строка с номера вопроса
        match = re.match(r'^(\d+)[\.\)]?\s+(.*)', line)
        if match:
            # Сохраняем предыдущий вопрос
            if current_q and current_number is not None:
                questions.append({
                    'number': current_number,
                    'text': '\n'.join(current_q)
                })
            # Начинаем новый вопрос
            current_number = int(match.group(1))
            current_q = [match.group(2)] if match.group(2) else []
        else:
            if current_q is not None:
                current_q.append(line)
    
    # Добавляем последний вопрос
    if current_q and current_number is not None:
        questions.append({
            'number': current_number,
            'text': '\n'.join(current_q)
        })
    
    return questions

def detect_subject(filename, text_chunk):
    """Определяет предмет по содержимому"""
    filename_lower = filename.lower()
    text_lower = text_chunk.lower()
    
    # Математические маркеры
    math_markers = ['equation', 'solve for', 'graph', 'function', 'triangle', 
                    'circle', 'angle', 'perimeter', 'area', 'volume',
                    'what is the value', 'how many', 'units']
    
    # Reading/Writing маркеры
    rw_markers = ['the following text', 'passage', 'author', 'poem', 'story',
                  'which choice completes', 'main purpose', 'overall structure']
    
    math_score = sum(1 for m in math_markers if m in text_lower)
    rw_score = sum(1 for m in rw_markers if m in text_lower)
    
    if 'math' in filename_lower:
        return 'математика'
    elif 'reading' in filename_lower or 'writing' in filename_lower:
        return 'чтение и письмо'
    elif math_score > rw_score:
        return 'математика'
    else:
        return 'чтение и письмо'

def main():
    files = list(RAW_DIR.glob("*.docx")) + list(RAW_DIR.glob("*.pdf"))
    print(f"Найдено файлов: {len(files)}")
    all_tasks = []
    task_id = 0
    
    for f in files:
        print(f"\nОбработка: {f.name}")
        text = extract_text(f)
        if not text:
            print(f"  ❌ Не удалось извлечь текст")
            continue
        
        text = clean_text(text)
        
        # Разбиваем на секции по две колонки (DIRECTIONS слева)
        # Текст обычно имеет структуру: левая колонка (инструкции) + правая (вопросы)
        # Убираем строки с DIRECTIONS
        text = re.sub(r'DIRECTIONS.*?(?=\n\d+\s|\Z)', '', text, flags=re.DOTALL)
        text = re.sub(r'STOP.*?(?=\n\d+\s|\Z)', '', text, flags=re.DOTALL)
        
        questions = extract_questions_by_numbers(text)
        print(f"  Найдено вопросов: {len(questions)}")
        
        for q in questions:
            subject = detect_subject(f.name, q['text'])
            
            if subject == 'математика':
                task = parse_math_question(q['text'], q['number'])
            else:
                task = parse_reading_question(q['text'], q['number'])
            
            if task:
                task_id += 1
                task['id'] = f"sat_{task_id}"
                all_tasks.append(task)
    
    # Удаляем дубликаты по тексту вопроса
    unique = {}
    for t in all_tasks:
        key = t['question'][:150]
        if key not in unique:
            unique[key] = t
    
    final = list(unique.values())
    final.sort(key=lambda x: x.get('number', 0))
    
    # Сохраняем
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ Сохранено задач: {len(final)}")
    
    # Статистика по предметам
    math_count = len([t for t in final if t['subject'] == 'математика'])
    rw_count = len([t for t in final if t['subject'] == 'чтение и письмо'])
    print(f"   Математика: {math_count}")
    print(f"   Чтение/письмо: {rw_count}")
    
    # Статистика по типам
    mc_count = len([t for t in final if t.get('question_type') == 'multiple_choice'])
    gi_count = len([t for t in final if t.get('question_type') == 'grid_in'])
    print(f"   Multiple choice: {mc_count}")
    print(f"   Grid-in: {gi_count}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()