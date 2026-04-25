# backend/app/services.py
import json
import os
import pickle
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .models import User, Session as SessionModel, TestResult, Lesson, ProgressHistory
from .deepseek_client import deepseek_client
from .config import settings
from .subject_topics import get_modules_for_subject  # ИЗМЕНЕНО: вместо math_topics

# Импортируем RAG
try:
    from .rag import VectorStore, ExamManager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG модуль не загружен")

class AITeacherService:
    def __init__(self):
        self.rag_available = RAG_AVAILABLE
        self.exam_manager = None
        self.vector_store = None
        
        print(f"RAG_AVAILABLE: {RAG_AVAILABLE}")
        if RAG_AVAILABLE:
            try:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                self.vector_store = VectorStore(os.path.join(base_dir, settings.VECTOR_STORE_PATH))
                self.exam_manager = ExamManager(self.vector_store)
                
                # Загрузка индекса для семантического поиска (только для математики)
                index_path = os.path.join(base_dir, "data", "ent", "index_ent.hnsw")
                vectors_path = os.path.join(base_dir, "data", "ent", "vectors.npy")
                metadata_path = os.path.join(base_dir, "data", "ent", "metadata_ent.pkl")
                
                if os.path.exists(index_path) and os.path.exists(vectors_path) and os.path.exists(metadata_path):
                    self.exam_manager.init_ent(index_path, vectors_path, metadata_path)
                    print(f"✅ ЕНТ (семантический поиск) загружен, задач: {len(self.exam_manager.active_exams['ent']['metadata'])}")
                else:
                    print("⚠️ HNSW индекс не найден, используем текстовый поиск")
                    old_metadata = os.path.join(base_dir, settings.ENT_METADATA_PATH)
                    if os.path.exists(old_metadata):
                        with open(old_metadata, 'rb') as f:
                            metadata = pickle.load(f)
                        self.exam_manager.active_exams['ent'] = {
                            'index': None,
                            'vectors': None,
                            'metadata': metadata,
                            'dim': 384
                        }
                        print(f"✅ ЕНТ (текстовый поиск) загружен, задач: {len(metadata)}")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации RAG: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("RAG не доступен")

    @staticmethod
    async def create_user(db: Session, email: str, name: str) -> User:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # НОВОЕ: определение предмета по названию экзамена
    def _get_subject(self, exam_name: str) -> str:
        exam_lower = exam_name.lower()
        if "математик" in exam_lower or "math" in exam_lower:
            return "математика"
        elif "физик" in exam_lower:
            return "физика"
        elif "хими" in exam_lower:
            return "химия"
        elif "биологи" in exam_lower:
            return "биология"
        elif "история казахстана" in exam_lower:
            return "история казахстана"
        elif "всемирная история" in exam_lower or "мировая история" in exam_lower:
            return "всемирная история"
        elif "английск" in exam_lower:
            return "английский язык"
        elif "русский язык" in exam_lower:
            return "русский язык"
        elif "казахский язык" in exam_lower or "қазақ тілі" in exam_lower:
            return "казахский язык"
        elif "географи" in exam_lower:
            return "география"
        else:
            return "математика"  # по умолчанию

    def _get_exam_type(self, exam_name: str) -> str:
        exam_lower = exam_name.lower()
        if 'ент' in exam_lower or 'ent' in exam_lower:
            return 'ent'
        return 'ent'  # по умолчанию
    
