# backend/scripts/parse_india_files.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from docx import Document

RAW_DIR = Path(__file__).parent.parent / "data" / "india" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "india" / "india_tasks.json"

SUBJECT_MAP = {
    "math": "математика",
    "physics": "физика",
    "chemistry": "химия",
    "biology": "биология",
    "jee": "математика",
    "neet": "биология"
}

def detect_subject(filename):
    name = filename.lower()
    for key, subj in SUBJECT_MAP.items():
        if key in name:
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
    ans_match = re.search(r'answer[:\s]*([A-D]|\d+)', block, re.IGNORECASE)
    if ans_match:
        answer = ans_match.group(1)
    topic = "general"
    # Примерная тематика (можно донастроить под свои файлы)
    if any(k in block.lower() for k in ["complex", "quadratic", "matrix", "probability"]):
        topic = "алгебра"
    elif any(k in block.lower() for k in ["trigonometric", "sin", "cos", "tan"]):
        topic = "тригонометрия"
    elif any(k in block.lower() for k in ["limit", "derivative", "integral"]):
        topic = "исчисление"
    elif any(k in block.lower() for k in ["kinematics", "force", "energy"]):
        topic = "механика"
    elif any(k in block.lower() for k in ["cell", "gene", "dna"]):
        topic = "биология"
    difficulty = "medium"
    if len(block) < 200:
        difficulty = "easy"
    elif len(block) > 600:
        difficulty = "hard"
    return {
        "id": f"india_{subject}_{number}_{source[:10]}",
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
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            old = json.load(f)
            all_tasks.extend(old)
    unique = {t["id"]: t for t in all_tasks}
    final = list(unique.values())
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено задач: {len(final)}")

if __name__ == "__main__":
    main()