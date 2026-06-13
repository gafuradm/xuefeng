# backend/app/services.py
import json
import os
import pickle
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .context_service import ContextService
from .models import User, Session as SessionModel, TestResult, Lesson, ProgressHistory, Role
from .deepseek_client import deepseek_client
from .config import settings
import yt_dlp
import re
from .models import (
    User, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance,
    School, SchoolMember, StudentPerformance, TopicTimeStats
)
import whisper
from pathlib import Path
import shutil
from .subject_topics import (
    get_modules_for_subject, get_default_tasks,
    get_gaokao_modules, GAOKAO_TOPICS,
    get_ege_modules, EGE_TOPICS,
    get_sat_modules, SAT_TOPICS,
    get_uzbek_modules, UZBEK_TOPICS,
    get_india_modules, INDIA_TOPICS
)
import asyncio

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
    
    async def process_video(self, url: str, target_language: str) -> Dict[str, Any]:
        """Скачивает видео с YouTube, извлекает аудио, распознаёт речь, переводит текст."""
        temp_dir = Path("temp_video")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            audio_path = await self._download_audio(url, temp_dir)
            transcript = await self._transcribe_audio(audio_path)
            translation = await self._translate_text(transcript, target_language)
            return {
                "original_text": transcript,
                "translated_text": translation,
                "language": target_language
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _download_audio(self, url: str, output_dir: Path) -> Path:
        """Скачивает аудио с YouTube с повторными попытками и улучшенными настройками"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extract_flat': False,
            'retries': 5,
            'fragment_retries': 5,
            'sleep_interval': 2,
            'max_sleep_interval': 5,
            'socket_timeout': 30,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        # Добавляем куки, если есть (опционально)
        # cookies_path = Path("cookies.txt")
        # if cookies_path.exists():
        #     ydl_opts['cookiefile'] = str(cookies_path)
        
        for attempt in range(3):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    base = output_dir / info['title']
                    audio_file = base.with_suffix('.mp3')
                    if not audio_file.exists():
                        # ищем любой аудиофайл в папке
                        for f in output_dir.glob("*"):
                            if f.suffix in ['.mp3', '.m4a', '.webm']:
                                audio_file = f
                                break
                    return audio_file
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(3)
            
    async def _transcribe_audio(self, audio_path: Path) -> str:
        """Распознаёт речь через Whisper (локально)"""
        model = whisper.load_model("base")
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
        
        if self._is_sat(exam_name):
            if "math" in exam_lower:
                return "математика"
            elif "reading" in exam_lower or "writing" in exam_lower or "essay" in exam_lower:
                return "чтение и письмо"
            else:
                return "математика"
        
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
    
    def _normalize_answer(self, answer: str) -> str:
        """Нормализует ответ для сравнения"""
        if not answer:
            return ""
        
        answer = answer.strip().lower()
        
        # Убираем единицы измерения
        units = ['см', 'м', 'км', 'мм', 'кг', 'г', 'км/ч', 'м/с', 'сек', 'мин', 'час', 'руб', 'шт', 'раз', '%']
        for unit in units:
            answer = re.sub(rf'\s*{unit}\b', '', answer)
        
        # Убираем слова-подсказки
        words_to_remove = ['ответ', 'равен', 'равно', 'получается', 'будет', 'это']
        for word in words_to_remove:
            answer = re.sub(rf'\b{word}\b', '', answer)
        
        # Убираем точки и запятые в конце
        answer = answer.rstrip('.,!?')
        
        # Убираем лишние пробелы
        answer = ' '.join(answer.split())
        
        # Пытаемся извлечь число
        number_match = re.search(r'(\d+(?:[.,]\d+)?)', answer)
        if number_match and len(answer) < 30:
            number = number_match.group(1).replace(',', '.')
            return number
        
        return answer

    @staticmethod
    async def submit_test(db: Session, session_id: int, user_answers: Dict[str, str], time_spent_seconds: int = 0, question_times: Dict[str, int] = None) -> Dict[str, Any]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        test = db.query(TestResult).filter(TestResult.session_id == session_id, TestResult.test_type == "initial").first()
        if not test:
            raise ValueError("Test not found")
        test.answers = user_answers
        test.time_spent_seconds = time_spent_seconds
        test.question_times = question_times or {}
        
        evaluation = await deepseek_client.evaluate_answers(test.questions, user_answers, session.exam_details)
        test.evaluation = evaluation
        test.score = evaluation.get("overall_score", 0)
        session.current_profile = evaluation.get("topic_scores", {})
        db.commit()
        
        # Сохраняем результаты теста в статистику по темам
        topic_scores = evaluation.get("topic_scores", {})
        for topic, score in topic_scores.items():
            try:
                is_correct = score >= 60
                
                performance = db.query(UserPerformance).filter(
                    UserPerformance.user_id == session.user_id,
                    UserPerformance.topic == topic
                ).first()
                
                if not performance:
                    performance = UserPerformance(
                        user_id=session.user_id,
                        topic=topic,
                        correct_count=0,
                        total_count=0,
                        mastery_level=0
                    )
                    db.add(performance)
                
                if is_correct:
                    performance.correct_count = (performance.correct_count or 0) + 1
                performance.total_count = (performance.total_count or 0) + 1
                performance.mastery_level = (performance.correct_count / performance.total_count) * 100 if performance.total_count > 0 else 0
                performance.last_attempt = datetime.utcnow()
                db.commit()
            except Exception as e:
                print(f"Ошибка обновления статистики для темы {topic}: {e}")
        
        return evaluation

    # ==================== ПОСТРОЕНИЕ ПЛАНА ====================
    def _build_plan_from_weak_topics(self, weak_topics: List[str], exam_name: str, subject: str) -> Dict:
        weak_set = set(weak_topics)
        
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
        
        # Получаем слабые темы из последнего теста
        last_test = db.query(TestResult).filter(
            TestResult.session_id == session_id
        ).order_by(TestResult.id.desc()).first()
        weak_topics = last_test.evaluation.get("weak_topics", []) if last_test else []
        
        # Генерируем план через ИИ
        plan = await deepseek_client.generate_study_plan(
            target_profile=session.target_profile,
            current_profile=session.current_profile,
            days=days,
            weak_topics=weak_topics,
            exam_details=session.exam_details
        )
        session.study_plan = plan
        session.time_available_days = days
        session.status = "planning"
        db.commit()
        return plan

    async def get_next_lesson(self, db: Session, session_id: int) -> Dict[str, Any]:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        # Проверяем, есть ли невыполненный урок
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
        
        # Пытаемся получить план в формате schedule (новый формат от ИИ)
        study_plan = session.study_plan or {}
        schedule = study_plan.get("schedule", [])
        
        # Если schedule пуст – возможно, используется старый формат modules (для обратной совместимости)
        if not schedule:
            modules = study_plan.get("modules", [])
            all_topics_in_order = []
            for module in modules:
                all_topics_in_order.extend(module.get("topics", []))
        else:
            # Собираем все темы из расписания (уникальные, в порядке появления)
            all_topics_in_order = []
            seen = set()
            for day in schedule:
                topics = day.get("topics", [])
                for t in topics:
                    if t not in seen:
                        seen.add(t)
                        all_topics_in_order.append(t)
        
        # Получаем уже пройденные темы
        completed_lessons = db.query(Lesson).filter(
            Lesson.session_id == session_id,
            Lesson.completed == True
        ).all()
        completed_topics = {l.topic for l in completed_lessons}
        
        # Ищем следующую не пройденную тему
        next_topic = None
        for topic in all_topics_in_order:
            if topic not in completed_topics:
                next_topic = topic
                break
        
        if not next_topic:
            session.status = "completed"
            db.commit()
            return {"status": "completed", "message": "Поздравляем! Вы успешно завершили курс!"}
        
        # Генерируем урок для следующей темы
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

    async def get_study_plan(self, db: Session, session_id: int) -> Dict:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        return session.study_plan or {}
    
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
    
    async def check_lesson_answers_flexible(self, lesson_content: Dict, user_answers: Dict[str, str]) -> Dict[str, Any]:
        """Гибкая проверка ответов на урок с помощью ИИ"""
        tasks = lesson_content.get("tasks", [])
        results = []
        all_correct = True
        correct_count = 0
        
        questions_for_ai = []
        
        for i, task in enumerate(tasks):
            question_text = task.get("task", "")
            user_ans = user_answers.get(str(i), "").strip()
            correct_ans = task.get("answer", "").strip()
            topic = lesson_content.get("topic", "математика")
            
            user_normalized = self._normalize_answer(user_ans)
            correct_normalized = self._normalize_answer(correct_ans)
            is_correct = (user_normalized == correct_normalized)
            
            if not user_ans:
                is_correct = False
                results.append({
                    "task_index": i,
                    "correct": False,
                    "hint": "Ответ не введён",
                    "user_answer": user_ans,
                    "correct_answer": correct_ans
                })
                all_correct = False
                continue
            
            if not is_correct and len(user_ans) > 0:
                questions_for_ai.append({
                    "index": i,
                    "question": question_text,
                    "user_answer": user_ans,
                    "correct_answer": correct_ans,
                    "topic": topic
                })
            else:
                if is_correct:
                    correct_count += 1
                else:
                    all_correct = False
                results.append({
                    "task_index": i,
                    "correct": is_correct,
                    "hint": task.get("hint", "Проверьте решение") if not is_correct else None,
                    "user_answer": user_ans,
                    "correct_answer": correct_ans
                })
        
        if questions_for_ai:
            print(f"Sending {len(questions_for_ai)} questions to AI for evaluation")
            prompt = "Оцени следующие ответы ученика. Для каждого вопроса верни JSON объект с полями is_correct (true/false) и reason.\n\n"
            for q in questions_for_ai:
                prompt += f"""
Вопрос {q['index']+1}: {q['question']}
Правильный ответ: {q['correct_answer']}
Ответ ученика: {q['user_answer']}
Тема: {q['topic']}

"""
            prompt += """
Верни ТОЛЬКО JSON: {"результаты": [{"index": 1, "is_correct": true, "reason": "..."}]}
Индексы 1-based.
"""
            try:
                response = await deepseek_client.chat_completion([
                    {"role": "system", "content": "Ты эксперт по проверке ответов. Отвечай только JSON."},
                    {"role": "user", "content": prompt}
                ], max_tokens=2000)
                
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    ai_results = json.loads(json_match.group())
                    ai_list = ai_results.get("результаты", [])
                    ai_dict = {r["index"]: r for r in ai_list}
                    
                    for q in questions_for_ai:
                        task_index = q["index"] + 1
                        ai_result = ai_dict.get(task_index, {})
                        is_correct = ai_result.get("is_correct", False)
                        reason = ai_result.get("reason", "")
                        
                        if is_correct:
                            correct_count += 1
                        else:
                            all_correct = False
                        
                        results.append({
                            "task_index": q["index"],
                            "correct": is_correct,
                            "hint": reason if not is_correct else None,
                            "user_answer": q["user_answer"],
                            "correct_answer": q["correct_answer"]
                        })
            except Exception as e:
                print(f"AI batch evaluation failed: {e}")
                for q in questions_for_ai:
                    results.append({
                        "task_index": q["index"],
                        "correct": False,
                        "hint": "Ошибка проверки ответа",
                        "user_answer": q["user_answer"],
                        "correct_answer": q["correct_answer"]
                    })
                    all_correct = False
        
        return {
            "all_correct": all_correct,
            "correct_count": correct_count,
            "total_count": len(tasks),
            "results": results
        }

    async def submit_lesson(self, db: Session, session_id: int, lesson_id: int, user_answers: Dict[str, str], time_spent_seconds: float = 0.0, task_times: Dict[str, float] = None) -> Dict[str, Any]:
        print(f"=== DEBUG submit_lesson ===")
        print(f"session_id: {session_id}, lesson_id: {lesson_id}")
        print(f"time_spent_seconds: {time_spent_seconds}")
        
        try:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.session_id == session_id).first()
            if not lesson:
                raise ValueError("Lesson not found")
            
            # Сохраняем время на урок (округляем до целых секунд)
            lesson.time_spent_seconds = int(time_spent_seconds)
            lesson.task_times = {k: int(v) for k, v in (task_times or {}).items()}
            
            try:
                lesson_content = json.loads(lesson.content) if lesson.content else {}
                lesson_content["topic"] = lesson.topic
            except Exception as e:
                print(f"Error parsing lesson content: {e}")
                lesson_content = {"tasks": []}
            
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
            
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            
            # Гибкая проверка ответов
            check_result = await self.check_lesson_answers_flexible(lesson_content, user_answers)
            
            correct_count = check_result["correct_count"]
            all_correct = check_result["all_correct"]
            results = check_result["results"]
            
            # Обновляем статистику по времени для тем
            if session and time_spent_seconds > 0:
                await self._update_topic_time(db, session.user_id, lesson.topic, int(time_spent_seconds))
            
            if session:
                for result in results:
                    await self._update_topic_performance(db, session.user_id, lesson.topic, result["correct"])
            
            # ===== СИНХРОНИЗАЦИЯ ДЛЯ ВСЕХ ШКОЛ (ДАЖЕ ЕСЛИ УРОК НЕ ЗАВЕРШЁН) =====
            if session:
                user_schools = db.query(SchoolMember).filter(SchoolMember.user_id == session.user_id).all()
                print(f"🔍 Синхронизация для школ ученика {session.user_id}: {[s.school_id for s in user_schools]}")
                for school_member in user_schools:
                    try:
                        await self.sync_student_performance(db, session.user_id, school_member.school_id)
                        print(f"✅ Синхронизация для школы {school_member.school_id} успешна")
                    except Exception as e:
                        print(f"❌ Ошибка синхронизации для школы {school_member.school_id}: {e}")

            if not all_correct:
                error_details = []
                for r in results:
                    if not r["correct"]:
                        error_details.append(f"Задача {r['task_index']+1}: ваш ответ '{r['user_answer']}', правильно '{r['correct_answer']}'")
                return {
                    "status": "failed",
                    "message": f"Правильных ответов: {correct_count}/{len(tasks)}. Ошибки:\n" + "\n".join(error_details[:3]),
                    "results": results
                }
            
            lesson.completed = True
            lesson.completed_at = datetime.utcnow()
            lesson.score = 100
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
                "message": f"Урок успешно завершён! Правильных ответов: {correct_count}/{len(tasks)}",
                "results": results
            }
            
        except Exception as e:
            print(f"ERROR in submit_lesson: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(str(e))
    
    async def _update_topic_performance(self, db: Session, user_id: int, topic: str, is_correct: bool) -> None:
        try:
            performance = db.query(UserPerformance).filter(
                UserPerformance.user_id == user_id,
                UserPerformance.topic == topic
            ).first()
            
            if not performance:
                performance = UserPerformance(
                    user_id=user_id,
                    topic=topic,
                    correct_count=0,
                    total_count=0,
                    mastery_level=0.0
                )
                db.add(performance)
                db.flush()
            
            performance.correct_count = (performance.correct_count or 0) + (1 if is_correct else 0)
            performance.total_count = (performance.total_count or 0) + 1
            performance.mastery_level = (performance.correct_count / performance.total_count) * 100 if performance.total_count > 0 else 0.0
            performance.last_attempt = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            print(f"Error in _update_topic_performance: {e}")
            db.rollback()
    
    async def _update_topic_time(self, db: Session, user_id: int, topic: str, seconds: int) -> None:
        """Обновление времени по теме"""
        try:
            time_stat = db.query(TopicTimeStats).filter(
                TopicTimeStats.user_id == user_id,
                TopicTimeStats.topic == topic
            ).first()
            
            if not time_stat:
                time_stat = TopicTimeStats(
                    user_id=user_id,
                    topic=topic,
                    total_seconds=0,
                    sessions_count=0
                )
                db.add(time_stat)
            
            time_stat.total_seconds += seconds
            time_stat.sessions_count += 1
            time_stat.last_updated = datetime.utcnow()
            db.commit()
            
            # Также обновляем время в UserPerformance
            performance = db.query(UserPerformance).filter(
                UserPerformance.user_id == user_id,
                UserPerformance.topic == topic
            ).first()
            if performance:
                performance.total_time_spent = (performance.total_time_spent or 0) + seconds
                db.commit()
                
        except Exception as e:
            print(f"Error in _update_topic_time: {e}")
            db.rollback()

    async def sync_student_performance(self, db: Session, user_id: int, school_id: int):
        performances = db.query(UserPerformance).filter(UserPerformance.user_id == user_id).all()
        time_stats = db.query(TopicTimeStats).filter(TopicTimeStats.user_id == user_id).all()
        time_dict = {ts.topic: ts.total_seconds for ts in time_stats}
        
        student_perf = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == user_id,
            StudentPerformance.school_id == school_id
        ).first()
        
        if not student_perf:
            student_perf = StudentPerformance(user_id=user_id, school_id=school_id)
            student_perf.current_graph = {}
            student_perf.target_graph = {}
            db.add(student_perf)
        else:
            if student_perf.current_graph is None:
                student_perf.current_graph = {}
            if student_perf.target_graph is None:
                student_perf.target_graph = {}
        
        # КОПИРУЕМ СЛОВАРЬ, А НЕ МЕНЯЕМ ПО КЛЮЧУ
        new_current = dict(student_perf.current_graph)
        for perf in performances:
            if perf.total_count > 0:
                new_current[perf.topic] = perf.mastery_level
        student_perf.current_graph = new_current
        
        student_perf.total_time_spent = sum(time_dict.values())
        student_perf.last_updated = datetime.utcnow()
        db.commit()
        print(f"Synced user {user_id} to school {school_id}")
    
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
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты – ИИ учитель, который запоминает структуру тестов и может генерировать похожие вопросы."},
            {"role": "user", "content": prompt}
        ], max_tokens=500)
        return response.strip()

    async def _generate_similar_from_custom(self, examples_text: str, num_questions: int = 5) -> str:
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
        
        await ContextService.add_interaction(
            db, user_id, 'question', question, response, session_id, topic
        )
        
        return response
    
    # ========== ГЕНЕРАЦИЯ ПОЛЬЗОВАТЕЛЬСКОГО КУРСА ==========
    async def generate_course_structure(self, db: Session, user_id: int, name: str, description: str, success_criteria: str) -> Dict:
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
        context = await ContextService.get_user_context(db, user_id, current_topic=title)
        
        prompt = f"""
Ты – опытный преподаватель по предмету "{subject}". Создай подробный урок на тему "{title}".

Описание от пользователя: {description if description else 'нет дополнительных требований'}

Контекст ученика:
{context}

Сгенерируй содержание урока в JSON формате со следующими полями:

1. theory (string) – теоретическая часть, объяснение темы.
2. practice (array) – практические задания (3-5). Каждая: {{"task": "текст", "answer": "ответ"}}.
3. homework (array) – домашние задания (3-5).
4. success_criteria (string) – критерии успеха.
5. youtube_urls (array) – 2-3 ссылки на YouTube.
6. presentation_content (string) – HTML/CSS для презентации.

Верни ТОЛЬКО JSON.
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
                
                await ContextService.add_interaction(
                    db, user_id, 'lesson_created',
                    f"Создан урок: {title}",
                    f"Сгенерировано {len(content.get('practice', []))} заданий",
                    topic=title
                )
                
                return content
            else:
                return {"error": "Не удалось распарсить ответ"}
        except Exception as e:
            return {"error": f"Ошибка парсинга: {str(e)}"}
        
    async def get_user_statistics(self, db: Session, user_id: int) -> Dict:
        performances = db.query(UserPerformance).filter(UserPerformance.user_id == user_id).all()
        time_stats = db.query(TopicTimeStats).filter(TopicTimeStats.user_id == user_id).all()
        time_dict = {ts.topic: ts.total_seconds for ts in time_stats}
        
        weak_topics = []
        strong_topics = []
        average_mastery = 0
        
        result = []
        for p in performances:
            mastery = p.mastery_level or 0
            time_min = round((time_dict.get(p.topic, 0) / 60), 1)
            result.append({
                "topic": p.topic,
                "mastery_level": mastery,
                "correct_count": p.correct_count,
                "total_count": p.total_count,
                "total_time_spent_minutes": time_min,
                "last_attempt": p.last_attempt
            })
            
            if mastery < 50:
                weak_topics.append({"topic": p.topic, "mastery": mastery})
            elif mastery > 70:
                strong_topics.append({"topic": p.topic, "mastery": mastery})
            average_mastery += mastery
        
        if performances:
            average_mastery /= len(performances)
        
        interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).order_by(UserInteraction.created_at.desc()).limit(10).all()
        
        return {
            "total_topics": len(performances),
            "average_mastery": average_mastery,
            "weak_topics": weak_topics[:5],
            "strong_topics": strong_topics[:5],
            "topics_detail": result,
            "recent_interactions": [
                {
                    "type": i.interaction_type,
                    "topic": i.topic,
                    "created_at": i.created_at
                } for i in interactions
            ]
        }

    # ========== УПРАВЛЕНИЕ ШКОЛОЙ (АДАПТИРОВАНО ПОД НОВЫЕ РОЛИ) ==========
    async def create_school(self, db: Session, owner_id: int, name: str, description: str = None) -> Dict:
        print(f"DEBUG: create_school called with owner_id={owner_id}, name={name}")
        user = db.query(User).filter(User.id == owner_id).first()
        if not user:
            raise ValueError(f"Пользователь с id={owner_id} не найден")
        
        # Проверка наличия роли учителя (school_teacher или professor)
        teacher_roles = ['school_teacher', 'professor']
        if not any(role.name in teacher_roles for role in user.roles):
            raise ValueError(f"Только учитель может создать школу. Ваши роли: {[r.name for r in user.roles]}")
        
        import secrets
        invite_code = secrets.token_hex(4).upper()
        school = School(owner_id=owner_id, name=name, description=description, invite_code=invite_code)
        db.add(school)
        db.commit()
        db.refresh(school)
        
        member = SchoolMember(school_id=school.id, user_id=owner_id, role='teacher')
        db.add(member)
        db.commit()
        
        return {"id": school.id, "name": school.name, "description": school.description, "invite_code": invite_code}
    
    async def join_school(self, db: Session, user_id: int, invite_code: str) -> Dict:
        school = db.query(School).filter(School.invite_code == invite_code).first()
        if not school:
            raise ValueError("Школа с таким кодом не найдена")
        
        existing = db.query(SchoolMember).filter(
            SchoolMember.school_id == school.id, SchoolMember.user_id == user_id
        ).first()
        if existing:
            raise ValueError("Вы уже в этой школе")
        
        member = SchoolMember(school_id=school.id, user_id=user_id, role='student')
        db.add(member)
        db.commit()
        
        # Создаём запись StudentPerformance при вступлении в школу
        sp = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == user_id,
            StudentPerformance.school_id == school.id
        ).first()
        if not sp:
            sp = StudentPerformance(user_id=user_id, school_id=school.id)
            sp.current_graph = {}
            sp.target_graph = {}
            db.add(sp)
            db.commit()
            print(f"✅ Создана запись StudentPerformance для ученика {user_id} в школе {school.id}")
        
        # ===== ВАЖНО: синхронизируем существующий прогресс ученика =====
        await self.sync_student_performance(db, user_id, school.id)
        
        return {"school_id": school.id, "school_name": school.name, "role": "student"}

    async def get_school_stats(self, db: Session, school_id: int, teacher_id: int) -> Dict:
        school = db.query(School).filter(School.id == school_id, School.owner_id == teacher_id).first()
        if not school:
            raise ValueError("Школа не найдена или у вас нет доступа")
        
        members = db.query(SchoolMember).filter(SchoolMember.school_id == school_id).all()
        students = []
        
        for member in members:
            if member.role != 'student':
                continue
            user = member.user
            
            performances = db.query(UserPerformance).filter(UserPerformance.user_id == user.id).all()
            time_stats = db.query(TopicTimeStats).filter(TopicTimeStats.user_id == user.id).all()
            total_seconds = sum(ts.total_seconds for ts in time_stats)
            
            topics_progress = {}
            weak_topics = []
            total_mastery = 0
            
            for perf in performances:
                mastery = perf.mastery_level or 0
                topics_progress[perf.topic] = mastery
                total_mastery += mastery
                if mastery < 50:
                    weak_topics.append(perf.topic)
            
            avg_mastery = total_mastery / len(performances) if performances else 0
            
            students.append({
                "user_id": user.id,
                "name": user.name,
                "average_mastery": round(avg_mastery, 1),
                "total_time_spent_hours": round(total_seconds / 3600, 1),
                "topics_progress": topics_progress,
                "weak_topics": weak_topics[:5],
                "topics_count": len(performances)
            })
        
        students.sort(key=lambda x: x["average_mastery"], reverse=True)
        
        return {
            "school_name": school.name,
            "total_students": len(students),
            "students": students
        }

    # ========== ГРАФЫ ЗНАНИЙ ==========
    async def build_target_graph(self, db: Session, user_id: int, school_id: int, exam_name: str) -> Dict:
        prompt = f"""
    Ты эксперт по экзамену "{exam_name}". Проведи детальный анализ.
    Верни ТОЛЬКО JSON:
    {{
    "topics": [
        {{"topic": "название", "weight": 15, "hours_to_learn": 10, "difficulty": "medium"}}
    ],
    "total_days": 90
    }}
    """
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты эксперт по образованию. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                target_graph = {}
                for topic in data.get("topics", []):
                    target_graph[topic["topic"]] = {
                        "weight": topic.get("weight", 0),
                        "hours_to_learn": topic.get("hours_to_learn", 5),
                        "difficulty": topic.get("difficulty", "medium")
                    }
                
                performance = db.query(StudentPerformance).filter(
                    StudentPerformance.user_id == user_id,
                    StudentPerformance.school_id == school_id
                ).first()
                if not performance:
                    performance = StudentPerformance(user_id=user_id, school_id=school_id)
                    db.add(performance)
                
                performance.target_graph = target_graph
                performance.current_graph = performance.current_graph or {}
                db.commit()
                
                return {"target_graph": target_graph, "total_days": data.get("total_days", 60)}
        except Exception as e:
            print(f"Ошибка: {e}")
            return {"error": str(e)}
    
    async def update_current_graph(self, db: Session, user_id: int, school_id: int, topic: str, score: float) -> Dict:
        performance = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == user_id,
            StudentPerformance.school_id == school_id
        ).first()
        
        if not performance:
            performance = StudentPerformance(user_id=user_id, school_id=school_id)
            db.add(performance)
        
        current = performance.current_graph.get(topic, 0)
        new_level = current * 0.7 + score * 0.3
        new_current = dict(performance.current_graph or {})
        new_current[topic] = min(100, new_level)
        performance.current_graph = new_current
        
        if topic not in performance.topics_progress:
            performance.topics_progress[topic] = []
        performance.topics_progress[topic].append({"score": score, "timestamp": datetime.utcnow().isoformat()})
        performance.topics_progress[topic] = performance.topics_progress[topic][-20:]
        performance.last_updated = datetime.utcnow()
        db.commit()
        
        target_level = performance.target_graph.get(topic, {}).get("weight", 100)
        return {"topic": topic, "new_level": new_level, "target_level": target_level}

    async def get_coefficient(self, db: Session, user_id: int, school_id: int) -> Dict:
        performance = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == user_id,
            StudentPerformance.school_id == school_id
        ).first()
        
        if not performance or not performance.target_graph:
            return {"error": "Нет данных для расчёта"}
        
        target = performance.target_graph
        current = performance.current_graph
        
        total_gap = 0
        total_weight = 0
        topics_analysis = []
        
        for topic, target_data in target.items():
            target_level = target_data.get("weight", 100)
            current_level = current.get(topic, 0)
            gap = target_level - current_level
            weight = target_data.get("weight", 1)
            
            topics_analysis.append({
                "topic": topic,
                "target": target_level,
                "current": current_level,
                "gap": gap,
                "weight": weight,
                "status": "success" if gap <= 20 else "needs_attention"
            })
            total_gap += gap * weight
            total_weight += weight
        
        coefficient = max(0, 100 - (total_gap / total_weight)) if total_weight > 0 else 0
        
        return {
            "coefficient": coefficient,
            "topics": topics_analysis,
            "recommendation": "Нужно больше практики в слабых темах" if coefficient < 70 else "Хороший прогресс"
        }

    async def get_learning_graphs(self, db: Session, user_id: int, school_id: int) -> Dict:
        performance = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == user_id,
            StudentPerformance.school_id == school_id
        ).first()

        if not performance:
            return {"target_graph": [], "current_graph": []}

        target_list = []
        if performance.target_graph:
            for topic, data in performance.target_graph.items():
                target_list.append({
                    "topic": topic,
                    "value": data.get("weight", 0),
                    "hours": data.get("hours_to_learn", 0),
                    "difficulty": data.get("difficulty", "medium")
                })

        current_list = []
        if performance.current_graph:
            for topic, mastery in performance.current_graph.items():
                current_list.append({
                    "topic": topic,
                    "value": mastery,
                    "progress_history": performance.topics_progress.get(topic, [])
                })

        return {
            "target_graph": target_list,
            "current_graph": current_list,
            "last_updated": performance.last_updated
        }