# ============== МЕТОД create_session ==============
    async def create_session(self, db: Session, user_id: int, exam_name: str) -> SessionModel:
        exam_type = self._get_exam_type(exam_name)
        exam_details = await deepseek_client.generate_exam_analysis(exam_name)
        target_data = await deepseek_client.generate_target_profile(exam_details)
        target_profile = target_data.get("target_profile", {})
        
        session = SessionModel(
            user_id=user_id,
            exam_name=exam_name,
            exam_details=exam_details,
            target_profile=target_profile,
            current_profile={topic: 0 for topic in target_profile.keys()},
            status="testing"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Определяем предмет для генерации теста
        subject = self._get_subject(exam_name)
        
        # Генерация теста: для математики используем RAG (если доступен), иначе DeepSeek с учётом предмета
        if self.rag_available and subject == "математика":
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15)
        else:
            questions = await deepseek_client.generate_initial_test(exam_details, 15, subject)
        
        test_result = TestResult(
            session_id=session.id,
            test_type="initial",
            questions=questions,
            answers={},
            evaluation={}
        )
        db.add(test_result)
        db.commit()
        return session
    
    # ============== МЕТОД _generate_test_with_rag ==============
    async def _generate_test_with_rag(self, exam_details: Dict, exam_type: str, num_questions: int = 15) -> List[Dict]:
        """
        Генерация теста с использованием RAG (только для математики).
        Для других предметов этот метод не вызывается.
        """
        questions = []
        topics = exam_details.get('topics', [])
        questions_per_topic = max(1, num_questions // len(topics))
        
        for topic_info in topics:
            topic_name = topic_info.get('name', '')
            similar = []
            if self.exam_manager and exam_type in self.exam_manager.active_exams:
                try:
                    similar = self.exam_manager.search_problems(
                        exam_type, 
                        topic_name, 
                        k=questions_per_topic * 2
                    )
                    print(f"  RAG: найдено {len(similar)} задач по теме {topic_name}")
                except Exception as e:
                    print(f"  RAG ошибка: {e}")
            
            import random
            random.shuffle(similar)
            
            # Добавляем найденные задачи из RAG
            for s in similar[:questions_per_topic]:
                if len(questions) < num_questions:
                    question_text = s.get('text', s.get('question', ''))
                    repaired_text = await self._repair_task_if_needed(s.get('id', ''), question_text)
                    questions.append({
                        'topic': topic_name,
                        'difficulty': s.get('difficulty', 'medium'),
                        'question': repaired_text[:2000],
                        'correct_answer': s.get('answer', ''),
                        'explanation': s.get('solution', '')[:2000],
                        'source': 'rag'
                    })
            
            # Если не хватает – генерируем через DeepSeek с примерами
            needed = questions_per_topic - len([q for q in questions if q['topic'] == topic_name])
            if needed > 0:
                examples = similar[:3] if similar else []
                new_questions = await deepseek_client.generate_with_rag_context(
                    exam_type, topic_name, 0, 85, examples
                )
                for q in new_questions[:needed]:
                    if len(questions) < num_questions:
                        questions.append({
                            'topic': topic_name,
                            'difficulty': q.get('difficulty', 'medium'),
                            'question': q.get('text', ''),
                            'correct_answer': q.get('answer', ''),
                            'explanation': q.get('solution', ''),
                            'source': 'generated_from_rag'
                        })
        
        # Если всё равно не хватает – DeepSeek с нуля (fallback)
        if len(questions) < num_questions:
            print(f"  Не хватает вопросов, генерируем через DeepSeek")
            default_questions = await deepseek_client.generate_initial_test(
                exam_details, 
                num_questions - len(questions),
                "математика"  # явно указываем предмет
            )
            for q in default_questions:
                q['source'] = 'deepseek_fallback'
            questions.extend(default_questions)
        
        return questions[:num_questions]
    
    async def generate_lesson_with_rag(self, topic: str, target_level: int, current_level: int, exam_type: str = 'ent', subject: str = 'математика') -> Dict:
        # ИЗМЕНЕНО: RAG используем только для математики
        examples = []
        if subject == "математика" and self.exam_manager and exam_type in self.exam_manager.active_exams:
            examples = self.exam_manager.get_similar_for_generation(exam_type, topic, num_examples=5)
            print(f"  RAG: найдено {len(examples)} примеров для урока по теме {topic}")
        lesson = await deepseek_client.generate_lesson_with_examples(topic, target_level, current_level, examples)
        return lesson

    async def _repair_task_if_needed(self, task_id: str, text: str) -> str:
        if not hasattr(self, '_repair_cache'):
            self._repair_cache = {}
        if len(text) < 50:
            return text
        if task_id in self._repair_cache:
            return self._repair_cache[task_id]
        if len(text) > 200 and not ('нұсқа' in text.lower() and len(text) < 300):
            return text
        try:
            repaired = await deepseek_client.repair_task(text)
            self._repair_cache[task_id] = repaired
            return repaired
        except Exception as e:
            import traceback
            print(f"⚠️ Ошибка ремонта задачи {task_id}:")
            traceback.print_exc()
            return text

    async def generate_progress_test_with_rag(self, weak_topics: List[str], exam_details: Dict, exam_type: str = 'ent', num_questions: int = 10) -> List[Dict]:
        questions = []
        questions_per_topic = max(1, num_questions // len(weak_topics))
        for topic in weak_topics[:5]:
            similar = []
            if self.exam_manager and exam_type in self.exam_manager.active_exams:
                similar = self.exam_manager.search_problems(exam_type, topic, k=questions_per_topic)
                print(f"  RAG: найдено {len(similar)} задач по теме {topic}")
            for s in similar[:questions_per_topic]:
                if len(questions) < num_questions:
                    questions.append({
                        'topic': topic,
                        'difficulty': s.get('difficulty', 'medium'),
                        'question': s.get('text', s.get('question', ''))[:2000],
                        'correct_answer': s.get('answer', ''),
                        'explanation': s.get('solution', '')[:500],
                        'source': 'rag'
                    })
            needed = questions_per_topic - len([q for q in questions if q['topic'] == topic])
            if needed > 0:
                new_questions = await deepseek_client.generate_progress_test([topic], exam_details, needed)
                for q in new_questions:
                    if len(questions) < num_questions:
                        q['source'] = 'generated'
                        questions.append(q)
        return questions[:num_questions]

    @staticmethod
    async def submit_test(db: Session, session_id: int, user_answers: Dict[str, str]) -> Dict[str, Any]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        test = db.query(TestResult).filter(TestResult.session_id == session_id, TestResult.test_type == "initial").first()
        if not test:
            raise ValueError("Test not found")
        test.answers = user_answers
        evaluation = await deepseek_client.evaluate_answers(test.questions, user_answers, session.exam_details)
        test.evaluation = evaluation
        test.score = evaluation.get("overall_score", 0)
        session.current_profile = evaluation.get("topic_scores", {})
        db.commit()
        return evaluation

    # ИЗМЕНЕНО: теперь используем subject_topics и передаём предмет
    def _build_plan_from_weak_topics(self, weak_topics: List[str], subject: str) -> Dict:
        """
        Строит план обучения только из модулей, содержащих слабые темы.
        Если слабых тем нет или их очень мало, добавляет базовые модули.
        """
        all_modules = get_modules_for_subject(subject)
        
        # Преобразуем weak_topics в множество для быстрого поиска
        weak_set = set(weak_topics)
        
        # Отбираем модули, у которых хотя бы одна тема есть в weak_set
        selected_modules = []
        for module in all_modules:
            # Проверяем, есть ли пересечение тем модуля со слабыми темами
            topics_set = set(module.get("topics", []))
            if topics_set.intersection(weak_set):
                selected_modules.append(module)
        
        # Если после фильтрации не осталось модулей (слабых тем нет или они не совпали),
        # добавляем первые 3 базовых модуля (например, алгебра 5-6, 7, 8 классы)
        if not selected_modules:
            selected_modules = all_modules[:3]
        
        # Сортируем модули по количеству совпадающих слабых тем (убывание)
        selected_modules.sort(
            key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
            reverse=True
        )
        
        return {
            "modules": selected_modules,
            "total_modules": len(selected_modules),
            "strategy": f"Адаптивный план по {subject}. Изучаются только темы, в которых вы допустили ошибки."
        }

    async def set_time_and_plan(self, db: Session, session_id: int, days: int) -> Dict[str, Any]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        subject = self._get_subject(session.exam_name)
        
        # Получаем weak_topics из последнего теста (начального)
        last_test = db.query(TestResult).filter(
            TestResult.session_id == session_id
        ).order_by(TestResult.id.desc()).first()
        
        weak_topics = []
        if last_test and last_test.evaluation:
            weak_topics = last_test.evaluation.get("weak_topics", [])
        
        # Строим адаптивный план
        study_plan = self._build_plan_from_weak_topics(weak_topics, subject)
        
        # Удаляем старые уроки
        db.query(Lesson).filter(Lesson.session_id == session.id).delete()
        db.commit()
        
        session.study_plan = study_plan
        session.time_available_days = days
        session.status = "planning"
        
        # Создаём первый урок (первая тема первого модуля)
        modules = study_plan.get("modules", [])
        if modules:
            first_module = modules[0]
            first_topic = first_module["topics"][0] if first_module["topics"] else "Математика"
            lesson_content = await self.generate_lesson_with_rag(
                first_topic,
                session.target_profile.get(first_topic, 80),
                session.current_profile.get(first_topic, 0),
                'ent',
                subject
            )
            lesson = Lesson(
                session_id=session.id,
                topic=first_topic,
                content=json.dumps(lesson_content, ensure_ascii=False),
                tasks=lesson_content.get("tasks", [])
            )
            db.add(lesson)
            print(f"Создан первый урок по теме {first_topic}")
        
        session.status = "learning"
        db.commit()
        return study_plan

    async def get_next_lesson(self, db: Session, session_id: int) -> Dict[str, Any]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        # Проверяем, есть ли незавершённый урок
        lesson = db.query(Lesson).filter(Lesson.session_id == session_id, Lesson.completed == False).order_by(Lesson.id).first()
        if lesson:
            try:
                lesson_content = json.loads(lesson.content) if lesson.content else {}
            except:
                lesson_content = {"theory": lesson.content, "examples": [], "tasks": lesson.tasks}
            return {
                "status": "lesson",
                "lesson_id": lesson.id,
                "topic": lesson.topic,
                "content": lesson_content,
                "completed": lesson.completed
            }
        
        # Если нет незавершённых, ищем следующую тему
        study_plan = session.study_plan
        modules = study_plan.get("modules", [])
        all_topics_in_order = []
        for module in modules:
            all_topics_in_order.extend(module.get("topics", []))
        
        completed_lessons = db.query(Lesson).filter(
            Lesson.session_id == session_id,
            Lesson.completed == True
        ).all()
        completed_topics = {l.topic for l in completed_lessons}
        
        next_topic = None
        for topic in all_topics_in_order:
            if topic not in completed_topics:
                next_topic = topic
                break
        
        if not next_topic:
            session.status = "completed"
            db.commit()
            return {"status": "completed", "message": "Поздравляем! Вы успешно завершили курс!"}
        
        subject = self._get_subject(session.exam_name)  # НОВОЕ
        lesson_content = await self.generate_lesson_with_rag(
            next_topic,
            session.target_profile.get(next_topic, 80),
            session.current_profile.get(next_topic, 0),
            'ent',
            subject
        )
        new_lesson = Lesson(
            session_id=session.id,
            topic=next_topic,
            content=json.dumps(lesson_content, ensure_ascii=False),
            tasks=lesson_content.get("tasks", [])
        )
        db.add(new_lesson)
        db.commit()
        
        return {
            "status": "lesson",
            "lesson_id": new_lesson.id,
            "topic": next_topic,
            "content": lesson_content,
            "completed": False
        }
    
    async def check_lesson_answers(self, lesson: Lesson, user_answers: Dict[str, str]) -> Dict[str, Any]:
        """Проверяет ответы и возвращает подсказки для неправильных."""
        try:
            lesson_content = json.loads(lesson.content) if lesson.content else {}
        except:
            lesson_content = {}
        tasks = lesson_content.get("tasks", [])
        results = []
        all_correct = True
        for i, task in enumerate(tasks):
            user_ans = user_answers.get(str(i), "").strip().lower()
            correct_ans = task.get("answer", "").strip().lower()
            is_correct = (user_ans == correct_ans)
            if not is_correct:
                all_correct = False
            hint = task.get("hint", "Проверьте решение. Возможно, нужно применить формулу или правило.")
            results.append({
                "task_index": i,
                "correct": is_correct,
                "hint": hint if not is_correct else None
            })
        return {"all_correct": all_correct, "results": results}

    async def submit_lesson(self, db: Session, session_id: int, lesson_id: int, user_answers: Dict[str, str]) -> Dict[str, Any]:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.session_id == session_id).first()
        if not lesson:
            raise ValueError("Lesson not found")
        
        check = await self.check_lesson_answers(lesson, user_answers)
        if not check["all_correct"]:
            return {
                "status": "failed",
                "message": "Некоторые ответы неправильные. Исправьте их.",
                "results": check["results"]
            }
        
        lesson.completed = True
        lesson.completed_at = datetime.utcnow()
        db.commit()
        
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        new_level = 0
        if session:
            current = session.current_profile.get(lesson.topic, 0)
            new_level = min(100, current + 10)
            session.current_profile[lesson.topic] = new_level
            progress = ProgressHistory(session_id=session_id, profile_snapshot=session.current_profile.copy())
            db.add(progress)
            db.commit()
        
        return {
            "status": "success",
            "score": 100,
            "new_level": new_level,
            "message": "Урок успешно завершён!"
        }

    async def generate_progress_test(self, db: Session, session_id: int) -> List[Dict[str, Any]]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        weak_topics = []
        for topic, target_level in session.target_profile.items():
            current_level = session.current_profile.get(topic, 0)
            if target_level - current_level > 20:
                weak_topics.append(topic)
        if not weak_topics:
            weak_topics = list(session.target_profile.keys())[:5]
        exam_type = self._get_exam_type(session.exam_name)
        if self.rag_available and exam_type in self.exam_manager.active_exams:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, num_questions=15)
        else:
            questions = await deepseek_client.generate_progress_test(weak_topics, session.exam_details, num_questions=15)
        test_result = TestResult(
            session_id=session.id,
            test_type="progress",
            questions=questions,
            answers={},
            evaluation={}
        )
        db.add(test_result)
        db.commit()
        return questions

    # НОВОЕ: метод для чата с ботом (уже был, оставляем)
    async def chat_with_bot(self, db: Session, session_id: int, lesson_id: int, question: str) -> str:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not session or not lesson:
            return "Извините, не удалось найти контекст урока."
        topic = lesson.topic
        weak_topics = [t for t, score in session.current_profile.items() if score < 50]
        prompt = f"""
Ты – ИИ-помощник по математике. Ученик изучает тему "{topic}".
Его слабые темы (по входному тесту): {', '.join(weak_topics) if weak_topics else 'не определены'}.
Вопрос ученика: {question}

Дай понятный, подробный ответ, объясни шаги решения, если нужно. Используй формулы в LaTeX (например, \\(x^2\\)).
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты полезный помощник по математике. Отвечай дружелюбно и понятно."},
            {"role": "user", "content": prompt}
        ], max_tokens=1000)
        return response