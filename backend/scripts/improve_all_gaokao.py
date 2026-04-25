# scripts/improve_all_gaokao.py
"""
Полный пайплайн улучшения всех задач гаокао на китайском языке
Запускается один раз, обрабатывает все 70,871 задач
"""
import numpy as np
import re
import pickle
import json
import os
from tqdm import tqdm
from collections import Counter
from typing import Dict, List, Tuple

class GaokaoImprover:
    """
    Улучшение всех задач гаокао (китайский язык)
    """
    
    # Полный список тем гаокао (соответствует реальному экзамену)
    GAOKAO_TOPICS = {
        # 代数 - Алгебра
        'алгебра': ['代数', '方程', '不等式', '数列', '复数', '向量', '集合', '函数', '映射', '排列', '组合'],
        
        # 三角函数 - Тригонометрия  
        'тригонометрия': ['三角函数', '三角', '正弦', '余弦', '正切', 'sin', 'cos', 'tan', '弧度', '角度'],
        
        # 几何 - Геометрия
        'геометрия': ['几何', '直线', '圆', '椭圆', '双曲线', '抛物线', '圆锥曲线', '空间', '平面', '立体几何'],
        
        # 微积分 - Матанализ
        'матанализ': ['函数', '导数', '积分', '极限', '单调性', '极值', '最值', '切线', '连续'],
        
        # 概率统计 - Вероятность и статистика
        'вероятность': ['概率', '统计', '随机', '分布', '期望', '方差', '排列组合', '二项式'],
        
        # 解析几何 - Аналитическая геометрия
        'аналит_геометрия': ['解析几何', '坐标', '方程', '曲线', '参数方程', '极坐标'],
        
        # 复数 - Комплексные числа
        'комплексные': ['复数', '虚数', '实部', '虚部', '共轭'],
        
        # 数列 - Прогрессии
        'прогрессии': ['数列', '等差数列', '等比数列', '通项', '求和', '递推'],
        
        # 不等式 - Неравенства
        'неравенства': ['不等式', '绝对值', '均值', '柯西', '排序'],
        
        # 逻辑 - Логика и множества
        'логика': ['逻辑', '命题', '充分条件', '必要条件', '集合', '元素'],
        
        # 向量 - Векторы
        'векторы': ['向量', '点积', '叉积', '平行', '垂直'],
        
        # 立体几何 - Стереометрия
        'стереометрия': ['立体几何', '空间', '平面', '垂直', '平行', '体积', '表面积'],
    }
    
    # Словарь для исправления OCR ошибок в китайских формулах
    OCR_FIXES = {
        # Цифры и операторы
        '十': '+',
        '一': '-',
        '二': '2',
        '三': '3',
        '四': '4',
        '五': '5',
        '六': '6',
        '七': '7',
        '八': '8',
        '九': '9',
        '零': '0',
        '×': '*',
        '÷': '/',
        '＝': '=',
        '＞': '>',
        '＜': '<',
        '≥': '≥',
        '≤': '≤',
        '≠': '≠',
        '≈': '≈',
        '∞': '∞',
        'π': 'π',
        '°': '°',
        
        # Китайские математические термины
        '平方': '²',
        '立方': '³',
        '根号': '√',
        '分之': '/',
        '等于': '=',
        '大于': '>',
        '小于': '<',
        
        # Функции
        '正弦': 'sin',
        '余弦': 'cos',
        '正切': 'tan',
        '余切': 'cot',
        '正割': 'sec',
        '余割': 'csc',
        '反正弦': 'arcsin',
        '反余弦': 'arccos',
        '反正切': 'arctan',
        
        # Греческие буквы
        '阿尔法': 'α',
        '贝塔': 'β',
        '伽马': 'γ',
        '德尔塔': 'δ',
        '西格玛': 'σ',
        '欧米伽': 'ω',
        '派': 'π',
    }
    
    def __init__(self, chunks_path="data/gaokao/chunks.npy"):
        self.chunks_path = chunks_path
        self.texts = np.load(chunks_path, allow_pickle=True)
        print(f"📚 Загружено {len(self.texts)} задач")
    
    def clean_ocr_artifacts(self, text: str) -> str:
        """Шаг 1: Очистка OCR артефактов"""
        if not isinstance(text, str):
            text = str(text)
        
        # Удаляем лишние пробелы между китайскими иероглифами
        text = re.sub(r'(?<=[\u4e00-\u9fff]) +(?=[\u4e00-\u9fff])', '', text)
        
        # Применяем словарь исправлений
        for old, new in self.OCR_FIXES.items():
            text = text.replace(old, new)
        
        # Исправляем пробелы вокруг операторов
        text = re.sub(r'\s*([+\-*/=<>≤≥≠])\s*', r' \1 ', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем URL и рекламные строки
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'【.*?淘.*?宝.*?】', '', text)
        text = re.sub(r'【.*?学.*?霸.*?】', '', text)
        
        return text.strip()
    
    def fix_chinese_formulas(self, text: str) -> str:
        """Шаг 2: Исправление формул на китайском"""
        
        # sin²A + sin²C (исправляем OCR ошибки)
        text = re.sub(r'sin(\d+)\s*[十\+]\s*sin([A-Z])', r'sin²\1 + sin²\2', text)
        text = re.sub(r'cos(\d+)\s*[十\+]\s*cos([A-Z])', r'cos²\1 + cos²\2', text)
        
        # sin2C → sin²C
        text = re.sub(r'sin2([A-Z])', r'sin²\1', text)
        text = re.sub(r'cos2([A-Z])', r'cos²\1', text)
        
        # sin34 → sin²A (если 4 означает A)
        text = re.sub(r'sin(\d+)(?![a-z])', lambda m: f'sin{chr(ord("A") + int(m.group(1)) - 1)}' if m.group(1).isdigit() and 1 <= int(m.group(1)) <= 26 else f'sin{m.group(1)}', text)
        
        # Исправляем степени
        text = re.sub(r'(\w)2(\d+)', r'\1²\2', text)
        text = re.sub(r'(\w)3(\d+)', r'\1³\2', text)
        
        return text
    
    def extract_question(self, text: str) -> str:
        """Шаг 3: Извлечение условия задачи"""
        # Ищем после номера задачи
        match = re.search(r'^\d+\.\s*(.+?)(?=\n【参考答案】|\n【详细解析】|$)', text, re.DOTALL)
        if match:
            return match.group(1).strip()[:800]
        
        # Если не нашли, берём начало текста
        if '【参考答案】' in text:
            return text.split('【参考答案】')[0].strip()[:800]
        if '【详细解析】' in text:
            return text.split('【详细解析】')[0].strip()[:800]
        
        return text[:800]
    
    def extract_answer(self, text: str) -> Tuple[str, bool]:
        """Шаг 4: Извлечение ответа"""
        patterns = [
            r'【参考答案】\s*([^【]+?)(?=\s*【|$)',
            r'【答案】\s*([^【]+?)(?=\s*【|$)',
            r'答案[：:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                answer = match.group(1).strip()[:200]
                # Очищаем ответ от лишних символов
                answer = re.sub(r'[【】]', '', answer)
                return answer, True
        
        return "", False
    
    def extract_solution(self, text: str) -> Tuple[str, bool]:
        """Шаг 5: Извлечение решения"""
        patterns = [
            r'【详细解析】\s*([^【]+?)(?=\s*【|$)',
            r'【解析】\s*([^【]+?)(?=\s*【|$)',
            r'解[：:]\s*([^\n]+(?:\n[^【])*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                solution = match.group(1).strip()[:1000]
                return solution, True
        
        return "", False
    
    def detect_topic(self, text: str) -> str:
        """Шаг 6: Определение темы (китайские ключевые слова)"""
        text_lower = text.lower()
        
        # Считаем очки для каждой темы
        scores = {}
        for topic, keywords in self.GAOKAO_TOPICS.items():
            score = 0
            for kw in keywords:
                # Ищем китайские ключевые слова
                if kw in text:
                    score += 2
                # Ищем латинские варианты (sin, cos и т.д.)
                if kw in text_lower:
                    score += 1
            if score > 0:
                scores[topic] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        # Если не определили, пытаемся определить по структуре
        if '导数' in text or '微分' in text:
            return 'матанализ'
        if '向量' in text or '坐标' in text:
            return 'векторы'
        if '概率' in text or '统计' in text:
            return 'вероятность'
        
        return 'unknown'
    
    def detect_difficulty(self, text: str, has_solution: bool, has_answer: bool) -> str:
        """Шаг 7: Определение сложности"""
        text_len = len(text)
        
        # Ключевые слова сложных задач
        hard_keywords = ['证明', '最大值', '最小值', '取值范围', '存在', '恒成立', '综合']
        medium_keywords = ['求', '计算', '判断', '确定', '设']
        
        hard_count = sum(1 for kw in hard_keywords if kw in text)
        medium_count = sum(1 for kw in medium_keywords if kw in text)
        
        if text_len > 800 and hard_count >= 2:
            return 'hard'
        elif text_len > 500 or hard_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'easy'
    
    def detect_year(self, text: str) -> int:
        """Шаг 8: Определение года"""
        # Ищем 2024, 2023, 2022
        years = re.findall(r'20(?:2[0-4]|2[0-9])', text)
        if years:
            return int(years[0])
        
        # Если нет, пробуем найти 2024年全国
        if '2024年全国' in text:
            return 2024
        if '2023年全国' in text:
            return 2023
            
        return 2024
    
    def detect_question_type(self, text: str) -> str:
        """Шаг 9: Определение типа задачи"""
        types = {
            'choice': ['选择题', '单选', 'A.', 'B.', 'C.', 'D.'],
            'fill': ['填空题', '填', '空'],
            'proof': ['证明题', '求证', '证明'],
            'calculation': ['计算题', '求', '计算'],
            'application': ['应用题', '实际', '应用'],
        }
        
        for qtype, keywords in types.items():
            if any(kw in text for kw in keywords):
                return qtype
        
        return 'unknown'
    
    def process_all(self) -> Tuple[List[Dict], Dict]:
        """Запуск обработки всех задач"""
        print("🔄 Начинаем обработку всех 70,871 задач...")
        
        improved = []
        stats = {
            'total': len(self.texts),
            'with_answer': 0,
            'with_solution': 0,
            'topics': Counter(),
            'years': Counter(),
            'difficulties': Counter(),
            'question_types': Counter(),
            'errors': []
        }
        
        for i, text in enumerate(tqdm(self.texts, desc="Обработка")):
            try:
                # Шаг 1: Очистка OCR
                text = self.clean_ocr_artifacts(text)
                
                # Шаг 2: Исправление формул
                text = self.fix_chinese_formulas(text)
                
                # Шаг 3: Извлечение условия
                question = self.extract_question(text)
                
                # Шаг 4: Извлечение ответа
                answer, has_answer = self.extract_answer(text)
                
                # Шаг 5: Извлечение решения
                solution, has_solution = self.extract_solution(text)
                
                # Шаг 6: Определение темы
                topic = self.detect_topic(text)
                
                # Шаг 7: Определение сложности
                difficulty = self.detect_difficulty(text, has_solution, has_answer)
                
                # Шаг 8: Определение года
                year = self.detect_year(text)
                
                # Шаг 9: Определение типа задачи
                qtype = self.detect_question_type(text)
                
                # Собираем улучшенную задачу
                improved.append({
                    'id': f"gaokao_{i}",
                    'year': year,
                    'topic': topic,
                    'topic_cn': self._get_topic_chinese(topic),
                    'difficulty': difficulty,
                    'question_type': qtype,
                    'question': question,
                    'solution': solution,
                    'answer': answer,
                    'has_answer': has_answer,
                    'has_solution': has_solution,
                    'raw_text': text[:300]
                })
                
                # Обновляем статистику
                stats['topics'][topic] += 1
                stats['years'][year] += 1
                stats['difficulties'][difficulty] += 1
                stats['question_types'][qtype] += 1
                
                if has_answer:
                    stats['with_answer'] += 1
                if has_solution:
                    stats['with_solution'] += 1
                    
            except Exception as e:
                stats['errors'].append({'id': i, 'error': str(e)})
                # В случае ошибки сохраняем базовую информацию
                improved.append({
                    'id': f"gaokao_{i}",
                    'year': 2024,
                    'topic': 'unknown',
                    'topic_cn': '未知',
                    'difficulty': 'medium',
                    'question_type': 'unknown',
                    'question': str(text)[:500],
                    'solution': '',
                    'answer': '',
                    'has_answer': False,
                    'has_solution': False,
                    'raw_text': str(text)[:300]
                })
        
        # Сохраняем результаты
        self.save_results(improved, stats)
        
        return improved, stats
    
    def _get_topic_chinese(self, topic: str) -> str:
        """Получить китайское название темы"""
        mapping = {
            'алгебра': '代数',
            'тригонометрия': '三角函数',
            'геометрия': '几何',
            'матанализ': '微积分',
            'вероятность': '概率统计',
            'аналит_геометрия': '解析几何',
            'комплексные': '复数',
            'прогрессии': '数列',
            'неравенства': '不等式',
            'логика': '逻辑',
            'векторы': '向量',
            'стереометрия': '立体几何',
        }
        return mapping.get(topic, '其他')
    
    def save_results(self, improved: List[Dict], stats: Dict):
        """Сохранение улучшенных данных"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(base_dir, "data", "gaokao")
        
        # Сохраняем как JSON
        json_path = os.path.join(data_dir, "improved_tasks.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(improved, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Сохранено JSON: {json_path}")
        
        # Сохраняем метаданные для RAG
        metadata_path = os.path.join(data_dir, "metadata_improved.pkl")
        with open(metadata_path, 'wb') as f:
            pickle.dump(improved, f)
        print(f"✅ Сохранены метаданные: {metadata_path}")
        
        # Сохраняем очищенные тексты для эмбеддингов
        clean_texts = [item['question'] for item in improved]
        chunks_path = os.path.join(data_dir, "chunks_improved.npy")
        np.save(chunks_path, np.array(clean_texts))
        print(f"✅ Сохранены очищенные тексты: {chunks_path}")
        
        # Сохраняем статистику
        stats_path = os.path.join(data_dir, "improvement_stats.json")
        stats_copy = {k: v for k, v in stats.items() if k != 'errors'}
        stats_copy['topics'] = dict(stats['topics'])
        stats_copy['years'] = dict(stats['years'])
        stats_copy['difficulties'] = dict(stats['difficulties'])
        stats_copy['question_types'] = dict(stats['question_types'])
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats_copy, f, ensure_ascii=False, indent=2)
        print(f"✅ Сохранена статистика: {stats_path}")
        
        # Выводим статистику
        self.print_stats(stats)
    
    def print_stats(self, stats: Dict):
        """Вывод статистики"""
        total = stats['total']
        
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА УЛУЧШЕНИЯ ВСЕХ ЗАДАЧ")
        print("="*60)
        
        print(f"\n📌 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Всего задач: {total:,}")
        print(f"   С ответами: {stats['with_answer']:,} ({stats['with_answer']/total*100:.1f}%)")
        print(f"   С решениями: {stats['with_solution']:,} ({stats['with_solution']/total*100:.1f}%)")
        print(f"   Ошибок обработки: {len(stats['errors'])}")
        
        print(f"\n📚 РАСПРЕДЕЛЕНИЕ ПО ТЕМАМ:")
        for topic, count in stats['topics'].most_common(15):
            percentage = count/total*100
            bar = '█' * int(percentage/2)
            print(f"   {topic:20} {bar} {count:6,} ({percentage:5.1f}%)")
        
        print(f"\n📅 РАСПРЕДЕЛЕНИЕ ПО ГОДАМ:")
        for year in sorted(stats['years'].keys()):
            count = stats['years'][year]
            print(f"   {year}: {count:,} ({count/total*100:.1f}%)")
        
        print(f"\n⭐ РАСПРЕДЕЛЕНИЕ ПО СЛОЖНОСТИ:")
        for diff in ['easy', 'medium', 'hard']:
            count = stats['difficulties'].get(diff, 0)
            print(f"   {diff}: {count:,} ({count/total*100:.1f}%)")
        
        print(f"\n📝 РАСПРЕДЕЛЕНИЕ ПО ТИПАМ ЗАДАЧ:")
        for qtype, count in stats['question_types'].most_common():
            print(f"   {qtype}: {count:,} ({count/total*100:.1f}%)")
        
        print("\n" + "="*60)
        print("✅ Улучшение завершено!")
        print("="*60)


if __name__ == "__main__":
    improver = GaokaoImprover()
    improved, stats = improver.process_all()