import httpx
import os
import json
import asyncio
import re
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY не установлен")
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 4000) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    # --- Анализ экзамена (для математики возвращает все темы 5-11 классов) ---
    # backend/app/deepseek_client.py (фрагмент)

    async def generate_exam_analysis(self, exam_name: str) -> Dict[str, Any]:
        exam_lower = exam_name.lower()
        # Определяем предмет
        if "математик" in exam_lower or "math" in exam_lower:
            subject = "математика"
        elif "физик" in exam_lower:
            subject = "физика"
        elif "хими" in exam_lower:
            subject = "химия"
        elif "биологи" in exam_lower:
            subject = "биология"
        elif "история казахстана" in exam_lower:
            subject = "история казахстана"
        elif "всемирная история" in exam_lower or "мировая история" in exam_lower:
            subject = "всемирная история"
        elif "английск" in exam_lower:
            subject = "английский язык"
        elif "русский язык" in exam_lower:
            subject = "русский язык"
        elif "казахский язык" in exam_lower or "қазақ тілі" in exam_lower:
            subject = "казахский язык"
        elif "географи" in exam_lower:
            subject = "география"
        else:
            subject = "математика"

        # Предопределённые структуры для каждого предмета
        subjects_config = {
            "математика": {
                "topics": [
                    {"name": "Алгебра", "weight": 35},
                    {"name": "Геометрия", "weight": 25},
                    {"name": "Тригонометрия", "weight": 15},
                    {"name": "Математический анализ", "weight": 15},
                    {"name": "Вероятность и статистика", "weight": 10}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "физика": {
                "topics": [
                    {"name": "Механика", "weight": 30},
                    {"name": "Молекулярная физика", "weight": 20},
                    {"name": "Электродинамика", "weight": 30},
                    {"name": "Колебания и волны", "weight": 10},
                    {"name": "Оптика и квантовая физика", "weight": 10}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "химия": {
                "topics": [
                    {"name": "Общая химия", "weight": 25},
                    {"name": "Неорганическая химия", "weight": 30},
                    {"name": "Органическая химия", "weight": 30},
                    {"name": "Расчётные задачи", "weight": 15}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            # Для остальных предметов можно использовать общую структуру (пока без весов)
            "биология": {
                "topics": [
                    {"name": "Общая биология", "weight": 30},
                    {"name": "Ботаника", "weight": 15},
                    {"name": "Зоология", "weight": 15},
                    {"name": "Анатомия человека", "weight": 30},
                    {"name": "Экология", "weight": 10}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "история казахстана": {
                "topics": [
                    {"name": "Древний Казахстан", "weight": 15},
                    {"name": "Средневековый Казахстан", "weight": 20},
                    {"name": "Казахское ханство", "weight": 20},
                    {"name": "Казахстан в составе РФ", "weight": 15},
                    {"name": "Советский период", "weight": 15},
                    {"name": "Независимый Казахстан", "weight": 15}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "всемирная история": {
                "topics": [
                    {"name": "Древний мир", "weight": 25},
                    {"name": "Средние века", "weight": 25},
                    {"name": "Новое время", "weight": 25},
                    {"name": "Новейшая история", "weight": 25}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "английский язык": {
                "topics": [
                    {"name": "Грамматика", "weight": 35},
                    {"name": "Лексика", "weight": 30},
                    {"name": "Чтение и аудирование", "weight": 20},
                    {"name": "Письмо и говорение", "weight": 15}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "русский язык": {
                "topics": [
                    {"name": "Орфография", "weight": 25},
                    {"name": "Пунктуация", "weight": 25},
                    {"name": "Морфология", "weight": 20},
                    {"name": "Синтаксис", "weight": 20},
                    {"name": "Текст и стилистика", "weight": 10}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "казахский язык": {
                "topics": [
                    {"name": "Грамматика", "weight": 35},
                    {"name": "Орфография", "weight": 25},
                    {"name": "Лексика", "weight": 20},
                    {"name": "Мәтін", "weight": 20}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            },
            "география": {
                "topics": [
                    {"name": "Физическая география", "weight": 30},
                    {"name": "Социально-экономическая география", "weight": 30},
                    {"name": "География Казахстана", "weight": 30},
                    {"name": "Картография", "weight": 10}
                ],
                "total_questions": 25,
                "exam_duration_minutes": 180,
                "passing_score": 50
            }
        }
        config = subjects_config.get(subject, subjects_config["математика"])
        return {
            "topics": [{"name": t["name"], "weight": t["weight"], "difficulty_levels": ["легкий", "средний", "сложный"]} for t in config["topics"]],
            "scoring": {
                "max_score": 100,
                "passing_score": config["passing_score"],
                "criteria": f"Оценка за каждый правильный ответ. Для перехода к следующему модулю необходимо набрать не менее 80%."
            },
            "total_questions": config["total_questions"],
            "exam_duration_minutes": config["exam_duration_minutes"],
            "subject": subject,
            "is_full_course": True
        }
    
    # --- Целевой профиль (высокий уровень) ---
    async def generate_target_profile(self, exam_details: Dict[str, Any]) -> Dict[str, Any]:
        # Для полного курса – целевой уровень 90-95%
        if exam_details.get("is_full_course"):
            topics = {t["name"]: 95 for t in exam_details["topics"]}
            return {"target_profile": topics, "reasoning": "Для освоения всей школьной математики необходим высокий уровень."}
        prompt = f"""На основе структуры экзамена: {json.dumps(exam_details, ensure_ascii=False)}
        Определи целевой профиль ученика — необходимый уровень владения КАЖДОЙ темой (от 0 до 100), 
        чтобы успешно сдать экзамен на 85% от максимального балла.
        Верни ТОЛЬКО JSON: {{"target_profile": {{"тема1": 85, "тема2": 90}}, "reasoning": "..."}}"""
        response = await self.chat_completion([
            {"role": "system", "content": "Ты эксперт по образованию. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ])
        try:
            return json.loads(response)
        except:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Не удалось распарсить JSON: {response}")
    
    # --- Генерация начального теста (используется если RAG не дал достаточно вопросов) ---
    async def generate_initial_test(self, exam_details: Dict[str, Any], num_questions: int = 15, subject: str = "математика") -> List[Dict[str, Any]]:
        subject = subject.lower()
        
        # Базовый промпт для математики
        if subject == "математика":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по МАТЕМАТИКЕ.
            Структура экзамена: {json.dumps(exam_details, ensure_ascii=False)}
            Требования:
            1. Задачи должны покрывать ВСЕ темы из exam_details
            2. Разное распределение сложности: 40% легкие, 40% средние, 20% сложные
            3. Для каждой задачи укажи: тему, сложность, текст задачи, правильный ответ, пояснение решения
            Верни ТОЛЬКО JSON массив объектов. Формат:
            [
            {{
                "topic": "название темы",
                "difficulty": "легкий/средний/сложный",
                "question": "текст задачи",
                "correct_answer": "правильный ответ",
                "explanation": "пояснение решения"
            }}
            ]"""
        elif subject == "физика":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по ФИЗИКЕ.
            Темы: механика, молекулярная физика, электродинамика, колебания и волны, оптика, квантовая физика.
            Требования:
            1. Задачи должны быть именно по физике (расчёты скорости, ускорения, силы, тока, напряжения, энергии, оптические формулы, фотоэффект и т.д.)
            2. НЕ используй чистые геометрические задачи (конусы, цилиндры, трапеции, ромбы, призмы), если только они не являются частью физической задачи (например, движение по наклонной плоскости, расчёт объёма тела через интеграл).
            3. Распределение сложности: 40% легкие, 40% средние, 20% сложные.
            4. Для каждой задачи укажи: тему, сложность, текст задачи, правильный ответ, пояснение решения.
            Верни ТОЛЬКО JSON массив объектов.
            Пример правильной физической задачи:
            {{
                "topic": "Механика",
                "difficulty": "легкий",
                "question": "Автомобиль движется со скоростью 72 км/ч. Какое расстояние он проедет за 10 секунд?",
                "correct_answer": "200 м",
                "explanation": "Скорость 72 км/ч = 20 м/с. Расстояние = скорость × время = 20×10 = 200 м."
            }}
            """
        elif subject == "химия":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по ХИМИИ.
            Темы: общая химия, неорганическая химия, органическая химия, химические реакции, расчётные задачи.
            Требования:
            1. Задачи должны быть по химии (расчёты по формулам, уравнения реакций, массовая доля, молярность и т.д.)
            2. Распределение сложности: 40% легкие, 40% средние, 20% сложные.
            Верни JSON массив."""
        elif subject == "биология":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по БИОЛОГИИ.
            Темы: общая биология, ботаника, зоология, анатомия человека, экология.
            Требования:
            1. Задачи должны быть по биологии (строение клетки, генетика, системы органов, экосистемы и т.д.)
            2. Распределение сложности: 40% легкие, 40% средние, 20% сложные.
            Верни JSON массив."""
        elif subject == "история казахстана":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по ИСТОРИИ КАЗАХСТАНА.
            Темы: древний Казахстан, средневековый Казахстан, Казахское ханство, Казахстан в составе РФ, советский период, независимый Казахстан.
            Верни JSON массив."""
        elif subject == "всемирная история":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по ВСЕМИРНОЙ ИСТОРИИ.
            Темы: древний мир, средние века, новое время, новейшая история.
            Верни JSON массив."""
        elif subject == "английский язык":
            prompt = f"""Сгенерируй {num_questions} заданий для начального тестирования по АНГЛИЙСКОМУ ЯЗЫКУ.
            Типы заданий: грамматика, лексика, чтение, аудирование, письмо.
            Верни JSON массив."""
        elif subject == "русский язык":
            prompt = f"""Сгенерируй {num_questions} заданий для начального тестирования по РУССКОМУ ЯЗЫКУ.
            Темы: орфография, пунктуация, морфология, синтаксис, текст и стилистика.
            Верни JSON массив."""
        elif subject == "казахский язык":
            prompt = f"""Сгенерируй {num_questions} заданий для начального тестирования по КАЗАХСКОМУ ЯЗЫКУ.
            Темы: грамматика, орфография, лексика, мәтін.
            Верни JSON массив."""
        elif subject == "география":
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по ГЕОГРАФИИ.
            Темы: физическая география, социально-экономическая география, география Казахстана, картография.
            Верни JSON массив."""
        else:
            prompt = f"""Сгенерируй {num_questions} задач для начального тестирования по предмету "{subject}".
            Верни JSON массив."""
        
        response = await self.chat_completion([
            {"role": "system", "content": "Ты составитель тестов. Отвечай только JSON массивом."},
            {"role": "user", "content": prompt}
        ], max_tokens=8000)
        
        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Не удалось распарсить JSON: {response}")
        except:
            return []
    
    # --- Оценка ответов ---
    async def evaluate_answers(self, questions: List[Dict], user_answers: Dict[str, str], exam_details: Dict) -> Dict[str, Any]:
        prompt = f"""Оцени ответы пользователя на тестовые вопросы.
        Вопросы: {json.dumps(questions, ensure_ascii=False)}
        Ответы пользователя: {json.dumps(user_answers, ensure_ascii=False)}
        Структура экзамена: {json.dumps(exam_details, ensure_ascii=False)}
        Для каждого вопроса определи правильность (да/нет), выставь балл 0 или 1.
        Рассчитай для каждой темы процент правильных ответов и общий балл.
        Верни JSON: {{"topic_scores": {{...}}, "overall_score": 58, "detailed_feedback": "...", "weak_topics": [...], "strong_topics": [...]}}"""
        response = await self.chat_completion([
            {"role": "system", "content": "Ты эксперт по оценке знаний. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ])
        try:
            return json.loads(response)
        except:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Не удалось распарсить JSON: {response}")
    
    # --- Генерация долгого плана (минимум 180 дней) ---
    async def generate_study_plan(self, target_profile: Dict, current_profile: Dict, days: int, exam_details: Dict) -> Dict[str, Any]:
      # Принудительно делаем план не короче 180 дней
      if days < 180:
          days = 180
      full_course_note = ""
      if exam_details.get("is_full_course"):
          full_course_note = "Это полный курс школьной математики (5-11 классы). Разбей материал на модули по классам или крупным темам. Каждый модуль должен заканчиваться тестом с порогом 80%. Уроки должны быть очень подробными, с большим количеством задач."
      prompt = f"""Ты – методист по математике. Составь детальный план подготовки по математике на {days} дней.
      {full_course_note}
      Целевой профиль: {json.dumps(target_profile, ensure_ascii=False)}
      Текущий профиль: {json.dumps(current_profile, ensure_ascii=False)}
      Требования:
      - План должен быть разбит на модули (по 20-30 дней). В каждом модуле перечислите темы.
      - Ежедневно: теория + практика (20-30 задач).
      - Промежуточные тесты каждые 5-7 дней с порогом 80%. После теста – день на разбор ошибок.
      - Интенсивность: 4 часа в день.
      - Итоговый экзамен в последние 5 дней.
      Верни ТОЛЬКО JSON, без пояснений. Формат:
      {{
        "total_days": {days},
        "hours_per_day": 4,
        "schedule": [
          {{"day": 1, "module": "Алгебра 5-6", "topics": ["Натуральные числа", "Дроби"], "hours": 4, "type": "theory", "tasks": "20 задач на дроби"}},
          {{"day": 7, "type": "test", "topics": ["Алгебра 5-6"], "description": "Тест 15 вопросов, проходной 80%"}}
        ],
        "strategy": "Общая стратегия подготовки"
      }}"""
      response = await self.chat_completion([
          {"role": "system", "content": "Ты методист по подготовке к экзаменам. Отвечай только JSON. Не добавляй никакой текст до или после JSON."},
          {"role": "user", "content": prompt}
      ], max_tokens=8000)
      
      # Очистка ответа: убираем возможные Markdown-блоки и лишний текст
      cleaned = response.strip()
      # Удаляем ```json ... ``` если есть
      if cleaned.startswith("```json"):
          cleaned = cleaned[7:]
      if cleaned.startswith("```"):
          cleaned = cleaned[3:]
      if cleaned.endswith("```"):
          cleaned = cleaned[:-3]
      cleaned = cleaned.strip()
      
      # Пытаемся найти JSON в тексте (на случай, если остался лишний текст)
      json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
      if json_match:
          cleaned = json_match.group()
      
      # Пробуем распарсить
      try:
          plan = json.loads(cleaned)
          # Проверяем наличие обязательных полей
          if "schedule" not in plan:
              plan["schedule"] = []
          if "total_days" not in plan:
              plan["total_days"] = days
          if "hours_per_day" not in plan:
              plan["hours_per_day"] = 4
          if "strategy" not in plan:
              plan["strategy"] = "Интенсивный курс с промежуточными тестами."
          return plan
      except json.JSONDecodeError as e:
          print(f"Ошибка парсинга JSON: {e}")
          print(f"Ответ DeepSeek: {response[:500]}...")
          # Возвращаем заглушку, чтобы сервер не падал
          return {
              "total_days": days,
              "hours_per_day": 4,
              "schedule": [
                  {"day": 1, "type": "theory", "topics": ["Алгебра"], "hours": 4, "tasks": "Изучение основ"},
                  {"day": 2, "type": "theory", "topics": ["Геометрия"], "hours": 4, "tasks": "Изучение основ"},
                  {"day": 3, "type": "test", "topics": ["Алгебра", "Геометрия"], "description": "Тест"}
              ],
              "strategy": "План создан автоматически из-за ошибки генерации."
          }
    
    # --- Генерация глубокого урока (Khan Academy style) ---
    async def generate_lesson_with_examples(self, topic: str, target_level: int, current_level: int, examples: List[Dict]) -> Dict[str, Any]:
        examples_text = ""
        if examples:
            examples_text = "\n\n## Примеры реальных задач из архива:\n"
            for i, ex in enumerate(examples[:3]):
                text = ex.get('text', ex.get('question', ''))[:500]
                examples_text += f"\n**Пример {i+1}:**\n{text}\n"
        prompt = f"""
Ты – опытный преподаватель математики. Подготовь ОЧЕНЬ ПОДРОБНЫЙ урок по теме "{topic}".

Текущий уровень ученика: {current_level}/100
Целевой уровень: {target_level}/100

{examples_text}

## Требования к уроку:

1. **Теория** – объясни с самых основ, приведи интуитивные примеры, выведи формулы. Используй LaTeX для формул (например, \\(x^2\\)). Объяснение должно быть доступным, с акцентами на сложные моменты.

2. **Примеры** – 5-6 задач разной сложности (от простых до олимпиадных) с пошаговым решением. Каждый пример должен демонстрировать важный приём.

3. **Задачи для самостоятельного решения** – 15-20 задач, разбитых на три уровня: начальный (5-6), средний (5-6), продвинутый (5-8). Для каждой задачи дай ответ и краткую подсказку (hint).

4. **Советы** – 5-7 практических советов, как избежать типичных ошибок, лайфхаки.

5. **Дополнительные ресурсы** – ссылки на Khan Academy (или аналоги) по данной теме (если есть).

Верни JSON формата:
{{
  "theory": "текст теории",
  "examples": [{{"problem": "условие", "solution": "решение"}}],
  "tasks": [{{"task": "задача", "answer": "ответ", "hint": "подсказка"}}],
  "tips": ["совет1", "совет2"],
  "resources": ["https://khanacademy.org/..."]
}}
"""
        response = await self.chat_completion([
            {"role": "system", "content": "Ты опытный преподаватель. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=8000)
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {
            "theory": response,
            "examples": [],
            "tasks": [],
            "tips": [],
            "resources": []
        }
    
    # --- Генерация прогресс-теста (промежуточный) ---
    async def generate_progress_test(self, weak_topics: List[str], exam_details: Dict, num_questions: int = 15) -> List[Dict]:
        prompt = f"""Сгенерируй тест для проверки прогресса по темам: {weak_topics}
        Структура экзамена: {json.dumps(exam_details, ensure_ascii=False)}
        Количество вопросов: {num_questions}
        Верни JSON массив: [{{"topic": "тема", "difficulty": "легкий/средний/сложный", "question": "текст", "correct_answer": "ответ", "explanation": "пояснение"}}]"""
        response = await self.chat_completion([
            {"role": "system", "content": "Ты составитель тестов. Отвечай только JSON массивом."},
            {"role": "user", "content": prompt}
        ], max_tokens=6000)
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Не удалось распарсить JSON: {response}")
        except:
            return []
    
    # --- Генерация задач на основе RAG (используется в _generate_test_with_rag) ---
    async def generate_with_rag_context(self, exam_type: str, topic: str, user_level: int, target_level: int, examples: List[Dict]) -> List[Dict]:
        examples_text = ""
        if examples:
            examples_text = "\n\n## Примеры реальных задач из архива:\n"
            for i, ex in enumerate(examples[:3]):
                text = ex.get('text', ex.get('question', ''))[:500]
                examples_text += f"\n**Пример {i+1}:**\n{text}\n"
        prompt = f"""
Ты составитель экзаменационных задач по теме "{topic}".
Текущий уровень ученика: {user_level}/100
Целевой уровень: {target_level}/100
{examples_text}
Сгенерируй 3-5 задач, похожих по стилю и сложности на примеры.
Для каждой задачи укажи текст, решение, ответ, сложность.
Верни JSON массив: [{{"text": "текст", "solution": "решение", "answer": "ответ", "difficulty": "легкий/средний/сложный"}}]"""
        response = await self.chat_completion([
            {"role": "system", "content": "Ты составитель экзаменационных задач. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000)
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except:
            return []
    
    # --- Ремонт задачи (очистка мусора) ---
    async def repair_task(self, task_text: str) -> str:
        if not task_text or len(task_text.strip()) < 20:
            return task_text
        prompt = f"""
Ты – репетитор по математике. Перед тобой текст задачи, возможно испорченный. Восстанови условие, удали мусор, номера вариантов, фразы "нұсқа" без уравнений. Не додумывай, просто очисти.
Исходный текст: {task_text[:1500]}
Верни ТОЛЬКО исправленный текст задачи.
"""
        try:
            response = await self.chat_completion([
                {"role": "system", "content": "Ты помощник, очищающий тексты математических задач."},
                {"role": "user", "content": prompt}
            ], max_tokens=1000)
            return response.strip() if response.strip() else task_text
        except Exception as e:
            print(f"Ошибка в repair_task: {e}")
            return task_text

deepseek_client = DeepSeekClient()