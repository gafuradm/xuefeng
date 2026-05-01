# backend/scripts/parse_gaokao_files.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from docx import Document

RAW_DIR = Path(__file__).parent.parent / "data" / "gaokao" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "gaokao" / "gaokao_tasks.json"

# Сопоставление ключевых слов в имени файла с предметом (можно дополнить)
SUBJECT_MAP = {
    "语文": "китайский язык",
    "数学": "математика",
    "英语": "английский язык",
    "物理": "физика",
    "化学": "химия",
    "生物": "биология",
    "历史": "история",
    "地理": "география",
    "政治": "политика"
}

def detect_subject(filename):
    for key, subj in SUBJECT_MAP.items():
        if key in filename:
            return subj
    return "математика"

def extract_text(filepath):
    if filepath.suffix == ".pdf":
        text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except:
            pass
        return text
    elif filepath.suffix == ".docx":
        try:
            doc = Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        except:
            return ""
    return ""

def split_tasks(text):
    # Простой split по номерам (можно улучшить под структуру GAOKAO)
    lines = text.split('\n')
    tasks = []
    current = []
    for line in lines:
        if re.match(r'^\s*\d+\.', line):
            if current:
                tasks.append('\n'.join(current))
                current = []
        current.append(line)
    if current:
        tasks.append('\n'.join(current))
    return tasks

def parse_task(block, subject, source):
    if len(block) < 50:
        return None
    num_match = re.search(r'^\s*(\d+)\.', block)
    number = int(num_match.group(1)) if num_match else 0
    question = block[:800]
    answer = ""
    # Пытаемся найти ответ (может быть "答案" или "参考答案")
    ans_match = re.search(r'答案[：:]\s*(\w+)', block)
    if ans_match:
        answer = ans_match.group(1)
    topic = "general"
    # Простое определение темы по ключевым словам (можно расширить)
    if "函数" in block: topic = "функции"
    elif "几何" in block: topic = "геометрия"
    elif "三角" in block: topic = "тригонометрия"
    elif "概率" in block: topic = "вероятность"
    elif "文言" in block: topic = "древняя литература"
    difficulty = "medium"
    if len(block) < 200:
        difficulty = "easy"
    elif len(block) > 600:
        difficulty = "hard"
    return {
        "id": f"gaokao_{subject}_{number}_{source[:10]}",
        "source": source,
        "number": number,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "solution": "",
        "full_text": block
    }

def main():
    files = list(RAW_DIR.glob("*.pdf")) + list(RAW_DIR.glob("*.docx"))
    print(f"Найдено файлов: {len(files)}")
    all_tasks = []
    for f in files:
        print(f"Обработка: {f.name}")
        subject = detect_subject(f.name)
        text = extract_text(f)
        if not text:
            print(f"  Не удалось извлечь текст")
            continue
        blocks = split_tasks(text)
        print(f"  Найдено блоков: {len(blocks)}")
        for block in blocks:
            task = parse_task(block, subject, f.name)
            if task:
                all_tasks.append(task)
    # Если файл уже существовал, объединяем
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            old = json.load(f)
            all_tasks.extend(old)
    # Удаляем дубликаты по id
    unique = {}
    for t in all_tasks:
        unique[t["id"]] = t
    final = list(unique.values())
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено задач: {len(final)}")

if __name__ == "__main__":
    main()