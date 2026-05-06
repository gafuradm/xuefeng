# backend/app/services.py
import json
import os
import pickle
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .context_service import ContextService
from .models import User, Session as SessionModel, TestResult, Lesson, ProgressHistory
from .deepseek_client import deepseek_client
from .config import settings
import yt_dlp
import whisper
from pathlib import Path
import shutil
from .models import (
    User, Session as SessionModel, TestResult, Lesson, 
    ProgressHistory, UserCourse, CourseModule, CourseLesson, 
    UserLesson, UserInteraction, UserPerformance  # <-- добавить UserPerformance
)
from .subject_topics import (
    get_modules_for_subject, get_default_tasks,
    get_gaokao_modules, GAOKAO_TOPICS,
    get_ege_modules, EGE_TOPICS,
    get_sat_modules, SAT_TOPICS,
    get_uzbek_modules, UZBEK_TOPICS,
    get_india_modules, INDIA_TOPICS
)

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
        self.gaokao_manager = None
        self.ege_manager = None
        self.sat_manager = None
        self.uzbek_manager = None
        self.india_manager = None
        
        print(f"RAG_AVAILABLE: {RAG_AVAILABLE}")
        if RAG_AVAILABLE:
            try:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                self.vector_store = VectorStore(os.path.join(base_dir, settings.VECTOR_STORE_PATH))
                self.exam_manager = ExamManager(self.vector_store)
                
                # ---------------------------- ЕНТ ---------------------------------
                index_path = os.path.join(base_dir, "data", "ent", "index_ent.hnsw")
                vectors_path = os.path.join(base_dir, "data", "ent", "vectors.npy")
                metadata_path = os.path.join(base_dir, "data", "ent", "metadata_ent.pkl")
                if os.path.exists(index_path) and os.path.exists(vectors_path) and os.path.exists(metadata_path):
                    self.exam_manager.init_ent(index_path, vectors_path, metadata_path, exam_key='ent')
                    print(f"✅ ЕНТ загружен, задач: {len(self.exam_manager.active_exams['ent']['metadata'])}")
                else:
                    print("⚠️ HNSW индекс ЕНТ не найден")
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
                
                # ---------------------------- GAOKAO ---------------------------------
                gaokao_index = os.path.join(base_dir, "data", "vector_stores", "gaokao", "index.hnsw")
                gaokao_vectors = os.path.join(base_dir, "data", "vector_stores", "gaokao", "vectors.npy")
                gaokao_metadata = os.path.join(base_dir, "data", "vector_stores", "gaokao", "metadata.pkl")
                if os.path.exists(gaokao_index) and os.path.exists(gaokao_vectors) and os.path.exists(gaokao_metadata):
                    self.gaokao_manager = ExamManager(self.vector_store)
                    self.gaokao_manager.init_ent(gaokao_index, gaokao_vectors, gaokao_metadata, exam_key='gaokao')
                    print(f"✅ GAOKAO загружен, задач: {len(self.gaokao_manager.active_exams['gaokao']['metadata'])}")
                else:
                    print("⚠️ Файлы GAOKAO не найдены")
                    self.gaokao_manager = None
                
                # ---------------------------- ЕГЭ ---------------------------------
                ege_index = os.path.join(base_dir, "data", "vector_stores", "ege", "index.hnsw")
                ege_vectors = os.path.join(base_dir, "data", "vector_stores", "ege", "vectors.npy")
                ege_metadata = os.path.join(base_dir, "data", "vector_stores", "ege", "metadata.pkl")
                if os.path.exists(ege_index) and os.path.exists(ege_vectors) and os.path.exists(ege_metadata):
                    self.ege_manager = ExamManager(self.vector_store)
                    self.ege_manager.init_ent(ege_index, ege_vectors, ege_metadata, exam_key='ege')
                    print(f"✅ ЕГЭ загружен, задач: {len(self.ege_manager.active_exams['ege']['metadata'])}")
                else:
                    print("⚠️ Файлы ЕГЭ не найдены")
                    self.ege_manager = None
                
                # ---------------------------- SAT ---------------------------------
                sat_index = os.path.join(base_dir, "data", "vector_stores", "sat", "index.hnsw")
                sat_vectors = os.path.join(base_dir, "data", "vector_stores", "sat", "vectors.npy")
                sat_metadata = os.path.join(base_dir, "data", "vector_stores", "sat", "metadata.pkl")
                if os.path.exists(sat_index) and os.path.exists(sat_vectors) and os.path.exists(sat_metadata):
                    self.sat_manager = ExamManager(self.vector_store)
                    self.sat_manager.init_ent(sat_index, sat_vectors, sat_metadata, exam_key='sat')
                    print(f"✅ SAT загружен, задач: {len(self.sat_manager.active_exams['sat']['metadata'])}")
                else:
                    print("⚠️ Файлы SAT не найдены")
                    self.sat_manager = None
                
                # ---------------------------- УЗБЕКИСТАН ---------------------------------
                uzbek_index = os.path.join(base_dir, "data", "vector_stores", "uzbek", "index.hnsw")
                uzbek_vectors = os.path.join(base_dir, "data", "vector_stores", "uzbek", "vectors.npy")
                uzbek_metadata = os.path.join(base_dir, "data", "vector_stores", "uzbek", "metadata.pkl")
                if os.path.exists(uzbek_index) and os.path.exists(uzbek_vectors) and os.path.exists(uzbek_metadata):
                    self.uzbek_manager = ExamManager(self.vector_store)
                    self.uzbek_manager.init_ent(uzbek_index, uzbek_vectors, uzbek_metadata, exam_key='uzbek')
                    print(f"✅ Узбекистан загружен, задач: {len(self.uzbek_manager.active_exams['uzbek']['metadata'])}")
                else:
                    print("⚠️ Файлы Узбекистана не найдены")
                    self.uzbek_manager = None
                
                # ---------------------------- ИНДИЯ ---------------------------------
                india_index = os.path.join(base_dir, "data", "vector_stores", "india", "index.hnsw")
                india_vectors = os.path.join(base_dir, "data", "vector_stores", "india", "vectors.npy")
                india_metadata = os.path.join(base_dir, "data", "vector_stores", "india", "metadata.pkl")
                if os.path.exists(india_index) and os.path.exists(india_vectors) and os.path.exists(india_metadata):
                    self.india_manager = ExamManager(self.vector_store)
                    self.india_manager.init_ent(india_index, india_vectors, india_metadata, exam_key='india')
                    print(f"✅ Индия загружен, задач: {len(self.india_manager.active_exams['india']['metadata'])}")
                else:
                    print("⚠️ Файлы Индии не найдены")
                    self.india_manager = None
                    
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

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    def _is_ege(self, exam_name: str) -> bool:
        exam_lower = exam_name.lower()
        return 'егэ' in exam_lower or 'ege' in exam_lower

    def _is_gaokao(self, exam_name: str) -> bool:
        exam_lower = exam_name.lower()
        return 'gaokao' in exam_lower or 'гаокао' in exam_lower

    def _is_sat(self, exam_name: str) -> bool:
        exam_lower = exam_name.lower()
        return 'sat' in exam_lower

    def _is_uzbek(self, exam_name: str) -> bool:
        exam_lower = exam_name.lower()
        return 'uzbek' in exam_lower or 'узбек' in exam_lower or 'dtm' in exam_lower

    def _is_india(self, exam_name: str) -> bool:
        exam_lower = exam_name.lower()
        return 'india' in exam_lower or 'jee' in exam_lower or 'neet' in exam_lower

    def _get_exam_type(self, exam_name: str) -> str:
        exam_lower = exam_name.lower()
        if 'ент' in exam_lower or 'ent' in exam_lower:
            return 'ent'
        elif self._is_gaokao(exam_name):
            return 'gaokao'
        elif self._is_ege(exam_name):
            return 'ege'
        elif self._is_sat(exam_name):
            return 'sat'
        elif self._is_uzbek(exam_name):
            return 'uzbek'
        elif self._is_india(exam_name):
            return 'india'
        return 'ent'
    
    # backend/app/services.py (добавить в класс AITeacherService)

    import os
    import subprocess
    import whisper
    import yt_dlp
    from pathlib import Path

    async def process_video(self, url: str, target_language: str) -> Dict[str, Any]:
        """Скачивает видео с YouTube, извлекает аудио, распознаёт речь, переводит текст."""
        # Создаём временную папку
        temp_dir = Path("temp_video")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # 1. Скачиваем аудио
            audio_path = await self._download_audio(url, temp_dir)
            # 2. Распознаём речь
            transcript = await self._transcribe_audio(audio_path)
            # 3. Переводим на целевой язык
            translation = await self._translate_text(transcript, target_language)
            return {
                "original_text": transcript,
                "translated_text": translation,
                "language": target_language
            }
        finally:
            # Очищаем временные файлы
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _download_audio(self, url: str, output_dir: Path) -> Path:
        """Скачивает аудио с YouTube и возвращает путь к файлу"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Ищем созданный файл
            base = output_dir / info['title']
            audio_file = base.with_suffix('.mp3')
            # Если файл не существует, ищем другой
            if not audio_file.exists():
                for f in output_dir.glob("*"):
                    if f.suffix in ['.mp3', '.m4a', '.webm']:
                        audio_file = f
                        break
            return audio_file

    async def _transcribe_audio(self, audio_path: Path) -> str:
        """Распознаёт речь через Whisper (локально)"""
        model = whisper.load_model("base")  # можно "small", "medium" для качества
        result = model.transcribe(str(audio_path), language="ru", task="transcribe")
        return result["text"]

    async def _translate_text(self, text: str, target_language: str) -> str:
        """Переводит текст через DeepSeek"""
        prompt = f"Переведи следующий текст на {target_language} язык:\n\n{text}"
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты профессиональный переводчик. Отвечай только переведённым текстом без пояснений."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000)
        return response.strip()

    def _get_subject(self, exam_name: str) -> str:
        exam_lower = exam_name.lower()
        
        # GAOKAO
        if self._is_gaokao(exam_name):
            if "math" in exam_lower or "数学" in exam_lower:
                return "математика"
            elif "physics" in exam_lower or "物理" in exam_lower:
                return "физика"
            elif "chemistry" in exam_lower or "化学" in exam_lower:
                return "химия"
            elif "biology" in exam_lower or "生物" in exam_lower:
                return "биология"
            elif "history" in exam_lower or "历史" in exam_lower:
                return "история"
            elif "geography" in exam_lower or "地理" in exam_lower:
                return "география"
            elif "politics" in exam_lower or "政治" in exam_lower:
                return "политика"
            elif "chinese" in exam_lower or "语文" in exam_lower:
                return "китайский язык"
            elif "english" in exam_lower:
                return "английский язык"
            else:
                return "математика"
        
        # ЕГЭ
        if self._is_ege(exam_name):
            if "русский" in exam_lower:
                return "русский язык"
            elif "математик" in exam_lower:
                return "математика"
            elif "физик" in exam_lower:
                return "физика"
            elif "хими" in exam_lower:
                return "химия"
            elif "биологи" in exam_lower:
                return "биология"
            elif "история" in exam_lower:
                return "история"
            elif "обществ" in exam_lower:
                return "обществознание"
            elif "географ" in exam_lower:
                return "география"
            elif "информатик" in exam_lower:
                return "информатика"
            elif "литератур" in exam_lower:
                return "литература"
            else:
                return "математика"
        
        # SAT
        if self._is_sat(exam_name):
            if "math" in exam_lower:
                return "математика"
            elif "reading" in exam_lower or "writing" in exam_lower or "essay" in exam_lower:
                return "чтение и письмо"
            else:
                return "математика"
        
        # Узбекистан
        if self._is_uzbek(exam_name):
            if "matematika" in exam_lower or "математик" in exam_lower:
                return "математика"
            elif "fizika" in exam_lower or "физик" in exam_lower:
                return "физика"
            elif "kimyo" in exam_lower or "хими" in exam_lower:
                return "химия"
            elif "biologiya" in exam_lower or "биологи" in exam_lower:
                return "биология"
            elif "tarix" in exam_lower or "история" in exam_lower:
                return "история узбекистана"
            elif "ona tili" in exam_lower or "узбекский язык" in exam_lower:
                return "узбекский язык и литература"
            elif "adabiyot" in exam_lower:
                return "узбекский язык и литература"
            else:
                return "математика"
        
        # Индия
        if self._is_india(exam_name):
            if "math" in exam_lower:
                return "математика"
            elif "physics" in exam_lower:
                return "физика"
            elif "chemistry" in exam_lower:
                return "химия"
            elif "biology" in exam_lower or "neet" in exam_lower:
                return "биология"
            else:
                return "математика"
        
        # ЕНТ (по умолчанию)
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
            return "математика"

    # ==================== СОЗДАНИЕ СЕССИИ ====================
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
        
        subject = self._get_subject(exam_name)
        is_gaokao = self._is_gaokao(exam_name)
        is_ege = self._is_ege(exam_name)
        is_sat = self._is_sat(exam_name)
        is_uzbek = self._is_uzbek(exam_name)
        is_india = self._is_india(exam_name)
        
        # Генерация теста с использованием соответствующего RAG менеджера
        if is_gaokao and self.gaokao_manager is not None:
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.gaokao_manager, store_key='gaokao')
        elif is_ege and self.ege_manager is not None:
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.ege_manager, store_key='ege')
        elif is_sat and self.sat_manager is not None:
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.sat_manager, store_key='sat')
        elif is_uzbek and self.uzbek_manager is not None:
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.uzbek_manager, store_key='uzbek')
        elif is_india and self.india_manager is not None:
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.india_manager, store_key='india')
        elif self.rag_available and subject == "математика" and exam_type == "ent":
            questions = await self._generate_test_with_rag(exam_details, exam_type, num_questions=15, manager=self.exam_manager, store_key='ent')
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

    # ==================== ГЕНЕРАЦИЯ ТЕСТА С RAG ====================
    async def _generate_test_with_rag(self, exam_details: Dict, exam_type: str, num_questions: int = 15, manager=None, store_key='ent') -> List[Dict]:
        if manager is None:
            return await deepseek_client.generate_initial_test(exam_details, num_questions, "general")
        
        questions = []
        topics = exam_details.get('topics', [])
        questions_per_topic = max(1, num_questions // len(topics))
        
        for topic_info in topics:
            topic_name = topic_info.get('name', '')
            similar = []
            if manager and store_key in manager.active_exams:
                try:
                    similar = manager.search_problems(
                        store_key, 
                        topic_name, 
                        k=questions_per_topic * 2
                    )
                    print(f"  RAG: найдено {len(similar)} задач по теме {topic_name}")
                except Exception as e:
                    print(f"  RAG ошибка: {e}")
            
            import random
            random.shuffle(similar)
            
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
        
        if len(questions) < num_questions:
            print(f"  Не хватает вопросов, генерируем через DeepSeek")
            default_questions = await deepseek_client.generate_initial_test(
                exam_details, 
                num_questions - len(questions),
                "general"
            )
            for q in default_questions:
                q['source'] = 'deepseek_fallback'
            questions.extend(default_questions)
        
        return questions[:num_questions]

    # ==================== ГЕНЕРАЦИЯ УРОКА С RAG ====================
    async def generate_lesson_with_rag(self, topic: str, target_level: int, current_level: int, exam_type: str = 'ent', subject: str = 'математика', is_gaokao: bool = False, is_ege: bool = False, is_sat: bool = False, is_uzbek: bool = False, is_india: bool = False) -> Dict:
        examples = []
        
        if is_india and self.india_manager and 'india' in self.india_manager.active_exams:
            examples = self.india_manager.get_similar_for_generation('india', topic, num_examples=5)
            print(f"  RAG (India): найдено {len(examples)} примеров для урока по теме {topic}")
        elif is_uzbek and self.uzbek_manager and 'uzbek' in self.uzbek_manager.active_exams:
            examples = self.uzbek_manager.get_similar_for_generation('uzbek', topic, num_examples=5)
            print(f"  RAG (Узбекистан): найдено {len(examples)} примеров для урока по теме {topic}")
        elif is_sat and self.sat_manager and 'sat' in self.sat_manager.active_exams:
            examples = self.sat_manager.get_similar_for_generation('sat', topic, num_examples=5)
            print(f"  RAG (SAT): найдено {len(examples)} примеров для урока по теме {topic}")
        elif is_gaokao and self.gaokao_manager and 'gaokao' in self.gaokao_manager.active_exams:
            examples = self.gaokao_manager.get_similar_for_generation('gaokao', topic, num_examples=5)
            print(f"  RAG (GAOKAO): найдено {len(examples)} примеров для урока по теме {topic}")
        elif is_ege and self.ege_manager and 'ege' in self.ege_manager.active_exams:
            examples = self.ege_manager.get_similar_for_generation('ege', topic, num_examples=5)
            print(f"  RAG (ЕГЭ): найдено {len(examples)} примеров для урока по теме {topic}")
        elif not is_gaokao and not is_ege and not is_sat and not is_uzbek and not is_india and subject == "математика" and self.exam_manager and exam_type in self.exam_manager.active_exams:
            examples = self.exam_manager.get_similar_for_generation(exam_type, topic, num_examples=5)
            print(f"  RAG: найдено {len(examples)} примеров для урока по теме {topic}")
        
        lesson = await deepseek_client.generate_lesson_with_examples(topic, target_level, current_level, examples, subject)
        
        if not lesson.get("tasks"):
            default_tasks = get_default_tasks(subject, num_tasks=5)
            lesson["tasks"] = default_tasks
            print(f"  Добавлены типовые задачи для {subject}")
        
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

    async def generate_progress_test_with_rag(self, weak_topics: List[str], exam_details: Dict, exam_type: str = 'ent', num_questions: int = 10, manager=None, store_key='ent') -> List[Dict]:
        if manager is None:
            manager = self.exam_manager
        
        questions = []
        questions_per_topic = max(1, num_questions // len(weak_topics))
        for topic in weak_topics[:5]:
            similar = []
            if manager and store_key in manager.active_exams:
                similar = manager.search_problems(store_key, topic, k=questions_per_topic)
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
        
        # Сохраняем результаты теста в статистику по темам
        topic_scores = evaluation.get("topic_scores", {})
        for topic, score in topic_scores.items():
            # Для каждой темы считаем количество правильных ответов
            # (упрощённо: если score > 60 считаем тему усвоенной)
            is_correct = score >= 60
            await ContextService.update_performance(db, session.user_id, topic, is_correct)
        
        return evaluation

    # ==================== ПОСТРОЕНИЕ ПЛАНА ====================
    def _build_plan_from_weak_topics(self, weak_topics: List[str], exam_name: str, subject: str) -> Dict:
        weak_set = set(weak_topics)
        
        # GAOKAO
        if self._is_gaokao(exam_name):
            modules = get_gaokao_modules(subject)
            selected_modules = []
            for module in modules:
                topics_set = set(module.get("topics", []))
                if topics_set.intersection(weak_set):
                    selected_modules.append(module)
            if not selected_modules:
                selected_modules = modules[:min(3, len(modules))]
            selected_modules.sort(
                key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
                reverse=True
            )
            return {
                "modules": selected_modules,
                "total_modules": len(selected_modules),
                "strategy": f"Адаптивный план по GAOKAO {subject}. Изучаются только темы, в которых вы допустили ошибки."
            }
        
        # ЕГЭ
        if self._is_ege(exam_name):
            modules = get_ege_modules(subject)
            selected_modules = []
            for module in modules:
                topics_set = set(module.get("topics", []))
                if topics_set.intersection(weak_set):
                    selected_modules.append(module)
            if not selected_modules:
                selected_modules = modules[:min(3, len(modules))]
            selected_modules.sort(
                key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
                reverse=True
            )
            return {
                "modules": selected_modules,
                "total_modules": len(selected_modules),
                "strategy": f"Адаптивный план по ЕГЭ {subject}. Изучаются только темы, в которых вы допустили ошибки."
            }
        
        # SAT
        if self._is_sat(exam_name):
            modules = get_sat_modules(subject)
            selected_modules = []
            for module in modules:
                topics_set = set(module.get("topics", []))
                if topics_set.intersection(weak_set):
                    selected_modules.append(module)
            if not selected_modules:
                selected_modules = modules[:min(3, len(modules))]
            selected_modules.sort(
                key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
                reverse=True
            )
            return {
                "modules": selected_modules,
                "total_modules": len(selected_modules),
                "strategy": f"Адаптивный план по SAT {subject}. Изучаются только темы, в которых вы допустили ошибки."
            }
        
        # Узбекистан
        if self._is_uzbek(exam_name):
            modules = get_uzbek_modules(subject)
            selected_modules = []
            for module in modules:
                topics_set = set(module.get("topics", []))
                if topics_set.intersection(weak_set):
                    selected_modules.append(module)
            if not selected_modules:
                selected_modules = modules[:min(3, len(modules))]
            selected_modules.sort(
                key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
                reverse=True
            )
            return {
                "modules": selected_modules,
                "total_modules": len(selected_modules),
                "strategy": f"Адаптивный план по {subject} (Узбекистан). Изучаются только темы, в которых вы допустили ошибки."
            }
        
        # Индия
        if self._is_india(exam_name):
            modules = get_india_modules(subject)
            selected_modules = []
            for module in modules:
                topics_set = set(module.get("topics", []))
                if topics_set.intersection(weak_set):
                    selected_modules.append(module)
            if not selected_modules:
                selected_modules = modules[:min(3, len(modules))]
            selected_modules.sort(
                key=lambda m: len(set(m.get("topics", [])).intersection(weak_set)),
                reverse=True
            )
            return {
                "modules": selected_modules,
                "total_modules": len(selected_modules),
                "strategy": f"Адаптивный план по {subject} (Индия). Изучаются только темы, в которых вы допустили ошибки."
            }
        
        # ЕНТ (по умолчанию)
        all_modules = get_modules_for_subject(subject)
        selected_modules = []
        for module in all_modules:
            topics_set = set(module.get("topics", []))
            if topics_set.intersection(weak_set):
                selected_modules.append(module)
        if not selected_modules:
            selected_modules = all_modules[:min(3, len(all_modules))]
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
        is_gaokao = self._is_gaokao(session.exam_name)
        is_ege = self._is_ege(session.exam_name)
        is_sat = self._is_sat(session.exam_name)
        is_uzbek = self._is_uzbek(session.exam_name)
        is_india = self._is_india(session.exam_name)
        
        last_test = db.query(TestResult).filter(
            TestResult.session_id == session_id
        ).order_by(TestResult.id.desc()).first()
        
        weak_topics = []
        if last_test and last_test.evaluation:
            weak_topics = last_test.evaluation.get("weak_topics", [])
        
        study_plan = self._build_plan_from_weak_topics(weak_topics, session.exam_name, subject)
        
        db.query(Lesson).filter(Lesson.session_id == session.id).delete()
        db.commit()
        
        session.study_plan = study_plan
        session.time_available_days = days
        session.status = "planning"
        
        modules = study_plan.get("modules", [])
        if modules:
            first_module = modules[0]
            first_topic = first_module["topics"][0] if first_module["topics"] else "Начало"
            lesson_content = await self.generate_lesson_with_rag(
                first_topic,
                session.target_profile.get(first_topic, 80),
                session.current_profile.get(first_topic, 0),
                'ent',
                subject,
                is_gaokao,
                is_ege,
                is_sat,
                is_uzbek,
                is_india
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
        
        subject = self._get_subject(session.exam_name)
        is_gaokao = self._is_gaokao(session.exam_name)
        is_ege = self._is_ege(session.exam_name)
        is_sat = self._is_sat(session.exam_name)
        is_uzbek = self._is_uzbek(session.exam_name)
        is_india = self._is_india(session.exam_name)
        lesson_content = await self.generate_lesson_with_rag(
            next_topic,
            session.target_profile.get(next_topic, 80),
            session.current_profile.get(next_topic, 0),
            'ent',
            subject,
            is_gaokao,
            is_ege,
            is_sat,
            is_uzbek,
            is_india
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
    
    # ==================== ПРОВЕРКА ОТВЕТОВ ====================
    async def check_lesson_answers(self, lesson: Lesson, user_answers: Dict[str, str]) -> Dict[str, Any]:
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
        
        try:
            lesson_content = json.loads(lesson.content) if lesson.content else {}
        except:
            lesson_content = {}
        tasks = lesson_content.get("tasks", [])
        if not tasks:
            lesson.completed = True
            lesson.completed_at = datetime.utcnow()
            db.commit()
            return {
                "status": "success",
                "score": 100,
                "new_level": 0,
                "message": "Урок успешно завершён (без задач)"
            }
        
        # Проверяем ответы и обновляем статистику по каждой задаче
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        results = []
        all_correct = True
        correct_count = 0
        
        for i, task in enumerate(tasks):
            user_ans = user_answers.get(str(i), "").strip().lower()
            correct_ans = task.get("answer", "").strip().lower()
            is_correct = (user_ans == correct_ans)
            if is_correct:
                correct_count += 1
            else:
                all_correct = False
            
            # Обновляем статистику по теме
            if session:
                await ContextService.update_performance(
                    db, session.user_id, lesson.topic, is_correct
                )
            
            hint = task.get("hint", "Проверьте решение. Возможно, нужно применить формулу или правило.")
            results.append({
                "task_index": i,
                "correct": is_correct,
                "hint": hint if not is_correct else None
            })
        
        if not all_correct:
            return {
                "status": "failed",
                "message": f"Правильных ответов: {correct_count}/{len(tasks)}. Исправьте ошибки.",
                "results": results
            }
        
        lesson.completed = True
        lesson.completed_at = datetime.utcnow()
        db.commit()
        
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
            "message": f"Урок успешно завершён! Правильных ответов: {correct_count}/{len(tasks)}"
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
        is_gaokao = self._is_gaokao(session.exam_name)
        is_ege = self._is_ege(session.exam_name)
        is_sat = self._is_sat(session.exam_name)
        is_uzbek = self._is_uzbek(session.exam_name)
        is_india = self._is_india(session.exam_name)
        
        if is_gaokao and self.gaokao_manager is not None:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.gaokao_manager, 'gaokao')
        elif is_ege and self.ege_manager is not None:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.ege_manager, 'ege')
        elif is_sat and self.sat_manager is not None:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.sat_manager, 'sat')
        elif is_uzbek and self.uzbek_manager is not None:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.uzbek_manager, 'uzbek')
        elif is_india and self.india_manager is not None:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.india_manager, 'india')
        elif self.rag_available and exam_type in self.exam_manager.active_exams:
            questions = await self.generate_progress_test_with_rag(weak_topics, session.exam_details, exam_type, 15, self.exam_manager, 'ent')
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

    # ==================== ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ ====================
    async def _custom_train(self, prompt: str) -> str:
        """Обучает ИИ на основе пользовательского теста"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты – ИИ учитель, который запоминает структуру тестов и может генерировать похожие вопросы."},
            {"role": "user", "content": prompt}
        ], max_tokens=500)
        return response.strip()

    async def _generate_similar_from_custom(self, examples_text: str, num_questions: int = 5) -> str:
        """Генерирует похожие вопросы на основе примеров"""
        prompt = f"""
Ты – генератор тестов. Пользователь предоставил примеры своих вопросов:

{examples_text}

На основе этих примеров, сгенерируй {num_questions} НОВЫХ вопросов в ТОМ ЖЕ СТИЛЕ и ТОЙ ЖЕ СЛОЖНОСТИ.
Каждый вопрос должен быть оригинальным, но похожим по структуре, формулировкам и сложности.
Для каждого вопроса укажи текст, правильный ответ и пояснение.

Верни ТОЛЬКО JSON массив:
[
  {{"question": "текст вопроса", "correct_answer": "ответ", "explanation": "пояснение"}}
]
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты генератор тестов. Отвечай только JSON массивом."},
            {"role": "user", "content": prompt}
        ], max_tokens=3000)
        return response

    # ==================== ЧАТ-БОТ ====================
    async def chat_with_bot(self, db: Session, session_id: int, lesson_id: int, question: str) -> str:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not session or not lesson:
            return "Извините, не удалось найти контекст урока."
        
        topic = lesson.topic
        user_id = session.user_id
        
        # Получаем контекст из истории
        context = await ContextService.get_user_context(db, user_id, current_topic=topic)
        
        prompt = f"""
