# backend/scripts/parse_gaokao_files_v2.py
import os
import re
import json
from pathlib import Path
import pdfplumber
from docx import Document

RAW_DIR = Path(__file__).parent.parent / "data" / "gaokao" / "raw"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "gaokao" / "gaokao_tasks.json"

# Более точное определение предмета по имени файла
SUBJECT_MAP = {
    "数学": "математика",
    "math": "математика",
    "物理": "физика",
    "physics": "физика",
    "化学": "химия",
    "chemistry": "химия",
    "生物": "биология",
    "biology": "биология",
    "历史": "история",
    "history": "история",
    "地理": "география",
    "geography": "география",
    "政治": "политика",
    "politics": "политика",
    "语文": "китайский язык",
    "chinese": "китайский язык",
    "英语": "английский язык",
    "english": "английский язык"
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
    # Улучшенное разбиение: ищем номера задач (1. 1、 1． и т.д.)
    lines = text.split('\n')
    tasks = []
    current = []
    for line in lines:
        if re.match(r'^\s*(\d+)[\.\、．]\s*', line):
            if current:
                tasks.append('\n'.join(current))
                current = []
        current.append(line)
    if current:
        tasks.append('\n'.join(current))
    return tasks

def clean_text(text):
    # Удаляем непечатные символы, сохраняя иероглифы, латиницу, цифры и базовую пунктуацию
    return re.sub(r'[^\u4e00-\u9fff\u0400-\u04FFa-zA-Z0-9\s\.\,\!\?\;\:\-\"\'\(\)\[\]\{\}\<\>]', ' ', text)

def is_garbage(text, threshold=0.3):
    allowed = re.compile(r'[\u4e00-\u9fff\u0400-\u04FFa-zA-Z0-9\s\.\,\!\?\;\:\-\"\'\(\)\[\]\{\}\<\>]')
    if not text:
        return True
    total = len(text)
    good = len(allowed.findall(text))
    return (1 - good/total) > threshold

def parse_task(block, subject, source):
    if len(block) < 50:
        return None
    # Очищаем блок
    block = clean_text(block)
    if is_garbage(block):
        return None

    num_match = re.search(r'^\s*(\d+)[\.\、．]', block)
    number = int(num_match.group(1)) if num_match else 0
    question = block[:800]
    
    # Извлечение ответа
    answer = ""
    ans_match = re.search(r'【答案】\s*([^【]+?)(?=【|$)', block)
    if ans_match:
        answer = ans_match.group(1).strip()
    else:
        ans_match2 = re.search(r'答案[：:]\s*([^\n]+)', block)
        if ans_match2:
            answer = ans_match2.group(1).strip()
    
    # Извлечение решения
    solution = ""
    sol_match = re.search(r'【解析】\s*([^【]+?)(?=【|$)', block)
    if sol_match:
        solution = sol_match.group(1).strip()
    
    # Определение темы (улучшенное)
    topic = "general"
    text_lower = block.lower()
    if any(w in text_lower for w in ["集合", "交集", "元素"]):
        topic = "алгебра (множества)"
    elif any(w in text_lower for w in ["椭圆", "双曲线", "抛物线", "离心率"]):
        topic = "геометрия (конические сечения)"
    elif any(w in text_lower for w in ["三角形", "正弦", "余弦", "正切"]):
        topic = "тригонометрия"
    elif any(w in text_lower for w in ["导数", "极值", "单调性"]):
        topic = "математический анализ"
    elif any(w in text_lower for w in ["概率", "统计", "列联表"]):
        topic = "вероятность и статистика"
    elif any(w in text_lower for w in ["电场", "电势", "磁场"]):
        topic = "электродинамика"
    elif any(w in text_lower for w in ["折射", "反射", "全反射"]):
        topic = "оптика"
    elif any(w in text_lower for w in ["力", "加速度", "速度"]):
        topic = "механика"
    
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
        "solution": solution,
        "full_text": block[:1500]
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
    # Загружаем старые задачи, если есть, и объединяем (уникальные по id)
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            old = json.load(f)
            all_tasks.extend(old)
    unique = {}
    for t in all_tasks:
        unique[t["id"]] = t
    final = list(unique.values())
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено задач: {len(final)}")

if __name__ == "__main__":
    main()