#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный парсер ЕНТ с очисткой от мусора и фильтрацией коротких задач
"""

import os
import re
import json
import pickle
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter

try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False


class ENTCleanedParser:
    def __init__(self, raw_dir="data/ent/raw", output_dir="data/ent/processed"):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_tasks = []
        self.errors = []

        # Стоп-фразы для удаления
        self.stop_phrases = [
            r'МИНИСТЕРСТВО ОБРАЗОВАНИЯ',
            r'РЕСПУБЛИКИ КАЗАХСТАН',
            r'НАЦИОНАЛЬНЫЙ ЦЕНТР ТЕСТИРОВАНИЯ',
            r'УЧЕБНО-МЕТОДИЧЕСКОЕ ПОСОБИЕ',
            r'Интеллектуальной собственностью',
            r'Запрещается без письменного разрешения',
            r'АСТАНА\s*\d{4}',
            r'УДК\s*\d+\.\d+',
            r'ББК\s*[\d\.]+\s*я\s*\d+',
            r'ВВЕДЕНИЕ',
            r'Тесты являются интеллектуальной собственностью',
            r'ISBN',
            r'©',
            r'\.\.\.',
            r'^\s*$',
        ]
        self.stop_phrases_compiled = [re.compile(phrase, re.IGNORECASE) for phrase in self.stop_phrases]

    def clean_text(self, text: str) -> str:
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            is_garbage = False
            for pattern in self.stop_phrases_compiled:
                if pattern.search(line):
                    is_garbage = True
                    break
            if len(line) < 10 and not re.search(r'\d', line):
                is_garbage = True
            if re.match(r'^[^\w\s]+$', line):
                is_garbage = True
            if not is_garbage:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def extract_text_from_doc(self, filepath: Path) -> str:
        try:
            result = subprocess.run(
                ['catdoc', '-w', str(filepath)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                return self.clean_text(result.stdout)
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
            return self.clean_text(text)
        except Exception as e:
            self.errors.append(f"PDF error {filepath.name}: {e}")
            return ""

    def extract_text_from_docx(self, filepath: Path) -> str:
        if not DOCX_AVAILABLE:
            return ""
        try:
            doc = Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
            return self.clean_text(text)
        except Exception as e:
            self.errors.append(f"DOCX error {filepath.name}: {e}")
            return ""

    def extract_text_from_txt(self, filepath: Path) -> str:
        encodings = ['utf-8', 'cp1251', 'utf-16', 'latin-1']
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return self.clean_text(f.read())
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

        blocks = self.split_into_tasks(text)
        tasks = []
        for block in blocks:
            task = self.parse_task_block(block, filepath.name)
            if task:
                tasks.append(task)
        return tasks

    def split_into_tasks(self, text: str) -> List[str]:
        patterns = [
            r'(?=\n\d+[\.\)]\s+)',
            r'(?=\n№\s*\d+)',
            r'(?=\nЗадача\s*\d+)',
            r'(?=\nВариант\s*\d+)',
        ]
        regex = '|'.join(patterns)
        blocks = re.split(regex, text)
        blocks = [b.strip() for b in blocks if b.strip()]
        return blocks

    def parse_task_block(self, block: str, source_file: str) -> Optional[Dict]:
        if len(block) < 20:
            return None

        num_match = re.search(r'^(\d+)[\.\)]', block)
        if not num_match:
            num_match = re.search(r'№\s*(\d+)', block)
        number = int(num_match.group(1)) if num_match else 0

        options = {}
        opt_pattern = r'([A-D])[\.\)]\s*([^\n]+)'
        for match in re.finditer(opt_pattern, block):
            options[match.group(1)] = match.group(2).strip()

        has_options = len(options) > 0

        question = block
        if has_options:
            first_opt_pos = min([block.find(f"{l})") for l in options.keys() if f"{l})" in block] + [len(block)])
            question = block[:first_opt_pos].strip()
        else:
            answer_pos = re.search(r'(Ответ|Решение|Объяснение)', question, re.IGNORECASE)
            if answer_pos:
                question = question[:answer_pos.start()].strip()

        # ФИЛЬТРАЦИЯ: отбрасываем задачи с очень коротким вопросом
        if len(question) < 100:
            return None

        answer_match = re.search(r'Ответ[:\s]*([A-D]|\d+|[-0-9.]+)', block, re.IGNORECASE)
        answer = answer_match.group(1) if answer_match else ""

        solution_match = re.search(r'(?:Решение|Объяснение|Разбор)[:\s]*(.+?)(?=\n\n|\Z)', block, re.DOTALL | re.IGNORECASE)
        solution = solution_match.group(1).strip() if solution_match else ""

        language = self.detect_language(block)
        subject = self.detect_subject(block)
        topic = self.detect_topic(block, subject)
        difficulty = self.detect_difficulty(block)

        return {
            "id": f"ent_{subject}_{number}_{source_file[:15]}",
            "source_file": source_file,
            "number": number,
            "language": language,
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "question": question[:2000],
            "options": options,
            "answer": answer,
            "solution": solution[:2000],
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
            'math': ['математик', 'алгебр', 'геометри', 'тригонометр', 'уравнени', 'функц', 'есеп', 'математика', 'теңдеу', 'өрнек', 'сан'],
            'physics': ['физик', 'механик', 'электричеств', 'оптик', 'термодинамик', 'жылдамдық', 'күш', 'энергия'],
            'chemistry': ['хими', 'реакц', 'веществ', 'мол', 'раствор', 'қышқыл', 'ерітінді', 'зат'],
            'biology': ['биологи', 'клетк', 'ген', 'органим', 'экосистем', 'тіршілік', 'өсімдік', 'жануар'],
            'history_kz': ['казахстан тарихы', 'история казахстан', 'хан', 'орда', 'қазақстан', 'ұлы жібек жолы'],
            'history_world': ['всемирная история', 'мировая история', 'войн', 'революц', 'египет', 'греция'],
            'english': ['english', 'английск', 'language', 'vocabulary', 'grammar'],
            'russian': ['русский язык', 'орфографи', 'пунктуаци', 'словосочетани', 'суффикс'],
            'kazakh': ['қазақ тілі', 'казахский язык', 'тіл', 'грамматик', 'сөз', 'жалғау'],
            'geography': ['географи', 'климат', 'рельеф', 'страна', 'жағрафия', 'табиғат']
        }
        for subject, keywords in subjects.items():
            if any(kw in text_lower for kw in keywords):
                return subject
        return 'unknown'

    def detect_topic(self, text: str, subject: str) -> str:
        text_lower = text.lower()
        topics = {
            'алгебра': ['уравнение', 'неравенство', 'функция', 'логарифм', 'степень', 'корень', 'квадрат', 'прогрессия', 'теңдеу', 'теңсіздік'],
            'геометрия': ['треугольник', 'окружность', 'прямая', 'плоскость', 'угол', 'площадь', 'үшбұрыш', 'дөңгелек', 'кесінді'],
            'тригонометрия': ['sin', 'cos', 'tan', 'тригонометрическ', 'синус', 'косинус', 'тангенс'],
            'матанализ': ['производная', 'интеграл', 'предел', 'дифференциал', 'туынды'],
            'вероятность': ['вероятность', 'статистика', 'комбинаторика', 'ықтималдық'],
            'механика': ['скорость', 'ускорение', 'сила', 'масса', 'жылдамдық', 'күш'],
            'электричество': ['ток', 'напряжение', 'сопротивление', 'ток күші', 'кернеу'],
            'химия': ['реакция', 'вещество', 'моль', 'раствор', 'кислота', 'реакция', 'зат'],
            'биология': ['клетка', 'днк', 'организм', 'ген', 'эволюция', 'жасуша']
        }
        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        return 'general'

    def detect_difficulty(self, text: str) -> str:
        text_len = len(text)
        hard_words = ['докажите', 'найдите все', 'исследуйте', 'доказать', 'комплексный', 'олимпиад', 'дәлелдеңіз']
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
    parser = ENTCleanedParser()
    parser.process_all()