Ты – ИИ-помощник по {session.exam_name}. Ученик изучает тему "{topic}".

{context}

Вопрос ученика: {question}

Дай понятный, подробный ответ, объясни шаги решения. Учти историю предыдущих вопросов и уровень знаний ученика.
Используй формулы в LaTeX (например, \\(x^2\\)).
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты полезный помощник по учебным предметам. Отвечай дружелюбно и понятно."},
            {"role": "user", "content": prompt}
        ], max_tokens=1000)
        
        # Сохраняем взаимодействие
        await ContextService.add_interaction(
            db, user_id, 'question', question, response, session_id, topic
        )
        
        return response
    
    # backend/app/services.py (добавить в конец класса AITeacherService)

    # ========== ГЕНЕРАЦИЯ ПОЛЬЗОВАТЕЛЬСКОГО КУРСА ==========
    async def generate_course_structure(self, db: Session, user_id: int, name: str, description: str, success_criteria: str) -> Dict:
        """Генерирует структуру курса и сохраняет в БД"""
        criteria_text = success_criteria if success_criteria else "не указаны, придумай разумные критерии"
        prompt = f"""
    Ты – эксперт по созданию образовательных курсов. Пользователь хочет создать курс:

    НАЗВАНИЕ: {name}
    ОПИСАНИЕ: {description if description else 'не указано'}
    КРИТЕРИИ УСПЕХА: {criteria_text}

    Сгенерируй подробную структуру курса в формате JSON. Курс должен состоять из 3-5 модулей, в каждом модуле 2-4 урока.
    Для каждого урока укажи: название, краткое описание, тип (theory/practice/test). Также добавь общие критерии успеха для всего курса и для каждого модуля.

    Верни ТОЛЬКО JSON:
    {{
    "success_criteria": "общие критерии успеха для курса",
    "modules": [
        {{
        "title": "Название модуля",
        "description": "Описание модуля",
        "success_criteria": "критерии успеха модуля",
        "lessons": [
            {{"title": "Название урока", "description": "краткое описание", "type": "theory"}},
            ...
        ]
        }}
    ]
    }}
    """
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты эксперт по структуре курсов. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                structure = json.loads(json_match.group())
                
                # Сохраняем взаимодействие
                await ContextService.add_interaction(
                    db, user_id, 'course_created',
                    f"Создан курс: {name}",
                    f"Структура сгенерирована: {len(structure.get('modules', []))} модулей",
                    topic=name
                )
                
                return structure
            else:
                return {"error": "Не удалось распарсить ответ"}
        except Exception as e:
            return {"error": f"Ошибка парсинга: {str(e)}"}
    
    async def generate_lesson_content(self, db: Session, user_id: int, title: str, subject: str, description: str) -> Dict:
        """Генерирует полное содержание урока и сохраняет в БД"""
        
        # Получаем контекст пользователя для персонализации
        context = await ContextService.get_user_context(db, user_id, current_topic=title)
        
        prompt = f"""
    Ты – опытный преподаватель по предмету "{subject}". Создай подробный урок на тему "{title}".

    Описание от пользователя: {description if description else 'нет дополнительных требований'}

    Контекст ученика:
    {context}

    Сгенерируй содержание урока в JSON формате со следующими полями:

    1. theory (string) – теоретическая часть, объяснение темы, формулы в LaTeX.
    2. practice (array) – практические задания для закрепления (3-5 задач). Каждая задача: {{"task": "текст", "answer": "ответ"}}.
    3. homework (array) – домашние задания (3-5 задач). Каждая задача: {{"task": "текст", "answer": "ответ"}}.
    4. success_criteria (string) – критерии успешного освоения урока (что ученик должен знать и уметь).
    5. youtube_urls (array) – 2-3 ссылки на обучающие видео с YouTube по этой теме (реальные ссылки).
    6. presentation_content (string) – HTML/CSS код для презентации.

    Верни ТОЛЬКО JSON:
    {{
    "theory": "...",
    "practice": [{{"task": "...", "answer": "..."}}],
    "homework": [{{"task": "...", "answer": "..."}}],
    "success_criteria": "...",
    "youtube_urls": ["url1", "url2"],
    "presentation_content": "..."
    }}
    """
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты создатель учебных материалов. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=8000)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                content = json.loads(json_match.group())
                
                # Сохраняем взаимодействие
                await ContextService.add_interaction(
                    db, user_id, 'lesson_created',
                    f"Создан урок: {title}",
                    f"Сгенерировано {len(content.get('practice', []))} практических заданий",
                    topic=title
                )
                
                return content
            else:
                return {"error": "Не удалось распарсить ответ"}
        except Exception as e:
            return {"error": f"Ошибка парсинга: {str(e)}"}
        
    async def get_user_statistics(self, db: Session, user_id: int) -> Dict:
        """Получить статистику успеваемости пользователя"""
        performances = db.query(UserPerformance).filter(UserPerformance.user_id == user_id).all()
        
        weak_topics = []
        strong_topics = []
        average_mastery = 0
        
        for p in performances:
            if p.mastery_level < 50:
                weak_topics.append({"topic": p.topic, "mastery": p.mastery_level})
            elif p.mastery_level > 70:
                strong_topics.append({"topic": p.topic, "mastery": p.mastery_level})
            average_mastery += p.mastery_level
        
        if performances:
            average_mastery /= len(performances)
        
        # Получаем последние взаимодействия
        interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).order_by(UserInteraction.created_at.desc()).limit(10).all()
        
        return {
            "total_topics": len(performances),
            "average_mastery": average_mastery,
            "weak_topics": weak_topics[:5],
            "strong_topics": strong_topics[:5],
            "recent_interactions": [
                {
                    "type": i.interaction_type,
                    "topic": i.topic,
                    "created_at": i.created_at
                } for i in interactions
            ]
        }