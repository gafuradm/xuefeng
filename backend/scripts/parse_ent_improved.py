#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный парсер ЕНТ
- Поддержка .doc через catdoc
- Лучшее распознавание задач (нумерованные списки, варианты ответов)
- Предобработка текста
"""

import os
import re
import json
import pickle
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import Counter

# Импорт для PDF
try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

# Импорт для DOCX
try:
    from docx import Document
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False


class ENTImprovedParser:
    def __init__(self, raw_dir="data/ent/raw", output_dir="data/ent/processed"):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_tasks = []
        self.errors = []

    def extract_text_from_doc(self, filepath: Path) -> str:
        """Извлечение текста из старого .doc через catdoc"""
        try:
            result = subprocess.run(
                ['catdoc', '-w', str(filepath)],  # -w для сохранения пробелов
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except FileNotFoundError:
            self.errors.append("catdoc not installed. Run: brew install catdoc")
        except Exception as e:
            self.errors.append(f"catdoc error {filepath.name}: {e}")
        return ""

    def extract_text_from_pdf(self, filepath: Path) -> str:
        if not PDF_AVAILABLE:
            return ""
        text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.errors.append(f"PDF error {filepath.name}: {e}")
        return text

    def extract_text_from_docx(self, filepath: Path) -> str:
        if not DOCX_AVAILABLE:
            return ""
        try:
            doc = Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            self.errors.append(f"DOCX error {filepath.name}: {e}")
            return ""

    def extract_text_from_txt(self, filepath: Path) -> str:
        encodings = ['utf-8', 'cp1251', 'utf-16', 'latin-1']
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return f.read()
            except:
                continue
        return ""

    def parse_file(self, filepath: Path) -> List[Dict]:
        ext = filepath.suffix.lower()
        text = ""

        if ext == '.pdf':
            text = self.extract_text_from_pdf(filepath)
        elif ext == '.docx':
            text = self.extract_text_from_docx(filepath)
        elif ext == '.doc':
            text = self.extract_text_from_doc(filepath)
        elif ext == '.txt':
            text = self.extract_text_from_txt(filepath)
        else:
            return []

        if not text:
            return []

        # Предобработка текста
        text = self.preprocess_text(text)

        # Разбиваем на задачи
        blocks = self.split_into_tasks(text)
        
        tasks = []
        for block in blocks:
            task = self.parse_task_block(block, filepath.name)
            if task:
                tasks.append(task)
        return tasks

    def preprocess_text(self, text: str) -> str:
        """Очистка и нормализация текста"""
        # Заменяем множественные переводы строк
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Убираем лишние пробелы
        text = re.sub(r' +', ' ', text)
        # Убираем разрывы слов (переносы)
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        return text

    def split_into_tasks(self, text: str) -> List[str]:
        """Разбивает текст на блоки задач по номерам"""
        # Паттерны начала задачи: цифра с точкой/скобкой, "№", "Задача №"
        patterns = [
            r'(?=\n\d+[\.\)]\s+)',           # "1. " или "1) "
            r'(?=\n№\s*\d+)',                # "№ 1"
            r'(?=\nЗадача\s*\d+)',           # "Задача 1"
            r'(?=\nВариант\s*\d+)',          # "Вариант 1"
        ]
        # Объединяем паттерны
        regex = '|'.join(patterns)
        blocks = re.split(regex, text)
        # Убираем пустые блоки
        blocks = [b.strip() for b in blocks if b.strip()]
        return blocks

    def parse_task_block(self, block: str, source_file: str) -> Optional[Dict]:
        """Извлекает из блока: номер, вопрос, варианты, ответ, решение"""
        if len(block) < 20:
            return None

        # Номер задачи (первая цифра в начале блока)
        num_match = re.search(r'^(\d+)[\.\)]', block)
        if not num_match:
            num_match = re.search(r'№\s*(\d+)', block)
        number = int(num_match.group(1)) if num_match else 0

        # Извлекаем варианты ответов (A) ... B) ... C) ... D) ...)
        options = {}
        opt_pattern = r'([A-D])[\.\)]\s*([^\n]+)'
        for match in re.finditer(opt_pattern, block):
            opt_letter = match.group(1)
            opt_text = match.group(2).strip()
            options[opt_letter] = opt_text

        # Если нет вариантов, возможно это задача с кратким ответом
        has_options = len(options) > 0

        # Вопрос: всё, что до вариантов или до ответа
        question = block
        if has_options:
            # Обрезаем до первого варианта
            first_opt_pos = min([block.find(f"{l})") for l in options.keys() if f"{l})" in block] + [len(block)])
            question = block[:first_opt_pos].strip()
        else:
            # Обрезаем до слова "Ответ:" или "Решение:"
            answer_pos = re.search(r'(Ответ|Решение|Объяснение)', question, re.IGNORECASE)
            if answer_pos:
                question = question[:answer_pos.start()].strip()

        # Ответ
        answer_match = re.search(r'Ответ[:\s]*([A-D]|\d+|[-0-9.]+)', block, re.IGNORECASE)
        answer = answer_match.group(1) if answer_match else ""

        # Решение
        solution_match = re.search(r'(?:Решение|Объяснение|Разбор)[:\s]*(.+?)(?=\n\n|\Z)', block, re.DOTALL | re.IGNORECASE)
        solution = solution_match.group(1).strip() if solution_match else ""

        # Определяем язык
        language = self.detect_language(block)
        # Предмет и тема
        subject = self.detect_subject(block)
        topic = self.detect_topic(block, subject)
        difficulty = self.detect_difficulty(block)

        return {
            "id": f"ent_{subject}_{number}_{source_file[:10]}",
            "source_file": source_file,
            "number": number,
            "language": language,
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "question": question[:1000],
            "options": options,
            "answer": answer,
            "solution": solution[:1000],
            "full_text": block[:2000]
        }

    def detect_language(self, text: str) -> str:
        kz_letters = set('әғқңөұүһіӘҒҚҢӨҰҮҺІ')
        ru_letters = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
        text_clean = text.lower()
        kz_count = sum(1 for ch in text_clean if ch in kz_letters)
        ru_count = sum(1 for ch in text_clean if ch in ru_letters)
        if kz_count > ru_count * 1.5:
            return 'kazakh'
        elif ru_count > kz_count * 1.5:
            return 'russian'
        return 'mixed'

    def detect_subject(self, text: str) -> str:
        text_lower = text.lower()
        subjects = {
            'math': ['математик', 'алгебр', 'геометри', 'тригонометр', 'уравнени', 'функц', 'есеп', 'математика'],
            'physics': ['физик', 'механик', 'электричеств', 'оптик', 'термодинамик', 'жылдамдық', 'күш'],
            'chemistry': ['хими', 'реакц', 'веществ', 'мол', 'раствор', 'қышқыл', 'ерітінді'],
            'biology': ['биологи', 'клетк', 'ген', 'органим', 'экосистем', 'тіршілік'],
            'history_kz': ['казахстан тарихы', 'история казахстан', 'хан', 'орда', 'қазақстан'],
            'history_world': ['всемирная история', 'мировая история', 'войн', 'революц'],
            'english': ['english', 'английск', 'language', 'vocabulary'],
            'russian': ['русский язык', 'орфографи', 'пунктуаци', 'словосочетани'],
            'kazakh': ['қазақ тілі', 'казахский язык', 'тіл', 'грамматик', 'сөз'],
            'geography': ['географи', 'климат', 'рельеф', 'страна', 'жағрафия']
        }
        for subject, keywords in subjects.items():
            if any(kw in text_lower for kw in keywords):
                return subject
        return 'unknown'

    def detect_topic(self, text: str, subject: str) -> str:
        text_lower = text.lower()
        topics = {
            'алгебра': ['уравнение', 'неравенство', 'функция', 'логарифм', 'степень', 'корень'],
            'геометрия': ['треугольник', 'окружность', 'прямая', 'плоскость', 'угол', 'площадь'],
            'тригонометрия': ['sin', 'cos', 'tan', 'тригонометрическ'],
            'матанализ': ['производная', 'интеграл', 'предел', 'дифференциал'],
            'вероятность': ['вероятность', 'статистика', 'комбинаторика'],
            'механика': ['скорость', 'ускорение', 'сила', 'масса'],
            'электричество': ['ток', 'напряжение', 'сопротивление'],
            'химия': ['реакция', 'вещество', 'моль', 'раствор', 'кислота'],
            'биология': ['клетка', 'днк', 'организм', 'ген', 'эволюция'],
        }
        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        return 'general'

    def detect_difficulty(self, text: str) -> str:
        text_len = len(text)
        hard_words = ['докажите', 'найдите все', 'исследуйте', 'доказать', 'комплексный', 'олимпиад']
        if any(w in text.lower() for w in hard_words):
            return 'hard'
        elif text_len > 300:
            return 'medium'
        else:
            return 'easy'

    def process_all(self):
        files = list(self.raw_dir.glob('*.*'))
        print(f"📁 Найдено файлов: {len(files)}")
        for filepath in files:
            if filepath.name == '.DS_Store':
                continue
            print(f"\n📄 Обработка: {filepath.name}")
            tasks = self.parse_file(filepath)
            if tasks:
                print(f"   ✅ Извлечено задач: {len(tasks)}")
                self.all_tasks.extend(tasks)
            else:
                print(f"   ⚠️ Не удалось извлечь задачи")
        print(f"\n📊 Всего извлечено задач: {len(self.all_tasks)}")
        self.save_results()

    def save_results(self):
        json_path = self.output_dir / "ent_tasks.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.all_tasks, f, ensure_ascii=False, indent=2)
        texts = [f"{t['subject']} {t['topic']} {t['question']}" for t in self.all_tasks]
        chunks_path = self.output_dir / "chunks.npy"
        np.save(chunks_path, np.array(texts))
        metadata_path = self.output_dir / "metadata.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.all_tasks, f)
        print(f"\n✅ Сохранено: {json_path}, {chunks_path}, {metadata_path}")
        self.print_stats()

    def print_stats(self):
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ЕНТ")
        print("="*60)
        subjects = Counter([t['subject'] for t in self.all_tasks])
        print("\n📚 Предметы:")
        for subj, cnt in subjects.most_common():
            print(f"   {subj}: {cnt}")
        languages = Counter([t['language'] for t in self.all_tasks])
        print("\n🌐 Языки:")
        for lang, cnt in languages.items():
            print(f"   {lang}: {cnt}")
        difficulties = Counter([t['difficulty'] for t in self.all_tasks])
        print("\n⭐ Сложность:")
        for diff, cnt in difficulties.items():
            print(f"   {diff}: {cnt}")
        print("="*60)

if __name__ == "__main__":
    parser = ENTImprovedParser()
    parser.process_all()