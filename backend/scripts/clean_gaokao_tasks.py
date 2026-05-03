# backend/scripts/clean_gaokao_tasks.py
"""
Очищает gaokao_tasks.json:
- удаляет дубликаты по тексту вопроса
- удаляет задачи с большим количеством нечитаемых символов (мусор)
- улучшает определение темы (topic) на основе ключевых слов
- пытается извлечь ответы из текста, если их нет
"""

import json
import re
from pathlib import Path

def clean_text(text):
    """Удаляет непечатные символы, оставляет кириллицу, латиницу, цифры, пунктуацию, пробелы"""
    # Оставляем только читаемые символы
    cleaned = re.sub(r'[^\u4e00-\u9fff\u0400-\u04FFa-zA-Z0-9\s\.\,\!\?\;\:\-\"\'\(\)\[\]\{\}\<\>]', '', text)
    return cleaned

def is_garbage(text, threshold=0.3):
    """Считает долю нечитаемых символов (не из нужных диапазонов)"""
    # Подсчитываем символы, не входящие в допустимые диапазоны
    allowed = re.compile(r'[\u4e00-\u9fff\u0400-\u04FFa-zA-Z0-9\s\.\,\!\?\;\:\-\"\'\(\)\[\]\{\}\<\>]')
    total = len(text)
    if total == 0:
        return True
    good = len(allowed.findall(text))
    bad_ratio = 1 - good/total
    return bad_ratio > threshold

def detect_topic(text, subject):
    """Улучшенное определение темы на основе ключевых слов"""
    text_lower = text.lower()
    # Для математики
    if subject == "математика":
        if any(w in text_lower for w in ["集合", "交集", "并集", "补集", "元素", "子集"]):
            return "алгебра (множества)"
        elif any(w in text_lower for w in ["椭圆", "双曲线", "抛物线", "离心率", "焦点", "准线"]):
            return "геометрия (конические сечения)"
        elif any(w in text_lower for w in ["三角形", "正弦", "余弦", "正切", "余弦定理", "正弦定理"]):
            return "тригонометрия"
        elif any(w in text_lower for w in ["导数", "极值", "单调性", "切线", "积分"]):
            return "математический анализ"
        elif any(w in text_lower for w in ["概率", "统计", "列联表", "卡方", "期望", "方差"]):
            return "вероятность и статистика"
        elif any(w in text_lower for w in ["方程", "不等式", "函数", "对数", "指数"]):
            return "алгебра"
        elif any(w in text_lower for w in ["向量", "复数"]):
            return "алгебра"
    # Для физики
    elif subject == "физика":
        if any(w in text_lower for w in ["电场", "电势", "电容", "磁场", "电磁感应"]):
            return "электродинамика"
        elif any(w in text_lower for w in ["折射", "反射", "全反射", "透镜", "光线"]):
            return "оптика"
        elif any(w in text_lower for w in ["力", "加速度", "速度", "动量", "能量", "机械能"]):
            return "механика"
        elif any(w in text_lower for w in ["气体", "温度", "压强", "体积"]):
            return "термодинамика"
    # По умолчанию
    return "general"

def extract_answer_from_text(text):
    """Пытается извлечь ответ из китайского текста (форматы 【答案】, 【解析】)"""
    answer = ""
    # Поиск 【答案】 или 【答案】:
    ans_match = re.search(r'【答案】\s*([^【]+?)(?=【|$)', text)
    if ans_match:
        answer = ans_match.group(1).strip()
    else:
        # Альтернативный формат: "答案："
        ans_match2 = re.search(r'答案[：:]\s*([^\n]+)', text)
        if ans_match2:
            answer = ans_match2.group(1).strip()
    return answer

def extract_solution_from_text(text):
    """Извлекает решение из 【解析】"""
    sol_match = re.search(r'【解析】\s*([^【]+?)(?=【|$)', text)
    if sol_match:
        return sol_match.group(1).strip()
    return ""

def main():
    base_dir = Path(__file__).parent.parent
    tasks_path = base_dir / "data" / "gaokao" / "gaokao_tasks.json"
    if not tasks_path.exists():
        print("❌ Файл не найден")
        return

    with open(tasks_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    print(f"Загружено задач: {len(tasks)}")

    # Удаляем дубликаты по тексту вопроса
    unique = {}
    for t in tasks:
        q = t.get("question", "")
        # Нормализуем вопрос (удаляем лишние пробелы)
        q_norm = re.sub(r'\s+', ' ', q).strip()
        if q_norm not in unique:
            unique[q_norm] = t
    tasks_unique = list(unique.values())
    print(f"Удалено дубликатов: {len(tasks)-len(tasks_unique)}")

    # Фильтруем мусор
    filtered = []
    for t in tasks_unique:
        text = t.get("question", "") + " " + t.get("full_text", "")
        if len(text) < 30:
            continue
        if is_garbage(text):
            print(f"  Отброшена задача {t.get('id', '')} (мусор)")
            continue
        # Очищаем текст вопроса
        t["question"] = clean_text(t["question"])
        t["full_text"] = clean_text(t["full_text"])
        # Улучшаем тему
        subject = t.get("subject", "математика")
        t["topic"] = detect_topic(t["question"], subject)
        # Извлекаем ответ и решение, если их нет
        if not t.get("answer"):
            t["answer"] = extract_answer_from_text(t["full_text"])
        if not t.get("solution"):
            t["solution"] = extract_solution_from_text(t["full_text"])
        filtered.append(t)

    print(f"Удалено мусорных задач: {len(tasks_unique)-len(filtered)}")
    print(f"Осталось задач: {len(filtered)}")

    # Сохраняем очищенный JSON
    output_path = base_dir / "data" / "gaokao" / "gaokao_tasks_cleaned.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    print(f"✅ Сохранено в {output_path}")

    # Заменяем старый файл (создаём бэкап)
    backup_path = base_dir / "data" / "gaokao" / "gaokao_tasks_backup.json"
    tasks_path.rename(backup_path)
    output_path.rename(tasks_path)
    print(f"✅ Старый файл заменён, бэкап: {backup_path}")

if __name__ == "__main__":
    main()