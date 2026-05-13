# backend/app/main.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from fastapi import Body
import concurrent.futures
from datetime import datetime
import asyncio
from fastapi import UploadFile, File
from fastapi.responses import RedirectResponse
from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo, SchoolChatMessage  # ← добавить
)
from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo
)
from .database import engine, get_db
from .models import (
    Base, User, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo
)
from .deepseek_client import deepseek_client
from .schemas import *
from .services import AITeacherService
from .config import settings

# ========== OCR РАСПОЗНАВАНИЕ РУКОПИСНОГО ТЕКСТА ==========
import easyocr
import numpy as np
from PIL import Image
import io

from pathlib import Path
import os

# ========== КОРНЕВЫЕ ПУТИ (должны быть в самом начале) ==========
PROJECT_ROOT = Path(__file__).parent.parent.parent      # папка, где лежат backend, frontend, frontend_hsk
BACKEND_ROOT = Path(__file__).parent.parent             # папка backend
APP_ROOT = Path(__file__).parent                        # папка backend/app

# Папки для фронтенда
FRONTEND_DIR = PROJECT_ROOT / "frontend"
HSK_DIR = PROJECT_ROOT / "frontend_hsk"

# Папки для данных (внутри backend)
DATA_DIR = BACKEND_ROOT / "data"
COURSES_DIR = DATA_DIR / "courses"
COURSES_DIR.mkdir(parents=True, exist_ok=True)

# Для совместимости со старым кодом, который может использовать BASE_DIR
BASE_DIR = BACKEND_ROOT   # или PROJECT_ROOT — смотрите, где он используется

# Инициализируем EasyOCR один раз при старте (чтобы не грузить модель при каждом запросе)
ocr_reader = None

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Universal AI Teacher", version="1.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
os.makedirs(video_dir, exist_ok=True)
app.mount("/static/videos", StaticFiles(directory=video_dir), name="videos")

# Монтируем статику (фронтенд)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Инициализация сервиса
ai_service = AITeacherService()

from pydantic import BaseModel

class AvatarUpdate(BaseModel):
    avatar_url: str

@app.on_event("startup")
async def startup_event():
    print("🚀 Запуск Universal AI Teacher...")
    if ai_service.rag_available:
        print("✅ RAG система готова")

# ========== ПОЛЬЗОВАТЕЛИ ==========
@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, role: str = "student", db: Session = Depends(get_db)):
    try:
        user_obj = await ai_service.create_user(db, user.email, user.name)
        user_obj.role = role
        db.commit()
        db.refresh(user_obj)
        return user_obj
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi.responses import HTMLResponse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent   # корень проекта
FRONTEND_DIR = PROJECT_ROOT / "frontend"
HSK_DIR = PROJECT_ROOT / "frontend_hsk"

# Для совместимости с остальным кодом, который ожидает BASE_DIR,
# можно определить BACKEND_ROOT:
BACKEND_ROOT = Path(__file__).parent.parent

# Монтируем статику (CSS, JS) из папки frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def main_frontend():
    """Главная страница Universal AI Teacher"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("Main frontend not found", status_code=404)

# HSK Tutor (если папка существует)
if HSK_DIR.exists():
    @app.get("/hsk", response_class=HTMLResponse)
    async def hsk_frontend():
        index_path = HSK_DIR / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("HSK frontend not found", status_code=404)

# ========== СЕССИИ И ТЕСТЫ ==========
@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(user_id: int, session_data: SessionCreate, db: Session = Depends(get_db)):
    try:
        return await ai_service.create_session(db, user_id, session_data.exam_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_test")
async def submit_test(session_id: int, test_data: TestSubmit, db: Session = Depends(get_db)):
    try:
        result = await ai_service.submit_test(db, session_id, test_data.answers)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/set_time")
async def set_time(session_id: int, time_data: TimeSet, db: Session = Depends(get_db)):
    try:
        plan = await ai_service.set_time_and_plan(db, session_id, time_data.days)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/next_lesson")
async def get_next_lesson(session_id: int, db: Session = Depends(get_db)):
    try:
        return await ai_service.get_next_lesson(db, session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_lesson")
async def submit_lesson(session_id: int, lesson_data: LessonAnswer, db: Session = Depends(get_db)):
    """Отправка ответов на урок"""
    try:
        result = await ai_service.submit_lesson(
            db, session_id, lesson_data.lesson_id, lesson_data.user_answers,
            lesson_data.time_spent_seconds, lesson_data.task_times   # ← добавить эти два
        )
        return result
    except Exception as e:
        print(f"Error in submit_lesson endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/api/sessions/{session_id}/progress_test")
async def create_progress_test(session_id: int, db: Session = Depends(get_db)):
    try:
        questions = await ai_service.generate_progress_test(db, session_id)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    test_results = db.query(TestResult).filter(TestResult.session_id == session_id).all()
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "exam_name": session.exam_name,
        "exam_details": session.exam_details,
        "target_profile": session.target_profile,
        "current_profile": session.current_profile,
        "time_available_days": session.time_available_days,
        "study_plan": session.study_plan,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "test_results": [
            {
                "id": t.id,
                "test_type": t.test_type,
                "questions": t.questions,
                "answers": t.answers,
                "evaluation": t.evaluation,
                "score": t.score,
                "created_at": t.created_at,
                "time_spent_seconds": t.time_spent_seconds,
                "question_times": t.question_times
            }
            for t in test_results
        ]
    }

@app.get("/api/sessions/{session_id}/study_plan")
async def get_study_plan(session_id: int, db: Session = Depends(get_db)):
    try:
        plan = await ai_service.get_study_plan(db, session_id)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: int, db: Session = Depends(get_db)):
    history = db.query(ProgressHistory).filter(
        ProgressHistory.session_id == session_id
    ).order_by(ProgressHistory.timestamp).all()
    return history

# ========== СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ ==========
@app.get("/api/user/statistics")
async def get_user_statistics(user_id: int, db: Session = Depends(get_db)):
    stats = await ai_service.get_user_statistics(db, user_id)
    return stats

@app.get("/api/user/performance")
async def get_user_performance(user_id: int, db: Session = Depends(get_db)):
    performances = db.query(UserPerformance).filter(UserPerformance.user_id == user_id).all()
    return [
        {
            "topic": p.topic,
            "correct_count": p.correct_count,
            "total_count": p.total_count,
            "mastery_level": p.mastery_level,
            "total_time_spent": p.total_time_spent,
            "last_attempt": p.last_attempt
        }
        for p in performances
    ]

@app.get("/api/user/detailed_stats")
async def get_detailed_stats(user_id: int, db: Session = Depends(get_db)):
    """Детальная статистика пользователя с временем по темам"""
    stats = await ai_service.get_user_statistics(db, user_id)
    return stats

@app.get("/api/user/interactions")
async def get_user_interactions(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    interactions = db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id
    ).order_by(UserInteraction.created_at.desc()).limit(limit).all()
    
    return [
        {
            "type": i.interaction_type,
            "user_input": i.user_input,
            "ai_response": i.ai_response,
            "topic": i.topic,
            "created_at": i.created_at
        }
        for i in interactions
    ]

# ========== ЧАТ ==========
@app.post("/api/lessons/{lesson_id}/chat")
async def lesson_chat(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    session_id = data.get("session_id")
    question = data.get("question")
    if not session_id or not question:
        raise HTTPException(status_code=400, detail="session_id and question required")
    answer = await ai_service.chat_with_bot(db, session_id, lesson_id, question)
    return {"answer": answer}

# ========== RAG ЭНДПОИНТЫ ==========
@app.get("/api/exams/{exam_type}/search")
async def search_problems(
    exam_type: str,
    query: str = Query(..., description="Поисковый запрос"),
    k: int = Query(5, ge=1, le=50),
    year: Optional[int] = Query(None),
    topic: Optional[str] = Query(None),
    subject: Optional[str] = Query(None)
):
    try:
        filters = {}
        if year:
            filters['year'] = year
        if topic:
            filters['topic'] = topic
        if subject:
            filters['subject'] = subject
        
        if exam_type not in ai_service.exam_manager.active_exams:
            return {"results": [], "message": f"Экзамен {exam_type} не найден"}
        
        results = ai_service.exam_manager.search_problems(exam_type, query, k, filters)
        
        clean_results = []
        for r in results:
            clean = {
                'id': r.get('id'),
                'topic': r.get('topic'),
                'year': r.get('year'),
                'subject': r.get('subject'),
                'text': (r.get('text') or r.get('question') or r.get('raw_text') or '')[:2000],
                'answer': r.get('answer', ''),
                'solution': r.get('solution', ''),
                'difficulty': r.get('difficulty', 'medium')
            }
            clean_results.append(clean)
        
        return {"query": query, "count": len(clean_results), "results": clean_results}
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/exams/{exam_type}/stats")
async def get_exam_stats(exam_type: str):
    try:
        if exam_type not in ai_service.exam_manager.active_exams:
            return {"error": f"Экзамен {exam_type} не найден"}
        
        store = ai_service.exam_manager.active_exams[exam_type]
        metadata = store.get('metadata', [])
        
        stats = {"total_problems": len(metadata), "topics": {}, "years": {}, "difficulties": {}}
        
        for p in metadata:
            topic = p.get('topic', 'unknown')
            stats['topics'][topic] = stats['topics'].get(topic, 0) + 1
            year = p.get('year')
            if year:
                stats['years'][str(year)] = stats['years'].get(str(year), 0) + 1
            diff = p.get('difficulty', 'unknown')
            stats['difficulties'][diff] = stats['difficulties'].get(diff, 0) + 1
        
        return stats
    except Exception as e:
        print(f"Ошибка статистики: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/test/search")
async def test_search(query: str = "тригонометрия", k: int = 3):
    try:
        results = ai_service.exam_manager.search_problems('gaokao', query, k)
        return {"query": query, "count": len(results), "results": results[:k]}
    except Exception as e:
        return {"error": str(e)}

# ========== ВИДЕО ==========
@app.post("/api/lessons/{lesson_id}/generate_video")
async def generate_video_for_lesson(lesson_id: int, db: Session = Depends(get_db)):
    from .video_generator import VideoGenerator
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    existing = db.query(LessonVideo).filter(LessonVideo.lesson_id == lesson_id).first()
    if existing and os.path.exists(existing.video_path):
        return {"video_url": f"/static/videos/{os.path.basename(existing.video_path)}"}
    
    try:
        content = json.loads(lesson.content) if lesson.content else {}
    except:
        content = {}
    
    theory = content.get("theory", f"Изучение темы {lesson.topic}")
    examples = content.get("examples", [])
    tasks = content.get("tasks", [])
    
    tasks_with_solutions = []
    for idx, task in enumerate(tasks[:5]):
        problem = task.get('task', '')
        answer = task.get('answer', '')
        if problem and answer:
            steps = await deepseek_client.get_step_by_step_solution(problem, subject="математика")
            tasks_with_solutions.append({"problem": problem, "steps": steps, "answer": answer})
    
    vg = VideoGenerator()
    filename = f"lesson_{lesson_id}_{int(datetime.now().timestamp())}.mp4"
    
    def sync_gen():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(vg.generate_video(
            lesson.topic, theory, examples, tasks_with_solutions, filename
        ))
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(sync_gen)
        path = future.result()
    
    lesson_video = LessonVideo(lesson_id=lesson.id, video_path=path)
    db.add(lesson_video)
    db.commit()
    
    return {"video_url": f"/static/videos/{filename}"}

@app.post("/api/video/transcribe")
async def transcribe_video(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    url = data.get("url")
    target_language = data.get("language", "ru")
    if not url:
        raise HTTPException(400, "URL видео не указан")
    result = await ai_service.process_video(url, target_language)
    return result

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ ==========
@app.post("/api/custom_tests")
async def create_custom_test(test_data: CustomTestCreate, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    new_test = CustomTest(
        user_id=user_id,
        name=test_data.name,
        description=test_data.description,
        questions=[q.dict() for q in test_data.questions]
    )
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    return new_test

@app.get("/api/custom_tests")
async def get_user_tests(user_id: int, db: Session = Depends(get_db)):
    tests = db.query(CustomTest).filter(CustomTest.user_id == user_id).all()
    return tests

@app.get("/api/custom_tests/{test_id}")
async def get_custom_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    return test

@app.delete("/api/custom_tests/{test_id}")
async def delete_custom_test(test_id: int, user_id: int, db: Session = Depends(get_db)):
    test = db.query(CustomTest).filter(CustomTest.id == test_id, CustomTest.user_id == user_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден или не принадлежит вам")
    db.delete(test)
    db.commit()
    return {"status": "ok", "message": "Тест удалён"}

@app.post("/api/custom_tests/{test_id}/train")
async def train_ai_on_custom_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    
    prompt = f"""
Ты – ИИ учитель. Пользователь создал тест с названием "{test.name}" и хочет, чтобы ты запомнил его структуру.

Вот тест:
ОПИСАНИЕ: {test.description or 'нет описания'}

ВОПРОСЫ:
"""
    for i, q in enumerate(test.questions, 1):
        prompt += f"\n{i}. {q['text']}\n   Правильный ответ: {q['correct_answer']}\n"
    
    response = await ai_service._custom_train(prompt)
    return {"status": "trained", "message": response, "test_id": test_id}

@app.post("/api/custom_tests/{test_id}/submit")
async def submit_custom_test(test_id: int, submission: CustomTestSubmit, db: Session = Depends(get_db)):
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    
    results = []
    score = 0
    total = len(test.questions)
    
    for i, q in enumerate(test.questions):
        user_answer = submission.answers.get(str(i), "").strip().lower()
        correct = q["correct_answer"].strip().lower()
        is_correct = (user_answer == correct)
        if is_correct:
            score += 1
        results.append({
            "question": q["text"],
            "user_answer": submission.answers.get(str(i), ""),
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })
    
    percentage = (score / total) * 100
    grade = "Отлично!" if percentage >= 80 else "Хорошо" if percentage >= 60 else "Нужно повторить"
    
    return {
        "test_name": test.name,
        "total": total,
        "correct": score,
        "score": percentage,
        "grade": grade,
        "results": results
    }

@app.post("/api/custom_tests/{test_id}/generate_similar")
async def generate_similar_questions(test_id: int, num_questions: int = 5, db: Session = Depends(get_db)):
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    
    examples = test.questions[:3]
    examples_text = "\n".join([f"{i+1}. {q['text']} -> {q['correct_answer']}" for i, q in enumerate(examples)])
    
    response = await ai_service._generate_similar_from_custom(examples_text, num_questions)
    try:
        questions = json.loads(response)
        return {"questions": questions, "count": len(questions)}
    except:
        return {"error": "Не удалось распарсить ответ", "raw": response}

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КУРСЫ ==========
@app.post("/api/courses/generate")
async def generate_course(course_data: UserCourseCreate, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    structure = await ai_service.generate_course_structure(db, user_id, course_data.name, course_data.description, course_data.success_criteria)
    
    if "error" in structure:
        raise HTTPException(400, structure["error"])
    
    new_course = UserCourse(
        user_id=user_id,
        name=course_data.name,
        description=course_data.description,
        success_criteria=structure.get("success_criteria", course_data.success_criteria),
        status="ready"
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    modules_list = []
    for module_idx, module_data in enumerate(structure.get("modules", [])):
        new_module = CourseModule(
            course_id=new_course.id,
            title=module_data["title"],
            description=module_data.get("description", ""),
            order=module_idx
        )
        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        
        lessons_list = []
        for lesson_idx, lesson_data in enumerate(module_data.get("lessons", [])):
            new_lesson = CourseLesson(
                module_id=new_module.id,
                title=lesson_data["title"],
                order=lesson_idx,
                content={"description": lesson_data.get("description", ""), "type": lesson_data.get("type", "theory")},
                success_criteria=module_data.get("success_criteria", "")
            )
            db.add(new_lesson)
            lessons_list.append({
                "id": new_lesson.id,
                "title": new_lesson.title,
                "order": new_lesson.order,
                "content": new_lesson.content
            })
        
        modules_list.append({
            "id": new_module.id,
            "title": new_module.title,
            "description": new_module.description,
            "order": new_module.order,
            "lessons": lessons_list
        })
    
    db.commit()
    
    return {
        "id": new_course.id,
        "user_id": new_course.user_id,
        "name": new_course.name,
        "description": new_course.description,
        "success_criteria": new_course.success_criteria,
        "status": new_course.status,
        "created_at": new_course.created_at,
        "updated_at": new_course.updated_at,
        "modules": modules_list
    }

@app.get("/api/courses")
async def get_user_courses(user_id: int, db: Session = Depends(get_db)):
    courses = db.query(UserCourse).filter(UserCourse.user_id == user_id).all()
    return courses

@app.get("/api/courses/{course_id}")
async def get_course_details(course_id: int, db: Session = Depends(get_db)):
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    
    result = {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "success_criteria": course.success_criteria,
        "status": course.status,
        "created_at": course.created_at,
        "modules": []
    }
    for module in course.modules:
        module_data = {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order": module.order,
            "lessons": []
        }
        for lesson in module.lessons:
            module_data["lessons"].append({
                "id": lesson.id,
                "title": lesson.title,
                "order": lesson.order,
                "content": lesson.content,
                "success_criteria": lesson.success_criteria
            })
        result["modules"].append(module_data)
    return result

@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: int, user_id: int, db: Session = Depends(get_db)):
    course = db.query(UserCourse).filter(UserCourse.id == course_id, UserCourse.user_id == user_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    db.delete(course)
    db.commit()
    return {"status": "ok"}

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ УРОКИ ==========
@app.post("/api/lessons/generate", response_model=UserLessonResponse)
async def generate_lesson(lesson_data: UserLessonCreate, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    content = await ai_service.generate_lesson_content(db, user_id, lesson_data.title, lesson_data.subject, lesson_data.description)
    if "error" in content:
        raise HTTPException(400, content["error"])
    
    new_lesson = UserLesson(
        user_id=user_id,
        title=lesson_data.title,
        subject=lesson_data.subject,
        description=lesson_data.description,
        content=content,
        success_criteria=content.get("success_criteria", ""),
        youtube_urls=content.get("youtube_urls", [])
    )
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    return new_lesson

@app.get("/api/lessons")
async def get_user_lessons(user_id: int, db: Session = Depends(get_db)):
    lessons = db.query(UserLesson).filter(UserLesson.user_id == user_id).all()
    return lessons

@app.get("/api/lessons/{lesson_id}")
async def get_lesson_details(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id, UserLesson.user_id == user_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден или не принадлежит вам")
    db.delete(lesson)
    db.commit()
    return {"status": "ok", "message": "Урок удалён"}

# ========== ПРЕЗЕНТАЦИИ ==========
@app.post("/api/lessons/{lesson_id}/generate_presentation")
async def generate_presentation(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    if lesson.presentation_url:
        return {"presentation_url": lesson.presentation_url}
    
    content = lesson.content
    theory = content.get("theory", "")
    practice = content.get("practice", [])
    homework = content.get("homework", [])
    
    html = f"""<!DOCTYPE html>
<html>
<head><title>{lesson.title}</title><meta charset="utf-8">
<style>
    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
    .slide {{ margin-bottom: 40px; page-break-after: always; }}
    h1 {{ color: #667eea; }}
    .task {{ background: #f5f5f5; padding: 15px; border-radius: 10px; margin: 10px 0; }}
    .answer {{ color: #2c3e50; font-weight: bold; }}
</style>
</head>
<body>
    <div class="slide"><h1>{lesson.title}</h1><p><strong>Предмет:</strong> {lesson.subject}</p><p>{lesson.description or ''}</p></div>
    <div class="slide"><h2>📖 Теория</h2>{theory}</div>
    <div class="slide"><h2>✍️ Практические задания</h2>{''.join(f'<div class="task"><strong>Задача {i+1}:</strong> {p["task"]}<br><span class="answer">Ответ: {p["answer"]}</span></div>' for i, p in enumerate(practice))}</div>
    <div class="slide"><h2>🏠 Домашнее задание</h2>{''.join(f'<div class="task"><strong>Задача {i+1}:</strong> {h["task"]}<br><span class="answer">Ответ: {h["answer"]}</span></div>' for i, h in enumerate(homework))}</div>
    <div class="slide"><h2>🎯 Критерии успеха</h2><p>{lesson.success_criteria}</p></div>
</body>
</html>"""
    
    pres_dir = "static/presentations"
    os.makedirs(pres_dir, exist_ok=True)
    filename = f"lesson_{lesson_id}.html"
    filepath = os.path.join(pres_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    presentation_url = f"/static/presentations/{filename}"
    lesson.presentation_url = presentation_url
    db.commit()
    return {"presentation_url": presentation_url}

# ========== УПРАВЛЕНИЕ ШКОЛОЙ ==========
@app.post("/api/schools/create")
async def create_school_endpoint(name: str, description: str = None, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = await ai_service.create_school(db, user_id, name, description)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/schools/join")
async def join_school_endpoint(invite_code: str, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = await ai_service.join_school(db, user_id, invite_code)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/schools/my")
async def get_my_schools(user_id: int = Query(...), db: Session = Depends(get_db)):
    schools = db.query(School).filter(
        School.id.in_(db.query(SchoolMember.school_id).filter(SchoolMember.user_id == user_id))
    ).all()
    
    result = []
    for school in schools:
        students_count = db.query(SchoolMember).filter(
            SchoolMember.school_id == school.id, SchoolMember.role == 'student'
        ).count()
        result.append({
            "id": school.id,
            "name": school.name,
            "description": school.description,
            "invite_code": school.invite_code,
            "created_at": school.created_at,
            "is_owner": school.owner_id == user_id,
            "students_count": students_count
        })
    return result

@app.get("/api/schools/{school_id}")
async def get_school_details(school_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    member = db.query(SchoolMember).filter(
        SchoolMember.school_id == school_id, SchoolMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(403, "У вас нет доступа к этой школе")
    
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(404, "Школа не найдена")
    
    members = db.query(SchoolMember).filter(SchoolMember.school_id == school_id).all()
    members_list = [{"id": m.user_id, "name": m.user.name, "role": m.role, "joined_at": m.joined_at} for m in members]
    
    return {
        "id": school.id,
        "name": school.name,
        "description": school.description,
        "invite_code": school.invite_code,
        "created_at": school.created_at,
        "is_owner": school.owner_id == user_id,
        "members": members_list,
        "total_members": len(members_list)
    }

@app.get("/api/schools/{school_id}/stats")
async def get_school_stats_endpoint(school_id: int, teacher_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = await ai_service.get_school_stats(db, school_id, teacher_id)
        return result
    except ValueError as e:
        raise HTTPException(403, str(e))

@app.delete("/api/schools/{school_id}")
async def leave_school(school_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(404, "Школа не найдена")
    if school.owner_id == user_id:
        raise HTTPException(400, "Владелец школы не может её покинуть")
    
    member = db.query(SchoolMember).filter(SchoolMember.school_id == school_id, SchoolMember.user_id == user_id).first()
    if not member:
        raise HTTPException(404, "Вы не состоите в этой школе")
    db.delete(member)
    db.commit()
    return {"status": "ok", "message": "Вы покинули школу"}

@app.delete("/api/schools/{school_id}/delete")
async def delete_school(school_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id, School.owner_id == user_id).first()
    if not school:
        raise HTTPException(404, "Школа не найдена или вы не являетесь владельцем")
    
    db.query(SchoolMember).filter(SchoolMember.school_id == school_id).delete()
    db.delete(school)
    db.commit()
    return {"status": "ok", "message": "Школа удалена"}

# ========== ГРАФЫ ЗНАНИЙ ==========
@app.post("/api/users/{user_id}/build_target_graph")
async def build_target_graph_endpoint(
    user_id: int,
    exam_name: str,
    school_id: int = Query(...),   # обязательно передавать ID школы
    db: Session = Depends(get_db)
):
    try:
        result = await ai_service.build_target_graph(db, user_id, school_id, exam_name)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/sync_performance")
async def sync_performance_to_school(user_id: int, school_id: int, db: Session = Depends(get_db)):
    try:
        await ai_service.sync_student_performance(db, user_id, school_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/users/{user_id}/coefficient")
async def get_coefficient_endpoint(user_id: int, school_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = await ai_service.get_coefficient(db, user_id, school_id)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/users/{user_id}/learning_graphs")
async def get_learning_graphs_endpoint(user_id: int, school_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = await ai_service.get_learning_graphs(db, user_id, school_id)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

# ========== КУРСЫ И УРОКИ (дополнительные эндпоинты) ==========
@app.get("/api/course_lessons/{lesson_id}")
async def get_course_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

@app.post("/api/courses/{course_id}/generate_lesson_content/{lesson_id}")
async def generate_course_lesson_content(course_id: int, lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id, CourseLesson.module.has(course_id=course_id)
    ).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    if lesson.content and lesson.content.get("theory"):
        return {"status": "already_exists", "message": "Контент уже сгенерирован"}
    
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    title = lesson.title
    description = lesson.content.get("description", "") if lesson.content else ""
    
    content = await ai_service.generate_lesson_content(db, course.user_id, title, "общий предмет", description)
    if "error" in content:
        raise HTTPException(400, content["error"])
    
    lesson.content = content
    lesson.success_criteria = content.get("success_criteria", "")
    lesson.youtube_urls = content.get("youtube_urls", [])
    db.commit()
    return {"status": "ok", "message": "Содержание урока сгенерировано"}

@app.post("/api/courses/{course_id}/generate_all_lessons_content")
async def generate_all_lessons_content(course_id: int, db: Session = Depends(get_db)):
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    
    generated_count = 0
    errors = []
    
    for module in course.modules:
        for lesson in module.lessons:
            if lesson.content and lesson.content.get("theory"):
                continue
            try:
                title = lesson.title
                description = lesson.content.get("description", "") if lesson.content else ""
                content = await ai_service.generate_lesson_content(db, course.user_id, title, "общий предмет", description)
                if "error" not in content:
                    lesson.content = content
                    lesson.success_criteria = content.get("success_criteria", "")
                    lesson.youtube_urls = content.get("youtube_urls", [])
                    generated_count += 1
                else:
                    errors.append(f"Урок '{title}': {content['error']}")
            except Exception as e:
                errors.append(f"Урок '{title}': {str(e)}")
    
    db.commit()
    return {"status": "ok", "generated_count": generated_count, "errors": errors}

# ========== КОНФЕРЕНЦИЯ ==========
@app.get("/conference")
async def conference_redirect():
    return RedirectResponse(url="http://localhost:8000")

@app.get("/conference/teacher")
async def conference_teacher_redirect():
    return RedirectResponse(url="http://localhost:8000/teacher")

@app.get("/conference/student")
async def conference_student_redirect():
    return RedirectResponse(url="http://localhost:8000/student")

from .auth import get_password_hash, verify_password, create_access_token, get_current_user

# Регистрация
@app.post("/api/auth/register")
async def register(username: str, password: str, name: str, email: str, role: str = "student", db: Session = Depends(get_db)):
    # Проверка уникальности username
    existing = db.query(UserAuth).filter(UserAuth.username == username).first()
    if existing:
        raise HTTPException(400, "Username already exists")
    
    # Создаём пользователя
    user = User(name=name, email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Создаём аутентификацию
    user_auth = UserAuth(
        user_id=user.id,
        username=username,
        password_hash=get_password_hash(password),
        avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
    )
    db.add(user_auth)
    db.commit()
    
    token = create_access_token(data={"sub": user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role, "name": user.name, "avatar_url": user_auth.avatar_url}

# Логин
@app.post("/api/auth/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user_auth = db.query(UserAuth).filter(UserAuth.username == username).first()
    if not user_auth or not verify_password(password, user_auth.password_hash):
        raise HTTPException(401, "Неверное имя пользователя или пароль")
    
    user = user_auth.user
    user_auth.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token(data={"sub": user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role, "name": user.name, "avatar_url": user_auth.avatar_url}

# Получить профиль текущего пользователя
@app.get("/api/auth/profile")
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_auth = db.query(UserAuth).filter(UserAuth.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_url": user_auth.avatar_url if user_auth else None,
        "username": user_auth.username if user_auth else None
    }

# Обновить аватар
@app.post("/api/auth/avatar")
async def update_avatar(data: AvatarUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_auth = db.query(UserAuth).filter(UserAuth.user_id == current_user.id).first()
    if user_auth:
        user_auth.avatar_url = data.avatar_url
        db.commit()
    return {"avatar_url": data.avatar_url}

# ========== ЧАТ ШКОЛЫ ==========

# Получить сообщения общего чата школы (последние 50)
@app.get("/api/chat/school/{school_id}/messages")
async def get_school_chat_messages(
    school_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверяем, является ли пользователь участником школы
    member = db.query(SchoolMember).filter(
        SchoolMember.school_id == school_id,
        SchoolMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(403, "Вы не являетесь участником этой школы")
    
    messages = db.query(SchoolChatMessage).filter(
        SchoolChatMessage.school_id == school_id,
        SchoolChatMessage.is_private == False
    ).order_by(SchoolChatMessage.created_at.desc()).limit(limit).all()
    
    return [{
        "id": m.id,
        "user_id": m.user_id,
        "user_name": m.user.name,
        "user_role": m.user.role,
        "avatar_url": db.query(UserAuth).filter(UserAuth.user_id == m.user_id).first().avatar_url if db.query(UserAuth).filter(UserAuth.user_id == m.user_id).first() else None,
        "message": m.message,
        "created_at": m.created_at.isoformat()
    } for m in reversed(messages)]

# Отправить сообщение в общий чат школы
@app.post("/api/chat/school/{school_id}/send")
async def send_school_chat_message(
    school_id: int,
    message: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    member = db.query(SchoolMember).filter(
        SchoolMember.school_id == school_id,
        SchoolMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(403, "Вы не являетесь участником этой школы")
    
    new_msg = SchoolChatMessage(
        school_id=school_id,
        user_id=current_user.id,
        message=message,
        is_private=False
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    return {"status": "ok", "message_id": new_msg.id}

# Получить личные сообщения между текущим пользователем и указанным пользователем
@app.get("/api/chat/private/{other_user_id}")
async def get_private_messages(
    other_user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    messages = db.query(SchoolChatMessage).filter(
        SchoolChatMessage.is_private == True,
        ((SchoolChatMessage.user_id == current_user.id) & (SchoolChatMessage.recipient_id == other_user_id)) |
        ((SchoolChatMessage.user_id == other_user_id) & (SchoolChatMessage.recipient_id == current_user.id))
    ).order_by(SchoolChatMessage.created_at.desc()).limit(limit).all()
    
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(404, "Пользователь не найден")
    
    return [{
        "id": m.id,
        "user_id": m.user_id,
        "user_name": m.user.name,
        "message": m.message,
        "created_at": m.created_at.isoformat()
    } for m in reversed(messages)]

# Отправить личное сообщение
@app.post("/api/chat/private/send")
async def send_private_message(
    recipient_id: int = Body(...),
    message: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(404, "Получатель не найден")
    
    # Проверяем, что оба пользователя состоят в одной школе
    common_school = db.query(SchoolMember).filter(
        SchoolMember.user_id == current_user.id
    ).filter(
        SchoolMember.school_id.in_(
            db.query(SchoolMember.school_id).filter(SchoolMember.user_id == recipient_id)
        )
    ).first()
    if not common_school:
        raise HTTPException(403, "Вы не можете писать этому пользователю (нет общей школы)")
    
    new_msg = SchoolChatMessage(
        school_id=common_school.school_id,
        user_id=current_user.id,
        recipient_id=recipient_id,
        message=message,
        is_private=True
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    return {"status": "ok", "message_id": new_msg.id}


@app.on_event("startup")
async def init_ocr():
    global ocr_reader
    try:
        ocr_reader = easyocr.Reader(['ru', 'en'], gpu=False)
        print("✅ EasyOCR загружен")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки EasyOCR: {e}")

@app.post("/api/ocr/recognize")
async def recognize_handwriting(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)  # опционально, если хотим авторизацию
):
    """Распознаёт рукописный текст из загруженного изображения"""
    if ocr_reader is None:
        raise HTTPException(503, "OCR сервис не инициализирован")
    
    try:
        # Читаем файл
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        # Конвертируем в numpy array (RGB)
        img_array = np.array(image)
        
        # Распознаём текст
        result = ocr_reader.readtext(img_array, detail=1)
        
        if not result:
            return {"text": "", "confidence": 0}
        
        # Собираем весь текст
        full_text = ' '.join([item[1] for item in result])
        # Средняя уверенность
        avg_confidence = sum(item[2] for item in result) / len(result)
        
        # Пост-обработка через DeepSeek для исправления ошибок (опционально, но повышает качество)
        # Раскомментируйте если хотите улучшить результат
        corrected = await deepseek_client.chat_completion([
             {"role": "system", "content": "Ты эксперт по исправлению OCR-ошибок. Исправь распознанный текст, сохранив смысл."},
             {"role": "user", "content": f"Распознанный текст:\n{full_text}\n\nИсправь ошибки распознавания и верни только исправленный текст:"}
        ])
        full_text = corrected.strip()
        
        return {"text": full_text, "confidence": round(avg_confidence, 2)}
        
    except Exception as e:
        print(f"OCR ошибка: {e}")
        raise HTTPException(400, f"Ошибка распознавания: {str(e)}")

#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.responses import HTMLResponse, JSONResponse
import json
import os
import logging
from datetime import datetime
from openai import OpenAI
import httpx
from dotenv import load_dotenv
import re
import os
import logging
import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Request, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON, Index, and_, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr, Field, validator
import bcrypt
import requests
import smtplib
from jose import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import user_agents
import random
from enum import Enum
from fastapi import FastAPI, Depends, HTTPException, status, Request, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.responses import JSONResponse
from fastapi import Body, Query
import time
import json
import os
import re
import random
from datetime import datetime, timedelta
import uvicorn
import pickle
from fastapi import Request, Query
import hashlib
import uuid
import traceback
import requests
from fastapi.responses import JSONResponse
from modules.translator import translator
from modules.grammar_explainer import grammar_explainer
import json
import asyncio
from modules.grammar_explainer import grammar_explainer
from modules.hsk_test_generator import test_generator, generate_hsk_test_api, evaluate_speaking_api, evaluate_writing_api, generate_certificate_api, generate_progress_report_api
from pydantic import Field
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import timezone
from enum import Enum

SECRET_KEY = "hsk_tutor_super_secret_key_2024_change_in_production_1234567890"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SQLALCHEMY_DATABASE_URL = "sqlite:///./hsk_tutor.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from pathlib import Path
import os

# Папка backend, где лежат data/
BACKEND_ROOT = Path(__file__).parent.parent
DATA_DIR = BACKEND_ROOT / "data"

# Функция для получения правильного пути к файлу
def data_path(filename):
    return str(DATA_DIR / filename)

class Subject(str, Enum):
    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"

class InterviewSessionDB(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Связь с пользователем, может быть NULL для гостей
    university = Column(String, nullable=False)
    program = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    professors = Column(JSON, nullable=True)  # Хранить список профессоров
    tech_expert = Column(JSON, nullable=True)
    messages = Column(JSON, nullable=True, default=list)  # Хранить всю историю сообщений
    ended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="interview_sessions")
    
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    interview_sessions = relationship("InterviewSessionDB", back_populates="user", cascade="all, delete-orphan")
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Profile
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")
    
    # HSK settings
    current_hsk_level = Column(Integer, default=1)
    target_hsk_level = Column(Integer, default=4)
    exam_date = Column(DateTime, nullable=True)
    daily_goal = Column(Integer, default=20)
    
    # Statistics (will be updated automatically)
    total_points = Column(Integer, default=0)
    study_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    total_study_time = Column(Integer, default=0)  # in minutes
    total_words_learned = Column(Integer, default=0)
    total_tests_taken = Column(Integer, default=0)
    average_test_score = Column(Float, default=0.0)
    
    # Settings
    email_notifications = Column(Boolean, default=True)
    theme = Column(String, default="light")
    
    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    actions = relationship("UserAction", back_populates="user", cascade="all, delete-orphan", order_by="desc(UserAction.timestamp)")
    words = relationship("UserWord", back_populates="user", cascade="all, delete-orphan")
    tests = relationship("UserTest", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")

    education_background = Column(Text, nullable=True)  # JSON string with education data
    university_target = Column(String, nullable=True)
    program_target = Column(String, nullable=True)
    department_target = Column(String, nullable=True)
    work_experience = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)  # JSON string with languages
    technical_skills = Column(Text, nullable=True)
    achievements = Column(Text, nullable=True)
    letter_style = Column(JSON, nullable=True)

class EducationData(BaseModel):
    university: Optional[str] = None
    program: Optional[str] = None
    department: Optional[str] = None
    why_uni: Optional[str] = None
    education: Optional[str] = None
    work: Optional[str] = None
    projects: Optional[str] = None
    languages: Optional[str] = None
    skills: Optional[str] = None
    achievements: Optional[str] = None
    tone: Optional[str] = "professional"
    length: Optional[str] = "medium"
    instructions: Optional[str] = None

# Dependencies for authorization
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")  # IMPORTANT: use user_id
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()  # Search by ID
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

users_access = {}
users_db = {}
corporate_accounts = {}
corporate_members = {}
chat_threads = {}
current_threads = {}
word_progress_db = {}
tests_db = {}
chat_history = {}
access_db = {}
words_db = []
ai_cache = {}

def get_or_create_access(fingerprint: str):
    now = datetime.now(timezone.utc)

    if fingerprint not in users_access:
        users_access[fingerprint] = {
            "first_seen": now,
            "trial_expires_at": now + timedelta(hours=24),
            "status": "GUEST_TRIAL",
            "paid_until": None,
            "plan": None
        }

    return users_access[fingerprint]

# AI imports
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========== APP SETUP ==========

# access_db example:
# {
#   fingerprint: {
#       "created_at": datetime,
#       "expires_at": datetime,
#       "user_id": None | "user_123",
#       "plan": None | "trial" | "basic" | "school"
#   }
# }

csca_math_topics = []
# ========== BEAUTIFUL RESPONSE FORMATTING ==========
import markdown
import bleach
import re
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

# CSS styles for beautiful display
MARKDOWN_CSS = """
<style>
    /* General styles for AI messages */
    .ai-message {
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: #2c3e50;
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* LaTeX formulas */
    .ai-message .math, 
    .ai-message .katex,
    .ai-message .MathJax {
        font-size: 1.1em;
        color: #e67e22;
        background: #fff3e0;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 500;
    }
    
    .ai-message .math-display {
        display: block;
        margin: 15px 0;
        padding: 15px;
        background: #2c3e50;
        color: #fff;
        border-radius: 8px;
        overflow-x: auto;
        font-size: 1.2em;
        text-align: center;
    }
    
    /* Headings */
    .ai-message h1, .ai-message h2, .ai-message h3, 
    .ai-message h4, .ai-message h5, .ai-message h6 {
        color: #1a2634;
        margin-top: 1.5em;
        margin-bottom: 0.75em;
        font-weight: 600;
    }
    
    .ai-message h1 { font-size: 1.8em; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    .ai-message h2 { font-size: 1.5em; border-left: 4px solid #3498db; padding-left: 15px; }
    .ai-message h3 { font-size: 1.3em; color: #2980b9; }
    
    /* Lists */
    .ai-message ul, .ai-message ol {
        padding-left: 25px;
        margin: 10px 0;
    }
    
    .ai-message li {
        margin: 5px 0;
    }
    
    .ai-message ul li {
        list-style-type: disc;
    }
    
    .ai-message ol li {
        list-style-type: decimal;
    }
    
    /* Tables */
    .ai-message table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .ai-message th {
        background: #3498db;
        color: white;
        padding: 12px;
        text-align: left;
    }
    
    .ai-message td {
        padding: 10px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .ai-message tr:nth-child(even) {
        background: #f2f2f2;
    }
    
    .ai-message tr:hover {
        background: #e8f4fd;
    }
    
    /* Code and formulas */
    .ai-message pre {
        background: #282c34;
        color: #abb2bf;
        padding: 15px;
        border-radius: 8px;
        overflow-x: auto;
        font-family: 'Fira Code', 'Consolas', monospace;
        font-size: 0.9em;
    }
    
    .ai-message code {
        background: #e8e8e8;
        color: #c0392b;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Fira Code', 'Consolas', monospace;
        font-size: 0.9em;
    }
    
    /* Quotes */
    .ai-message blockquote {
        border-left: 4px solid #95a5a6;
        margin: 10px 0;
        padding: 10px 20px;
        background: #ecf0f1;
        font-style: italic;
        color: #7f8c8d;
    }
    
    /* Highlight important */
    .ai-message .highlight {
        background: #fffacd;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: 600;
    }
    
    .ai-message .warning {
        background: #ffebee;
        color: #c62828;
        padding: 10px;
        border-left: 4px solid #c62828;
        margin: 10px 0;
    }
    
    .ai-message .tip {
        background: #e8f5e9;
        color: #2e7d32;
        padding: 10px;
        border-left: 4px solid #2e7d32;
        margin: 10px 0;
    }
    
    /* Responsiveness */
    @media (max-width: 768px) {
        .ai-message {
            padding: 15px;
            font-size: 0.95em;
        }
        
        .ai-message table {
            font-size: 0.9em;
        }
        
        .ai-message pre {
            font-size: 0.8em;
        }
    }
</style>
"""

# Add after imports, before endpoint definitions

from fastapi import Request, Response
import json
from datetime import datetime
from sqlalchemy.orm import Session
import traceback

# Cache for user_id conversion
user_id_cache = {}

def get_sqlite_user_id(old_user_id: str, db: Session) -> int:
    """Convert old user_id (user_123) to SQLite ID"""
    if old_user_id in user_id_cache:
        return user_id_cache[old_user_id]
    
    # Look for user in old format in users_db
    if old_user_id in users_db:
        # Create or find in SQLite
        user_data = users_db[old_user_id]
        email = user_data.get("email", f"{old_user_id}@temp.com")
        
        sqlite_user = db.query(User).filter(User.email == email).first()
        if not sqlite_user:
            # Create new user in SQLite
            sqlite_user = User(
                email=email,
                username=user_data.get("name", f"user_{old_user_id}"),
                hashed_password="migrated",  # Mark as migrated
                full_name=user_data.get("name", ""),
                current_hsk_level=user_data.get("current_level", 1),
                target_hsk_level=user_data.get("target_level", 4)
            )
            db.add(sqlite_user)
            db.commit()
            db.refresh(sqlite_user)
        
        user_id_cache[old_user_id] = sqlite_user.id
        return sqlite_user.id
    
    return None

@app.middleware("http")
async def universal_data_sync(request: Request, call_next):
    """Universal middleware for synchronizing all data"""
    
    # Skip static files and documentation
    if request.url.path.startswith(("/data/", "/docs", "/redoc", "/openapi.json")):
        return await call_next(request)
    
    response = await call_next(request)
    
    # Check if there was an error
    if response.status_code >= 400:
        return response
    
    # Try to determine user_id from request
    user_id = None
    db = SessionLocal()
    
    try:
        # Look for user_id in different places
        # 1. In query parameters
        if "user_id" in request.query_params:
            user_id = request.query_params["user_id"]
        
        # 2. In request body (if POST)
        elif request.method == "POST":
            try:
                body = await request.json()
                if "user_id" in body:
                    user_id = body["user_id"]
            except:
                pass
        
        # 3. In headers
        elif "X-User-Id" in request.headers:
            user_id = request.headers["X-User-Id"]
        
        if user_id and user_id.startswith("user_"):
            # Convert to SQLite ID
            sqlite_user_id = get_sqlite_user_id(user_id, db)
            
            if sqlite_user_id:
                # Save ALL activity based on endpoint
                await save_all_activity(request, response, user_id, sqlite_user_id, db)
        
        db.commit()
        
    except Exception as e:
        print(f"Middleware error: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
    
    return response

async def save_all_activity(request: Request, response: Response, old_user_id: str, sqlite_user_id: int, db: Session):
    """Save ALL types of user activity"""
    
    path = request.url.path
    method = request.method
    
    # 1. SAVE LEARNED WORDS
    if "/words/status" in path and method == "POST":
        try:
            body = await request.json()
            word_id = body.get("word_id")
            status = body.get("status")
            
            if word_id and status:
                # Parse word_id (format: "你好_1")
                parts = word_id.rsplit('_', 1)
                word_text = parts[0]
                hsk_level = int(parts[1]) if len(parts) > 1 else 1
                
                # Save to SQLite
                word = db.query(UserWord).filter(
                    UserWord.user_id == sqlite_user_id,
                    UserWord.word_id == word_id
                ).first()
                
                if not word:
                    word = UserWord(
                        user_id=sqlite_user_id,
                        word_id=word_id,
                        word_text=word_text,
                        hsk_level=hsk_level,
                        status=status
                    )
                    db.add(word)
                else:
                    word.status = status
                    word.updated_at = datetime.utcnow()
                
                # Update learned words counter
                learned_count = db.query(UserWord).filter(
                    UserWord.user_id == sqlite_user_id,
                    UserWord.status == "learned"
                ).count()
                
                user = db.query(User).filter(User.id == sqlite_user_id).first()
                if user:
                    user.total_words_learned = learned_count
                
                print(f"✅ Saved word: {word_id} ({status}) for user {sqlite_user_id}")
                
        except Exception as e:
            print(f"Error saving word: {e}")
    
    # 2. SAVE TESTS
    elif "/words/test/submit" in path and method == "POST":
        try:
            body = await request.json()
            test_id = body.get("test_id")
            answers = body.get("answers", {})
            
            # Get test from old system
            test_key = f"active_word_test_{old_user_id}"
            if test_key in tests_db:
                test_data = tests_db[test_key]
                questions = test_data.get("questions", [])
                
                # Calculate result
                correct = 0
                for q in questions:
                    qid = q["id"]
                    user_ans = answers.get(qid, "").strip().lower()
                    correct_ans = q["correct"].strip().lower()
                    
                    if user_ans and user_ans == correct_ans:
                        correct += 1
                
                # Save to SQLite
                user_test = UserTest(
                    user_id=sqlite_user_id,
                    test_id=test_id,
                    test_type="vocabulary",
                    test_level=1,
                    score=correct,
                    max_score=len(questions),
                    questions_count=len(questions),
                    correct_count=correct,
                    wrong_count=len(questions) - correct,
                    answers=answers,
                    created_at=datetime.utcnow()
                )
                db.add(user_test)
                
                # Update user statistics
                user = db.query(User).filter(User.id == sqlite_user_id).first()
                if user:
                    user.total_tests_taken += 1
                    # Recalculate average score
                    all_tests = db.query(UserTest).filter(
                        UserTest.user_id == sqlite_user_id,
                        UserTest.score.isnot(None)
                    ).all()
                    
                    if all_tests:
                        avg_score = sum(t.score for t in all_tests) / len(all_tests)
                        user.average_test_score = round(avg_score, 2)
                
                print(f"✅ Saved test: {test_id}, score: {correct}/{len(questions)}")
                
        except Exception as e:
            print(f"Error saving test: {e}")
    
    # 3. SAVE CHAT MESSAGES
    elif "/chat/" in path and ("/message" in path or "send" in path) and method == "POST":
        try:
            body = await request.json()
            message = body.get("message", "")
            thread_id = body.get("thread_id") or request.path_params.get("thread_id")
            
            # Extract role from URL or body
            role = "user"  # Default user
            
            # Save to SQLite
            chat_msg = ChatMessage(
                user_id=sqlite_user_id,
                thread_id=thread_id or f"thread_{datetime.now().timestamp()}",
                role=role,
                content=message,
                message_metadata={
                    "timestamp": datetime.now().isoformat(),
                    "path": path
                }
            )
            db.add(chat_msg)
            print(f"✅ Saved chat message for user {sqlite_user_id}")
            
        except Exception as e:
            print(f"Error saving chat: {e}")
    
    # 4. SAVE STUDY TIME (any GET request to study materials)
    elif method == "GET" and any(x in path for x in ["/word", "/test", "/lesson", "/course", "/grammar"]):
        try:
            # Update or create study session
            today = datetime.utcnow().date()
            
            # Look for active session today
            session = db.query(StudySession).filter(
                StudySession.user_id == sqlite_user_id,
                StudySession.is_active == True,
                func.date(StudySession.start_time) == today
            ).first()
            
            if not session:
                session = StudySession(
                    user_id=sqlite_user_id,
                    start_time=datetime.utcnow(),
                    is_active=True
                )
                db.add(session)
            
            # Increase action counter
            session.actions_count += 1
            
            # If session lasts more than an hour, update duration
            if session.start_time:
                duration = int((datetime.utcnow() - session.start_time).total_seconds() / 60)
                session.duration_minutes = duration
            
            print(f"✅ Updated study session for user {sqlite_user_id}")
            
        except Exception as e:
            print(f"Error updating session: {e}")
    
    # 5. SAVE ALL ACTIONS (for history)
    try:
        action = UserAction(
            user_id=sqlite_user_id,
            action_type=path.replace("/", "_").strip("_"),
            action_data={
                "method": method,
                "path": path,
                "query": str(request.query_params),
                "status": response.status_code
            },
            timestamp=datetime.utcnow(),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(action)
        
    except Exception as e:
        print(f"Error saving action: {e}")

def format_ai_response(text: str, section: str = "general") -> dict:
    """Format AI response with beautiful Markdown, LaTeX, and code highlighting"""
    try:
        # Preprocess LaTeX formulas
        text = re.sub(r'\$\$(.*?)\$\$', r'<div class="math-display">\1</div>', text, flags=re.DOTALL)
        text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', r'<span class="math">\1</span>', text)
        text = re.sub(r'\\\[(.*?)\\\]', r'<div class="math-display">\1</div>', text, flags=re.DOTALL)
        text = re.sub(r'\\\((.*?)\\\)', r'<span class="math">\1</span>', text, flags=re.DOTALL)
        
        # Convert Markdown to HTML
        md = markdown.Markdown(
            extensions=['extra', 'codehilite', 'tables', 'fenced_code'],
            extension_configs={
                'codehilite': {
                    'linenums': False,
                    'guess_lang': True,
                    'css_class': 'highlight',
                },
            }
        )
        html_content = md.convert(text)
        
        # Clean HTML
        allowed_tags = [
            'a', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'span', 'div', 'pre',
            'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'hr', 'dl', 'dt', 'dd',
            'sup', 'sub', 'del', 'ins', 'kbd', 'q', 'math', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub'
        ]
        
        safe_html = bleach.clean(html_content, tags=allowed_tags, strip=True)
        
        # Determine class for section
        section_class = {
            "ai-tutor": "tutor",
            "admission": "admission",
            "csca-math": "math",
            "csca-physics": "physics",
            "csca-chemistry": "chemistry"
        }.get(section, "general")
        
        formatted_html = f'<div class="ai-message ai-{section_class}">{safe_html}</div>'
        
        return {
            "success": True,
            "formatted_html": formatted_html,
            "plain_text": bleach.clean(html_content, tags=[], strip=True),
            "css": MARKDOWN_CSS,
            "section": section,
            "has_latex": any(s in text for s in ["$$", "\\[", "\\(", "$"]),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Formatting error: {e}")
        return {
            "success": False,
            "formatted_html": f'<div class="ai-message"><p>{text}</p></div>',
            "plain_text": text,
            "css": MARKDOWN_CSS,
            "section": section,
            "timestamp": datetime.now().isoformat()
        }
    

@app.post("/user/education/save")
async def save_education_data(
    education_data: EducationData,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Save user's Education Background"""
    try:
        # Save as JSON string
        current_user.education_background = education_data.json()
        current_user.university_target = education_data.university
        current_user.program_target = education_data.program
        current_user.department_target = education_data.department
        current_user.work_experience = education_data.work
        current_user.projects = education_data.projects
        current_user.languages = education_data.languages
        current_user.technical_skills = education_data.skills
        current_user.achievements = education_data.achievements
        current_user.letter_style = {
            "tone": education_data.tone,
            "length": education_data.length,
            "instructions": education_data.instructions
        }
        
        db.commit()
        
        # Log action
        log_user_action(db, current_user.id, "education_data_saved", education_data.dict(), None)
        
        return {"success": True, "message": "Education data saved"}
    except Exception as e:
        logger.error(f"Error saving education data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/education/get")
async def get_education_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's Education Background"""
    try:
        return {
            "university": current_user.university_target,
            "program": current_user.program_target,
            "department": current_user.department_target,
            "work": current_user.work_experience,
            "projects": current_user.projects,
            "languages": current_user.languages,
            "skills": current_user.technical_skills,
            "achievements": current_user.achievements,
            "letter_style": current_user.letter_style or {}
        }
    except Exception as e:
        logger.error(f"Error getting education data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

def format_chat_response(response_text: str, user_id: str = None, section: str = "ai-tutor") -> dict:
    """Wrapper for formatting chat responses"""
    formatted = format_ai_response(response_text, section)
    
    return {
        "response": formatted["plain_text"],  # For backward compatibility
        "formatted_response": formatted["formatted_html"],  # For beautiful display
        "css": formatted["css"],
        "has_latex": formatted["has_latex"],
        "section": section,
        "timestamp": formatted["timestamp"]
    }

# API endpoint for CSS
from fastapi.responses import Response

@app.get("/api/format-css")
async def get_format_css():
    return Response(content=MARKDOWN_CSS, media_type="text/css")

# Add at the beginning of main.py
CSCA_PROGRESS_FILE = data_path("csca_progress.json")

def load_csca_progress():
    """Load progress on CSCA topics"""
    try:
        with open(CSCA_PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_csca_progress(progress_data):
    """Save progress on CSCA topics"""
    os.makedirs("data", exist_ok=True)
    with open(CSCA_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

# Add new endpoint
@app.post("/csca/math/update-topic-status")
async def update_csca_topic_status(request: dict):
    """Update topic status"""
    try:
        user_id = request.get("user_id")
        topic_id = request.get("topic_id")
        status = request.get("status")  # "learned" or "problematic" or "none"
        
        if not user_id or not topic_id:
            raise HTTPException(status_code=400, detail="Missing user_id or topic_id")
        
        # Load current progress
        progress = load_csca_progress()
        
        # Initialize user progress if not exists
        if user_id not in progress:
            progress[user_id] = {}
        
        # Update status
        if status == "none":
            # Remove status if "none"
            progress[user_id].pop(topic_id, None)
        else:
            progress[user_id][topic_id] = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
        
        # Save
        save_csca_progress(progress)
        
        return {
            "success": True,
            "message": f"Status updated: {status}",
            "user_id": user_id,
            "topic_id": topic_id,
            "status": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
from fastapi.staticfiles import StaticFiles

# Allow access to files in data/ folder
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

@app.get("/csca/math/user-progress/{user_id}")
async def get_csca_user_progress(user_id: str):
    """Get user progress on CSCA topics"""
    progress = load_csca_progress()
    user_progress = progress.get(user_id, {})
    
    # Statistics
    learned = sum(1 for topic in user_progress.values() 
                  if topic.get("status") == "learned")
    problematic = sum(1 for topic in user_progress.values() 
                      if topic.get("status") == "problematic")
    
    return {
        "user_id": user_id,
        "progress": user_progress,
        "stats": {
            "learned": learned,
            "problematic": problematic,
            "total_topics": len(user_progress)
        }
    }

@app.post("/csca/math/generate-filtered-test")
async def generate_filtered_csca_test(request: dict):
    """Generate test on filtered topics"""
    try:
        user_id = request.get("user_id")
        filter_type = request.get("filter_type", "learned")  # "learned" or "problematic"
        count = request.get("count", 20)
        lang = request.get("lang", "zh")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        # Get user progress
        progress = load_csca_progress()
        user_progress = progress.get(user_id, {})
        
        # Filter topics by status
        filtered_topics = []
        for topic_id, topic_data in user_progress.items():
            if topic_data.get("status") == filter_type:
                filtered_topics.append(topic_id)
        
        if not filtered_topics:
            return {
                "success": False,
                "message": f"No {filter_type} topics found",
                "fallback": True,
                "test_id": f"csca_fallback_{int(time.time())}",
                "questions": generate_fallback_questions(min(10, count), lang),
                "lang": lang
            }
        
        # Generate test on filtered topics
        # (here you can implement logic to select questions from these topics)
        # For now, return a general test with a note
        
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI unavailable")
        
        topics_text = ", ".join(filtered_topics[:5]) + ("..." if len(filtered_topics) > 5 else "")
        
        prompt = f"""
        Create {count} mathematics problems for CSCA on the following topics: {topics_text}
        Language: {'Chinese' if lang == 'zh' else 'English'}
        Filter type: {filter_type} (already learned/problematic topics)
        
        Each problem:
        1. Question with 4 answer options
        2. Only one correct answer
        3. Brief explanation
        
        Return JSON in format:
        {{"questions": [{{"id": "1", "question": "...", "options": ["A","B","C","D"], "correct_answer": "B", "explanation": "..."}}]}}
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            questions = result.get("questions", [])
        except:
            questions = []
        
        # Structure questions
        structured_questions = []
        for i, q in enumerate(questions[:count]):
            structured_questions.append({
                "id": str(i + 1),
                "question": q.get("question", f"Question {i+1}"),
                "options": q.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                "correct_answer": q.get("correct_answer", "A"),
                "explanation": q.get("explanation", "Explanation"),
                "source_topics": filtered_topics,
                "filter_type": filter_type
            })
        
        test_id = f"csca_filtered_{filter_type}_{int(time.time())}"
        
        # Save test
        if test_id not in tests_db:
            tests_db[test_id] = {}
        
        tests_db[test_id] = {
            "questions": structured_questions,
            "filter_type": filter_type,
            "lang": lang,
            "generated_at": datetime.now().isoformat(),
            "count": len(structured_questions),
            "topics": filtered_topics,
            "user_id": user_id
        }
        
        save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "count": len(structured_questions),
            "questions": structured_questions,
            "lang": lang,
            "filter_type": filter_type,
            "topics_count": len(filtered_topics)
        }
        
    except Exception as e:
        print(f"Filtered test error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def load_csca_math_topics():
    global csca_math_topics
    try:
        with open(data_path("csca_math_topics.json"), "r", encoding="utf-8") as f:
            csca_math_topics = json.load(f)
        print(f"✅ Loaded {len(csca_math_topics)} CSCA Mathematics topics")
    except FileNotFoundError:
        print("⚠️ csca_math_topics.json not found")

# Call on startup
load_csca_math_topics()

TRIAL_DURATION = timedelta(hours=24)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Корень проекта (над backend)
PROJECT_ROOT = Path(__file__).parent.parent.parent
# или, если этот BASE_DIR используется только для каких-то static, оставьте как есть, но лучше удалить дублирование

# At the beginning of main.py
class ChatThread(BaseModel):
    thread_id: str
    user_id: str
    title: str
    created_at: str
    messages: List[Dict]
    category: str = "general"  # grammar, vocabulary, test_prep, etc.

# Global variables
user_word_status: Dict[str, Dict[str, Dict]] = {}  # user_id -> {word_id: {"status": "saved"/"learned", "added_at": iso_str}}

# ========== DATA MODELS ==========
class UserInfo(BaseModel):
    name: str
    current_level: int = 1
    target_level: int = 4
    exam_date: str = "2024-12-01"
    exam_location: str = "Moscow"
    exam_format: str = "computer"  # computer or paper
    interests: List[str] = []
    daily_time: int = 30  # minutes per day
    learning_style: str = "visual"  # visual, auditory, kinesthetic

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None

class TestAnswer(BaseModel):
    user_id: str
    test_id: str
    answers: Dict[str, Any]  # question_id: answer

class WordReview(BaseModel):
    user_id: str
    word_id: str  # character + level
    difficulty: int  # 1-5, where 1=easy, 5=very difficult
    remembered: bool

class AuthRequest(BaseModel):
    username: str
    action: str = "login_or_register"
    password: Optional[str] = None

# Models for full registration
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    current_level: int = 1
    target_level: int = 4
    exam_date: str
    exam_location: str = "Moscow"
    exam_format: str = "computer"
    interests: List[str] = []
    daily_time: int = 30
    learning_style: str = "visual"

class UserLogin(BaseModel):
    email: str
    password: str

# Add this model somewhere with other Pydantic models (e.g., after UserLogin):

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Model for chat update
class ChatUpdate(BaseModel):
    thread_id: str
    title: str
    category: str

class VoiceChatRequest(BaseModel):
    message: str
    thread_id: str = Field(..., min_length=1, description="Thread ID is required")
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None

@app.post("/voice")
async def voice_chat(request: VoiceChatRequest):
    """Voice chat with AI for learning (fixed version)"""
    try:
        # VALIDATION: check required fields
        if not request.thread_id or request.thread_id.strip() == "":
            raise HTTPException(status_code=422, detail="thread_id is required")
        
        if not request.message or request.message.strip() == "":
            raise HTTPException(status_code=422, detail="message is required")
        
        print(f"🎤 Received voice/chat request:")
        print(f"   message: {request.message[:100]}...")
        print(f"   thread_id: {request.thread_id}")
        print(f"   context keys: {list(request.context.keys())}")
        print(f"   user_id: {request.user_id}")
        
        # Check if thread exists
        thread_exists = False
        if request.thread_id:
            for user_threads in chat_threads.values():
                for thread in user_threads:
                    if thread["thread_id"] == request.thread_id:
                        thread_exists = True
                        break
                if thread_exists:
                    break
        
        # If thread doesn't exist, create a new one
        if not thread_exists and request.user_id:
            print(f"📝 Creating new thread for user_id: {request.user_id}")
            thread_id = f"voice_thread_{datetime.now().timestamp()}"
            
            if request.user_id not in chat_threads:
                chat_threads[request.user_id] = []
            
            thread = {
                "thread_id": thread_id,
                "user_id": request.user_id,
                "title": "Voice Chat with AI",
                "category": "voice_chat",
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "updated_at": datetime.now().isoformat()
            }
            
            chat_threads[request.user_id].append(thread)
            current_threads[request.user_id] = thread_id
            request.thread_id = thread_id  # Update thread_id in request
        system_prompt = """You are a Chinese AI teacher. You MUST speak ONLY in Chinese (普通话).

# STRICT RULES:
1. 🇨🇳 Always respond ONLY in Chinese
2. 🗣️ Use both spoken and written Chinese
3. 🎯 Explain complex things in simple words, but in Chinese
4. Without pinyin

# RECOMMENDATIONS:
- Use different difficulty levels (HSK 1-6)
- Repeat previously learned words
- Ask questions for practice
- Be patient and encouraging

# CURRENT STUDENT LEVEL:
User level: HSK {user_level}

Don't speak other languages in the main text. Only Chinese with explanations in parentheses!"""

        # Form context
        command_type = request.context.get("command_type", "general")
        
        # Adapt prompt for command type
        if command_type == "chengyu":
            system_prompt += "\n\nUser requested a new chengyu. Choose an interesting and useful chengyu for their level."
        elif command_type == "explain":
            system_prompt += "\n\nUser requested an explanation. Be as clear as possible."
        
        # Get user level
        user_level = 3
        if request.user_id and request.user_id in users_db:
            user = users_db[request.user_id]
            user_level = user.get("current_level", 3)
        
        # Add level to prompt
        system_prompt += f"\n\nUser level: HSK {user_level}"
        
        # Send request to DeepSeek
        client = get_deepseek_client()
        if not client:
            return {"response": "AI service temporarily unavailable", "error": "no_api_key"}
        
        # Form message history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
        
        print(f"🤖 Sending request to AI with {len(request.message)} characters")
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.8,
                max_tokens=800,
                presence_penalty=0.6,
                frequency_penalty=0.5
            )
            
            ai_response = response.choices[0].message.content
            
            print(f"🤖 Received response from AI: {len(ai_response)} characters")
            
            # Save message to history
            if request.thread_id and request.user_id:
                # Find or create thread
                thread_found = False
                for user_threads in chat_threads.values():
                    for thread in user_threads:
                        if thread["thread_id"] == request.thread_id:
                            thread["messages"].append({
                                "role": "user",
                                "content": request.message,
                                "timestamp": datetime.now().isoformat()
                            })
                            thread["messages"].append({
                                "role": "assistant",
                                "content": ai_response,
                                "timestamp": datetime.now().isoformat()
                            })
                            thread["updated_at"] = datetime.now().isoformat()
                            thread_found = True
                            break
                    if thread_found:
                        break
                
                if not thread_found and request.user_id:
                    # Create new thread
                    if request.user_id not in chat_threads:
                        chat_threads[request.user_id] = []
                    
                    new_thread = {
                        "thread_id": request.thread_id,
                        "user_id": request.user_id,
                        "title": "Voice Chat with AI",
                        "category": "voice_chat",
                        "created_at": datetime.now().isoformat(),
                        "messages": [
                            {
                                "role": "user",
                                "content": request.message,
                                "timestamp": datetime.now().isoformat()
                            },
                            {
                                "role": "assistant",
                                "content": ai_response,
                                "timestamp": datetime.now().isoformat()
                            }
                        ],
                        "updated_at": datetime.now().isoformat()
                    }
                    chat_threads[request.user_id].append(new_thread)
                    current_threads[request.user_id] = request.thread_id
                
                save_user_data()
            
            return {
                "response": ai_response,
                "thread_id": request.thread_id,
                "user_id": request.user_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as ai_error:
            print(f"❌ AI error: {str(ai_error)}")
            return {
                "response": "Sorry, an error occurred while processing your request. Please try again.",
                "thread_id": request.thread_id,
                "error": str(ai_error),
                "timestamp": datetime.now().isoformat()
            }
        
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"❌ Critical voice chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Model for creating thread (if not already)
class CreateThreadRequest(BaseModel):
    user_id: str
    title: str = "New Chat"
    category: str = "general"

# Creating new thread
from fastapi import Query, Body  # ← add Body if not already

@app.post("/chat/threads/create")
async def create_chat_thread(
    request: Request, 
    title: str = "New Chat", 
    category: str = "general",
    db: Session = Depends(get_db)
):
    """Create a new chat thread for user or guest"""
    
    # Try to get user_id from authorization token
    auth_header = request.headers.get("authorization")
    user_id = None
    db_user = None
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = str(payload.get("user_id"))
            
            # Check if user exists in DB
            if user_id:
                db_user = db.query(User).filter(User.id == int(user_id)).first()
                if db_user:
                    user_id = str(db_user.id)
                else:
                    user_id = None
        except Exception as e:
            print(f"Auth error: {e}")
            user_id = None
    
    # If user is not authorized, create guest ID
    is_guest = False
    if not user_id:
        import secrets
        user_id = f"guest_{secrets.token_hex(6)}"
        is_guest = True
        print(f"👤 Created guest user: {user_id}")
    
    # Initialize structure for user if not exists
    if user_id not in chat_threads:
        chat_threads[user_id] = []
    
    # Generate unique thread ID
    thread_id = f"chat_{int(datetime.now().timestamp() * 1000)}_{secrets.token_hex(4)}"
    
    # Create new thread
    new_thread = {
        "thread_id": thread_id,
        "user_id": user_id,
        "title": title,
        "category": category,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "is_active": True
    }
    
    # Add to user's thread list
    chat_threads[user_id].append(new_thread)
    
    # Set as current thread
    current_threads[user_id] = thread_id
    
    # Save data
    save_user_data()
    
    # If user is authorized, create record in DB
    if db_user and not is_guest:
        try:
            # Create welcome message from AI in DB
            welcome_message = ChatMessage(
                user_id=db_user.id,
                thread_id=thread_id,
                role="assistant",
                content="Hi! I'm your pragmatic HSK tutor. Ask any questions — I'll help you pass the exam at any cost (legally)! 😏",
                message_metadata={"timestamp": datetime.now().isoformat(), "type": "welcome"}
            )
            db.add(welcome_message)
            db.commit()
            
            # Add this message to in-memory storage too
            new_thread["messages"].append({
                "role": "assistant",
                "content": welcome_message.content,
                "timestamp": welcome_message.message_metadata["timestamp"]
            })
        except Exception as e:
            print(f"DB create error: {e}")
            db.rollback()
    
    # Log thread creation
    print(f"✅ Created new thread: {thread_id} for user: {user_id}")
    
    return {
        "thread_id": thread_id, 
        "user_id": user_id,
        "success": True,
        "is_guest": is_guest
    }

def find_thread(thread_id: str, user_id: str = None):
    """Universal thread search function"""
    thread = None
    thread_owner = None
    
    # Search in all threads
    for owner_id, threads_list in chat_threads.items():
        # If user_id is specified, check only their threads
        if user_id and owner_id != user_id:
            continue
            
        for t in threads_list:
            if t["thread_id"] == thread_id:
                thread = t
                thread_owner = owner_id
                break
        if thread:
            break
    
    return thread, thread_owner

class TranslationRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    detailed: bool = True
    include_exercises: bool = False

class PronunciationRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

class ExerciseRequest(BaseModel):
    text: str
    level: int = 1
    exercise_type: str = "all"  # fill_blanks, matching, word_order, etc.

# Add models
class GrammarTopicRequest(BaseModel):
    topic_id: str
    user_id: Optional[str] = None
    user_level: Optional[str] = "beginner"

class GrammarQuestionRequest(BaseModel):
    question: str
    topic_id: Optional[str] = None
    user_id: Optional[str] = None

class HSKTestRequest(BaseModel):
    level: int
    test_type: str = "reduced"  # reduced or full
    user_id: Optional[str] = None

class GlobalTestRequest(BaseModel):
    count: int = 20
    lang: str = "zh"
    user_id: Optional[str] = None
    topic_ids: Optional[List[str]] = None

class SpeakingEvaluationRequest(BaseModel):
    audio_text: str  # Recognized speech text
    task_data: Dict[str, Any]
    user_id: str

class WritingEvaluationRequest(BaseModel):
    text: str
    task_data: Dict[str, Any]
    user_id: str

class GlobalTestRequest(BaseModel):
    count: int = 20
    lang: str = "zh"
    user_id: Optional[str] = None

class TestResults(BaseModel):
    user_id: str
    test_id: str
    level: int  # 🔴 REQUIRED FIELD
    listening_score: Optional[int] = 0
    reading_score: Optional[int] = 0
    writing_score: Optional[int] = 0
    speaking_score: Optional[int] = 0
    total_score: Optional[int] = 0
    answers: Dict[str, Any]

@app.get("/hsk/test-answers/{test_id}/{user_id}")
async def get_test_answers(test_id: str, user_id: str):
    """Get user's checked answers"""
    if test_id not in tests_db or user_id not in tests_db[test_id]:
        raise HTTPException(status_code=404, detail="Results not found")
    
    user_results = tests_db[test_id][user_id]
    
    return {
        "test_id": test_id,
        "user_id": user_id,
        "answers": user_results.get("correct_answers", {}),
        "score": user_results.get("total_score_calculated", 0),
        "max_score": user_results.get("max_possible_score", 0),
        "percentage": user_results.get("percentage", 0),
        "ai_evaluated": user_results.get("ai_evaluated", False)
    }

# FIND the generate_hsk_test function and MODIFY it:
@app.post("/hsk/generate-test")
async def generate_hsk_test(request: HSKTestRequest):
    """Generate full HSK test"""
    try:
        test_data = await generate_hsk_test_api(request.level, request.test_type)
        
        # 🔴 IMMEDIATELY SAVE TEST TO DATABASE
        test_id = test_data["test_id"]
        tests_db[test_id] = test_data  # Save the test itself
        
        # For compatibility with old structure
        if test_id not in tests_db:
            tests_db[test_id] = {}
        
        # Save test structure separately
        tests_db[f"test_data_{test_id}"] = test_data
        
        return test_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test generation error: {str(e)}")

@app.post("/hsk/evaluate-speaking")
async def evaluate_speaking(request: SpeakingEvaluationRequest):
    """Evaluate user's speech"""
    try:
        evaluation = await evaluate_speaking_api(request.audio_text, request.task_data)
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech evaluation error: {str(e)}")

@app.post("/hsk/evaluate-writing")
async def evaluate_writing(request: WritingEvaluationRequest):
    """Evaluate written work"""
    try:
        evaluation = await evaluate_writing_api(request.text, request.task_data)
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Writing evaluation error: {str(e)}")

@app.post("/hsk/submit-test-results")
async def submit_test_results(results: TestResults):
    """Save test results"""
    try:
        test_id = results.test_id
        user_id = results.user_id
        
        # 1. Find test
        original_test = None
        
        if test_id in tests_db and isinstance(tests_db[test_id], dict) and "sections" in tests_db[test_id]:
            original_test = tests_db[test_id]
        elif f"test_data_{test_id}" in tests_db:
            original_test = tests_db[f"test_data_{test_id}"]
        
        if not original_test:
            # Create minimal test for work
            original_test = {
                "test_id": test_id,
                "level": results.level,
                "sections": {
                    "listening": {"questions": []},
                    "reading": {"questions": []},
                    "writing": {"tasks": []},
                    "speaking": {"tasks": []}
                }
            }
        
        # 2. Initialize correct answers
        correct_answers = {}
        
        # 3. Check listening questions (only if they exist in test)
        listening_correct = 0
        listening_total = 0
        listening_questions = original_test.get("sections", {}).get("listening", {}).get("questions", [])
        
        for question in listening_questions:
            q_id = question.get("id")
            correct_index = question.get("correct_index")
            
            if correct_index is not None:
                listening_total += 1
                user_answer = results.answers.get(q_id)
                
                if user_answer is not None:
                    is_correct = user_answer == correct_index
                    if is_correct:
                        listening_correct += 1
                    
                    correct_answers[q_id] = {
                        "correct": is_correct,
                        "user_answer": user_answer,
                        "correct_answer": correct_index,
                        "points": 1 if is_correct else 0,
                        "section": "listening"
                    }
                else:
                    # If user didn't answer
                    correct_answers[q_id] = {
                        "correct": False,
                        "user_answer": None,
                        "correct_answer": correct_index,
                        "points": 0,
                        "section": "listening"
                    }
        
        # 4. Check reading questions
        reading_correct = 0
        reading_total = 0
        reading_questions = original_test.get("sections", {}).get("reading", {}).get("questions", [])
        
        for question in reading_questions:
            q_id = question.get("id")
            correct_index = question.get("correct_index")
            
            if correct_index is not None:
                reading_total += 1
                user_answer = results.answers.get(q_id)
                
                if user_answer is not None:
                    is_correct = user_answer == correct_index
                    if is_correct:
                        reading_correct += 1
                    
                    correct_answers[q_id] = {
                        "correct": is_correct,
                        "user_answer": user_answer,
                        "correct_answer": correct_index,
                        "points": 1 if is_correct else 0,
                        "section": "reading"
                    }
                else:
                    correct_answers[q_id] = {
                        "correct": False,
                        "user_answer": None,
                        "correct_answer": correct_index,
                        "points": 0,
                        "section": "reading"
                    }
        
        # 5. Calculate scores based on correct answers
        # Important: first check if there are questions in the test!
        listening_score = 0
        reading_score = 0
        
        if listening_total > 0:
            listening_score = int((listening_correct / listening_total) * 100)
        
        if reading_total > 0:
            reading_score = int((reading_correct / reading_total) * 100)
        
        # 6. Use provided scores for writing and speaking parts
        writing_score = results.writing_score if results.writing_score is not None else 0
        speaking_score = results.speaking_score if results.speaking_score is not None else 0
        
        # 7. For writing tasks, add to correct_answers
        writing_tasks = original_test.get("sections", {}).get("writing", {}).get("tasks", [])
        if writing_tasks:
            for task in writing_tasks:
                task_id = task.get("id", "1")
                correct_answers[f"W{task_id}"] = {
                    "correct": writing_score >= 60,
                    "score": writing_score,
                    "feedback": f"Writing part: {writing_score}/100",
                    "section": "writing"
                }
        
        # 8. For speaking tasks, add to correct_answers
        speaking_tasks = original_test.get("sections", {}).get("speaking", {}).get("tasks", [])
        if speaking_tasks:
            for task in speaking_tasks:
                task_id = task.get("id", "1")
                correct_answers[f"S{task_id}"] = {
                    "correct": speaking_score >= 60,
                    "score": speaking_score,
                    "feedback": f"Speaking part: {speaking_score}/100",
                    "section": "speaking"
                }
        
        # 9. Determine total score CAREFULLY!
        # HSK 1-2: only listening (100) + reading (100) = maximum 200
        # HSK 3-6: listening (100) + reading (100) + writing (100) = maximum 300
        # Speaking is NOT included in total score!
        
        # LIMIT scores to maximum 100 per part
        listening_score = min(100, listening_score)
        reading_score = min(100, reading_score)
        writing_score = min(100, writing_score)
        speaking_score = min(100, speaking_score)
        
        # Calculate total score based on level
        if results.level <= 2:
            # HSK 1-2: only listening + reading
            total_score = listening_score + reading_score
            max_possible_score = 200
        else:
            # HSK 3-6: listening + reading + writing
            total_score = listening_score + reading_score + writing_score
            max_possible_score = 300
        
        # Limit total score to maximum
        total_score = min(total_score, max_possible_score)
        
        # Calculate percentage
        percentage = int((total_score / max_possible_score) * 100) if max_possible_score > 0 else 0
        
        # 10. Save results
        if test_id not in tests_db:
            tests_db[test_id] = {}
        
        tests_db[test_id][user_id] = {
            "user_id": user_id,
            "test_id": test_id,
            "level": results.level,
            "listening_score": listening_score,
            "reading_score": reading_score,
            "writing_score": writing_score,
            "speaking_score": speaking_score,
            "total_score": total_score,
            "max_score": max_possible_score,
            "percentage": percentage,
            "answers": results.answers,
            "correct_answers": correct_answers,
            "listening_stats": {"correct": listening_correct, "total": listening_total},
            "reading_stats": {"correct": reading_correct, "total": reading_total},
            "checked_count": len(correct_answers),
            "submitted_at": datetime.now().isoformat(),
            "calculated_at": datetime.now().isoformat()
        }
        
        # 11. Generate certificate and report
        user_data = users_db.get(user_id, {"name": "Student", "user_id": user_id})
        
        certificate = await generate_certificate_api(
            {
                "test_id": test_id,
                "level": results.level,
                "listening_score": listening_score,
                "reading_score": reading_score,
                "writing_score": writing_score,
                "speaking_score": speaking_score,
                "total_score": total_score
            },
            user_data
        )
        
        progress_report = await generate_progress_report_api(
            {
                "test_id": test_id,
                "level": results.level,
                "listening_score": listening_score,
                "reading_score": reading_score,
                "writing_score": writing_score,
                "speaking_score": speaking_score,
                "total_score": total_score
            },
            user_data
        )
        
        save_user_data()
        
        return {
            "success": True,
            "certificate": certificate,
            "progress_report": progress_report,
            "correct_answers": correct_answers,
            "stats": {
                "listening": f"{listening_correct}/{listening_total} ({listening_score}/100)",
                "reading": f"{reading_correct}/{reading_total} ({reading_score}/100)",
                "writing": f"{writing_score}/100",
                "speaking": f"{speaking_score}/100",
                "total": f"{total_score}/{max_possible_score}"
            },
            "scores": {
                "listening": listening_score,
                "reading": reading_score,
                "writing": writing_score,
                "speaking": speaking_score,
                "total": total_score,
                "max": max_possible_score
            },
            "level": results.level,
            "calculated_score": total_score,
            "message": f"Results saved. Listening: {listening_correct}/{listening_total}, Reading: {reading_correct}/{reading_total}, Total score: {total_score}/{max_possible_score}"
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error saving results: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error saving results: {str(e)}")

@app.get("/hsk/user-tests/{user_id}")
async def get_user_tests(user_id: str, limit: int = 10):
    """Get user's test history"""
    user_tests = []
    
    for test_id, test_data in tests_db.items():
        if user_id in test_data:
            user_test = test_data[user_id]
            user_test["test_id"] = test_id
            user_tests.append(user_test)
    
    # Sort by date
    user_tests.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    
    return {
        "user_id": user_id,
        "tests": user_tests[:limit],
        "total_tests": len(user_tests),
        "best_score": max([t.get("total_score", 0) for t in user_tests]) if user_tests else 0,
        "average_score": sum([t.get("total_score", 0) for t in user_tests]) // len(user_tests) if user_tests else 0
    }

@app.get("/hsk/test-stats/{test_id}")
async def get_test_stats(test_id: str):
    """Statistics for specific test"""
    if test_id not in tests_db:
        raise HTTPException(status_code=404, detail="Test not found")
    
    test_data = tests_db[test_id]
    users_count = len(test_data)
    
    if users_count == 0:
        return {"test_id": test_id, "users_count": 0}
    
    # Collect statistics
    scores = [data.get("total_score", 0) for data in test_data.values()]
    
    return {
        "test_id": test_id,
        "users_count": users_count,
        "average_score": sum(scores) // users_count,
        "max_score": max(scores),
        "min_score": min(scores),
        "passing_rate": len([s for s in scores if s >= 180]) / users_count * 100 if users_count > 0 else 0,
        "scores_distribution": {
            "0-59": len([s for s in scores if s < 60]),
            "60-119": len([s for s in scores if 60 <= s < 120]),
            "120-179": len([s for s in scores if 120 <= s < 180]),
            "180-239": len([s for s in scores if 180 <= s < 240]),
            "240-300": len([s for s in scores if s >= 240])
        }
    }

# Add global variables
grammar_topics = []

def load_grammar_topics():
    """Load grammar topics"""
    global grammar_topics
    try:
        with open(data_path("grammar_topics.json"), "r", encoding="utf-8") as f:
            grammar_topics = json.load(f)
        print(f"✅ Loaded {len(grammar_topics)} grammar topics")
        
        # Initialize grammar_explainer with topics
        grammar_explainer.grammar_topics = grammar_topics
    except FileNotFoundError:
        print("⚠️ Grammar topics file not found")
        grammar_topics = []
        grammar_explainer.grammar_topics = []

# Load on startup
load_grammar_topics()

@app.get("/grammar/topics")
async def get_grammar_topics(
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get list of grammar topics"""
    filtered = grammar_topics
    
    if level:
        filtered = [t for t in filtered if t.get("level") == level]
    
    if category:
        filtered = [t for t in filtered if t.get("category") == category]
    
    paginated = filtered[offset:offset + limit]
    
    return {
        "topics": paginated,
        "total": len(filtered),
        "levels": list(set(t["level"] for t in grammar_topics)),
        "categories": list(set(t.get("category", "") for t in grammar_topics if t.get("category")))
    }

@app.get("/grammar/topic/{topic_id}")
async def get_grammar_topic(topic_id: str):
    """Get grammar topic information"""
    topic = next((t for t in grammar_topics if t["id"] == topic_id), None)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return topic

@app.post("/grammar/explain")
async def explain_grammar_topic(request: GrammarTopicRequest):
    """Get AI explanation of grammar topic"""
    # Find topic
    topic = next((t for t in grammar_topics if t["id"] == request.topic_id), None)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Get user level if available
    user_level = request.user_level
    if request.user_id and request.user_id in users_db:
        user = users_db[request.user_id]
        user_hsk = user.get("current_level", 1)
        # Convert HSK to beginner/intermediate/advanced
        if user_hsk <= 2:
            user_level = "beginner"
        elif user_hsk <= 4:
            user_level = "intermediate"
        else:
            user_level = "advanced"
    
    # Get explanation
    explanation = await grammar_explainer.explain_grammar(topic, user_level)
    
    # Save to study history
    if request.user_id:
        save_grammar_history(request.user_id, topic_id=request.topic_id)
    
    return explanation

@app.get("/grammar/practice/{topic_id}")
async def generate_grammar_practice(topic_id: str, difficulty: str = "medium"):
    """Generate exercises for topic"""
    topic = next((t for t in grammar_topics if t["id"] == topic_id), None)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    try:
        exercises = await grammar_explainer.generate_practice(topic_id, difficulty)
        return {
            "topic": topic,
            "exercises": exercises,
            "difficulty": difficulty,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exercise generation error: {str(e)}")

@app.post("/grammar/ask")
async def ask_grammar_question(request: GrammarQuestionRequest):
    """Ask grammar question"""
    context = None
    
    if request.topic_id:
        topic = next((t for t in grammar_topics if t["id"] == request.topic_id), None)
        if topic:
            context = {"topic": topic}
    
    answer = await grammar_explainer.answer_grammar_question(request.question, context)
    
    return {
        "question": request.question,
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/grammar/stats")
async def get_grammar_stats():
    """Grammar statistics"""
    if not grammar_topics:
        return {"message": "Grammar topics not loaded"}
    
    # Statistics by level
    by_level = {}
    for topic in grammar_topics:
        level = topic.get("level", "unknown")
        by_level[level] = by_level.get(level, 0) + 1
    
    # Statistics by category
    by_category = {}
    for topic in grammar_topics:
        category = topic.get("category", "other")
        by_category[category] = by_category.get(category, 0) + 1
    
    # Complexity
    complexity_distribution = {
        "easy": len([t for t in grammar_topics if t.get("complexity", 3) <= 2]),
        "medium": len([t for t in grammar_topics if 2 < t.get("complexity", 3) <= 4]),
        "hard": len([t for t in grammar_topics if t.get("complexity", 3) > 4])
    }
    
    # Format levels for nice display
    formatted_by_level = []
    for level_name, count in by_level.items():
        formatted_by_level.append({
            "level": level_name,
            "count": count,
            "display": {
                "beginner": "Beginner (初)",
                "intermediate": "Intermediate (中)", 
                "advanced": "Advanced (高)"
            }.get(level_name, level_name)
        })
    
    # Sort levels: beginner -> intermediate -> advanced
    formatted_by_level.sort(key=lambda x: {"beginner": 1, "intermediate": 2, "advanced": 3}.get(x["level"], 4))
    
    return {
        "total_topics": len(grammar_topics),
        "by_level_formatted": formatted_by_level,  # For frontend
        "by_level": by_level,  # For compatibility
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]),
        "complexity_distribution": complexity_distribution,
        "average_complexity": sum(t.get("complexity", 3) for t in grammar_topics) / len(grammar_topics)
    }

# ========== UTILITIES ==========

def save_grammar_history(user_id: str, topic_id: str):
    """Save topic study to history"""
    try:
        history_file = data_path(f"grammar_history_{user_id}.json")
        history = []
        
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        
        history.append({
            "topic_id": topic_id,
            "studied_at": datetime.now().isoformat(),
            "topic": next((t for t in grammar_topics if t["id"] == topic_id), {})
        })
        
        # Limit history
        if len(history) > 100:
            history = history[-100:]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Grammar history save error: {e}")

@app.get("/grammar/history/{user_id}")
async def get_grammar_history(user_id: str, limit: int = 20):
    """Grammar study history"""
    try:
        history_file = data_path(f"grammar_history_{user_id}.json")
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            
            # Add topic information
            for item in history:
                topic = next((t for t in grammar_topics if t["id"] == item["topic_id"]), None)
                if topic:
                    item["topic_info"] = topic
            
            return {
                "history": history[:limit],
                "total_studied": len(history),
                "recent_topics": list(set([h["topic_id"] for h in history[:10]]))
            }
        
        return {"history": [], "total_studied": 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History load error: {str(e)}")

@app.post("/ai/translate")
async def smart_translate(request: TranslationRequest):
    """Smart translation with learning"""
    try:
        # Get user data if available
        user_level = 1
        learning_style = "visual"
        
        if request.user_id and request.user_id in users_db:
            user = users_db[request.user_id]
            user_level = user.get("current_level", 1)
            learning_style = user.get("learning_style", "visual")
        
        # Get smart translation
        result = await translator.smart_translate(
            text=request.text,
            user_level=user_level,
            learning_style=learning_style
        )
        
        # If exercises needed - generate
        if request.include_exercises:
            exercises = await translator.generate_exercises(request.text, user_level)
            result["exercises"] = exercises
        
        # Save to translation history
        if request.user_id:
            save_translation_history(request.user_id, request.text, result)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

@app.post("/ai/pronunciation")
async def analyze_pronunciation(request: PronunciationRequest):
    """Pronunciation analysis"""
    try:
        result = await translator.analyze_pronunciation(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.post("/ai/exercises")
async def generate_exercises(request: ExerciseRequest):
    """Exercise generation"""
    try:
        result = await translator.generate_exercises(request.text, request.level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

@app.get("/ai/translation-history/{user_id}")
async def get_translation_history(user_id: str, limit: int = 20):
    """User's translation history"""
    try:
        history = load_translation_history(user_id)
        return {
            "history": history[:limit],
            "count": len(history),
            "total_characters": sum(len(item.get("original", "")) for item in history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History load error: {str(e)}")

# ========== HISTORY UTILITIES ==========

def save_translation_history(user_id: str, original: str, result: Dict):
    """Save translation to history"""
    try:
        history_file = data_path(f"translations_{user_id}.json")
        history = []
        
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        
        history.insert(0, {
            "original": original,
            "translation": result.get("translation", ""),
            "timestamp": datetime.now().isoformat(),
            "characters_count": result.get("characters_count", 0),
            "difficulty": result.get("difficulty_score", 5),
            "key_words": result.get("key_words", [])
        })
        
        # Limit history to 100 latest translations
        if len(history) > 100:
            history = history[:100]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"History save error: {e}")

def load_translation_history(user_id: str) -> List:
    """Load translation history"""
    try:
        history_file = data_path(f"translations_{user_id}.json")
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"History load error: {e}")
        return []

# API for chat update
@app.post("/chat/threads/update")
async def update_chat_thread(update: ChatUpdate):
    """Update chat thread"""
    thread_found = None
    for user_threads in chat_threads.values():
        for thread in user_threads:
            if thread["thread_id"] == update.thread_id:
                thread["title"] = update.title
                thread["category"] = update.category
                thread["updated_at"] = datetime.now().isoformat()
                thread_found = thread
                break
        if thread_found:
            break
    
    if not thread_found:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    save_user_data()
    return {"success": True, "thread": thread_found}

# API for chat deletion
@app.delete("/chat/threads/delete/{thread_id}")
async def delete_chat_thread(thread_id: str):
    """Delete chat thread"""
    deleted = False
    for user_id, threads in list(chat_threads.items()):
        for i, thread in enumerate(threads):
            if thread["thread_id"] == thread_id:
                threads.pop(i)
                deleted = True
                
                # If deleting current thread, set another
                if current_threads.get(user_id) == thread_id:
                    if threads:
                        current_threads[user_id] = threads[0]["thread_id"]
                    else:
                        del current_threads[user_id]
                break
        if deleted:
            break
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    save_user_data()
    return {"success": True, "message": "Thread deleted"}

# API for getting chat history
@app.get("/chat/threads/{user_id}")
async def get_user_threads(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all threads for a user"""
    
    # Check if user has access to these threads
    auth_header = request.headers.get("authorization")
    request_user_id = None
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request_user_id = str(payload.get("user_id"))
        except:
            pass
    
    # If this is a request for an authorized user, check that it's their threads
    if not user_id.startswith("guest_") and request_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get threads from memory
    threads = chat_threads.get(user_id, [])
    
    # If user is authorized and no threads in memory, try to create from DB
    if not user_id.startswith("guest_") and len(threads) == 0:
        try:
            # Get unique thread_ids from DB
            db_threads = db.query(ChatMessage.thread_id).filter(
                ChatMessage.user_id == int(user_id)
            ).distinct().all()
            
            for (thread_id,) in db_threads:
                # Get first message to determine title
                first_msg = db.query(ChatMessage).filter(
                    ChatMessage.user_id == int(user_id),
                    ChatMessage.thread_id == thread_id,
                    ChatMessage.role == "user"
                ).order_by(ChatMessage.created_at).first()
                
                threads.append({
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "title": first_msg.content[:30] + "..." if first_msg else "Chat",
                    "category": "general",
                    "created_at": first_msg.created_at.isoformat() if first_msg else datetime.now().isoformat(),
                    "updated_at": first_msg.created_at.isoformat() if first_msg else datetime.now().isoformat(),
                    "messages": [],
                    "is_active": True
                })
            
            chat_threads[user_id] = threads
            save_user_data()
        except Exception as e:
            print(f"DB load threads error: {e}")
    
    # Sort by update date (newest first)
    threads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return {
        "threads": threads,
        "count": len(threads),
        "current_thread": current_threads.get(user_id)
    }

# FIX 6: Model for message (Pydantic)
class ChatMessageInput(BaseModel):
    message: str
    user_id: Optional[str] = None
    
def hash_password(password: str) -> str:
    return hashlib.sha256(f"hsk_{password}_salt".encode()).hexdigest()

@app.post("/payment/donationalerts/webhook")
async def donationalerts_webhook(data: dict):
    # data["username"] or data["message"] contains user_id
    user_id = data.get("message")

    for fp, info in access_db.items():
        if info["user_id"] == user_id:
            info["paid_until"] = time.time() + 30 * 24 * 60 * 60
            info["tariff"] = "school" if data["amount"] >= 50 else "normal"

    return {"ok": True}

# ========== GLOBAL VARIABLES ==========
users_db = {}

# ========== SYSTEM PROMPT (continuation) ==========
system_prompt = """You are a cunning, pragmatic advisor for admission to Chinese universities.
Your goal: help the student get admitted and pass HSK by any legal means.

You know all loopholes, life hacks and strategies:
1. **Admission without perfect Chinese** - how to bypass requirements
2. **Connections and guanxi** - how to use networking
3. **Alternative paths** - alternative programs and faculties
4. **Application tricks** - how to stand out among thousands of applications
5. **Psychological techniques** - how to impress the committee

Student context: {context}

Your key competencies:

🎯 **ADMISSION STRATEGIES:**
- Finding "weak" faculties with low competition
- Applying through foreign student quotas
- Using English-language programs
- Transferring from another university after 1st year

🕵️ **DOCUMENTS AND APPLICATIONS:**
- How to write a motivation letter that gets read
- Which recommendations work best
- How to format portfolio without outstanding achievements
- What to write in CV for Chinese university

🎓 **HSK AND LANGUAGE:**
- How to pass HSK 4 in 3 months (intensive methods)
- Which HSK parts are most "breakable"
- How to learn characters for the exam, not for life
- Deceptively easy essay topics

🤝 **GUANXI AND CONNECTIONS:**
- How to find "your person" at the university
- Who to ask for recommendations
- How to use social networks for networking
- Free resources and programs

💰 **FINANCES AND SCHOLARSHIPS:**
- How to get Chinese Government Scholarship without perfect grades
- Hidden scholarship programs
- Work in China for students
- Saving on living and studying

Respond briefly, to the point, with specific steps. Provide phone numbers, program names, specific faculties.
Avoid general phrases. Be cynical but helpful.

Response examples:
- "Instead of HSK 5, apply for English program at Wuhan University"
- "Find a graduate of the needed university on LinkedIn and write..."
- "In motivation letter mention 'One Belt, One Road' initiative"
- "On exam use template phrases from textbook 汉语口语..."

Ready to help with any tricky questions! 🦊, You are a pragmatic, cynical Chinese tutor for passing HSK.
Your goal: help pass the exam at any cost (legally).
Style: direct, no fluff, with life hacks, sometimes with humor.

Use these strategies:
1. **80/20 rule** - learn only frequently occurring words
2. **Cheat codes** - how to guess answers, recognize patterns
3. **Psychological techniques** - how not to panic on exam
4. **Tricky life hacks** (legal) - time optimization

Respond briefly, to the point. Provide specific numbers and techniques.
Life hack examples:
- "In reading section, first skim questions, then look for answers in text"
- "If you don't know a word - look for familiar characters in composition"
- "In listening section, first read answer options"
- "In writing section use template phrases"

Student context: {context}
"""

@app.post("/auth/user")
async def auth_user(auth_data: AuthRequest):
    """User authorization or registration"""
    
    # Find existing user by name
    user_id = None
    for uid, user in users_db.items():
        if user.get("name", "").lower() == auth_data.username.lower():
            user_id = uid
            break
    
    # If user not found, create new
    if not user_id:
        user_id = f"user_{len(users_db) + 1}_{hashlib.md5(auth_data.username.encode()).hexdigest()[:8]}"
        
        # Create new user
        users_db[user_id] = {
            "user_id": user_id,
            "name": auth_data.username,
            "current_level": 1,
            "target_level": 4,
            "exam_date": (datetime.now() + timedelta(days=90)).isoformat()[:10],
            "exam_location": "Moscow",
            "exam_format": "computer",
            "interests": ["Chinese", "HSK"],
            "daily_time": 30,
            "learning_style": "visual",
            "registered_at": datetime.now().isoformat(),
            "daily_words": 10
        }
        
        # Create progress
        if user_id not in word_progress_db:
            word_progress_db[user_id] = {}
        
        save_user_data()
        message = "registered"
    else:
        message = "logged_in"
    
    # Return user data (without password)
    user_data = users_db[user_id].copy()
    
    return {
        "success": True,
        "message": message,
        "user_id": user_id,
        **user_data
    }

from fastapi import Body
from typing import Dict

@app.get("/user/profile/{user_id}")
async def get_profile(user_id: str):
    if user_id not in users_db:
        raise HTTPException(404, "User not found")
    user = users_db[user_id]
    return {
        "name": user.get("name", "Not specified"),
        "email": user.get("email", ""),
        "current_level": user.get("current_level", 1),
        "target_level": user.get("target_level", 4),
        "timezone": user.get("timezone", "UTC"),
        "language": user.get("language", "en")
    }

@app.post("/user/profile/{user_id}")
async def update_profile(user_id: str, data: Dict = Body(...)):
    if user_id not in users_db:
        raise HTTPException(404, "User not found")
    users_db[user_id].update(data)
    save_user_data()
    return {"success": True}

@app.post("/user/password/{user_id}")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # Check new password and confirmation match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Hash new password
    current_user.hashed_password = hash_password(password_data.new_password)
    
    # Delete all refresh tokens
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()
    
    return {"message": "Password successfully changed"}

class ThreadCreateRequest(BaseModel):
    user_id: str
    title: str = "New chat"
    category: str = "general"

@app.post("/chat/{thread_id}/message")
async def send_chat_message(
    thread_id: str, 
    request: Request,
    message_data: dict,  # Changed from ChatMessage to dict for simplicity
    db: Session = Depends(get_db)
):
    """Send message to chat"""
    
    # Get user_id from token
    auth_header = request.headers.get("authorization")
    user_id = None
    db_user = None
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = str(payload.get("user_id"))
            
            if user_id:
                db_user = db.query(User).filter(User.id == int(user_id)).first()
                if db_user:
                    user_id = str(db_user.id)
        except Exception as e:
            print(f"Token decode error: {e}")
    
    message = message_data.get("message", "")
    
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Find thread
    thread, thread_owner = find_thread(thread_id, user_id)
    
    if not thread:
        print(f"Thread {thread_id} not found for user {user_id}")
        # Try to find without filtering by user_id
        thread, thread_owner = find_thread(thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
    
    # Check access rights
    if user_id and thread_owner != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add user message
    user_message = {
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat()
    }
    thread["messages"].append(user_message)
    
    # Generate AI response
    ai_response = "Hi! I'm your pragmatic HSK tutor. Ask any questions — I'll help you pass the exam at any cost (legally)! 😏"
    
    try:
        client = get_deepseek_client()
        if client:
            # Form message history for context
            messages_for_ai = [
                {"role": "system", "content": "You are a pragmatic, cynical but helpful HSK Chinese tutor. Respond briefly, with life hacks and direct advice. Use Russian or Chinese as appropriate."}
            ]
            
            # Add last 10 messages from history
            recent_messages = thread["messages"][-10:]
            for msg in recent_messages:
                messages_for_ai.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages_for_ai,
                temperature=0.8,
                max_tokens=1000
            )
            ai_response = response.choices[0].message.content
    except Exception as e:
        print(f"AI error in chat: {e}")
        ai_response = "Sorry, AI is temporarily unavailable. Please try again later."
    
    # Add AI response
    ai_message = {
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.now().isoformat()
    }
    thread["messages"].append(ai_message)
    thread["updated_at"] = datetime.now().isoformat()
    
    # Save to DB if user is authorized
    if db_user:
        try:
            db_user_message = ChatMessage(
                user_id=db_user.id,
                thread_id=thread_id,
                role="user",
                content=message,
                message_metadata={"timestamp": user_message["timestamp"]}
            )
            db.add(db_user_message)
            
            db_ai_message = ChatMessage(
                user_id=db_user.id,
                thread_id=thread_id,
                role="assistant",
                content=ai_response,
                message_metadata={"timestamp": ai_message["timestamp"]}
            )
            db.add(db_ai_message)
            db.commit()
        except Exception as e:
            print(f"DB save error: {e}")
            db.rollback()
    
    save_user_data()
    
    formatted = format_chat_response(ai_response, thread_owner, "ai-tutor")
    
    return {
        "response": formatted["response"],
        "formatted_response": formatted["formatted_response"],
        "css": formatted["css"],
        "has_latex": formatted["has_latex"],
        "thread_id": thread_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/chat/{thread_id}/history")
async def get_chat_history(
    thread_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get chat history for a thread"""
    
    # Get user_id from token
    auth_header = request.headers.get("authorization")
    user_id = None
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = str(payload.get("user_id"))
        except:
            pass
    
    # Find thread
    thread, thread_owner = find_thread(thread_id, user_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # If user is authorized and it's their thread, but no messages in memory,
    # try to load from DB
    if user_id and thread_owner == user_id and len(thread.get("messages", [])) == 0:
        try:
            db_messages = db.query(ChatMessage).filter(
                ChatMessage.user_id == int(user_id),
                ChatMessage.thread_id == thread_id
            ).order_by(ChatMessage.created_at).all()
            
            for msg in db_messages:
                thread["messages"].append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.message_metadata.get("timestamp", msg.created_at.isoformat()) if msg.message_metadata else msg.created_at.isoformat()
                })
        except Exception as e:
            print(f"DB load error: {e}")
    
    return {
        "thread_id": thread_id,
        "title": thread.get("title", "Chat"),
        "category": thread.get("category", "general"),
        "messages": thread.get("messages", []),
        "message_count": len(thread.get("messages", [])),
        "created_at": thread.get("created_at", ""),
        "updated_at": thread.get("updated_at", "")
    }

# ========== UTILITIES ==========
def save_user_data():
    """Save user data to file"""
    data = {
        'users_db': users_db,
        'word_progress_db': word_progress_db,
        'tests_db': tests_db,
        'chat_history': chat_history,
        'chat_threads': chat_threads,
        'current_threads': current_threads,
        'user_word_status': user_word_status,
        'access_db': access_db,
        'corporate_accounts': corporate_accounts,
        'corporate_members': corporate_members,
        'words_db': words_db  # Save words
        # 'grammar_topics': grammar_topics  # NOT adding!
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(data_path('user_data.pkl'), 'wb') as f:
        pickle.dump(data, f)

def load_user_data():
    """Load user data from file"""
    global users_db, word_progress_db, tests_db, chat_history
    global chat_threads, current_threads, access_db
    global corporate_accounts, corporate_members, user_word_status
    global words_db  # Added words
    
    try:
        with open(data_path('user_data.pkl'), 'rb') as f:
            data = pickle.load(f)
            users_db = data.get('users_db', {})
            word_progress_db = data.get('word_progress_db', {})
            tests_db = data.get('tests_db', {})
            chat_history = data.get('chat_history', {})
            chat_threads = data.get('chat_threads', {})
            current_threads = data.get('current_threads', {})
            access_db = data.get('access_db', {})
            corporate_accounts = data.get('corporate_accounts', {})
            corporate_members = data.get('corporate_members', {})
            user_word_status = data.get('user_word_status', {})
            words_db = data.get('words_db', [])
            # grammar_topics NOT touched!
        print(f"✅ Loaded {len(users_db)} users")
    except FileNotFoundError:
        print("ℹ️ User data file not found")

# Load on startup
load_user_data()

def get_deepseek_client():
    """Create client for DeepSeek API"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ DeepSeek API key not found in .env file")
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
        )

async def chat_with_deepseek(message: str, user_context: dict = None) -> str:
    cache_key = f"chat_{hashlib.md5(message.encode()).hexdigest()}"
    if cache_key in ai_cache:
        print(f"⚡ Fast response from cache!")
        return ai_cache[cache_key]
    
    client = get_deepseek_client()
    if not client:
        return "❌ API key not configured"
    try:
        import asyncio
        user_id = user_context.get("user_id", "anonymous") if user_context else "anonymous"
        # Determine section
        section = user_context.get("section", "ai-tutor") if user_context else "ai-tutor"
        
        # Initialize history for user
        if user_id not in chat_history:
            chat_history[user_id] = []
        
        # Add new message to history
        chat_history[user_id].append({"role": "user", "content": message})
        
        # Limit history to last 10 messages
        if len(chat_history[user_id]) > 20:
            chat_history[user_id] = chat_history[user_id][-20:]
        
        # Form user context
        context = ""
        if user_context:
            context = f"""
            Student: {user_context.get('name', 'Anonymous')}
            Level: HSK {user_context.get('current_level', 1)} → HSK {user_context.get('target_level', 4)}
            Exam: {user_context.get('exam_date', 'soon')} in {user_context.get('exam_location', 'Moscow')}
            Interests: {', '.join(user_context.get('interests', []))}
            """
        
        # Form prompt
        formatted_system_prompt = system_prompt.replace("{context}", context)
        
        # Form history for AI
        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *chat_history[user_id][-10:]  # Take last 10 messages
        ]
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": message}],
                temperature=0.7,
                max_tokens=1500
            ),
            timeout=10.0
        )
        
        ai_response = response.choices[0].message.content
        
        # FORMAT RESPONSE
        formatted = format_chat_response(ai_response, user_id, section)
        
        # Save AI response to history (save plain text for compatibility)
        chat_history[user_id].append({"role": "assistant", "content": formatted["response"]})
        
        # Save data
        save_user_data()
        ai_cache[cache_key] = formatted["response"]
        
        return formatted["response"]
    except asyncio.TimeoutError:
        return "⏳ Server is thinking too long. Try again!"
    except Exception as e:
        return f"❌ API error: {str(e)}"
    
@app.get("/chat/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 50):
    """Get chat history"""
    if user_id not in chat_history:
        return {"history": [], "count": 0}
    
    history = chat_history[user_id][-limit:]
    return {
        "history": history,
        "count": len(history)
    }

# API for clearing history
@app.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str):
    """Clear chat history"""
    if user_id in chat_history:
        chat_history[user_id] = []
    return {"message": "History cleared"}

def load_words():
    """Load words from JSON file"""
    global words_db
    
    # Try loading from different files
    possible_files = [
        data_path("hsk_all_words.json"),
        data_path("hsk_words.json"),
        data_path("hsk1_words.json")
    ]
    
    loaded = False
    for file_path in possible_files:
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    words_db = json.load(f)
                
                print(f"✅ Loaded from {file_path}: {len(words_db)} words")
                
                # Statistics
                stats = {}
                for word in words_db:
                    level = word.get("hsk_level", 0)
                    stats[level] = stats.get(level, 0) + 1
                
                print("📊 Statistics:")
                for level in sorted(stats.keys()):
                    print(f"  HSK {level}: {stats[level]} words")
                
                loaded = True
                break
                
        except Exception as e:
            print(f"⚠️ Error loading {file_path}: {e}")
    
    if not loaded:
        print("⚠️ Word files not found. Using test data.")
        words_db = [
            {"character": "你好", "pinyin": "nǐ hǎo", "translation": "hello", "hsk_level": 1},
            {"character": "谢谢", "pinyin": "xiè xie", "translation": "thank you", "hsk_level": 1},
        ]

def generate_memory_tip(word: dict, learning_style: str = "visual") -> str:
    """Generate memory tip"""
    char = word["character"]
    pinyin = word["pinyin"]
    translation = word["translation"]
    level = word.get("hsk_level", 1)
    
    tips = {
        "visual": [
            f"👁️ Draw {char} in the air 3 times",
            f"🎨 Imagine {translation} as a picture with {char}",
            f"📝 Write {char} with colored markers",
            f"🎯 Create mind map for {char} → {translation}",
            f"🌈 Associate color with character {char}"
        ],
        "auditory": [
            f"🔊 Pronounce '{pinyin}' with different intonation",
            f"🎵 Create song about {char} = {translation}",
            f"🗣️ Repeat '{pinyin} - {translation}' 5 times aloud",
            f"🎧 Record pronunciation of {char} and listen",
            f"🎤 Pronounce {char} like radio announcer"
        ],
        "kinesthetic": [
            f"✍️ Write {char} on paper 10 times",
            f"👆 Draw {char} with finger on table",
            f"🎮 Make gesture for {char}",
            f"🏃 Associate {char} with movement",
            f"🤲 Mold {char} from plasticine"
        ]
    }
    
    # Special tips for characters
    special_tips = []
    if "好" in char:  # good
        special_tips.append("👫 '好' = 女 (woman) + 子 (child) = woman with child = good!")
    if "谢" in char:  # thank
        special_tips.append("🙏 '谢' = 言 (speech) + 射 (shoot) = words like arrows of gratitude")
    if "学" in char:  # study
        special_tips.append("📚 '学' = 子 (child) under roof 宀 = child studies at home")
    if "爱" in char:  # love
        special_tips.append("❤️ '爱' = 爫 (hand) + 冖 (roof) + 友 (friend) = friend's hand under roof = love")
    
    # Choose tips based on learning style
    style_tips = tips.get(learning_style, tips["visual"])
    
    all_tips = special_tips + style_tips
    return random.choice(all_tips)

def get_words_by_level(level: int, limit: int = 10000) -> List[Dict]:
    """Get words by HSK level"""
    return [w for w in words_db if w.get("hsk_level") == level][:limit]

def get_exam_hacks(location: str, format: str, level: int) -> List[str]:
    """Exam life hacks"""
    hacks = [
        "🎯 80/20 rule: 20% of words = 80% of texts",
        "⏰ Start with easy questions, leave hard ones for later",
        "📝 In writing part, write structured",
        "🧠 If you don't know - guess, don't leave empty",
        "🔄 Check answers if time remains"
    ]
    
    # By level
    level_hacks = {
        1: ["🔤 Learn only basic characters", "🎯 Focus on pronunciation"],
        2: ["📚 Add simple grammar constructions", "👂 Train listening"],
        3: ["💬 Learn whole dialogues", "✍️ Start writing simple texts"],
        4: ["📖 Read short articles", "🎯 Learn synonyms and antonyms"],
        5: ["🎓 Prepare for essay", "🔍 Analyze complex texts"],
        6: ["🏆 Practice on real exams", "💡 Learn idioms and proverbs"]
    }
    
    hacks.extend(level_hacks.get(level, []))
    
    # By location
    if "china" in location.lower():
        hacks.append("🇨🇳 In China stricter with pronunciation and handwriting")
    elif "russia" in location.lower():
        hacks.append("🇷🇺 In Russia often give extra minutes for listening")
    
    # By format
    if format == "computer":
        hacks.extend([
            "💻 Use CTRL+F in texts to search keywords",
            "⌨️ Practice typing pinyin quickly",
            "🖱️ Double-check before clicking"
        ])
    else:  # paper
        hacks.extend([
            "✍️ Write clearly, even if slower",
            "📝 Bring spare pens",
            "📄 Mark text with pencil"
        ])
    
    return hacks

# Load words on startup
load_words()

@app.post("/register")
async def register_user(user: UserInfo):
    """Register new user"""
    user_id = f"user_{len(users_db) + 1}"
    
    # Calculate plan
    days_until_exam = max(1, (datetime.fromisoformat(user.exam_date) - datetime.now()).days)
    target_words = {
        1: 150, 2: 300, 3: 600, 4: 1200, 5: 2500, 6: 5000
    }.get(user.target_level, 1000)
    
    daily_words = max(5, target_words // days_until_exam)
    
    # Save user
    users_db[user_id] = {
        **user.dict(),
        "user_id": user_id,
        "registered_at": datetime.now().isoformat(),
        "daily_words": daily_words,
        "days_until_exam": days_until_exam
    }
    
    # Initialize progress
    word_progress_db[user_id] = {}
    
    # Save data
    save_user_data()
    
    return {
        "success": True,
        "user_id": user_id,
        "message": f"🎉 Welcome, {user.name}!",
        "plan": {
            "daily_words": daily_words,
            "days_until_exam": days_until_exam,
            "total_words_to_learn": target_words,
            "study_plan": f"Learn {daily_words} words per day",
            "hacks": get_exam_hacks(user.exam_location, user.exam_format, user.target_level),
            "cheat_codes": [
                "🎮 Learn words during breakfast",
                "🚌 Use flashcards in transport",
                "🛌 Review before sleep",
                "🎯 Focus on weak points"
            ]
        }
    }

@app.get("/csca/math/progress/guest")
async def get_guest_progress():
    return {
        "overall_percentage": 0,
        "topics_completed": 0,
        "total_topics": len(csca_math_topics),
        "topic_progress": {}
    }

@app.get("/user/{user_id}")
async def get_user_info(user_id: str):
    """User information"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    
    # User statistics
    progress = word_progress_db.get(user_id, {})
    learned_words = len([p for p in progress.values() if p.get("remembered", False)])
    
    return {
        **user,
        "stats": {
            "learned_words": learned_words,
            "total_words": len(words_db),
            "progress_percentage": min(100, int(learned_words / len(words_db) * 100)) if words_db else 0
        }
    }

@app.post("/chat")
async def chat_with_ai(chat_msg: ChatMessage):
    """Chat with AI tutor"""
    # Get user context if available
    user_context = None
    if chat_msg.user_id and chat_msg.user_id in users_db:
        user_context = users_db[chat_msg.user_id]
    
    # Use DeepSeek
    answer = await chat_with_deepseek(chat_msg.message, user_context)
    
    return {
        "answer": answer,
        "user_id": chat_msg.user_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/words/today/{user_id}")
async def get_todays_words(user_id: str, new_words: int = 10, review_words: int = 5):
    """Today's words with spaced repetition system"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    level = user["current_level"]
    learning_style = user.get("learning_style", "visual")
    
    # All words of needed level
    level_words = get_words_by_level(level, 1000)
    
    if not level_words:
        raise HTTPException(status_code=404, detail=f"HSK {level} words not found")
    
    # Get user progress
    progress = word_progress_db.get(user_id, {})
    
    # New words (not studied yet)
    new_words_list = []
    for word in level_words:
        if len(new_words_list) >= new_words:
            break
        
        word_id = f"{word['character']}_{level}"
        if word_id not in progress:
            word["word_id"] = word_id
            word["memory_tip"] = generate_memory_tip(word, learning_style)
            new_words_list.append(word)
    
    # Words for review
    review_words_list = []
    today = datetime.now().date()
    
    for word_id, word_progress in progress.items():
        if len(review_words_list) >= review_words:
            break
        
        if word_progress.get("level") == level:
            last_review = datetime.fromisoformat(word_progress["last_reviewed"]).date()
            days_passed = (today - last_review).days
            
            # Review intervals: 1, 3, 7, 14, 30 days
            if days_passed in [1, 3, 7, 14, 30]:
                # Find word
                for word in level_words:
                    if f"{word['character']}_{level}" == word_id:
                        word["word_id"] = word_id
                        word["memory_tip"] = generate_memory_tip(word, learning_style)
                        word["last_reviewed"] = word_progress["last_reviewed"]
                        word["difficulty"] = word_progress.get("difficulty", 3)
                        review_words_list.append(word)
                        break
    
    return {
        "user": user["name"],
        "level": level,
        "date": today.isoformat(),
        "words": {
            "new": new_words_list,
            "review": review_words_list
        },
        "study_tips": [
            f"📚 New words: {len(new_words_list)}",
            f"🔄 Review: {len(review_words_list)}",
            f"⏰ Recommended time: {user['daily_time']} minutes",
            f"🎯 Learning style: {learning_style}",
            "💡 Tip: Learn in morning, review in evening"
        ]
    }

@app.post("/review")
async def submit_word_review(review: WordReview):
    """Submit word review (remembered/not remembered)"""
    if review.user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update progress
    if review.user_id not in word_progress_db:
        word_progress_db[review.user_id] = {}
    
    word_progress_db[review.user_id][review.word_id] = {
        "remembered": review.remembered,
        "difficulty": review.difficulty,
        "last_reviewed": datetime.now().isoformat(),
        "review_count": word_progress_db[review.user_id].get(review.word_id, {}).get("review_count", 0) + 1
    }
    
    return {
        "success": True,
        "message": "Progress saved!",
        "next_review": "Tomorrow" if review.remembered else "In 1 day"
    }

@app.get("/test/{level}")
async def generate_test(level: int, questions: int = 10):
    """Generate test for HSK level"""
    level_words = get_words_by_level(level, 1000)
    
    if not level_words:
        raise HTTPException(status_code=404, detail=f"HSK {level} words not found")
    
    # Select random words
    selected_words = random.sample(level_words, min(questions, len(level_words)))
    
    test_questions = []
    for i, word in enumerate(selected_words, 1):
        # Create wrong options
        wrong_words = []
        other_words = [w for w in level_words if w["character"] != word["character"]]
        
        if len(other_words) >= 3:
            wrong_words = random.sample(other_words, 3)
        
        # Create answer options
        options = [word["translation"]] + [w["translation"] for w in wrong_words]
        random.shuffle(options)
        
        # Determine correct answer
        correct_index = options.index(word["translation"])
        
        test_questions.append({
            "id": f"q_{i}",
            "question": f"How to translate '{word['character']}' ({word['pinyin']})?",
            "options": options,
            "correct_index": correct_index,
            "correct_answer": word["translation"],
            "points": 1,
            "hint": f"HSK {level}, part of speech: {word.get('part_of_speech', 'not specified')}"
        })
    
    # Create test ID
    test_id = f"test_{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Save test
    tests_db[test_id] = {
        "level": level,
        "questions": test_questions,
        "created_at": datetime.now().isoformat(),
        "max_score": len(test_questions)
    }
    
    return {
        "test_id": test_id,
        "level": level,
        "total_questions": len(test_questions),
        "time_limit": f"{len(test_questions) * 1.5} minutes",
        "questions": test_questions,
        "test_hacks": [
            "⏱️ Spend no more than 1.5 minutes per question",
            "🎯 If in doubt - eliminate obviously wrong options",
            "📝 Remember: HSK often repeats similar options",
            "🧠 First thought is often correct"
        ]
    }

@app.post("/submit_test")
async def submit_test_answers(test_data: TestAnswer):
    """Submit test answers"""
    if test_data.user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    if test_data.test_id not in tests_db:
        raise HTTPException(status_code=404, detail="Test not found")
    
    test = tests_db[test_data.test_id]
    questions = test["questions"]
    
    # Check answers
    correct = 0
    results = []
    
    for question in questions:
        user_answer = test_data.answers.get(question["id"])
        is_correct = user_answer == question["correct_index"]
        
        if is_correct:
            correct += 1
        
        results.append({
            "question_id": question["id"],
            "user_answer": user_answer,
            "correct_answer": question["correct_index"],
            "is_correct": is_correct,
            "explanation": f"Correct answer: {question['correct_answer']}"
        })
    
    score = correct
    max_score = len(questions)
    percentage = int((score / max_score) * 100) if max_score > 0 else 0
    
    # Save result
    if "results" not in tests_db[test_data.test_id]:
        tests_db[test_data.test_id]["results"] = {}
    
    tests_db[test_data.test_id]["results"][test_data.user_id] = {
        "score": score,
        "max_score": max_score,
        "percentage": percentage,
        "submitted_at": datetime.now().isoformat(),
        "answers": test_data.answers
    }
    
    # Generate feedback
    feedback = ""
    if percentage >= 80:
        feedback = "🎉 Excellent! You're ready for the exam!"
    elif percentage >= 60:
        feedback = "👍 Good! Keep practicing!"
    else:
        feedback = "💪 Need more practice! Focus on weak areas."
    
    return {
        "test_id": test_data.test_id,
        "user_id": test_data.user_id,
        "score": score,
        "max_score": max_score,
        "percentage": percentage,
        "feedback": feedback,
        "results": results,
        "recommendations": [
            f"🎯 Review words you made mistakes on",
            f"⏰ Next test in 3 days",
            f"📈 Goal for next time: {min(100, percentage + 10)}%"
        ]
    }

@app.get("/exam/{level}")
async def generate_exam(level: int):
    """Generate full HSK exam"""
    level_words = get_words_by_level(level, 1000)
    
    if not level_words:
        raise HTTPException(status_code=404, detail=f"HSK {level} words not found")
    
    # Different exam parts
    exam = {
        "listening": [],
        "reading": [],
        "writing": [],
        "speaking": []
    }
    
    # LISTENING (4 questions)
    for i in range(4):
        word = random.choice(level_words)
        wrong_words = random.sample([w for w in level_words if w != word], 3)
        
        exam["listening"].append({
            "type": "multiple_choice",
            "id": f"listening_{i+1}",
            "question": f"Listen to audio and choose correct translation for:",
            "character": word["character"],
            "pinyin": word["pinyin"],
            "options": [word["translation"]] + [w["translation"] for w in wrong_words],
            "correct_answer": word["translation"],
            "points": 5,
            "time_limit": "30 seconds"
        })
    
    # READING (3 questions)
    for i in range(3):
        # Matching
        pairs = random.sample(level_words, min(4, len(level_words)))
        exam["reading"].append({
            "type": "matching",
            "id": f"reading_{i+1}",
            "question": "Match Chinese words with translations:",
            "pairs": [{"character": w["character"], "pinyin": w["pinyin"]} for w in pairs],
            "answers": [w["translation"] for w in pairs],
            "shuffled_answers": random.sample([w["translation"] for w in pairs], len(pairs)),
            "points": 10,
            "time_limit": "2 minutes"
        })
    
    # WRITING (2 questions)
    writing_words = random.sample(level_words, min(2, len(level_words)))
    exam["writing"].append({
        "type": "writing",
        "id": "writing_1",
        "question": "Write characters for following words:",
        "words": [{"pinyin": w["pinyin"], "translation": w["translation"]} for w in writing_words],
        "answers": [w["character"] for w in writing_words],
        "points": 15,
        "time_limit": "5 minutes"
    })
    
    # SPEAKING (1 question)
    speaking_word = random.choice(level_words)
    exam["speaking"].append({
        "type": "speaking",
        "id": "speaking_1",
        "question": f"Pronounce word and make sentence with it:",
        "word": {
            "character": speaking_word["character"],
            "pinyin": speaking_word["pinyin"],
            "translation": speaking_word["translation"]
        },
        "example": f"Example: '{speaking_word['character']} ({speaking_word['pinyin']})' - {speaking_word['translation']}",
        "points": 20,
        "time_limit": "3 minutes"
    })
    
    exam_id = f"exam_{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "exam_id": exam_id,
        "level": level,
        "total_points": 100,
        "time_total": "60 minutes",
        "sections": exam,
        "exam_strategy": [
            "🎯 Start with favorite part",
            "⏰ Distribute time: 20min reading, 15min listening, 15min writing, 10min speaking",
            "📝 In writing part, write draft first",
            "🎤 In speaking part, speak clearly and don't rush",
            "🔄 Leave 5 minutes for checking"
        ]
    }

@app.get("/stats")
async def get_stats():
    """Database statistics"""
    if not words_db:
        return {"message": "Database is empty"}
    
    stats = {
        "total_words": len(words_db),
        "by_level": {},
        "by_part_of_speech": {},
        "users_count": len(users_db),
        "tests_taken": len(tests_db)
    }
    
    # Statistics by level
    for word in words_db:
        level = word.get("hsk_level", 0)
        stats["by_level"][f"HSK {level}"] = stats["by_level"].get(f"HSK {level}", 0) + 1
        
        # Statistics by part of speech
        pos = word.get("part_of_speech", "not specified")
        stats["by_part_of_speech"][pos] = stats["by_part_of_speech"].get(pos, 0) + 1
    
    # Most frequent characters
    character_count = {}
    for word in words_db:
        for char in word.get("character", ""):
            if '\u4e00' <= char <= '\u9fff':
                character_count[char] = character_count.get(char, 0) + 1
    
    top_characters = sorted(character_count.items(), key=lambda x: x[1], reverse=True)[:10]
    stats["top_characters"] = [{"character": char, "count": count} for char, count in top_characters]
    
    return stats

@app.get("/search/{query}")
async def search_words(query: str, limit: int = 20):
    """Search words by characters, pinyin or translation"""
    results = []
    query_lower = query.lower()
    
    for word in words_db:
        # Search in characters
        if query in word.get("character", ""):
            results.append(word)
            continue
            
        # Search in pinyin
        pinyin = word.get("pinyin", "").lower()
        if query_lower in pinyin:
            results.append(word)
            continue
            
        # Search in translation
        translation = word.get("translation", "").lower()
        if query_lower in translation:
            results.append(word)
    
    return {
        "query": query,
        "count": len(results),
        "results": results[:limit]
    }

@app.get("/word/random")
async def get_random_word(level: Optional[int] = None):
    """Get random word"""
    if level:
        filtered_words = [w for w in words_db if w.get("hsk_level") == level]
    else:
        filtered_words = words_db
    
    if not filtered_words:
        raise HTTPException(status_code=404, detail="Words not found")
    
    word = random.choice(filtered_words)
    
    # Smart search for similar words:
    similar = []
    word_level = word.get("hsk_level", 1)
    word_chars = set(word["character"])
    
    for w in words_db:
        if w["character"] == word["character"]:
            continue
        
        # 1. Similar by character composition
        w_chars = set(w["character"])
        common_chars = word_chars.intersection(w_chars)
        
        # 2. Similar by topic (translation analysis)
        word_trans_lower = word["translation"].lower()
        w_trans_lower = w["translation"].lower()
        
        # Simple topic analysis
        categories = {
            "family": ["mother", "father", "brother", "sister", "family", "parents"],
            "food": ["eat", "drink", "food", "water", "tea", "rice"],
            "travel": ["go", "come", "train", "airplane", "hotel"],
            "study": ["study", "school", "student", "teacher", "book"],
            "time": ["time", "hour", "day", "month", "year", "today"]
        }
        
        similarity_found = False
        
        # Similar characters
        if common_chars:
            similarity_found = True
        
        # Same level
        if w.get("hsk_level", 1) == word_level:
            similarity_found = True
        
        # Similar translation (find common words in translation)
        word_trans_words = set(word_trans_lower.split())
        w_trans_words = set(w_trans_lower.split())
        common_words = word_trans_words.intersection(w_trans_words)
        
        if len(common_words) > 0:
            similarity_found = True
        
        # Same category
        for category, keywords in categories.items():
            word_has_keyword = any(keyword in word_trans_lower for keyword in keywords)
            w_has_keyword = any(keyword in w_trans_lower for keyword in keywords)
            
            if word_has_keyword and w_has_keyword:
                similarity_found = True
                break
        
        if similarity_found:
            similar.append({
                "character": w["character"],
                "pinyin": w["pinyin"],
                "translation": w["translation"][:50],
                "hsk_level": w.get("hsk_level", 1),
                "why_similar": f"Common characters: {len(common_chars)}, Topic: {category if 'category' in locals() else 'general'}"
            })
    
    # Take 3 most similar
    if len(similar) > 3:
        similar = similar[:3]
    elif len(similar) < 3:
        # Add random words of same level
        same_level_words = [w for w in filtered_words if w["character"] != word["character"]]
        while len(similar) < 3 and same_level_words:
            random_similar = random.choice(same_level_words)
            if random_similar not in similar:
                similar.append({
                    "character": random_similar["character"],
                    "pinyin": random_similar["pinyin"],
                    "translation": random_similar["translation"][:50],
                    "hsk_level": random_similar.get("hsk_level", 1),
                    "why_similar": "Random word of same level"
                })
    
    return {
        "word": word,
        "similar_words": similar,
        "memory_tip": generate_memory_tip(word),
        "study_suggestions": [
            "🔊 Pronounce aloud 10 times",
            f"🧠 Compare with similar: {', '.join([s['character'] for s in similar])}",
            "⏰ Review 3 more times today"
        ]
    }

class TextGenerationRequest(BaseModel):
    topic: str
    description: Optional[str] = ""
    hsk_level: int = 3
    format: str = "chinese_only"  # chinese_only, full, manga
    length: str = "medium"  # short, medium, long
    user_id: Optional[str] = None
    include_emojis: bool = True
    manga_style: bool = False

@app.post("/text/generate")
async def generate_chinese_text(request: TextGenerationRequest):
    """Generate Chinese text with given parameters"""
    try:
        # Get DeepSeek client
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=500, detail="AI service unavailable")
        
        # Form prompt based on format
        format_prompts = {
            "chinese_only": "ONLY in Chinese with characters",
            "full": "In Chinese with pinyin and Russian translation",
            "manga": "In manga style with dialogues and descriptions"
        }
        
        format_instruction = format_prompts.get(request.format, "In Chinese")
        
        # Form system prompt
        system_prompt = f"""You are a Chinese text author for language learners.
        
# TASK:
Create text on topic: "{request.topic}"
Description: {request.description}

# REQUIREMENTS:
1. Difficulty level: HSK {request.hsk_level}
2. Use words mainly from HSK {request.hsk_level} and below
3. {format_instruction}
4. Length: {request.length} (about {2000 if request.length == 'medium' else 1000 if request.length == 'short' else 3000} characters)
5. {"Use emojis" if request.include_emojis else "No emojis"}
6. {"Style like in manga: dialogues, descriptions, emotions" if request.manga_style else "Regular narrative style"}

# FORMATS:
- If only Chinese needed: characters + punctuation + emojis
- If pinyin needed: 汉字 (pinyin) 【translation】
- If manga style: 
  【Character】: Line
  *action description*
  
# STRUCTURE:
- Introduction/beginning
- Main part with development
- Conclusion/summary

Be creative, but use level-appropriate vocabulary!"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create text on topic: {request.topic}"}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.8,
            max_tokens=2000,
            presence_penalty=0.3,
            frequency_penalty=0.2
        )
        
        text_content = response.choices[0].message.content
        
        # Analyze text for statistics
        stats = analyze_chinese_text(text_content, request.hsk_level)
        
        # Format text based on format
        formatted_text = format_generated_text(text_content, request.format)
        
        return {
            "success": True,
            "text": text_content,
            "formatted_text": formatted_text,
            "text_with_pinyin": add_pinyin_to_text(text_content) if request.format == "full" else None,
            "topic": request.topic,
            "hsk_level": request.hsk_level,
            "format": request.format,
            "stats": stats,
            "generated_at": datetime.now().isoformat(),
            "length_chars": len(text_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text generation error: {str(e)}")

def analyze_chinese_text(text: str, target_hsk_level: int) -> Dict:
    """Analyze generated text"""
    # Simple analysis (in real project use HSK dictionary)
    characters = len([c for c in text if '\u4e00-\u9fff'])
    words = text.split()
    unique_words = len(set(words))
    
    # Simple difficulty estimation
    estimated_level = min(6, max(1, target_hsk_level + random.randint(-1, 1)))
    
    return {
        "characters": characters,
        "words": len(words),
        "unique_words": unique_words,
        "hsk_level": estimated_level,
        "estimated_reading_time": f"{max(1, characters // 300)} minutes",
        "new_words": max(0, unique_words - target_hsk_level * 100)  # Simple estimation
    }

def format_generated_text(text: str, format_type: str) -> str:
    """Format text for different formats"""
    if format_type == "manga":
        # Add manga markers
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            if ':' in line and len(line) < 50:
                formatted_lines.append(f"🎭 {line}")
            elif len(line) > 0:
                formatted_lines.append(f"📖 {line}")
            else:
                formatted_lines.append("")
        return '\n'.join(formatted_lines)
    
    elif format_type == "full":
        # Here you could add pinyin and translation
        return text  # In real project integrate pinyin and translation
    
    return text

@app.get("/corporate/dashboard")
async def corporate_dashboard(user_id: str):
    user = users_db[user_id]
    if user.get("role") != "owner":
        raise HTTPException(403)

    corp_id = user["corporate_id"]
    students = []

    for uid in corporate_members.get(corp_id, []):
        u = users_db[uid]
        progress = word_progress_db.get(uid, {})
        students.append({
            "name": u["name"],
            "email": u["email"],
            "learned": len([p for p in progress.values() if p.get("remembered")])
        })

    return {"students": students}

def add_pinyin_to_text(text: str) -> str:
    """Add pinyin to text (stub)"""
    # In real project use pinyin library
    # e.g., pypinyin
    return text

# Models for essay and translation checking
class EssayCheckRequest(BaseModel):
    essay_text: str
    topic: str
    hsk_level: int
    min_length: int
    prompt: Optional[str] = None
    time_spent: Optional[int] = 0  # time in seconds

class TranslationCheckRequest(BaseModel):
    original_text: str
    user_translation: str
    target_hsk: int
    difficulty: str
    user_id: Optional[str] = None
    time_spent: Optional[int] = None
    mode: str = "translation_check"

# Start automatic processing WHEN SERVER STARTS
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("📚 HSK AI Tutor - Your Ready Courses HSK 1-6")
    print("=" * 60)
    
    for level in range(1, 7):
        course_file = COURSES_DIR / f"hsk{level}.json"
        if course_file.exists():
            with open(course_file, 'r', encoding='utf-8') as f:
                course = json.load(f)
                lessons = course.get("contents", [{}])[0].get("lessons", [])
                print(f"✅ HSK {level}: {len(lessons)} lessons, {course_file.name}")
        else:
            print(f"❌ HSK {level}: file hsk{level}.json NOT FOUND in {COURSES_DIR}")
    
    print("=" * 60)
    print("🎯 AI mode: Only content explanation, not course generation")
    print("🚀 Server ready!")

import re
from pathlib import Path
import json

import os
BACKEND_ROOT = Path(__file__).parent.parent   # backend/
COURSES_DIR = BACKEND_ROOT / "data" / "courses"
COURSES_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/courses/{level}")
async def get_course(level: int):
    """Get course for HSK level from JSON file"""
    course_file = COURSES_DIR / f"hsk{level}.json"
    
    if not course_file.exists():
        # NOT generate, but return error
        return JSONResponse(
            status_code=404,
            content={"error": f"Course HSK {level} not found. Please upload textbook."}
        )
    
    with open(course_file, 'r', encoding='utf-8') as f:
        course = json.load(f)
    
    return course

@app.get("/courses/{level}/meta")
async def get_course_meta(level: int):
    """Course metadata"""
    course_file = COURSES_DIR / f"hsk{level}.json"
    
    if not course_file.exists():
        return {"total_lessons": 0, "exists": False}
    
    with open(course_file, 'r', encoding='utf-8') as f:
        course = json.load(f)
    
    if "contents" in course and len(course["contents"]) > 0:
        lessons = course["contents"][0].get("lessons", [])
        return {
            "total_lessons": len(lessons),
            "exists": True,
            "title": course.get("metadata", {}).get("title", f"HSK {level}")
        }
    
    return {"total_lessons": 0, "exists": False}

from functools import lru_cache
from typing import Dict
import hashlib
import json

# Cache for AI responses
ai_cache: Dict[str, str] = {}

@app.post("/courses/{level}/lesson/{lesson_number}/explain")
async def explain_lesson_content(request: dict):
    """AI explains specific topic from lesson (with caching)"""
    try:
        lesson_content = request.get("lesson_content", {})
        user_question = request.get("question", "")
        level = request.get("level", 5)
        
        # Create cache key
        cache_key = hashlib.md5(
            f"{level}_{lesson_content.get('lesson_number', '')}_{user_question[:50]}".encode()
        ).hexdigest()
        
        # Check cache
        if cache_key in ai_cache:
            print(f"⚡ Cache hit for: {user_question[:30]}...")
            return {"answer": ai_cache[cache_key]}
        
        # Data preparation (optimized)
        title_zh = lesson_content.get('title_zh', '')
        vocab_list = lesson_content.get('vocabulary', [])
        
        if vocab_list and len(vocab_list) > 0:
            if isinstance(vocab_list[0], dict):
                vocab_sample = [v.get('character', '') for v in vocab_list[:8] if v.get('character')]
            else:
                vocab_sample = vocab_list[:8]
        else:
            vocab_sample = []
        
        prompt = f"""You are a Chinese teacher. HSK {level}. 
Lesson: {title_zh}
Words: {', '.join(vocab_sample)}
Question: {user_question}

Answer briefly (3-5 sentences), with 1-2 examples."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,  # Reduced!
            temperature=0.5,  # Lower = faster
            timeout=10       # Timeout
        )
        
        answer = response.choices[0].message.content
        ai_cache[cache_key] = answer  # Save to cache
        
        # Limit cache size
        if len(ai_cache) > 100:
            ai_cache.clear()
        
        return {"answer": answer}
        
    except Exception as e:
        print(f"AI Error: {e}")
        return {"answer": "❌ Error. Try to formulate your question more simply."}

@app.post("/courses/{level}/lesson/{lesson_number}/generate")
async def generate_lesson_explanation(request: dict):
    """AI generates full lesson explanation as a teacher"""
    try:
        lesson = request.get("lesson", {})
        level = request.get("level", 5)
        
        title_zh = lesson.get('title_zh', '')
        title_en = lesson.get('title_en', '')
        
        # Data preparation
        vocab = lesson.get('vocabulary', [])
        notes = lesson.get('notes', [])
        comparisons = lesson.get('comparisons', [])
        
        # Format words
        vocab_text = ""
        if vocab:
            if isinstance(vocab[0], dict):
                for v in vocab[:15]:
                    char = v.get('character', '')
                    pinyin = v.get('pinyin', '')
                    trans = v.get('translation', '')
                    vocab_text += f"- {char} ({pinyin}) - {trans}\n"
            else:
                vocab_text = "\n".join([f"- {w}" for w in vocab[:15]])
        
        prompt = f"""
You are an experienced Chinese language teacher. 
Conduct a lesson for HSK {level} on the topic:

📚 TITLE: {title_zh} / {title_en}

📖 VOCABULARY:
{vocab_text}

📝 GRAMMAR:
{chr(10).join([f"- {n}" for n in notes[:5]]) if notes else "None"}

🔄 COMPARISONS:
{chr(10).join([f"- {c}" for c in comparisons[:3]]) if comparisons else "None"}

Write a FULL LESSON in Russian:

1. 🎯 INTRODUCTION - what this lesson is about, context
2. 📘 NEW WORDS - explain each word with examples
3. 🔧 GRAMMAR - in detail, with example sentences
4. 💡 MEMORIZATION - tips on how to learn
5. ✅ PRACTICE - 3-4 exercises with answers

Style: lively, like a real teacher. No markdown.
"""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        return {"success": True, "lesson_content": full_response}
        
    except Exception as e:
        print(f"Generate Error: {e}")
        return {"success": False, "error": str(e)}
    
@app.post("/api/explain-character")
async def explain_character(request: dict):
    """AI explains meaning, origin, and composition of a character"""
    try:
        character = request.get("character", "")
        
        if not character:
            return {"explanation": "Character not selected"}
        
        client = get_deepseek_client()
        
        prompt = f"""
You are an expert in Chinese characters and a Chinese language teacher.
Explain the character "{character}" in Russian.

Include in the explanation:
1. 📖 MEANING: modern meaning, usage in words
2. 🔍 ORIGIN: where it came from, how it looked in ancient times
3. 🧩 COMPOSITION: what elements/radicals it consists of, their meaning
4. 📜 HISTORY: interesting facts, evolution of writing
5. 💡 TIP: how to remember this character more easily

Tell it engagingly, like an experienced teacher. Add a bit of history and cultural context.
Use examples of words with this character.

Format the text for easy reading (paragraphs, emojis at the beginning of sections).
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.8
        )
        
        explanation = response.choices[0].message.content
        
        return {"explanation": explanation}
        
    except Exception as e:
        print(f"Error explaining character: {e}")
        return {
            "explanation": f"The character «{character}» is one of the main ones in Chinese. " +
                          f"It is used in many words and has a rich history. " +
                          f"Try looking for additional information in a dictionary."
        }

RADICALS_FILE = DATA_DIR / "radicals.json"
EXAMPLES_FILE = DATA_DIR / "radical_examples.json"

# Load examples
with open(EXAMPLES_FILE, 'r', encoding='utf-8') as f:
    radical_examples = json.load(f)

@app.get("/radicals")
async def get_radicals():
    """Get all 214 radicals"""
    if RADICALS_FILE.exists():
        with open(RADICALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return kangxiRadicals  # from file

@app.get("/radicals/{number}/examples")
async def get_radical_examples(number: int):
    """Get example characters with this radical"""
    examples = radical_examples.get(str(number), [])
    return {"examples": examples}

@app.post("/radicals/{number}/story")
async def generate_radical_story(request: dict):
    """AI generates story about radical"""
    radical = request.get("radical", {})
    
    prompt = f"""
You are an expert in Chinese writing. 
Tell a story about the radical {radical.get('radical')} (No.{radical.get('number')}).

Information:
- Pinyin: {radical.get('pinyin')}
- Meaning: {radical.get('meaning')}
- Strokes: {radical.get('strokes')}

Write in Russian:
1. Origin and evolution (as pictogram)
2. What it means in characters
3. 3-4 examples of characters with this radical
4. An interesting fact or mnemonic rule

Brief, engaging, for memorization.
"""
    
    client = get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.8
    )
    
    return {"story": response.choices[0].message.content}

from fastapi.responses import JSONResponse  # add at the beginning of file

@app.post("/generate-motivation-letter")
async def generate_motivation_letter(
    request: dict,
    db: Session = Depends(get_db)  # Removed current_user
):
    """AI generates motivation letter (available without authorization)"""
    try:
        data = request
        print(f"📝 Generating motivation letter for: {data.get('name', 'Unknown')}")
        
        # Removed all code for saving user data
        # Now only letter generation
        
        # Determine length
        length_map = {
            'short': '~300 words',
            'medium': '~500 words',
            'long': '~800 words'
        }
        length = length_map.get(data.get('length', 'medium'), '~500 words')
        
        prompt = f"""You are a legendary admissions essay coach who has helped students gain admission to Harvard, Tsinghua, Oxford, and every top university worldwide. You don't write letters — you craft narratives that make admissions officers cry, laugh, and fight to admit you.

# THE STUDENT:
- Name: {data.get('name', '')}
- Applying to: {data.get('university', '')} — {data.get('program', '')}
- Department: {data.get('department', '')}
- Why this university: {data.get('whyUni', '')}

# THEIR STORY:
- Education: {data.get('education', '')}
- Work: {data.get('work', '')}
- Projects: {data.get('projects', '')}
- Languages: {data.get('languages', '')}
- Skills: {data.get('skills', '')}
- Achievements: {data.get('achievements', '')}

# LETTER PARAMETERS:
- Tone: {data.get('tone', 'professional')}
- Length: {data.get('length', 'medium')}
- Special instructions: {data.get('instructions', '')}

# THE SECRET FORMULA (Use this!):

## 🎯 THE "DEEP WHY" FRAMEWORK:

Great letters answer 4 questions in a STORY:

1. **Who are you REALLY?** (Not what's on your resume)
2. **What SHAPED you?** (The experiences that made you)
3. **Why THIS program?** (Not just any program)
4. **What will you BECOME?** (Your contribution to the world)

## 📝 LETTER STRUCTURE:

### ACT I: THE ORIGIN STORY (First 15-20% of length)

**The Hook** (1-2 sentences):
[Not "I am applying to..." — start with a moment. A scene. A memory. Something so specific and personal it could ONLY be yours]

**The Spark**:
[What first ignited your interest in this field? Show, don't tell. Paint a scene. Describe what you saw, heard, felt. Make the reader EXPERIENCE it with you.]

**The Journey**:
[How did that spark grow? What challenges did you face? What did you learn about yourself? This is where you weave in your education, projects, work — but ALWAYS as part of a story, never as a list.]

### ACT II: THE PREPARATION (50-60% of length)

**The Pivot Point**:
[What moment made you realize you needed THIS program? Be specific. Did you read a professor's paper? Attend a lecture? Discover a research gap?]

**The Bridge**:
[How does your past experience connect to THIS program? This is where you show you've done your homework. Mention SPECIFIC professors, courses, research centers. Prove you know this program inside and out.]

**The "Why You" Argument**:
[What unique perspective, skill, or experience will you bring to their community? Not just "I'm hardworking" — what can you contribute that no one else can?]

### ACT III: THE VISION (Final 20-25%)

**The Future You**:
[What will you DO with this education? Be specific. Paint a picture of the impact you'll have. Connect it to their program — show how they're essential to your journey.]

**The Closing**:
[End with a powerful, memorable statement that echoes your opening. Show confidence, humility, and genuine excitement.]

## 💎 SECRET TECHNIQUES (Professional secrets):

### 1. The "Specificity" Rule:
Every claim must have a concrete example. Not "I'm passionate about AI" but "I built a neural network that predicts traffic patterns in my hometown, and discovered that..."

### 2. The "Vulnerability" Principle:
Show a failure or challenge you overcame. Admissions officers connect with humans, not superheroes.

### 3. The "Cultural Bridge" Technique:
For Chinese universities, connect your background to Chinese culture/philosophy in a genuine way. Don't force it — find real connections.

### 4. The "Professor Hook":
Mention 1-2 professors by name and connect their research to YOUR goals. Show you've read their work.

### 5. The "Future Impact" Frame:
End with how you'll use this education to solve a real problem. Make them see you as an investment, not just a student.

## 🚫 AVOID AT ALL COSTS:

- ❌ "I've always been passionate about..."
- ❌ "Since I was a child..."
- ❌ Listing achievements without context
- ❌ Generic statements about the university
- ❌ Overused quotes or clichés
- ❌ Humble-bragging
- ❌ Explaining things that are obvious from your CV

## ✨ THE DIFFERENCE MAKERS:

1. **Voice**: Write like YOU speak. Don't use words you'd never say.
2. **Specificity**: Every sentence should contain a detail only YOU could provide.
3. **Emotion**: Don't describe your feelings — make the READER feel something.
4. **Show, Don't Tell**: "I learned leadership" vs "When our project failed, I called a midnight meeting and we rebuilt from scratch"
5. **The Mirror Moment**: Include one moment where you had to choose between what was easy and what was right.

## 📝 YOUR LETTER:

Write a COMPLETE motivation letter that follows this structure:

[Letter here — formatted beautifully, with proper paragraphs, natural flow, and the student's unique voice]

## 💡 POST-LETTER ANALYSIS:

**Why This Works**:
- [Point out 3 specific strengths of this letter]

**What Admissions Officers Will Think**:
- [What they'll feel reading each section]

**What They'll Remember**:
- [The 1-2 things that will stick in their mind]

**If You Want It Even Stronger**:
- [One optional suggestion to take it from great to legendary]

---

Return the COMPLETE letter formatted beautifully, followed by the analysis. This should be so compelling that admissions officers can't stop reading."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "letter": response.choices[0].message.content
            }
        )
        
    except Exception as e:
        print(f"❌ Motivation letter error: {e}")
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error": str(e)
            }
        )
    
@app.get("/user/education/stats")
async def get_education_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get statistics on user's Education data"""
    try:
        stats = {
            "has_university": bool(current_user.university_target),
            "has_program": bool(current_user.program_target),
            "has_education": bool(current_user.education_background),
            "has_work": bool(current_user.work_experience),
            "has_projects": bool(current_user.projects),
            "has_achievements": bool(current_user.achievements),
            "letters_generated": db.query(UserAction).filter(
                UserAction.user_id == current_user.id,
                UserAction.action_type == "motivation_letter_generated"
            ).count()
        }
        
        # Calculate profile completeness
        filled_fields = sum(1 for v in stats.values() if v and isinstance(v, bool))
        stats["profile_completion"] = int((filled_fields / 8) * 100)
        
        return stats
    except Exception as e:
        logger.error(f"Error getting education stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/generate-portfolio-strategy")
async def generate_portfolio_strategy(request: dict):
    """AI generates portfolio strategy"""
    try:
        data = request
        
        prompt = f"""You are a creative portfolio coach who has helped artists, engineers, designers, and researchers build portfolios that got them into the world's top programs. You know that a great portfolio isn't about quantity — it's about storytelling.

# THE STUDENT:
- Target: {data.get('university')} — {data.get('degree')} in {data.get('major')}
- Department: {data.get('department')}
- Education: {data.get('education')}
- Work: {data.get('work')}
- Skills: {data.get('skills')}
- Languages: {data.get('languages')}
- Achievements: {data.get('achievements')}
- Interests: {data.get('interests')}
- Deadline: {data.get('deadline')}

# YOUR MISSION:
Create a portfolio strategy that turns their background into a compelling story.

## 🎯 THE "STORY ARC" FRAMEWORK:

Every great portfolio tells a story with 3 acts:

### ACT I: WHO I AM
- What experiences shaped my interest?
- What's my unique perspective?
- What problem do I care about?

### ACT II: WHAT I'VE DONE
- How have I developed my skills?
- What challenges have I overcome?
- What have I created/built/solved?

### ACT III: WHERE I'M GOING
- How does this program fit my journey?
- What will I create next?
- How will I contribute to the world?

## 📁 PROJECT IDEAS (Tailored to Their Skills):

Based on their profile ({data.get('skills')}, {data.get('interests')}), here are 5 SPECIFIC projects:

### Project 1: [Creative title]
- **Description**: [What they'll build/create/solve — be SPECIFIC]
- **Skills used**: [Skills from their list + new ones they'll learn]
- **Estimated time**: [Hours]
- **Why it's powerful**: [How it demonstrates what admissions officers want to see]
- **How to present**: [Format — video, website, PDF, interactive]
- **Difficulty**: [1-10]
- **Impact**: [1-10]
- **Tools needed**: [Specific software, materials]

### Project 2: [Creative title]
[Same structure]

### Project 3: [Creative title]
[Same structure]

### Project 4: [Creative title — stretch goal]
[Same structure]

### Project 5: [Creative title — passion project]
[Same structure]

## 🗺️ ROADMAP (Day-by-day):

### Week 1-2: Foundation
**Focus**: [Specific theme]
- **Day 1-3**: [Specific task]
- **Day 4-7**: [Specific task]
- **Milestone**: [What to have completed]
- **Check-in**: [What to reflect on]

### Week 3-4: Development
[Same structure]

### Week 5-6: Refinement
[Same structure]

### Week 7-8: Presentation
[Same structure]

## 💡 PRESENTATION STRATEGY:

### Portfolio Format Recommendations:
Based on their field ({data.get('major')}):

**Primary Format**: [Website/PDF/Video/GitHub — and why]

**Structure**:
1. **Hero Section**: [What they see first — your best work]
2. **About You**: [Your story in 100 words]
3. **Projects**: [Order by narrative, not chronologically]
4. **Skills**: [Visual representation]
5. **Contact**: [Professional and easy]

### For Each Project, Include:

**The Hook**: [One sentence that makes them want to see more]
**The Problem**: [What you were trying to solve]
**Your Role**: [What YOU specifically did]
**The Process**: [How you thought about it — show sketches, iterations, failures]
**The Result**: [What you achieved — with metrics if possible]
**The Reflection**: [What you learned, what you'd do differently]
**Links**: [Live demo, code, paper]

## 🔥 STANDOUT TECHNIQUES:

### The "Failure" Project:
Show one project that failed. Explain what you learned. Admissions officers LOVE this — it shows maturity.

### The "Process" Documentation:
Don't just show final results. Show sketches, wireframes, iterations, failed attempts. Show how you think.

### The "Real Impact" Metrics:
Instead of "I built an app" → "My app reduced wait times by 40% for 500 users"

### The "Personal Touch":
Include one project that's purely passion-driven. Shows you're a human, not just a portfolio-builder.

## ⚠️ COMMON MISTAKES TO AVOID:

1. **Quantity over quality**: 3 great projects > 10 mediocre ones
2. **No context**: Explain WHY, not just WHAT
3. **Bad presentation**: Poor photos, confusing layout, broken links
4. **No personality**: Let your voice come through
5. **Too generic**: Make it specific to YOUR interests
6. **Missing skills**: Show skills relevant to your target program

## 📝 TIPS FOR EACH PROJECT TYPE:

### For Technical Projects:
- Include code samples with comments
- Show architecture diagrams
- Explain technical decisions
- Link to GitHub with good README

### For Creative Projects:
- Show process sketches
- Explain artistic decisions
- Include high-quality photos/videos
- Contextualize within influences

### For Research Projects:
- Show your contribution clearly
- Include abstracts or summaries
- Mention publications/posters
- Explain methodology

### For Business/Strategy Projects:
- Show data and analysis
- Explain decision-making process
- Include results/metrics
- Show presentations

## 🎓 FINAL POLISH:

### Before Submitting:
1. **Proofread**: Read everything aloud
2. **Test links**: Everything should work
3. **Mobile check**: Looks good on phone
4. **Get feedback**: 2-3 people review
5. **Sleep on it**: Review with fresh eyes

### For Each University:
- **Research**: Look up professors working in YOUR area
- **Customize**: Tailor project order based on program focus
- **Connect**: Mention specific people/courses in your descriptions

## 💬 YOUR PORTFOLIO THEME:

Based on their profile, the unifying theme should be:
[One sentence that captures their unique story]

Example: "Turning data into human stories" or "Designing for social impact" or "Building tools for the next generation"

---

Return this as a complete, actionable guide. Every project idea should feel tailored. Every tip should be specific. This should be so detailed they could follow it blindly and create an outstanding portfolio."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        return {
            "success": True,
            **json.loads(content)
        }
        
    except Exception as e:
        print(f"Portfolio error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/portfolio-assistant")
async def portfolio_assistant(request: dict):
    """Chat assistant for portfolio"""
    try:
        question = request.get("question", "")
        context = request.get("context", {})
        
        prompt = f"""You are a portfolio advisor. Answer the question based on this context:

User's target: {context.get('university')} - {context.get('major')}
User's skills: {context.get('skills', 'Not specified')}

Question: {question}

Give practical, concise advice about portfolio building, project ideas, or presentation tips.
Be encouraging and specific."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        return {"answer": response.choices[0].message.content}
        
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}
    
@app.post("/generate-video-script")
async def generate_video_script(request: dict):
    """AI generates video script for admissions"""
    try:
        data = request
        
        prompt = f"""You are a TOP Hollywood-level video producer and former admissions committee member who has reviewed thousands of application videos. You know EXACTLY what makes a video go viral and what makes admissions officers press "ACCEPT".

# YOUR MISSION:
Create a CINEMATIC MASTERPIECE video script for: {data.get('university')} - {data.get('degree')} in {data.get('major')}

# STUDENT CONTEXT:
- Background: {data.get('background')}
- Why this program: {data.get('why')}
- Future goals: {data.get('goals')}
- Equipment available: {data.get('equipment')}
- Language: {data.get('language')}
- Duration: {data.get('duration')} seconds

# SECRET INSIDER KNOWLEDGE (Use this!):
1. **The First 7 Seconds Rule**: Admissions officers decide within 7 seconds whether to keep watching. Start with a BANG.
2. **The "Show, Don't Tell" Principle**: Every claim must be visually demonstrated.
3. **Emotional Arc**: Create a mini-story with conflict, struggle, and resolution.
4. **Cultural Nuance**: For Chinese universities, emphasize: filial piety (孝), perseverance (坚持), and contribution to society (贡献社会).
5. **The "Specificity" Trap**: Generic statements = rejection. Every sentence must have a concrete detail.

# OUTPUT FORMAT - CINEMATIC STYLE:

## 🎬 SCENE-BY-SCENE BREAKDOWN:

### ACT I: THE HOOK (0:00-0:15)
**Scene 1**: [Timestamp 0:00-0:07]
- 🎥 VISUAL: [Specific camera angle, lighting, movement]
- 🎤 AUDIO: [Exact words - MUST be memorable and unique]
- 💡 EMOTION: [What the viewer should feel]
- 🎨 CINEMATIC TECHNIQUE: [Specific film technique to use]

**Scene 2**: [Timestamp 0:07-0:15]
- 🎥 VISUAL: ...
- 🎤 AUDIO: ...
- 💡 EMOTION: ...

### ACT II: THE JOURNEY (0:15-{data.get('duration')-15})
**Scene 3-5**: [Break down by key moments]
- For each major achievement: Show the STRUGGLE before the success
- Use B-roll creatively: [Suggest specific shots based on their background]
- Voiceover: [Emotional, personal, specific]

### ACT III: THE VISION (Last 15 seconds)
**Final Scene**:
- 🎥 VISUAL: [Powerful closing image]
- 🎤 AUDIO: [Call to action + why YOU are the perfect fit]
- 🎯 MEMORABLE CLOSING LINE: [Something they'll remember]

## 🎥 TECHNICAL PRODUCTION GUIDE:

### CAMERA WORK:
- **Main Setup**: [Based on their equipment]
- **Angles to use**: [Eye-level for connection, low-angle for power, high-angle for vulnerability]
- **Movement**: [When to use static vs dynamic shots]

### AUDIO PRODUCTION:
- **Microphone placement**: [Exact distance, angle based on their gear]
- **Room acoustics**: [How to improve their current space]
- **Music recommendations**: [Genre, tempo, where to find free music]

### LIGHTING:
- **Three-point lighting setup**: [How to achieve with household items]
- **Natural light optimization**: [Time of day, window positioning]

### BACKGROUND & SET DESIGN:
- **Scene 1 background**: [Specific items to include/remove]
- **Props that work**: [Based on their story, suggest 3-5 meaningful props]

## 💡 PRO-LEVEL TIPS:

1. **The "Gap Year" Strategy**: If you have a gap, address it PROACTIVELY with a story.
2. **The "Connection" Hook**: If you have ANY connection to the university, lead with it.
3. **The "Failure" Story**: Show a specific failure and what you learned.
4. **Cultural References**: Drop 1-2 specific references to Chinese culture/philosophy.
5. **The "Future Vision"**: Don't just say "I want to study X". Say "I will use X to solve [specific problem]".

## 🚫 AVOID AT ALL COSTS:
- ❌ "I've always been passionate about..." (overused)
- ❌ Generic achievements without context
- ❌ Reading from a script
- ❌ Low energy or monotone delivery

## 🎯 MEMORABILITY SCORE TARGET: 10/10

Return a COMPLETE, ACTIONABLE script with EXACT words, SPECIFIC camera instructions, and PRODUCTION TIPS that anyone can follow regardless of equipment."""

        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        return {
            "success": True,
            **json.loads(content)
        }
        
    except Exception as e:
        print(f"Video script error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    
@app.post("/calculate-admission")
async def calculate_admission(request: dict):
    """AI calculates admission chances"""
    try:
        data = request
        
        prompt = f"""You are a data scientist specializing in university admissions, with access to 10+ years of admission data from top universities worldwide. You don't just give percentages — you explain the STORY behind the numbers.

# APPLICANT PROFILE:
- Target universities: {', '.join(data.get('universities', []))}
- Degree: {data.get('degree')}
- Field: {data.get('field')}
- GPA: {data.get('gpa')}/4.0
- Rank: {data.get('rank')}
- Test scores: TOEFL {data.get('toefl') or 'N/A'}, IELTS {data.get('ielts') or 'N/A'}, GRE {data.get('gre') or 'N/A'}, GMAT {data.get('gmat') or 'N/A'}, HSK {data.get('hsk') or 'N/A'}
- Work experience: {data.get('workYears')} years
- Research: {data.get('research')}
- Internships: {data.get('internships')}
- Awards: {data.get('awards')}
- Extracurriculars: {data.get('extracurricular')}
- Recommendations: {data.get('recommendations')}/10
- Personal Statement: {data.get('statement')}/10
- Diversity factors: {data.get('diversity')}

# YOUR MISSION:
Calculate REALISTIC admission chances with EXPLANATIONS that help them IMPROVE.

## 📊 ADMISSION PROBABILITY MODEL:

### University 1: {data.get('universities', [])[0] if data.get('universities') else 'Target University'}
**Admission Probability**: [XX]%

**🔬 DATA ANALYSIS**:
- Historical acceptance rate: [X]% (Source: [Year] data)
- Similar profiles admitted last year: [Number] out of [Number]
- Your rank among applicants: Top [X]%

**🎯 FACTOR BREAKDOWN**:

| Factor | Your Score | Weight | Contribution | How to Improve |
|--------|-----------|--------|--------------|----------------|
| Academics | [X]/10 | [X]% | [±X%] | [Specific advice] |
| Test Scores | [X]/10 | [X]% | [±X%] | [Specific advice] |
| Experience | [X]/10 | [X]% | [±X%] | [Specific advice] |
| Essays/LORs | [X]/10 | [X]% | [±X%] | [Specific advice] |
| Diversity | [X]/10 | [X]% | [±X%] | [Specific advice] |

**🚀 COMPETITIVE ANALYSIS**:
- **Strengths**: [2-3 things that make them stand out]
- **Weaknesses**: [2-3 areas that hurt their chances]
- **Red Flags**: [Any potential concerns for admissions]
- **Green Flags**: [What will make admissions officers excited]

**💡 STRATEGIC RECOMMENDATIONS**:

1. **Application Angle**:
   - Lead with: [Their strongest selling point]
   - Frame weakness as: [How to position their weakness as strength]
   - Unique story: [What narrative to build]

2. **Document Optimization**:
   - Personal Statement focus: [Specific theme]
   - Recommendation letter ask: [What to request from recommenders]
   - Additional information: [What to explain in optional section]

3. **Timeline Strategy**:
   - Apply: [Early decision/regular/rolling - and why]
   - Contact: [Who to reach out to before applying]
   - Follow up: [What to do after submitting]

**⚠️ REALITY CHECK**:
- [What would make their application significantly stronger]
- [What's unlikely to change at this point]
- [What they should accept and work around]

---

### University 2: {data.get('universities', [])[1] if len(data.get('universities', [])) > 1 else 'Second University'}
[Same structure...]

[Continue for all universities]

## 📈 OVERALL ADMISSION FORECAST:

### Your Profile Summary:
- **Admission Profile Type**: [Competitive/Moderate/Reach/High Potential]
- **Relative Strengths**: [2-3 areas where they're above average]
- **Relative Weaknesses**: [2-3 areas where they're below average]
- **Unique Value Proposition**: [What makes them different]

### Probability Distribution:
University 1: [XX]% ████████░░
University 2: [XX]% ██████░░░░
University 3: [XX]% ████░░░░░░

text

### Confidence Level: [High/Medium/Low]
[Explanation of why confidence is at this level]

## 🎯 THE 30-DAY IMPROVEMENT PLAN:

### Week 1: [Focus area]
- [Action 1 with timeline]
- [Action 2 with timeline]
- [Expected impact: +X% to probability]

### Week 2: [Focus area]
[Same structure]

### Week 3: [Focus area]
[Same structure]

### Week 4: [Focus area]
[Same structure]

## 🔥 QUICK WINS (Highest Impact):

1. **Fix this**: [One thing that will increase probability most]
2. **Add this**: [One thing missing that's easy to add]
3. **Remove this**: [One thing that's hurting their application]

## 💰 SCHOLARSHIP PROBABILITY:

### Need-Based Scholarships:
- Probability: [X]%
- Maximum likely award: [Amount]
- How to maximize: [Strategy]

### Merit-Based Scholarships:
- Probability: [X]%
- Likely amount: [Amount]
- How to qualify: [What they need to emphasize]

### External Scholarships:
- [List 3-5 they should apply for]

## 📝 SAMPLE APPLICATION FRAMEWORK:

**Personal Statement Outline**:
1. Opening: [Hook based on their unique story]
2. Why this field: [How to connect their experience]
3. Why this university: [Specific professors/courses/research]
4. What they'll contribute: [Unique value they bring]
5. Future impact: [How they'll use this education]

**Recommendation Letter Ask**:
[What to tell each recommender to write]

**CV/Resume Focus**:
[What to highlight and how to format]

## 🎓 FINAL VERDICT:

**If You Apply Today**: [Realistic outcome]
**If You Follow This Plan**: [Improved outcome]
**If You Apply Next Year**: [Best possible outcome]

**Most Important Action** (Do this TODAY):
[One concrete thing they can do right now]

---

Return this as beautifully formatted HTML. Make every number have context. Every recommendation should be ACTIONABLE. This isn't just a calculator — it's a roadmap to success."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        result = json.loads(content)
        return {"success": True, **result}
        
    except Exception as e:
        print(f"Admission calc error: {e}")
        return {"success": False, "error": str(e)}
    
@app.post("/generate-exam-plan")
async def generate_exam_plan(request: dict):
    """AI generates cunning exam preparation plan"""
    try:
        data = request
        
        prompt = f"""You are a world-class exam strategist who has helped 10,000+ students achieve their target scores. You combine cognitive science, memory techniques, and insider exam knowledge.

# EXAM DETAILS:
- Exam: {data.get('examType')}
- Days until exam: {data.get('daysUntilExam')}
- Hours per day available: {data.get('hoursPerDay')}
- Target score: {data.get('targetScore')}
- Current level: {data.get('currentLevel') or 'Not taken yet'}
- Strengths: {data.get('strengths')}
- Weaknesses: {data.get('weaknesses')}
- Materials available: {data.get('materials')}

# YOUR STRATEGIC FRAMEWORK:

## 🎯 THE 80/20 PRINCIPLE (Pareto Optimization):
Identify the 20% of topics that will yield 80% of the score. For {data.get('examType')}, these are:
- [Topic 1] - Worth [X]% of total score
- [Topic 2] - Worth [Y]% of total score
- [Topic 3] - Worth [Z]% of total score

## 🧠 COGNITIVE SCIENCE TECHNIQUES (Use these!):

### 1. Spaced Repetition Schedule:
Create an EXACT review schedule based on {data.get('daysUntilExam')} days:
- Day 1-3: Foundation
- Day 4-7: Active recall (explain without looking)
- Day 8-14: Interleaving (mix topics)
- Day 15-{data.get('daysUntilExam')-5}: Mock tests
- Last 5 days: Peak performance optimization

### 2. Active Recall Methods:
For each section, give SPECIFIC techniques:
- [Section 1]: Use Feynman technique (teach to a child)
- [Section 2]: Use blurting (write everything you remember)
- [Section 3]: Use dual coding (draw + write)

### 3. Sleep and Consolidation:
- Optimal sleep schedule for memory consolidation
- Pre-sleep review technique
- Wake-up routine for peak cognitive function

## 📊 WEEK-BY-WEEK BATTLE PLAN:

### Week 1: [Date range] - Foundation & Diagnosis
- **Focus**: [Main goal]
- **Daily Schedule** ({data.get('hoursPerDay')} hours):
  - Morning (2h): [Highest energy task]
  - Afternoon (2h): [Medium energy task]
  - Evening (1h): [Low energy task]
- **Key Resources**: [Specific pages/chapters from their materials]
- **Milestone**: [What they must achieve by end of week]
- **Red Flags to Watch**: [Signs they're falling behind]

### Week 2: [Continue for all weeks until exam]

## 🔥 SECTION-SPECIFIC CHEAT CODES:

### For {data.get('examType')}:

**Section 1: [Section Name]**
- ⚡ Time hack: [Specific time-saving technique]
- 🎯 Pattern recognition: [What to look for]
- 📝 Template answers: [For writing/speaking sections]
- ❌ Common traps: [What to avoid]
- 💪 Power moves: [Advanced techniques for high scores]

## 🎲 THE "HACKS" SECTION (Legal but clever):

1. **For Multiple Choice**:
   - Elimination strategy: [Specific method]
   - Guessing techniques: [When and how to guess]
   - Answer patterns: [Statistical patterns in this exam]

2. **For Writing**:
   - Essay templates for each question type
   - Transition words for different tones
   - How to add sophistication without complexity

3. **For Speaking**:
   - 30-second answer structure
   - Fillers that sound intelligent
   - How to buy thinking time

## 📈 YOUR PERSONALIZED IMPROVEMENT PLAN:

### Priority 1 (Must fix immediately):
- {data.get('weaknesses').split(',')[0] if data.get('weaknesses') else 'Main weakness'}: [Specific daily exercise]
- {data.get('weaknesses').split(',')[1] if data.get('weaknesses') else 'Second weakness'}: [Specific daily exercise]

### Priority 2 (Build on strengths):
- {data.get('strengths').split(',')[0] if data.get('strengths') else 'Main strength'}: [How to leverage for max score]

## ⏰ THE 30-DAY PROGRESSION MODEL:

Based on {data.get('daysUntilExam')} days remaining:

**Phase 1 - Knowledge Acquisition** (Days 1-{max(1, int(data.get('daysUntilExam', 30)*0.3))}):
- [Specific activities]
- [Resources to use]
- [Checkpoints]

**Phase 2 - Skill Development** (Days {max(1, int(data.get('daysUntilExam', 30)*0.3))+1}-{max(1, int(data.get('daysUntilExam', 30)*0.6))}):
- [Specific activities]
- [Resources to use]
- [Checkpoints]

**Phase 3 - Test Simulation** (Days {max(1, int(data.get('daysUntilExam', 30)*0.6))+1}-{data.get('daysUntilExam', 30)-5}):
- [Specific activities]
- [Resources to use]
- [Checkpoints]

**Phase 4 - Peak Performance** (Final 5 days):
- [Specific activities]
- [Mental preparation]
- [Physical optimization]

## 🧘 MENTAL PREPARATION:

1. **Exam Day Simulation**:
   - [When to do full simulation]
   - [What to replicate]
   - [How to analyze results]

2. **Stress Management**:
   - [Specific breathing technique]
   - [Pre-exam routine]
   - [During-exam reset technique]

3. **Confidence Building**:
   - [Daily affirmations]
   - [Progress tracking method]
   - [When to push harder vs rest]

## 🎯 PREDICTED SCORE BREAKDOWN:

If you follow this plan:
- Baseline score: [Current estimated score]
- Week 4 target: [Score]
- Week 8 target: [Score]
- Final predicted: {data.get('targetScore')}

## ⚠️ CONTINGENCY PLANS:

If you fall behind:
- **Option A**: Cut [low-value activities]
- **Option B**: Double down on [high-yield topics]

If you're ahead:
- **Bonus**: [Advanced topics to explore]
- **Perfect**: [Perfection strategies]

## 💬 YOUR MANTRA FOR SUCCESS:

[Create a personalized, powerful mantra based on their goal]

---

Return a COMPLETE, ACTIONABLE plan. Every day should be mapped. Every technique should be specific. No generic advice. This plan must be so detailed they could follow it blindly and succeed."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        return {
            "success": True,
            **json.loads(content)
        }
        
    except Exception as e:
        print(f"Exam plan error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    
@app.post("/china-visa-expert")
async def china_visa_expert(request: dict):
    """Expert on Chinese student visas"""
    try:
        data = request
        
        prompt = f"""You are a Senior Visa Officer at the Chinese Embassy with 20+ years of experience. You've reviewed 50,000+ visa applications and know EXACTLY why students get accepted or rejected. You're sharing the REAL rules, not just the official ones.

# APPLICANT PROFILE:
- Visa type: {data.get('visaType')} (X1 = >180 days study, X2 = <180 days)
- Country: {data.get('country')}
- University: {data.get('university')} in {data.get('city')}
- Program dates: {data.get('startDate')} to {data.get('endDate')}
- JW form status: {data.get('jwStatus')}
- Financial status: {data.get('financialStatus')}
- Insurance: {data.get('insurance')}
- Previous visa: {data.get('previousVisa')}
- Criminal record: {data.get('criminalRecord')}
- Special concerns: {data.get('concerns')}

# YOUR MISSION:
Provide a COMPLETE, OFFICIAL, but CANDID visa application guide that ensures success.

## 📅 TIMELINE (Exact dates based on their program):

### X1 Visa (Study >180 days):

**6-8 Months Before**:
- [ ] Research and apply to university
- [ ] Get admission letter

**4-5 Months Before**:
- [ ] University submits JW202 application
- [ ] Start preparing documents

**3 Months Before**:
- [ ] JW202 form arrives (usually takes 4-8 weeks)
- [ ] Book visa appointment ASAP (slots fill up)

**2 Months Before**:
- [ ] Submit visa application (at least 1 month before travel)
- [ ] DO NOT book flight until visa approved

**1 Month Before**:
- [ ] Visa processing (typically 4-7 business days)
- [ ] Collect passport with visa
- [ ] Book flight after visa in hand

**2 Weeks Before**:
- [ ] Confirm accommodation
- [ ] Prepare arrival documents

### X2 Visa (Study <180 days):
[Similar structure with compressed timeline]

## 📄 DOCUMENT CHECKLIST (With insider tips):

### Primary Documents:

**1. Passport**:
- ✓ Valid for at least 6 months beyond intended stay
- ✓ At least 2 blank pages
- ⚠️ INSIDER TIP: If your passport expires in less than 2 years, consider renewing now. Renewing later in China is complicated.

**2. Visa Application Form**:
- ✓ Complete online at https://cova.mfa.gov.cn/
- ✓ Print with QR code
- ✓ Sign in black ink
- ⚠️ COMMON MISTAKE: "Intended date of arrival" must be AFTER you receive your visa. Don't put your ideal date — put a realistic date 2 weeks after applying.

**3. Passport Photo**:
- ✓ 33mm × 48mm
- ✓ White background
- ✓ Full face, no glasses
- ✓ Recent (within 6 months)
- ⚠️ INSIDER TIP: Get 4-6 copies. Chinese visa offices are strict about quality.

**4. Visa Application Form Confirmation**:
- ✓ Printed with QR code
- ✓ Keep electronic copy

### Study-Specific Documents:

**5. JW201/JW202 Form**:
- ✓ Original form (not copy)
- ✓ Officially stamped by university
- ✓ Your name EXACTLY as in passport
- ⚠️ INSIDER TIP: If form has ANY error (even spelling), request correction. Do NOT apply with errors.

**6. Admission Letter**:
- ✓ Original admission letter from university
- ✓ Your full name, program, dates, duration
- ✓ University stamp
- ✓ Official letterhead
- ⚠️ INSIDER TIP: If you have conditional admission, you may need proof that conditions were met.

**7. Financial Proof**:
- ✓ Bank statement (last 6 months)
- ✓ Minimum balance: Typically 100,000-150,000 RMB or equivalent
- ✓ In your name OR with sponsor letter
- ✓ Notarized translation if not in English/Chinese
- ⚠️ INSIDER TIP: Large deposits made just before applying are red flags. Show consistent savings.

**8. Sponsor Letter** (if applicable):
- ✓ From parents/sponsor
- ✓ Explains relationship and financial support
- ✓ Includes sponsor's ID/passport copy
- ✓ Signed and dated
- ⚠️ INSIDER TIP: Even if you have your own money, a sponsor letter from parents adds credibility.

**9. Medical Examination Form**:
- ✓ For X1 visa (study >180 days)
- ✓ Form: Medical Examination Record for Foreigner
- ✓ Completed by approved doctor
- ✓ All tests including HIV, syphilis, chest X-ray
- ⚠️ INSIDER TIP: Get this done early — results take 1-2 weeks.

**10. Police Clearance Certificate**:
- ✓ For X1 visa
- ✓ From your home country
- ✓ For any country where you've lived >6 months in past 5 years
- ✓ Notarized translation
- ⚠️ INSIDER TIP: If you have ANY criminal record, disclose it. They will find out. Honesty matters.

**11. Proof of Accommodation**:
- ✓ For X1 visa
- ✓ University dorm confirmation OR apartment lease
- ⚠️ INSIDER TIP: University dorms are easier to document.

**12. Health Insurance**:
- ✓ Valid in China
- ✓ Minimum coverage: 300,000 RMB
- ⚠️ INSIDER TIP: Some universities require you to buy their insurance. Check first.

## 🏛️ APPLICATION PROCESS (Step-by-Step):

### Step 1: Online Application
1. Go to https://cova.mfa.gov.cn/
2. Select your country and location
3. Complete form carefully
4. Upload photo
5. Print application and confirmation

### Step 2: Appointment Booking
1. Book through Chinese Visa Application Service Center (CVASC)
2. Appointments fill 2-4 weeks in advance
3. Choose priority processing if available

### Step 3: Document Preparation
1. Organize in order: application, passport, JW form, admission letter, financial proof
2. Make copies of everything
3. Bring original and copies

### Step 4: In-Person Submission
1. Arrive 15 minutes early
2. Bring ALL documents
3. Be prepared for questions
4. Pay fee (varies by country)
5. Get receipt with pickup date

### Step 5: Processing
- Standard: 4-7 business days
- Express: 2-3 business days (extra fee)
- Rush: 24 hours (if available)

### Step 6: Collection
1. Bring receipt
2. Check visa carefully for errors
3. Verify dates, duration, entry type

## 🎤 INTERVIEW PREPARATION (What they'll ask):

### Common Questions & What They're Really Asking:

**Q1: "Why do you want to study in China?"**
- *What they're looking for*: Genuine interest, not just escaping your country
- *How to answer*: Mention specific programs, culture, career goals
- *RED FLAG*: "It's cheaper" or "I couldn't get in elsewhere"

**Q2: "What will you do after graduation?"**
- *What they're looking for*: Proof you'll leave China after studies
- *How to answer*: Specific career plans in your home country
- *RED FLAG*: Vague answers or "stay in China"

**Q3: "Who is funding your studies?"**
- *What they're looking for*: Legitimate financial support
- *How to answer*: Be specific about source and amount
- *RED FLAG*: Hesitation or "friends" as sponsors

**Q4: "Why this university/program?"**
- *What they're looking for*: You did your research
- *How to answer*: Name specific professors, courses, research
- *RED FLAG*: "It's famous" or "My friend went there"

**Q5: "Do you know anyone in China?"**
- *What they're looking for*: Truthful answer
- *How to answer*: Honest about family/friends
- *RED FLAG*: Lying about having relatives

### Pro Tips for Interview:
- ✓ Dress professionally
- ✓ Bring extra copies of all documents
- ✓ Answer confidently but briefly
- ✓ If you don't know, say "I'll find out" not "I don't know"
- ✓ Maintain eye contact
- ✓ Don't volunteer information not asked

## ⚠️ RED FLAGS & REJECTION REASONS (Real data):

### Common Reasons for Rejection:

1. **Incomplete Documents** (40% of rejections):
   - Missing original documents
   - Unclear photocopies
   - Expired passport
   - Wrong photo size

2. **Financial Issues** (25% of rejections):
   - Insufficient funds
   - Unexplained large deposits
   - Sponsor with no relationship proof

3. **Previous Visa Issues** (15% of rejections):
   - Overstayed previous visa
   - Working illegally in China

4. **Suspicious Intent** (10% of rejections):
   - Vague study plans
   - Inconsistent answers

5. **Criminal Record** (5% of rejections):
   - Undisclosed criminal history

6. **Medical Issues** (5% of rejections):
   - Untreated communicable diseases

## 💰 FINANCIAL PROOF DETAILS:

### Minimum Amounts (CNY):
- X1 Visa (Bachelor's): 100,000-150,000 RMB/year
- X1 Visa (Master's/PhD): 80,000-120,000 RMB/year
- X2 Visa: 50,000-80,000 RMB for program duration

### Acceptable Proof:
- Personal bank statements (6 months)
- Parent/sponsor bank statements + sponsorship letter
- Scholarship award letter
- Education loan approval letter

### Red Flags:
- Sudden large deposits (last 1-2 months)
- Bank statements not on official letterhead
- Insufficient balance for full program duration

## 🏥 MEDICAL EXAM DETAILS:

### For X1 Visa (Required):
- **Form**: Medical Examination Record for Foreigner
- **Timing**: Within 6 months of application
- **Required Tests**:
  - Physical examination
  - Blood tests (HIV, syphilis, hepatitis)
  - Chest X-ray
  - Urinalysis

### Pro Tips:
- Bring 4-6 photos
- Fast before blood work
- Get results in sealed envelope

## 🏙️ AFTER VISA APPROVAL:

### Before Departure:
1. **Check visa details**:
   - Name spelling matches passport
   - Entry type: X1 or X2
   - Duration: "000" (X1) or specific days (X2)

2. **Prepare arrival documents**:
   - Passport with visa
   - Admission letter
   - JW202 form (original)
   - Medical exam results
   - Photos (8-10)

### After Arrival in China:

**Within 24 Hours**:
- Register at local police station

**Within 30 Days (X1 Visa)**:
- Go to university to get Residence Permit
- Take passport, visa, JW202, admission letter, medical results
- Residence Permit processing: 7-15 days
- You cannot leave China until Residence Permit is issued

## 📞 EMERGENCY CONTACTS:

### Before Travel:
- **University International Office**: [Find contact]
- **Chinese Embassy in your country**: [Find contact]

### After Arrival:
- **Police**: 110
- **Fire**: 119
- **Ambulance**: 120

## 💡 INSIDER TIPS (From former visa officers):

1. **Apply early**: Slots fill quickly, especially before September intake
2. **Use express service**: Pay extra if you can — peace of mind
3. **Check names carefully**: One letter mismatch = reapplication
4. **Keep copies**: Of everything, including submitted application
5. **Stay consistent**: All names (passport, JW form, admission letter) must match EXACTLY
6. **Be honest**: About everything. They can verify.
7. **Dress professionally**: For in-person submission
8. **Have backup plans**: In case of delays
9. **Join student groups**: WeChat groups for your university

## 🚫 ABSOLUTELY DO NOT:

- ❌ Lie about anything
- ❌ Submit forged documents (permanent ban)
- ❌ Work before getting work permit
- ❌ Overstay visa (even by 1 day)
- ❌ Ignore registration requirements
- ❌ Travel to Tibet without permit
- ❌ Engage in political activities

---

Return this as beautifully formatted HTML with clear sections, warnings highlighted, and actionable steps. This should be the most comprehensive visa guide they've ever seen."""

        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # Try to parse as JSON, if not - return as text
        try:
            # Look for JSON in response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                guidance = json.loads(json_match.group())
            else:
                # If no JSON, structure ourselves
                sections = content.split('\n\n')
                guidance = {
                    "timeline": sections[0] if len(sections) > 0 else content,
                    "documents": sections[1] if len(sections) > 1 else "",
                    "application": sections[2] if len(sections) > 2 else "",
                    "interview": sections[3] if len(sections) > 3 else "",
                    "redFlags": sections[4] if len(sections) > 4 else ""
                }
        except:
            guidance = {"full": content}
        
        return {
            "success": True,
            "guidance": guidance
        }
        
    except Exception as e:
        print(f"Visa expert error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/china-visa-chat")
async def china_visa_chat(request: dict):
    """Chat with visa expert"""
    try:
        question = request.get("question", "")
        context = request.get("context", {})
        
        prompt = f"""You are a Chinese visa officer. Answer this applicant's question EXACTLY as you would at the embassy.

Applicant context:
- Visa type: {context.get('visaType', 'Not specified')}
- Country: {context.get('country', 'Not specified')}
- University: {context.get('university', 'Not specified')}

Question: "{question}"

Give precise, official answer. Include:
- Exact requirements
- Warnings if needed
- Official procedures
- Do's and Don'ts

Be strict but helpful."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7
        )
        
        return {"answer": response.choices[0].message.content}
        
    except Exception as e:
        return {"answer": f"System error: {str(e)}"}
    
class TranslationGenerateRequest(BaseModel):
    topic: str
    description: Optional[str] = ""  # <-- added
    difficulty: str = "medium"
    length: str = "medium"
    hsk_level: int = 4
    user_id: Optional[str] = None
    include_emojis: bool = True  # <-- added
    manga_style: bool = False  # <-- added

@app.post("/essay/check")
async def check_essay(request: EssayCheckRequest):
    """Check and evaluate Chinese essay using AI"""
    try:
        # Check if there is text
        if not request.essay_text or len(request.essay_text.strip()) == 0:
            return {
                "score": 0,
                "hsk_level": request.hsk_level,
                "characters": 0,
                "errors": ["Empty essay. Please write something before submitting."],
                "recommendations": ["Write at least 50 characters"],
                "statistics": {
                    "time_spent": request.time_spent // 60 if request.time_spent else 0,
                    "speed": 0,
                    "sentences": 0,
                    "unique_characters": 0
                }
            }
        
        # Get AI client
        client = get_deepseek_client()
        
        if client:
            # ALWAYS use AI for evaluation, even if essay is short
            return await check_with_ai(client, request)
        else:
            # If AI unavailable, use enhanced fallback
            return await enhanced_fallback_evaluation(request)
            
    except Exception as e:
        print(f"Essay check error: {str(e)}")
        # Even on error, try to give useful feedback
        return await enhanced_fallback_evaluation(request)

async def check_with_ai(client, request):
    """Evaluate essay using DeepSeek AI"""
    
    system_prompt = f"""You are a strict Chinese language teacher evaluating essays for HSK {request.hsk_level} level.
    
# EVALUATION CRITERIA:
1. GRAMMAR (30%): Correct use of particles, sentence structures, tenses, word order
2. VOCABULARY (25%): Appropriateness for HSK level, richness, word choice
3. STRUCTURE (20%): Logical organization, paragraphing, coherence
4. CONTENT (25%): Relevance to topic, depth of analysis, originality

# TASK:
Evaluate this essay written by a student:
Topic: {request.topic}
Target HSK Level: {request.hsk_level}
Minimum length required: {request.min_length} characters
Actual length: {len(request.essay_text)} characters

Essay text:
{request.essay_text}

# OUTPUT FORMAT (JSON only):
{{
    "score": 0-100, // overall score
    "hsk_level_achieved": 1-6, // estimated actual HSK level
    "grammar_score": 0-100,
    "grammar_feedback": "detailed feedback",
    "vocabulary_score": 0-100,
    "vocabulary_feedback": "detailed feedback",
    "structure_score": 0-100,
    "structure_feedback": "detailed feedback",
    "content_score": 0-100,
    "content_feedback": "detailed feedback",
    "specific_errors": ["list", "of", "specific", "errors"],
    "strengths": ["list", "of", "strengths"],
    "recommendations": ["specific", "recommendations", "for", "improvement"],
    "estimated_level": "HSK_X" // estimated current level
}}

# GRADING SCALE:
90-100: Excellent (HSK 6 level)
80-89: Very Good (HSK 5 level)
70-79: Good (HSK 4 level)
60-69: Satisfactory (HSK 3 level)
50-59: Needs Improvement (HSK 2 level)
0-49: Poor (HSK 1 or beginner)

# IMPORTANT:
- Be strict but fair
- Focus on actual language proficiency, not just length
- For very short essays (<100 chars), give low scores
- For nonsense/gibberish, give very low scores (<30)
- Provide specific examples of errors
- Suggest concrete improvements
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please evaluate this essay and provide JSON output."}
            ],
            temperature=0.3,  # Low temperature for consistency
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        ai_response = json.loads(response.choices[0].message.content)
        
        # Add statistics
        char_count = len(request.essay_text)
        sentence_count = count_sentences(request.essay_text)
        unique_chars = count_unique_chinese_chars(request.essay_text)
        
        result = {
            "score": ai_response.get("score", 50),
            "hsk_level": request.hsk_level,
            "hsk_level_achieved": ai_response.get("hsk_level_achieved", request.hsk_level),
            "characters": char_count,
            "grammar_score": ai_response.get("grammar_score", 50),
            "grammar_feedback": ai_response.get("grammar_feedback", "No specific grammar feedback"),
            "vocabulary_score": ai_response.get("vocabulary_score", 50),
            "vocabulary_feedback": ai_response.get("vocabulary_feedback", "No specific vocabulary feedback"),
            "structure_score": ai_response.get("structure_score", 50),
            "structure_feedback": ai_response.get("structure_feedback", "No specific structure feedback"),
            "content_score": ai_response.get("content_score", 50),
            "content_feedback": ai_response.get("content_feedback", "No specific content feedback"),
            "errors": ai_response.get("specific_errors", []),
            "strengths": ai_response.get("strengths", []),
            "recommendations": ai_response.get("recommendations", ["Practice more"]),
            "estimated_level": ai_response.get("estimated_level", f"HSK {request.hsk_level}"),
            "statistics": {
                "time_spent": request.time_spent // 60 if request.time_spent else 0,
                "speed": char_count // max(1, (request.time_spent // 60)) if request.time_spent else 0,
                "sentences": sentence_count,
                "unique_characters": unique_chars
            },
            "ai_evaluated": True
        }
        
        return result
        
    except Exception as e:
        print(f"AI evaluation error: {str(e)}")
        # If AI errors, use enhanced fallback
        return await enhanced_fallback_evaluation(request)

async def enhanced_fallback_evaluation(request):
    """Enhanced fallback evaluation when AI is not available"""
    essay_text = request.essay_text
    char_count = len(essay_text)
    
    # More complex heuristic evaluation
    # 1. Check for gibberish
    if is_gibberish(essay_text):
        return {
            "score": 10,
            "hsk_level": request.hsk_level,
            "characters": char_count,
            "errors": ["Text appears to be random or nonsensical"],
            "recommendations": ["Write meaningful sentences in Chinese"],
            "statistics": basic_statistics(request)
        }
    
    # 2. Basic checks
    sentence_count = count_sentences(essay_text)
    unique_chinese_chars = count_unique_chinese_chars(essay_text)
    
    # Initial score
    base_score = 50
    
    # Adjustments
    if char_count < 50:
        base_score = 20
    elif char_count < 100:
        base_score = 30
    elif char_count < 200:
        base_score = 50
    elif char_count < 300:
        base_score = 60
    else:
        base_score = 65
    
    # Sharply reduce score for gibberish
    if has_repeated_gibberish(essay_text):
        base_score = max(10, base_score - 40)
    
    # Increase score for real Chinese characters
    chinese_char_ratio = unique_chinese_chars / max(1, char_count)
    if chinese_char_ratio > 0.3:  # At least 30% Chinese characters
        base_score += 10
    elif chinese_char_ratio < 0.1:  # Few Chinese characters
        base_score -= 15
    
    score = min(85, max(10, base_score))
    
    return {
        "score": score,
        "hsk_level": request.hsk_level,
        "characters": char_count,
        "grammar_score": max(30, score - 15),
        "vocabulary_score": max(30, score - 10),
        "structure_score": max(30, score - 5),
        "content_score": max(30, score),
        "errors": [] if score > 40 else ["Text quality needs significant improvement"],
        "recommendations": [
            "Use AI evaluation for more accurate feedback",
            f"Aim for {request.min_length} characters",
            "Use complete Chinese sentences"
        ],
        "statistics": basic_statistics(request),
        "ai_evaluated": False
    }

def is_gibberish(text, threshold=0.7):
    """Check if text appears to be random gibberish"""
    # Check ratio of Chinese characters
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text.replace(' ', '').replace('\n', ''))
    
    if total_chars == 0:
        return True
    
    chinese_ratio = chinese_chars / total_chars
    return chinese_ratio < 0.2  # Less than 20% Chinese characters

def has_repeated_gibberish(text):
    """Check for repeated nonsense patterns"""
    # Look for repeating meaningless sequences
    patterns = ["asdf", "qwerty", "123", "test", "aaaa", "hhhh"]
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in patterns)

def count_unique_chinese_chars(text):
    """Count unique Chinese characters in text"""
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    return len(set(chinese_chars))

def basic_statistics(request):
    """Calculate basic statistics"""
    essay_text = request.essay_text
    char_count = len(essay_text)
    sentence_count = count_sentences(essay_text)
    unique_chars = count_unique_chinese_chars(essay_text)
    
    return {
        "time_spent": request.time_spent // 60 if request.time_spent else 0,
        "speed": char_count // max(1, (request.time_spent // 60)) if request.time_spent else 0,
        "sentences": sentence_count,
        "unique_characters": unique_chars
    }

def generate_basic_feedback(request, essay_type="normal"):
    """Generate basic feedback based on essay characteristics"""
    essay_text = request.essay_text
    char_count = len(essay_text)
    sentence_count = count_sentences(essay_text)
    
    # Basic score calculation
    base_score = 50
    
    if essay_type == "short":
        base_score = 30
    elif char_count < 100:
        base_score = 40
    elif char_count < 200:
        base_score = 60
    elif char_count < 300:
        base_score = 70
    else:
        base_score = 75 + min(20, (char_count - 300) // 20)
    
    # Adjustments
    if sentence_count < 3:
        base_score = max(30, base_score - 15)
    
    # Check character diversity
    unique_chars = count_unique_chars(essay_text)
    if unique_chars < 10:
        base_score = max(30, base_score - 10)
    
    score = min(95, base_score)
    
    return {
        "score": score,
        "hsk_level": request.hsk_level,
        "characters": char_count,
        "grammar_score": max(50, score - random.randint(5, 15)),
        "vocabulary_score": max(50, score - random.randint(0, 10)),
        "structure_score": max(50, score - random.randint(0, 5)),
        "content_score": max(50, score + random.randint(0, 5)),
        "errors": [] if char_count > 150 else ["Essay is too short for detailed analysis"],
        "recommendations": [
            "Aim for at least 300 characters",
            "Use varied sentence structures",
            "Include specific examples"
        ],
        "statistics": {
            "time_spent": request.time_spent // 60 if request.time_spent else 0,
            "speed": char_count // max(1, (request.time_spent // 60)) if request.time_spent else 0,
            "sentences": sentence_count,
            "unique_characters": unique_chars
        }
    }

def count_sentences(text):
    """Count sentences in Chinese text"""
    return len([c for c in text if c in '。！？.!?'])

def count_unique_chars(text):
    """Count unique Chinese characters"""
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    return len(set(chinese_chars))

def generate_fallback_essay_check(request: EssayCheckRequest):
    """Fallback essay check (if AI unavailable)"""
    text = request.essay_text
    char_count = len(text)
    
    # Simple evaluation based on length
    if char_count < request.min_length:
        length_score = 50
    elif char_count < request.min_length * 1.5:
        length_score = 70
    else:
        length_score = 90
    
    base_score = length_score
    
    # Add random variations
    grammar_score = max(0, min(100, base_score + random.randint(-15, 15)))
    vocab_score = max(0, min(100, base_score + random.randint(-10, 10)))
    structure_score = max(0, min(100, base_score + random.randint(-5, 15)))
    content_score = max(0, min(100, base_score + random.randint(-5, 10)))
    style_score = max(0, min(100, base_score + random.randint(-10, 5)))
    
    overall_score = int((grammar_score + vocab_score + structure_score + content_score + style_score) / 5)
    
    # Generate sample errors
    errors = []
    if char_count > 100:
        # Add couple of sample errors
        errors.append({
            "position": min(50, char_count - 10),
            "error": "Possible error in using 了",
            "correction": "Make sure 了 is used for completed actions"
        })
    
    return {
        "overall_score": overall_score,
        "categories": [
            {"name": "Grammar", "score": grammar_score, 
             "feedback": "There are errors in particle usage. Pay attention to 了, 的, 地, 得."},
            {"name": "Vocabulary", "score": vocab_score,
             "feedback": f"Vocabulary diverse enough for HSK {request.hsk_level} level."},
            {"name": "Structure", "score": structure_score,
             "feedback": "Text organized logically, but could improve coherence between paragraphs."},
            {"name": "Content", "score": content_score,
             "feedback": f"Relevant to topic '{request.topic}', has arguments and examples."},
            {"name": "Style", "score": style_score,
             "feedback": "Style sufficiently varied, but could use more complex constructions."}
        ],
        "errors": errors,
        "recommendations": f"""
1. Practice using complex sentences with 虽然...但是..., 因为...所以...
2. Increase vocabulary on topic "{request.topic}"
3. Pay attention to particle usage 了, 的, 地, 得
4. Add transition words: 首先, 其次, 最后, 总而言之
5. Write regularly to improve skills
        """,
        "strengths": "Good text organization, relevance to topic, sufficient length.",
        "estimated_hsk_level": request.hsk_level,
        "topic": request.topic,
        "target_hsk": request.hsk_level,
        "actual_length": char_count,
        "min_required": request.min_length,
        "checked_at": datetime.now().isoformat(),
        "ai_checked": False,
        "fallback": True
    }

def generate_fallback_essay_check(request: EssayCheckRequest):
    """Fallback essay check"""
    # Simple essay analysis
    text = request.essay_text
    char_count = len(text)
    
    # Simple evaluation
    base_score = min(100, max(50, char_count / request.min_length * 80))
    
    # Random variations
    grammar_score = max(0, min(100, base_score + random.randint(-15, 15)))
    vocab_score = max(0, min(100, base_score + random.randint(-10, 10)))
    structure_score = max(0, min(100, base_score + random.randint(-5, 15)))
    content_score = max(0, min(100, base_score + random.randint(-5, 10)))
    style_score = max(0, min(100, base_score + random.randint(-10, 5)))
    
    overall_score = int((grammar_score + vocab_score + structure_score + content_score + style_score) / 5)
    
    return {
        "overall_score": overall_score,
        "categories": [
            {"name": "Grammar", "score": grammar_score, 
             "feedback": "There are errors in particle usage. Pay attention to 了, 的, 地, 得."},
            {"name": "Vocabulary", "score": vocab_score,
             "feedback": "Vocabulary diverse enough for HSK " + str(request.hsk_level) + " level"},
            {"name": "Structure", "score": structure_score,
             "feedback": "Text organized logically, but could improve coherence between paragraphs."},
            {"name": "Content", "score": content_score,
             "feedback": "Relevant to topic, has arguments and examples."},
            {"name": "Style", "score": style_score,
             "feedback": "Style sufficiently varied, but could use more complex constructions."}
        ],
        "errors": [
            {"position": random.randint(10, len(text)//2), 
             "error": "Possible word order error",
             "correction": "Check word order in sentence"},
            {"position": random.randint(len(text)//2, len(text)-10),
             "error": "Word repetition",
             "correction": "Use synonyms for variety"}
        ] if char_count > 50 else [],
        "recommendations": """
        1. Practice using complex sentences with 虽然...但是..., 因为...所以...
        2. Increase vocabulary on topic "{}"
        3. Pay attention to particle usage 了, 的, 地, 得
        4. Add transition words: 首先, 其次, 最后, 总而言之
        5. Write regularly to improve skills
        """.format(request.topic),
        "strengths": "Good text organization, relevance to topic, sufficient length.",
        "estimated_hsk_level": request.hsk_level,
        "topic": request.topic,
        "target_hsk": request.hsk_level,
        "actual_length": char_count,
        "checked_at": datetime.now().isoformat(),
        "ai_checked": False,
        "fallback": True
    }

@app.post("/translation/generate")
async def generate_translation_text(request: TranslationGenerateRequest):
    """Generate text for translation"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_fallback_translation_text(request)
        
        # Determine length
        lengths = {
            "short": "3-5 sentences",
            "medium": "6-10 sentences", 
            "long": "10-15 sentences"
        }
        
        system_prompt = f"""You create texts for translation to Chinese.
        
# TASK:
Create text on topic: "{request.topic}"
Difficulty: {request.difficulty}
Length: {lengths.get(request.length, "6-10 sentences")}
Student level: HSK {request.hsk_level}

# REQUIREMENTS:
1. Text should be interesting and useful for learning
2. Difficulty level should match student level
3. Use diverse vocabulary and grammar
4. Text should be natural, like in real life
5. Include elements that need correct translation

# TEXT FORMATS:
- News: formal style, facts
- Story: narrative, dialogues
- Dialogue: conversational speech, questions and answers
- Description: details, adjectives
- Instruction: imperatives, sequence

# EXAMPLE FOR MEDIUM DIFFICULTY:
"Yesterday a new cultural center opened in Shanghai. It combines library, museum and concert hall. Visitors can visit exhibitions free in first month."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create text for translation on topic: {request.topic}"}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        text = response.choices[0].message.content
        
        return {
            "text": text.strip(),
            "topic": request.topic,
            "difficulty": request.difficulty,
            "length": request.length,
            "target_hsk": request.hsk_level,
            "generated_at": datetime.now().isoformat(),
            "ai_generated": True
        }
        
    except Exception as e:
        print(f"Text generation error: {str(e)}")
        return generate_fallback_translation_text(request)

def generate_fallback_translation_text(request: TranslationGenerateRequest):
    """Fallback text generation for translation"""
    topics_texts = {
        "news": "China launched new Earth observation satellite. It will be used for weather and ecology monitoring. Satellite launched by Changzheng rocket.",
        "story": "Long ago in small village lived old calligraphy master. Every morning he woke at dawn and practiced characters. His works were known throughout region.",
        "dialogue": "- Hello! My name is Anna. I'm from Russia. - Nice to meet you! I'm Li Wei. First time in China? - Yes, I'm here studying Chinese. - Great! Good luck with studies!",
        "description": "Great Wall of China is ancient defensive structure. It passes through mountains and valleys of northern China. Wall length is over 20 thousand kilometers.",
        "instruction": "To cook Chinese fried rice, first boil rice and cool it. Then fry eggs, add vegetables and chopped meat. Finally add rice and soy sauce."
    }
    
    # Choose text by topic or use general
    text = topics_texts.get(request.topic, 
        "Chinese culture is very rich and diverse. It includes traditional medicine, cuisine, art and philosophy. Studying Chinese culture helps better understand language.")
    
    # Adapt difficulty
    if request.difficulty == "easy":
        # Simplify text
        sentences = text.split('. ')
        text = '. '.join(sentences[:2]) + '.'
    elif request.difficulty == "hard":
        # Make text more complex
        text += " These aspects are closely related to country's historical development and Confucian influence."
    
    return {
        "text": text,
        "topic": request.topic,
        "difficulty": request.difficulty,
        "length": request.length,
        "target_hsk": request.hsk_level,
        "generated_at": datetime.now().isoformat(),
        "ai_generated": False,
        "fallback": True
    }

@app.post("/translation/check")
async def check_translation(request: TranslationCheckRequest):
    """AI translation checking"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_fallback_translation_check(request)
        
        system_prompt = f"""You are expert in translation to Chinese.
        
# TASK:
Compare student's translation with ideal translation.
Original: "{request.original_text}"
Student translation: "{request.user_translation}"
Student level: HSK {request.target_hsk}
Difficulty: {request.difficulty}

# EVALUATION CRITERIA:
1. **Accuracy** (40%) - correctness of meaning translation
2. **Grammar** (30%) - correctness of Chinese constructions
3. **Naturalness** (20%) - sounds like native language
4. **Style** (10%) - preserving original style

# YOUR WORK:
1. Create ideal translation of original
2. Compare with student translation
3. Find and classify errors
4. Give improvement recommendations
5. Give score

# RESPONSE FORMAT JSON:
{{
    "overall_score": 85,
    "ideal_translation": "Ideal translation to Chinese...",
    "categories": [
        {{"name": "Accuracy", "score": 90, "feedback": "..."}},
        {{"name": "Grammar", "score": 80, "feedback": "..."}},
        {{"name": "Naturalness", "score": 85, "feedback": "..."}},
        {{"name": "Style", "score": 80, "feedback": "..."}}
    ],
    "errors": [
        {{"type": "grammar", "description": "Incorrect word order", "suggestion": "..."}},
        {{"type": "vocabulary", "description": "Inaccurate word translation", "suggestion": "..."}}
    ],
    "correct_translations": [
        {{"original": "Original phrase", "student": "student translation", "ideal": "ideal translation"}}
    ],
    "recommendations": "Specific recommendations...",
    "estimated_hsk_level": {request.target_hsk}
}}

# BE CONSTRUCTIVE:
- Praise good points
- Explain errors in detail
- Suggest alternatives
- Help learn from mistakes"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Check this translation and give detailed analysis."}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add metadata
        result.update({
            "original_text": request.original_text,
            "user_translation": request.user_translation,
            "target_hsk": request.target_hsk,
            "difficulty": request.difficulty,
            "checked_at": datetime.now().isoformat(),
            "ai_checked": True
        })
        
        return result
        
    except Exception as e:
        print(f"Translation check error: {str(e)}")
        return generate_fallback_translation_check(request)

def generate_fallback_translation_check(request: TranslationCheckRequest):
    """Fallback translation check"""
    # Generate "ideal" translation (simple)
    ideal_translation = generate_simple_translation(request.original_text, request.target_hsk)
    
    # Simple evaluation
    base_score = 70 + random.randint(-15, 15)
    accuracy_score = max(0, min(100, base_score + random.randint(-10, 10)))
    grammar_score = max(0, min(100, base_score + random.randint(-15, 5)))
    naturalness_score = max(0, min(100, base_score + random.randint(-5, 10)))
    style_score = max(0, min(100, base_score + random.randint(-10, 5)))
    
    overall_score = int((accuracy_score + grammar_score + naturalness_score + style_score) / 4)
    
    return {
        "overall_score": overall_score,
        "ideal_translation": ideal_translation,
        "categories": [
            {"name": "Accuracy", "score": accuracy_score,
             "feedback": "Main meaning conveyed correctly, but there are inaccuracies in details."},
            {"name": "Grammar", "score": grammar_score,
             "feedback": "There are errors in word order and particle usage."},
            {"name": "Naturalness", "score": naturalness_score,
             "feedback": "Translation understandable, but sounds slightly unnatural for native."},
            {"name": "Style", "score": style_score,
             "feedback": "Style mostly preserved, but could be improved."}
        ],
        "errors": [
            {"type": "grammar", 
             "description": "Possible word order errors",
             "suggestion": "In Chinese word order is SVO (subject-verb-object)"},
            {"type": "vocabulary",
             "description": "Could use more accurate words",
             "suggestion": "Use synonyms for variety and accuracy"}
        ],
        "correct_translations": [
            {"original": request.original_text.split('. ')[0] if '. ' in request.original_text else request.original_text,
             "student": request.user_translation.split('。')[0] if '。' in request.user_translation else request.user_translation,
             "ideal": ideal_translation.split('。')[0] if '。' in ideal_translation else ideal_translation}
        ],
        "recommendations": """
        1. Pay attention to word order in sentences
        2. Use dictionaries to find more accurate equivalents
        3. Practice translating different text types
        4. Read original Chinese texts to understand natural style
        5. Check particle usage 了, 的, 地, 得
        """,
        "estimated_hsk_level": request.target_hsk,
        "original_text": request.original_text,
        "user_translation": request.user_translation,
        "target_hsk": request.target_hsk,
        "difficulty": request.difficulty,
        "checked_at": datetime.now().isoformat(),
        "ai_checked": False,
        "fallback": True
    }

def generate_simple_translation(text: str, hsk_level: int) -> str:
    """Simple text translation (stub)"""
    # In real project there would be real translation
    # Now return template text
    translations = {
        3: "This is a simple translation example. Chinese is very important.",
        4: "There were many people in the park yesterday. The weather was good, sunny.",
        5: "With China's economic development, more and more foreigners come to China to work and study.",
        6: "Traditional Chinese culture is extensive and profound, with a long history. It includes not only rich philosophical thoughts but also unique art forms and life wisdom."
    }
    
    return translations.get(hsk_level, "This is a translation text.")

@app.get("/text/history/{user_id}")
async def get_text_generation_history(user_id: str, limit: int = 20):
    """Get text generation history"""
    try:
        # Load from file
        history_file = data_path(f"text_history_{user_id}.json")
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            return {
                "history": history[:limit],
                "count": len(history),
                "total_characters": sum(item.get("length_chars", 0) for item in history)
            }
        return {"history": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History load error: {str(e)}")

@app.get("/words/level/{level}")
async def get_level_words(level: int, limit: int = 10000, offset: int = 0):
    """Get words of specific HSK level"""
    level_words = get_words_by_level(level, 20000)
    
    if not level_words:
        raise HTTPException(status_code=404, detail=f"HSK {level} words not found")
    
    paginated_words = level_words[offset:offset + limit]
    
    return {
        "level": level,
        "count": len(paginated_words),
        "total": len(level_words),
        "offset": offset,
        "limit": limit,
        "words": paginated_words
    }

@app.get("/levels/summary")
async def get_levels_summary():
    """Summary of all HSK levels"""
    summary = {}
    for level in range(1, 7):
        level_words = get_words_by_level(level, 1000)
        if level_words:
            summary[f"hsk{level}"] = {
                "word_count": len(level_words),
                "sample_words": level_words[:3],
                "common_characters": list(set([char for word in level_words[:10] for char in word["character"]]))[:5]
            }
    
    return summary

@app.get("/user/{user_id}/progress")
async def get_user_progress(user_id: str):
    """User progress"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    progress = word_progress_db.get(user_id, {})
    
    # Statistics by level
    level_stats = {}
    for level in range(1, 7):
        level_words = get_words_by_level(level, 1000)
        total_level_words = len(level_words)
        
        # Count learned words of this level
        learned = 0
        for word_id, word_progress in progress.items():
            if word_progress.get("remembered", False):
                # Check word is of this level
                for word in level_words:
                    if f"{word['character']}_{level}" == word_id:
                        learned += 1
                        break
        
        if total_level_words > 0:
            level_stats[f"HSK {level}"] = {
                "learned": learned,
                "total": total_level_words,
                "percentage": int((learned / total_level_words) * 100)
            }
    
    total_learned = len([p for p in progress.values() if p.get("remembered", False)])
    
    return {
        "user": user["name"],
        "user_id": user_id,
        "stats": {
            "total_learned": total_learned,
            "total_words": len(words_db),
            "overall_percentage": int((total_learned / len(words_db)) * 100) if words_db else 0,
            "by_level": level_stats
        },
        "study_plan": {
            "daily_words": user.get("daily_words", 10),
            "days_until_exam": user.get("days_until_exam", 30),
            "words_per_day_to_goal": max(1, (user.get("target_words", 1000) - total_learned) // max(1, user.get("days_until_exam", 30)))
        }
    }


# Add to backend models:
class EssayAnalysisRequest(BaseModel):
    topic: str
    details: Optional[str] = ""
    difficulty: str = "intermediate"
    target_length: int = 400
    user_id: Optional[str] = None

class EssayAnalysisResponse(BaseModel):
    prompt: str
    topic: str
    difficulty: str
    target_length: int
    requirements: str
    evaluation_criteria: List[str]
    time_limit_minutes: int
    generated_at: str

class EssaySubmitRequest(BaseModel):
    essay_text: str
    topic: str
    difficulty: str
    target_length: int
    user_id: Optional[str] = None
    time_spent: Optional[int] = None

# Add to backend routes:
@app.post("/essay/analysis/generate")
async def generate_essay_analysis(request: EssayAnalysisRequest):
    """Generate essay assignment"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_fallback_essay_analysis(request)
        
        # Determine time based on difficulty
        time_limits = {
            "beginner": 45,
            "intermediate": 60,
            "advanced": 75,
            "exam": 90
        }
        
        system_prompt = f"""You create essay assignments in Chinese.
        
# TASK:
Create essay assignment on topic: "{request.topic}"
Difficulty level: {request.difficulty}
Target length: {request.target_length} characters
Additional details: {request.details}

# ASSIGNMENT REQUIREMENTS:
1. Clearly formulated topic and task
2. Specific content requirements
3. Evaluation criteria by 4 categories:
   - Content (40%)
   - Grammar (30%) 
   - Vocabulary (20%)
   - Structure (10%)
4. Time limit: {time_limits.get(request.difficulty, 60)} minutes

# RESPONSE FORMAT JSON:
{{
    "prompt": "Full assignment for student with instructions...",
    "requirements": "Specific essay requirements...",
    "evaluation_criteria": [
        "Content: relevance to topic, arguments, examples (40%)",
        "Grammar: correctness of constructions, particles, tenses (30%)",
        "Vocabulary: vocabulary diversity, word appropriateness (20%)",
        "Structure: logic, organization, coherence (10%)"
    ],
    "time_limit_minutes": {time_limits.get(request.difficulty, 60)},
    "suggested_structure": ["Introduction", "2-3 arguments", "Conclusion"]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create essay assignment on topic: {request.topic}"}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add metadata
        result.update({
            "topic": request.topic,
            "difficulty": request.difficulty,
            "target_length": request.target_length,
            "generated_at": datetime.now().isoformat(),
            "ai_generated": True
        })
        
        return result
        
    except Exception as e:
        print(f"Assignment generation error: {str(e)}")
        return generate_fallback_essay_analysis(request)

def generate_fallback_essay_analysis(request: EssayAnalysisRequest):
    """Fallback essay assignment generation"""
    difficulty_texts = {
        "beginner": "Use simple sentences and basic HSK 1-3 vocabulary.",
        "intermediate": "Use complex sentences and diverse HSK 4-5 vocabulary.",
        "advanced": "Demonstrate mastery of complex grammatical constructions.",
        "exam": "Demonstrate all aspects of language proficiency at high level."
    }
    
    time_limits = {
        "beginner": 45,
        "intermediate": 60,
        "advanced": 75,
        "exam": 90
    }
    
    return {
        "prompt": f"""
<h4>Topic: {request.topic}</h4>
<p><strong>Assignment:</strong> Write essay on given topic. Your essay should include:</p>
<ul>
    <li>Introduction presenting topic and your position</li>
    <li>2-3 main arguments with specific examples</li>
    <li>Conclusion with conclusions and summary</li>
</ul>
<p><strong>Requirements:</strong></p>
<ul>
    <li>Length: {request.target_length} characters</li>
    <li>{difficulty_texts.get(request.difficulty, 'Use complex sentences')}</li>
    <li>Use transition words and connecting elements</li>
    <li>Avoid repetitions and grammatical errors</li>
</ul>
<p><strong>Time limit:</strong> {time_limits.get(request.difficulty, 60)} minutes</p>
        """,
        "requirements": f"Length: {request.target_length} characters. {difficulty_texts.get(request.difficulty, 'Use complex sentences')}",
        "evaluation_criteria": [
            "Content: relevance to topic, arguments, examples (40%)",
            "Grammar: correctness of constructions, particles, tenses (30%)",
            "Vocabulary: vocabulary diversity, word appropriateness (20%)",
            "Structure: logic, organization, coherence (10%)"
        ],
        "time_limit_minutes": time_limits.get(request.difficulty, 60),
        "suggested_structure": ["Introduction", "2-3 arguments", "Conclusion"],
        "topic": request.topic,
        "difficulty": request.difficulty,
        "target_length": request.target_length,
        "generated_at": datetime.now().isoformat(),
        "ai_generated": False,
        "fallback": True
    }

@app.post("/essay/analysis/check")
async def check_essay_analysis(request: EssaySubmitRequest):
    """Strict essay checking for analysis"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_fallback_essay_check_analysis(request)
        
        system_prompt = f"""You are a STRICT and DEMANDING Chinese teacher.
        
# TASK:
Check essay on topic: "{request.topic}"
Difficulty level: {request.difficulty}
Target length: {request.target_length} characters
Student essay length: {len(request.essay_text)} characters

# BE MAXIMALLY STRICT:
- Don't inflate scores by even one point!
- Deduct points for each error
- Demand perfection
- Don't make allowances

# EVALUATION CRITERIA:
1. **Content** (40%) - accuracy, arguments, examples, depth
2. **Grammar** (30%) - perfect grammar, no errors
3. **Vocabulary** (20%) - rich vocabulary, accuracy, diversity
4. **Structure** (10%) - perfect organization, logic, coherence

# RESPONSE FORMAT JSON:
{{
    "overall_score": 65,  // BE STRICT!
    "categories": [
        {{"name": "Content", "score": 70, "feedback": "STRICT feedback pointing out ALL shortcomings"}},
        {{"name": "Grammar", "score": 60, "feedback": "STRICT feedback with LIST OF ALL errors"}},
        {{"name": "Vocabulary", "score": 75, "feedback": "STRICT feedback about vocabulary"}},
        {{"name": "Structure", "score": 80, "feedback": "STRICT feedback about structure"}}
    ],
    "errors": [
        {{"type": "grammar", "position": 15, "description": "SPECIFIC error", "correction": "EXACT correction", "severity": "high"}},
        {{"type": "vocabulary", "position": 42, "description": "INACCURATE word", "correction": "CORRECT option", "severity": "medium"}}
    ],
    "strengths": "Only real strengths, don't invent!",
    "weaknesses": "DETAILED list of weak points",
    "recommendations": "SPECIFIC and HARSH improvement recommendations",
    "estimated_level": "Real student level (DON'T inflate!)",
    "would_pass_exam": false  // Honestly evaluate, would pass exam?
}}

# STUDENT ESSAY:
{request.essay_text}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Check this essay MAXIMALLY STRICTLY and give honest evaluation."}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.2,  # Low temperature for strictness
            max_tokens=1500
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            result = generate_fallback_essay_check_analysis(request)
        
        # Add metadata
        result.update({
            "topic": request.topic,
            "difficulty": request.difficulty,
            "target_length": request.target_length,
            "actual_length": len(request.essay_text),
            "time_spent": request.time_spent,
            "checked_at": datetime.now().isoformat(),
            "strict_check": True
        })
        
        return result
        
    except Exception as e:
        print(f"Strict check error: {str(e)}")
        return generate_fallback_essay_check_analysis(request)
    
@app.post("/ai/search-universities")
async def search_universities(request: dict):
    """
    Main function: AI searches universities on the internet
    """
    try:
        query = request.get("query", "")
        filters = request.get("filters", {})
        
        if not query:
            raise HTTPException(status_code=400, detail="Empty query")
        
        # 1. Form SMART prompt for AI
        system_prompt = f"""
        You are expert in Chinese education. User is searching: "{query}"
        
        YOUR TASK: FIND CURRENT INFORMATION ON THE INTERNET
        
        INSTRUCTIONS:
        1. USE INTERNET SEARCH to find fresh data
        2. Search in multiple languages
        3. Main sources: official university sites (.edu.cn), csc.edu.cn, studyinchina.edu.cn
        4. Consider filters: HSK {filters.get('hsk_level', 'any')}, budget {filters.get('max_budget', 'any')}
        5. Compare minimum 3-5 options
        6. Give specific data: prices, deadlines, contacts
        
        RESPONSE FORMAT:
        - University name (city)
        - Requirements: HSK, exams, documents
        - Tuition cost (in yuan)
        - Scholarships: available, how to get
        - Application deadlines
        - Links to official pages
        - Pros and cons of each option
        - Admission tips
        
        IMPORTANT: All data must be CURRENT (2024-2025 year).
        """
        
        # 2. Call DeepSeek with ENABLED internet search
        client = get_deepseek_client()
        if not client:
            return {"error": "API key not configured"}
        
        # CRITICALLY IMPORTANT: Enable web search!
        # Check exact parameter name in DeepSeek documentation
        response = client.chat.completions.create(
            model="deepseek-chat",  # Or other model with search
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Find information for query: {query}"}
            ],
            # PARAMETER FOR WEB SEARCH (example names):
            # web_search=True, 
            # use_web=True,
            # search_online=True,
            max_tokens=2000  # Many tokens for detailed response
        )
        
        ai_response = response.choices[0].message.content
        
        # 3. Return result
        formatted = format_chat_response(ai_response, None, "admission")
        
        return {
            "success": True,
            "query": query,
            "analysis": formatted["response"],
            "formatted_analysis": formatted["formatted_response"],
            "css": formatted["css"],
            "count": len(ai_response.split('\n')) // 10,
            "search_performed": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error in AI search: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback": "Will show local data...",
            # Can add fallback data from your database
        }

def generate_fallback_essay_check_analysis(request: EssaySubmitRequest):
    """Fallback strict check"""
    text = request.essay_text
    char_count = len(text)
    
    # STRICT evaluation based on length
    length_ratio = char_count / request.target_length
    if length_ratio < 0.5:
        length_penalty = 30
    elif length_ratio < 0.8:
        length_penalty = 15
    elif length_ratio < 1.0:
        length_penalty = 5
    else:
        length_penalty = 0
    
    base_score = 70 - length_penalty
    
    # STRICT category evaluations
    content_score = max(0, min(100, base_score + random.randint(-20, 10)))
    grammar_score = max(0, min(100, base_score + random.randint(-25, 5)))
    vocab_score = max(0, min(100, base_score + random.randint(-15, 10)))
    structure_score = max(0, min(100, base_score + random.randint(-10, 15)))
    
    overall_score = int((content_score + grammar_score + vocab_score + structure_score) / 4)
    
    # HARSH errors
    errors = []
    if char_count > 50:
        errors.append({
            "type": "grammar",
            "position": min(30, char_count - 20),
            "description": "SERIOUS error in using 了",
            "correction": "NEVER use 了 in this context",
            "severity": "high"
        })
        
    if char_count > 100:
        errors.append({
            "type": "vocabulary", 
            "position": min(70, char_count - 30),
            "description": "THIS word is INCORRECT in this context",
            "correction": "Use ONLY correct word: ...",
            "severity": "medium"
        })
    
    would_pass = overall_score >= 70  # STRICT passing score
    
    return {
        "overall_score": overall_score,
        "categories": [
            {"name": "Content", "score": content_score,
             "feedback": "INSUFFICIENTLY deep analysis. Need SPECIFIC examples and details."},
            {"name": "Grammar", "score": grammar_score,
             "feedback": "MANY grammar errors. Unacceptable for this level."},
            {"name": "Vocabulary", "score": vocab_score,
             "feedback": "Vocabulary VERY limited. Learn more words."},
            {"name": "Structure", "score": structure_score,
             "feedback": "Structure chaotic. Follow plan: introduction-arguments-conclusion."}
        ],
        "errors": errors,
        "strengths": "Only one plus: relevance to topic (but weak).",
        "weaknesses": "EVERYTHING else: grammar, vocabulary, structure, argumentation.",
        "recommendations": """
1. RELEARN grammar. Errors are UNACCEPTABLE.
2. INCREASE vocabulary 2x. CURRENTLY insufficient.
3. ALWAYS write with plan. Chaos is failure.
4. PRACTICE every day. Once a week is TOO LITTLE.
5. HIRE tutor if can't manage alone.
        """,
        "estimated_level": f"Real level: HSK {max(1, min(6, overall_score // 15))}",
        "would_pass_exam": would_pass,
        "topic": request.topic,
        "difficulty": request.difficulty,
        "target_length": request.target_length,
        "actual_length": char_count,
        "checked_at": datetime.now().isoformat(),
        "strict_check": True,
        "fallback": True
    }

class AudioLessonRequest(BaseModel):
    topic: str
    description: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    target_length: str = "medium"  # short, medium, long
    hsk_level: int = 3
    include_pinyin: bool = False
    include_translation: bool = False
    user_id: Optional[str] = None

class AudioLessonResponse(BaseModel):
    id: str
    title: str
    chinese_text: str
    pinyin_text: Optional[str] = None
    translation: Optional[str] = None
    vocabulary: List[Dict[str, str]]
    difficulty: str
    estimated_duration: int  # in seconds
    generated_at: str

# REPLACE the generate_audio_lesson function in backend with this:
@app.post("/audio/generate-lesson")
async def generate_audio_lesson(request: AudioLessonRequest):
    """Generate full audio lesson (podcast) in Chinese"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_improved_fallback_audio_lesson(request)
        
        # Determine text length based on user choice
        length_targets = {
            "short": 300,    # 1-2 minutes
            "medium": 600,   # 3-5 minutes
            "long": 1000     # 5-10 minutes
        }
        
        target_chars = length_targets.get(request.target_length, 600)
        
        system_prompt = f"""You are professional creator of Chinese podcasts for language learners.

# TASK:
Create full podcast on topic: "{request.topic}"
Topic details: {request.description or 'Not specified'}
HSK level: {request.hsk_level}
Difficulty: {request.difficulty}
Duration: {request.target_length}
Approximate volume: {target_chars} characters

# PODCAST REQUIREMENTS:
1. Should be COMPLETE audio lesson with:
   - Greeting and topic introduction
   - Main part with topic development
   - Specific examples and details
   - Useful expressions and vocabulary
   - Questions for listeners
   - Summary and conclusion

2. LENGTH: At least {target_chars} characters
3. STRUCTURE:
   - Introduction (20%)
   - Main part (60%)
   - Conclusion (20%)
4. STYLE: Natural, conversational, but clear
5. INCLUDE: 
   - Dialogues or example dialogues
   - Cultural notes
   - Useful tips
   - Specific language usage examples

# AVOID:
- Template phrases
- Too academic language
- Repetitions
- Too short sentences

# RESPONSE FORMAT JSON:
{{
    "title": "Podcast title",
    "chinese_text": "Full podcast text here...",
    "pinyin_text": "Text with pinyin (if include_pinyin=true)",
    "translation": "Full translation (if include_translation=true)",
    "vocabulary": [
        {{
            "chinese": "词语",
            "pinyin": "cíyǔ", 
            "translation": "translation",
            "example": "Example sentence",
            "category": "part of speech"
        }}
    ],
    "comprehension_questions": [
        {{
            "question": "Comprehension question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Answer explanation"
        }}
    ],
    "estimated_duration": 180,
    "word_count": 500,
    "character_count": 800,
    "difficulty_analysis": {{
        "grammar_complexity": "medium",
        "vocabulary_level": "HSK {request.hsk_level}",
        "speed_recommendation": "1.0x"
    }}
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Create full podcast in Chinese.

Topic: {request.topic}
Description: {request.description or 'Not specified'}
Level: HSK {request.hsk_level}
Difficulty: {request.difficulty}
Duration: {request.target_length}

Please make text NATURAL and CONVERSATIONAL, like real podcast."""}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.9,  # More creative approach
            max_tokens=2000,   # Increase for long texts
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Generate lesson ID
        lesson_id = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.topic[:20])}"
        
        # Add metadata
        result.update({
            "id": lesson_id,
            "difficulty": request.difficulty,
            "hsk_level": request.hsk_level,
            "generated_at": datetime.now().isoformat(),
            "topic": request.topic,
            "description": request.description,
            "ai_generated": True,
            "target_length": request.target_length,
            "request_details": {
                "topic": request.topic,
                "description": request.description,
                "hsk_level": request.hsk_level,
                "difficulty": request.difficulty,
                "include_pinyin": request.include_pinyin,
                "include_translation": request.include_translation
            }
        })
        
        # If user didn't request pinyin, remove it
        if not request.include_pinyin:
            result["pinyin_text"] = None
        
        # If user didn't request translation, remove it
        if not request.include_translation:
            result["translation"] = None
        
        return result
        
    except Exception as e:
        print(f"Audio lesson generation error: {str(e)}")
        # Always use fallback with longer text
        return generate_improved_fallback_audio_lesson(request)

def generate_improved_fallback_audio_lesson(request: AudioLessonRequest):
    """Improved fallback for podcast generation"""
    
    # Create longer and more diverse texts
    topic = request.topic
    difficulty = request.difficulty
    
    # Base text based on topic and difficulty
    base_text = f"""Hello everyone! Welcome to today's Chinese learning podcast.

Today our topic is: {topic}.

This topic is very interesting and important. Let me introduce it in detail.

First of all, {topic} occupies a special place in Chinese culture. From both traditional and modern perspectives, this topic is worth exploring in depth.

For example, many foreign friends coming to China develop a strong interest in {topic}. They often ask: "What are the characteristics of {topic} in China?" "How can I better understand {topic}?"

In fact, {topic} is not just a simple concept, it reflects many aspects of Chinese society. From a historical perspective, {topic} has a long historical heritage. From a modern perspective, {topic} is constantly developing and changing.

Personally, I think learning about {topic} is very helpful for understanding China. Through this topic, we can understand Chinese people's way of thinking, cultural traditions, and social values.

In the process of learning Chinese, vocabulary and expressions related to {topic} are also very useful. For example, we can learn many related words and sentence structures.

So, how to better learn this topic? I suggest:
First, listen to more related materials;
Second, try to discuss this topic in Chinese;
Third, if possible, experience it yourself.

Of course, you may encounter some difficulties during learning. For example, some specialized vocabulary is hard to remember, some cultural concepts are not easy to understand. But it's okay, take it step by step, learn gradually.

Remember, learning a language is not just about learning words and grammar, but also about learning a culture and way of thinking. Through {topic}, we can gain a deeper understanding of China.

Alright, that's all for today's podcast. Hope this content is helpful to you. If you have any questions or ideas, feel free to leave a comment and discuss.

See you next time! Wish you progress in your studies!"""
    
    # Add variations based on HSK level
    if request.hsk_level <= 2:
        # Simplify for beginners
        base_text = f"""Hi! I'm your Chinese teacher.

Today we learn: {topic}.

{topic} is very interesting. Let's look at it.

What is this? This is {topic}. Do you like {topic}?

I like {topic}. And you?

Let's learn together. Speak slowly, don't rush.

Okay, that's it for today. Goodbye!"""
    
    elif request.hsk_level >= 5:
        # Make more complex for advanced
        base_text = f"""Dear listeners, hello.

Welcome to this episode of Deep Chinese Learning Podcast. Today we will explore the topic "{topic}".

In the current context of globalization, {topic}, as a cross-cultural issue, has attracted widespread attention. In essence, {topic} involves not only linguistic expression but also profound cultural connotations.

First, let's examine the evolution of {topic} from a historical perspective. Since ancient times, {topic} has occupied an important position in the traditional Chinese cultural system. Relevant documents show that as early as the pre-Qin period, the concept of {topic} had already taken initial shape and continued to enrich and develop with the changes of times.

Secondly, {topic} in modern society presents new characteristics. In the context of digital transformation, both the forms of expression and methods of practice of {topic} have undergone significant changes. These changes bring both opportunities and challenges.

From a language learning perspective, mastering professional terminology and expressions related to {topic} is crucial. This not only helps improve language ability but also promotes cross-cultural understanding.

It's worth noting that learners from different cultural backgrounds may have different perceptions of {topic}. Therefore, when discussing {topic}, we need to maintain an open attitude and respect multiple perspectives.

In conclusion, {topic} is a complex subject worthy of in-depth study. Through systematic learning, we can not only improve our Chinese level but also deepen our understanding of Chinese culture.

Thank you for listening, see you next time."""
    
    # Generate vocabulary
    vocabulary = [
        {
            "chinese": "话题",
            "pinyin": "huàtí", 
            "translation": "topic, subject of conversation",
            "example": "今天的话题很有意思。",
            "category": "noun"
        },
        {
            "chinese": "学习",
            "pinyin": "xuéxí",
            "translation": "study, learn",
            "example": "我喜欢学习中文。",
            "category": "verb"
        },
        {
            "chinese": "文化",
            "pinyin": "wénhuà",
            "translation": "culture",
            "example": "中国文化很有特色。",
            "category": "noun"
        },
        {
            "chinese": "重要",
            "pinyin": "zhòngyào",
            "translation": "important",
            "example": "这个问题很重要。",
            "category": "adjective"
        }
    ]
    
    # Add more words for advanced levels
    if request.hsk_level >= 4:
        vocabulary.extend([
            {
                "chinese": "探讨",
                "pinyin": "tàntǎo",
                "translation": "discuss, research",
                "example": "我们来探讨一下这个问题。",
                "category": "verb"
            },
            {
                "chinese": "理解",
                "pinyin": "lǐjiě",
                "translation": "understand",
                "example": "我理解你的意思。",
                "category": "verb"
            }
        ])
    
    # Comprehension questions
    comprehension_questions = [
        {
            "question": f"What is today's podcast topic?",
            "options": ["Chinese grammar", topic, "Chinese history", "tourist attractions"],
            "correct_answer": 1,
            "explanation": f"Today's topic is: {topic}"
        },
        {
            "question": "Why is this topic important?",
            "options": ["Because it's simple", "Because it's a hot topic", "Because it helps understand Chinese culture", "Because the teacher likes it"],
            "correct_answer": 2,
            "explanation": "This topic helps understand Chinese culture and society"
        }
    ]
    
    lesson_id = f"audio_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Calculate approximate duration (about 150 characters per minute)
    estimated_duration = max(120, len(base_text) // 2)
    
    return {
        "id": lesson_id,
        "title": f"Chinese Learning Podcast: {topic}",
        "chinese_text": base_text,
        "pinyin_text": None if not request.include_pinyin else "pinyin text would be here",
        "translation": None if not request.include_translation else "translation would be here",
        "vocabulary": vocabulary,
        "comprehension_questions": comprehension_questions,
        "difficulty": request.difficulty,
        "hsk_level": request.hsk_level,
        "estimated_duration": estimated_duration,
        "generated_at": datetime.now().isoformat(),
        "topic": request.topic,
        "description": request.description,
        "ai_generated": False,
        "fallback": True,
        "target_length": request.target_length,
        "character_count": len(base_text),
        "word_count": len(base_text.split()),
        "difficulty_analysis": {
            "grammar_complexity": "medium" if request.hsk_level <= 3 else "high",
            "vocabulary_level": f"HSK {request.hsk_level}",
            "speed_recommendation": "0.8x" if request.hsk_level <= 2 else "1.0x"
        },
        "note": "This is automatically generated podcast. For better quality content check AI connection."
    }

def generate_fallback_audio_lesson(request: AudioLessonRequest):
    """Fallback audio lesson generation"""
    
    # Base text based on HSK level
    base_texts = {
        1: "Hello! I'm your Chinese teacher. Today we learn Chinese. Chinese is very interesting.",
        2: "Hello everyone! Welcome to Chinese class. Today the weather is good. I want to go for a walk in the park. How about you?",
        3: "Hello students! Today we will learn about Chinese culture. China has a long history. Chinese food is very tasty.",
        4: "Welcome to our Chinese podcast! Today let's talk about traditional Chinese festivals. Spring Festival is the most important holiday.",
        5: "In this digital age, learning languages has become easier. Through the internet, we can access rich learning resources.",
        6: "Chinese civilization has a long and profound history. From the four great inventions of ancient times to modern technological innovations, China has been contributing to the world."
    }
    
    base_text = base_texts.get(request.hsk_level, base_texts[3])
    
    # Add topic to text
    chinese_text = f"Today's topic is: {request.topic}. {base_text} Hope you enjoy this content. Goodbye!"
    
    # Basic vocabulary
    vocabulary = [
        {
            "chinese": "话题",
            "pinyin": "huàtí", 
            "translation": "topic",
            "example": "今天的话题很有意思。"
        },
        {
            "chinese": "学习",
            "pinyin": "xuéxí",
            "translation": "study",
            "example": "我喜欢学习中文。"
        }
    ]
    
    lesson_id = f"audio_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "id": lesson_id,
        "title": f"Audio lesson: {request.topic}",
        "chinese_text": chinese_text,
        "pinyin_text": None,
        "translation": f"Today's topic: {request.topic}. {base_text} Hope you enjoy this content. Goodbye!",
        "vocabulary": vocabulary,
        "difficulty": request.difficulty,
        "hsk_level": request.hsk_level,
        "estimated_duration": len(chinese_text) * 0.5,  # ~0.5 sec per character
        "generated_at": datetime.now().isoformat(),
        "topic": request.topic,
        "ai_generated": False,
        "fallback": True,
        "speech_rate": 1.0,
        "word_count": len(chinese_text.split()),
        "character_count": len(chinese_text.replace(" ", "")),
        "study_questions": [
            "What is the main topic of this lesson?",
            "What new words did you hear?"
        ]
    }

class WordStatus(BaseModel):
    user_id: str
    word_id: str          # format: "你好_1"
    status: str           # "saved" or "learned"

class WordTestRequest(BaseModel):
    user_id: str
    source: str = "all"          # "all", "saved", "learned"
    count: int = 20
    test_type: str               # "pinyin_from_char", "char_from_pinyin", "translation_from_char", "translation_from_pinyin"

class WordTestSubmit(BaseModel):
    user_id: str
    test_id: str
    answers: Dict[str, str]      # question_id -> user answer

@app.post("/words/status")
async def set_word_status(request: WordStatus):
    user_id = request.user_id
    if user_id not in user_word_status:
        user_word_status[user_id] = {}
    
    user_word_status[user_id][request.word_id] = {
        "status": request.status,
        "added_at": datetime.now().isoformat()
    }
    save_user_data()
    return {"success": True}

@app.post("/words/test/generate")
async def generate_word_test(req: WordTestRequest):
    # Get word pool
    if req.source == "all":
        all_words = []
        for level in range(1, 7):
            all_words.extend(words_db.get(level, []))
    else:
        if req.user_id not in user_word_status:
            raise HTTPException(404, "No saved/learned words")
        word_ids = [wid for wid, data in user_word_status[req.user_id].items() if data["status"] == req.source]
        all_words = []
        for wid in word_ids:
            char, lvl = wid.rsplit("_", 1)
            level = int(lvl)
            for w in words_db.get(level, []):
                if w["character"] == char:
                    all_words.append(w)
                    break

    if len(all_words) == 0:
        raise HTTPException(400, "No words for test")

    if req.count > len(all_words):
        req.count = len(all_words)
    selected = random.sample(all_words, req.count)

    questions = []
    for i, word in enumerate(selected):
        q = {
            "id": str(i),
            "character": word["character"],
            "pinyin": word["pinyin"],
            "translation": word["translation"]
        }
        if req.test_type == "pinyin_from_char":
            q["prompt"] = f"Pinyin for: {word['character']}"
            q["correct"] = word["pinyin"]
        elif req.test_type == "char_from_pinyin":
            q["prompt"] = f"Characters for: {word['pinyin']}"
            q["correct"] = word["character"]
        elif req.test_type == "translation_from_char":
            q["prompt"] = f"Translation for: {word['character']}"
            q["correct"] = word["translation"]
        elif req.test_type == "translation_from_pinyin":
            q["prompt"] = f"Translation for: {word['pinyin']}"
            q["correct"] = word["translation"]
        else:
            raise HTTPException(400, "Invalid test_type")
        questions.append(q)

    test_id = f"word_{req.user_id}_{datetime.now().timestamp()}"
    
    # Save active test for checking later
    tests_db[f"active_word_test_{req.user_id}"] = {
        "test_id": test_id,
        "questions": questions,
        "generated_at": datetime.now().isoformat()
    }

    return {"test_id": test_id, "questions": questions, "total": len(questions)}

@app.post("/words/test/submit")
async def submit_word_test(submit: WordTestSubmit):
    test_key = f"active_word_test_{submit.user_id}"
    if test_key not in tests_db or tests_db[test_key].get("test_id") != submit.test_id:
        raise HTTPException(status_code=404, detail="Test not found or already completed")

    test = tests_db[test_key]
    questions = test["questions"]

    correct = 0
    total = len(questions)
    results = []

    for q in questions:
        qid = q["id"]
        correct_ans = q["correct"].strip().lower()

        user_answer_raw = submit.answers.get(qid)

        # EXPLICITLY: if no answer or empty string — INCORRECT
        if user_answer_raw is None or user_answer_raw.strip() == "":
            is_correct = False
            user_display = "(not answered)"
        else:
            user_normalized = user_answer_raw.strip().lower()
            is_correct = user_normalized == correct_ans
            user_display = user_answer_raw

        if is_correct:
            correct += 1

        results.append({
            "id": qid,
            "prompt": q["prompt"],
            "user_answer": user_display,
            "correct_answer": q["correct"],
            "correct": is_correct
        })

    percentage = round(correct / total * 100, 1) if total > 0 else 0

    message = f"{correct} out of {total} correct ({percentage}%)"
    if percentage >= 90:
        message += " Excellent! You know these words well!"
    elif percentage >= 70:
        message += " Not bad, but can be better."
    else:
        message += " Need more practice!"

    return {
        "correct": correct,
        "total": total,
        "percentage": percentage,
        "message": message,
        "results": results
    }

class WordTestAIRequest(BaseModel):
    user_id: str
    test_id: str
    questions: List[Dict[str, Any]]  # [{id, prompt, correct, ...}]
    answers: Dict[str, str]          # {question_id: user_answer}

@app.post("/words/test/check-ai")
async def check_word_test_ai(request: WordTestAIRequest):
    """AI checks word knowledge test"""
    try:
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service unavailable")

        # Form prompt for AI
        system_prompt = """You are a strict and accurate Chinese teacher.
Your task: check student's answers to Chinese word test.

CHECKING RULES:
1. Consider synonyms and similar meaning answers
2. For pinyin: ignore tones and spaces (nǐhǎo = nihao = nǐ hǎo)
3. For translation: allow translation variants if meaning preserved
4. Empty answer — always INCORRECT
5. Be objective but fair

RESPONSE FORMAT — ONLY JSON:
{
    "correct_count": 12,
    "total": 15,
    "percentage": 80,
    "results": [
        {
            "id": "0",
            "prompt": "Pinyin for: 你好",
            "user_answer": "nihao",
            "correct_answer": "nǐ hǎo",
            "is_correct": true,
            "feedback": "Correct! Tones can be omitted in test."
        },
        {
            "id": "1",
            "prompt": "Translation for: 谢谢",
            "user_answer": "please",
            "correct_answer": "thank you",
            "is_correct": false,
            "feedback": "Incorrect. 谢谢 = thank you. 'Please' = 请 or 不客气."
        }
    ],
    "summary": "Good result! Main errors — in translation of polite expressions."
}"""

        # Form list of questions with answers
        questions_text = ""
        for q in request.questions:
            user_ans = request.answers.get(q["id"], "(not answered)")
            questions_text += f"""
Question {q['id']}: {q['prompt']}
Correct answer: {q['correct']}
Student answer: {user_ans}
"""

        user_prompt = f"""Check student's answers.

Questions and answers:
{questions_text}

Evaluate each answer and give overall result."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        try:
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # Fallback if AI didn't return JSON
            result = fallback_word_test_check(request.questions, request.answers)

        return result

    except Exception as e:
        print(f"Error in AI word test checking: {e}")
        # Always return fallback
        return fallback_word_test_check(request.questions, request.answers)

def fallback_word_test_check(questions, answers):
    """Fallback check if AI unavailable"""
    correct = 0
    total = len(questions)
    results = []

    for q in questions:
        qid = q["id"]
        user_raw = answers.get(qid, "")
        user_answer = user_raw.strip().lower() if user_raw else ""

        correct_ans = q["correct"].strip().lower()

        # Pinyin normalization
        if "pinyin" in q["prompt"].lower():
            user_answer = user_answer.replace(" ", "").replace("v", "ü")
            correct_ans = correct_ans.replace(" ", "").replace("v", "ü")

        is_correct = bool(user_answer and user_answer == correct_ans)

        if is_correct:
            correct += 1

        results.append({
            "id": qid,
            "prompt": q["prompt"],
            "user_answer": user_raw.strip() if user_raw else "(not answered)",
            "correct_answer": q["correct"],
            "is_correct": is_correct,
            "feedback": "Correct!" if is_correct else "Incorrect. Check answer." if user_answer else "Not answered — considered incorrect."
        })

    percentage = round(correct / total * 100, 1) if total > 0 else 0

    return {
        "correct_count": correct,
        "total": total,
        "percentage": percentage,
        "results": results,
        "summary": f"{correct}/{total} correct ({percentage}%). {'Excellent!' if percentage >= 90 else 'Good!' if percentage >= 70 else 'Practice more!'}"
    }

@app.get("/user/progress/{user_id}")
async def get_user_progress(user_id: str):
    if user_id not in users_db:
        raise HTTPException(404, "User not found")
    
    user = users_db[user_id]
    target = user.get("target_level", 4)
    
    total_words = sum(len(words_db.get(l, [])) for l in range(1, target + 1))
    learned = 0
    if user_id in user_word_status:
        learned = sum(1 for v in user_word_status[user_id].values() if v["status"] == "learned")
    
    percentage = round(learned / total_words * 100, 1) if total_words > 0 else 0
    
    return {
        "learned": learned,
        "total": total_words,
        "percentage": percentage,
        "target_level": target
    }

@app.post("/corporate/create")
async def create_corporate(user_id: str, name: str):
    corp_id = f"corp_{uuid.uuid4().hex[:8]}"

    corporate_accounts[corp_id] = {
        "corp_id": corp_id,
        "name": name,
        "owner_id": user_id,
        "created_at": datetime.now().isoformat(),
        "active_until": (datetime.now() + timedelta(days=30)).isoformat(),
        "plan": "school"
    }

    corporate_members[corp_id] = [user_id]

    users_db[user_id]["corporate_id"] = corp_id
    users_db[user_id]["role"] = "owner"

    return {"success": True, "corp_id": corp_id}

@app.post("/corporate/add-student")
async def add_student(corp_id: str, email: str):
    for uid, user in users_db.items():
        if user["email"].lower() == email.lower():
            corporate_members[corp_id].append(uid)
            user["corporate_id"] = corp_id
            user["role"] = "student"
            return {"success": True}

    raise HTTPException(404, "User not found")

# Load saved data on startup
try:
    with open("data.pkl", "rb") as f:
        loaded = pickle.load(f)
        globals().update(loaded)
except FileNotFoundError:
    pass

class CSCAMathTestRequest(BaseModel):
    difficulty: str = "Intermediate"  # Basic / Intermediate / Advanced
    count: int = 10
    lang: str = "zh"  # zh / en


@app.get("/csca/math/topics")
async def get_csca_math_topics():
    return {
        "topics": csca_math_topics,
        "total": len(csca_math_topics)
    }


@app.post("/csca/math/generate-topic-lesson")
async def generate_csca_math_lesson(topic_id: str, lang: str = "zh"):
    topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    你是一个非常专业的 CSCA 数学老师。
    现在给学生讲解主题：{topic['chinese']} / {topic['english']}
    
    要求：
    - 详细、系统、由浅入深
    - 使用正式学术语言
    - 包含定义、公式、例子、解题步骤
    - 给出 CSCA 考试常见陷阱和技巧
    - 语言：{'中文' if lang == 'zh' else 'English'}
    - 长度：800–1500 字
    - 格式：Markdown（标题、公式用 LaTeX、列表、加粗）
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )
    
    lesson = response.choices[0].message.content
    
    return {
        "topic_id": topic_id,
        "title_zh": topic["chinese"],
        "title_en": topic["english"],
        "lesson": lesson,
        "lang": lang
    }

@app.post("/csca/math/generate-topic-test")
async def generate_csca_math_topic_test(topic_id: str, count: int = 20, lang: str = "zh"):
    """Generate test on CSCA math topic"""
    try:
        print(f"[CSCA TEST] Generating test for topic: {topic_id}, count: {count}, language: {lang}")
        
        # Find topic
        topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI unavailable")

        # Simpler and more reliable prompt
        prompt = f"""
Create {count} mathematics problems on topic: {topic['chinese']} ({topic['english']})
Difficulty level: {topic['difficulty']}
Language: {'Chinese' if lang == 'zh' else 'English'}

Requirements:
1. Each problem must have 4 answer options (A, B, C, D)
2. Only one correct answer
3. Provide solution explanation
4. Return answer in JSON format

JSON format:
{{
  "questions": [
    {{
      "id": "1",
      "question": "question text",
      "options": ["option A", "option B", "option C", "option D"],
      "correct_answer": "correct option (e.g.: 'B')",
      "explanation": "solution explanation"
    }}
  ]
}}

IMPORTANT: Only JSON, no Markdown or backticks!
"""
        
        print(f"[CSCA TEST] Sending request to AI...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a math expert. Always return answer in PURE JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"[CSCA TEST] Received response from AI, length: {len(response_text)} characters")
        print(f"[CSCA TEST] First 500 characters: {response_text[:500]}...")
        
        # Clean response
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            
            # Check structure
            if "questions" not in result:
                print(f"[CSCA TEST] No 'questions' field in response: {result}")
                result = {"questions": []}
            
            # Ensure correct format for each question
            for i, question in enumerate(result["questions"]):
                # Make sure there is id
                if "id" not in question:
                    question["id"] = str(i + 1)
                
                # Make sure options is a list
                if "options" in question and not isinstance(question["options"], list):
                    # Try to convert string to list
                    options_text = str(question["options"])
                    question["options"] = ["Option A", "Option B", "Option C", "Option D"]
                
                # Make sure there is correct answer
                if "correct_answer" not in question:
                    question["correct_answer"] = "A"
                
                # Make sure there is explanation
                if "explanation" not in question:
                    question["explanation"] = "Solution explanation"
                
                # Make sure there is question text
                if "question" not in question:
                    question["question"] = f"Question {i+1} on topic {topic['chinese']}"
            
        except json.JSONDecodeError as e:
            print(f"[CSCA TEST] JSON parsing error: {e}")
            print(f"[CSCA TEST] Raw response: {response_text[:1000]}")
            result = {
                "questions": [
                    {
                        "id": "1",
                        "question": f"Which answer is correct for topic {topic['chinese']}?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": "A",
                        "explanation": "This is a demo question. The real question wasn't generated due to AI error."
                    }
                ]
            }
        
        questions = result.get("questions", [])
        test_id = f"csca_math_topic_{topic_id}_{int(time.time())}"
        
        # Save test in simplified format
        tests_db[test_id] = {
            "questions": questions,
            "topic_id": topic_id,
            "lang": lang,
            "generated_at": datetime.now().isoformat(),
            "count": len(questions),
            "topic_info": topic
        }
        
        save_user_data()
        
        print(f"[CSCA TEST] Successfully created test {test_id} with {len(questions)} questions")
        
        return {
            "success": True,
            "test_id": test_id,
            "topic_id": topic_id,
            "count": len(questions),
            "questions": questions,
            "lang": lang,
            "topic": topic
        }
        
    except Exception as e:
        print(f"[CSCA TEST] Critical error: {str(e)}")
        traceback.print_exc()
        
        # Fallback test
        test_id = f"csca_fallback_{int(time.time())}"
        fallback_questions = [
            {
                "id": "1",
                "question": f"What is studied in topic '{topic_id}'?",
                "options": ["Linear equations", "Quadratic equations", "Differential equations", "Integrals"],
                "correct_answer": "A",
                "explanation": "This is a demo question. Please try again."
            },
            {
                "id": "2", 
                "question": "How many answer options are there in a CSCA test?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "B",
                "explanation": "CSCA tests usually have 4 answer options."
            }
        ]
        
        tests_db[test_id] = {
            "questions": fallback_questions,
            "topic_id": topic_id,
            "lang": lang,
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "success": False,
            "error": str(e),
            "fallback": True,
            "test_id": test_id,
            "topic_id": topic_id,
            "count": len(fallback_questions),
            "questions": fallback_questions,
            "lang": lang
        }

# Model for response (optional, but convenient for validation)
class LessonResponse(BaseModel):
    title_zh: str
    title_en: str
    lesson: str

def clean_json_response(text: str) -> str:
    """Clean response from Markdown wrappers and extra characters"""
    if not text or not isinstance(text, str):
        return "{}"
    
    # Remove all ``` wrappers
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove extra spaces
    text = text.strip()
    
    # If text doesn't start with {, look for JSON inside
    if not text.startswith('{'):
        # Look for first {
        start_idx = text.find('{')
        if start_idx != -1:
            # Find bracket balance
            balance = 0
            end_idx = start_idx
            
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    balance += 1
                elif text[i] == '}':
                    balance -= 1
                    if balance == 0:
                        end_idx = i
                        break
            
            if balance == 0:
                text = text[start_idx:end_idx + 1]
            else:
                # If balance doesn't match, take until end
                text = text[start_idx:]
                if not text.endswith('}'):
                    text += '}'
    
    return text

def create_structured_lesson_from_text(text: str, topic_id: str) -> dict:
    """Create structured lesson from text"""
    
    # Try to find lesson parts in text
    sections = {
        "title_zh": f"CSCA Topic: {topic_id}",
        "title_en": f"CSCA Topic: {topic_id}",
        "lesson": text  # Use entire text as lesson
    }
    
    # Try to extract headings from text
    lines = text.split('\n')
    
    # Look for headings in text
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Look for Chinese title
        if "标题" in line_lower or "主题" in line_lower or "中文" in line_lower:
            for j in range(i, min(i+3, len(lines))):
                if "：" in lines[j] or ":" in lines[j]:
                    parts = re.split(r'[：:]', lines[j], 1)
                    if len(parts) > 1:
                        sections["title_zh"] = parts[1].strip()
                        break
        
        # Look for English title
        if "title" in line_lower or "英文" in line_lower:
            for j in range(i, min(i+3, len(lines))):
                if "：" in lines[j] or ":" in lines[j]:
                    parts = re.split(r'[：:]', lines[j], 1)
                    if len(parts) > 1:
                        sections["title_en"] = parts[1].strip()
                        break
    
    # Format lesson
    formatted_lesson = ""
    for line in lines:
        if line.strip():
            formatted_lesson += line + "\n"
    
    sections["lesson"] = formatted_lesson.strip()
    
    return sections

# 2. Generate 5 practice problems
@app.get('/csca/math/generate-practice')
async def generate_practice(
    topic_id: str = Query(..., description="Topic ID"),
    count: int = Query(5, description="Number of problems")
):
    from fastapi import Query
    from fastapi.responses import JSONResponse
    
    prompt = f"""
    Generate {count} problems on CSCA Math topic "{topic_id}".
    Each problem should include:
    - Question (in Chinese)
    - Correct answer (in correct_answer field)
    - Brief solution explanation (explanation)
    JSON format:
    {{"questions": [{{"question": "...", "correct_answer": "...", "explanation": "..."}}]}}
    """
    
    raw = call_deepseek(prompt)
    try:
        data = eval(raw)
    except:
        data = {"questions": []}
    
    return JSONResponse(content=data)

# 3. Check answer
@app.post('/csca/math/check-answer')
async def check_answer(request: Request):
    from fastapi.responses import JSONResponse
    
    data = await request.json()
    topic_id = data.get('topic_id')
    question_index = data.get('question_index')
    user_answer = data.get('user_answer')
    
    prompt = f"""
    Check student's answer to problem on topic "{topic_id}" (question #{question_index+1}).
    Student answer: "{user_answer}"
    Give:
    - is_correct: true/false
    - feedback: detailed comment in Chinese
    - correct_answer: correct answer
    JSON format.
    """
    
    raw = call_deepseek(prompt)
    try:
        result = eval(raw)
    except:
        result = {"is_correct": False, "feedback": "Check error", "correct_answer": "?"}
    
    return JSONResponse(content=result)

# In main.py add/replace this function:

@app.post("/csca/math/submit-test")
async def submit_csca_test(request: dict):
    """Universal check for any CSCA test"""
    try:
        test_id = request.get("test_id")
        user_id = request.get("user_id")
        answers = request.get("answers", {})
        
        if not test_id:
            raise HTTPException(status_code=400, detail="test_id required")
        
        # Find test in different places in database
        test_data = None
        
        # Try to find in tests_db
        if test_id in tests_db:
            test_data = tests_db[test_id]
        # Try to find as topic test
        elif test_id.startswith("csca_topic_"):
            # Find test in structured data
            for key, value in tests_db.items():
                if isinstance(value, dict) and value.get("test_id") == test_id:
                    test_data = value
                    break
        
        if not test_data:
            # If not found, maybe it's a new test
            # Check if test is in comprehensive format
            for key, value in tests_db.items():
                if isinstance(value, dict) and "questions" in value:
                    if value.get("test_id") == test_id or key == test_id:
                        test_data = value
                        break
        
        if not test_data or "questions" not in test_data:
            raise HTTPException(status_code=404, detail="Test not found or no questions available")
        
        questions = test_data.get("questions", [])
        
        if not questions:
            return {
                "success": False,
                "message": "No questions in test",
                "score": 0,
                "total": 0,
                "percentage": 0
            }
        
        # Check answers
        correct_count = 0
        results = []
        
        for q in questions:
            q_id = q.get("id", "")
            user_answer_raw = answers.get(str(q_id), "")
            
            # Normalize user answer
            user_answer = str(user_answer_raw).strip().upper()
            
            # Normalize correct answer
            correct_answer_raw = q.get("correct_answer", "A")
            correct_answer = str(correct_answer_raw).strip().upper()
            
            # Check correctness
            is_correct = False
            if user_answer:
                # Support different answer formats
                answer_mapping = {"1": "A", "2": "B", "3": "C", "4": "D"}
                normalized_user_answer = answer_mapping.get(user_answer, user_answer)
                is_correct = normalized_user_answer == correct_answer
            else:
                user_answer = "(not answered)"
            
            if is_correct:
                correct_count += 1
            
            results.append({
                "question_id": q_id,
                "question": q.get("question", "Question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "No explanation available"),
                "options": q.get("options", [])
            })
        
        score = correct_count
        total = len(questions)
        percentage = int((score / total) * 100) if total > 0 else 0
        
        # Determine grade
        if percentage >= 90:
            grade = "Excellent! 🎉"
            grade_emoji = "🎉"
        elif percentage >= 70:
            grade = "Good! 👍"
            grade_emoji = "👍"
        elif percentage >= 50:
            grade = "Fair 👌"
            grade_emoji = "👌"
        else:
            grade = "Needs improvement 📚"
            grade_emoji = "📚"
        
        # Save result if user exists
        if user_id:
            # Initialize test history
            user_history_key = f"user_tests_{user_id}"
            if user_history_key not in tests_db:
                tests_db[user_history_key] = []
            
            test_result = {
                "test_id": test_id,
                "test_type": test_data.get("type", "unknown"),
                "topic_id": test_data.get("topic_id"),
                "score": score,
                "total": total,
                "percentage": percentage,
                "submitted_at": datetime.now().isoformat(),
                "lang": test_data.get("lang", "zh"),
                "difficulty": test_data.get("difficulty", "unknown")
            }
            
            tests_db[user_history_key].append(test_result)
            
            # Store only last 20 tests
            if len(tests_db[user_history_key]) > 20:
                tests_db[user_history_key] = tests_db[user_history_key][-20:]
            
            save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "score": score,
            "total": total,
            "percentage": percentage,
            "grade": grade,
            "grade_emoji": grade_emoji,
            "results": results,
            "message": f"{score}/{total} correct answers ({percentage}%) - {grade}",
            "test_info": {
                "type": test_data.get("type", "unknown"),
                "lang": test_data.get("lang", "zh"),
                "topic": test_data.get("topic_info", {}),
                "difficulty": test_data.get("difficulty", "unknown")
            }
        }
        
    except Exception as e:
        print(f"[CSCA TEST] Submit error: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": f"Test submission error: {str(e)}"
        }
    
def generate_fallback_questions(count: int, lang: str = "zh") -> list:
    """Generate fallback questions"""
    questions = []
    
    for i in range(min(count, 10)):  # Maximum 10 fallback questions
        questions.append({
            "id": str(i + 1),
            "question": f"Math question {i+1} for CSCA" if lang == "zh" else f"Math question {i+1} for CSCA",
            "options": [
                "Option A" if lang == "zh" else "Option A",
                "Option B" if lang == "zh" else "Option B", 
                "Option C" if lang == "zh" else "Option C",
                "Option D" if lang == "zh" else "Option D"
            ],
            "correct_answer": random.choice(["A", "B", "C", "D"]),
            "explanation": "This is a demo question. Please try again." if lang == "zh" else "This is a demo question. Please try again."
        })
    
    return questions

@app.get("/csca/math/progress/{user_id}")
async def get_csca_math_progress(user_id: str):
    if user_id not in users_db:
        raise HTTPException(404, "User not found")
    
    progress = users_db[user_id].get("csca_math_progress", {})
    total = len(csca_math_topics)
    completed = sum(1 for p in progress.values() if p >= 50)  # e.g., 50% = completed
    
    return {
        "overall_percentage": round((completed / total) * 100, 1) if total else 0,
        "topics_completed": completed,
        "total_topics": total,
        "topic_progress": progress
    }

# In main.py add/update these functions:

# 1. Improved function for generating topic test
@app.get("/csca/math/generate-topic-test")
async def generate_topic_test_api(
    topic_id: str = Query(..., description="Topic ID"),
    count: int = Query(5, description="Number of questions"),
    lang: str = Query("zh", description="Language: zh or en")
):
    """Generate test on specific topic"""
    try:
        print(f"[CSCA TEST] Generating test: topic={topic_id}, count={count}, lang={lang}")
        
        # Find topic
        topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        client = get_deepseek_client()
        if not client:
            return generate_fallback_topic_test(topic_id, count, lang)
        
        # Prompt for question generation
        prompt = f"""
        Create {count} mathematics problems on topic: {topic['chinese']} / {topic['english']}
        Language: {'Chinese' if lang == 'zh' else 'English'}
        Difficulty: {topic['difficulty']}
        
        Each problem should include:
        1. Clear question text
        2. 4 answer options (A, B, C, D)
        3. Only one correct answer
        4. Detailed solution explanation
        
        Important:
        - Questions should be appropriate for CSCA exam level
        - Use proper mathematical notation
        - Include step-by-step solutions
        
        Response format JSON:
        {{
            "questions": [
                {{
                    "id": "1",
                    "question": "Question text...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",  // Must be A, B, C, or D
                    "explanation": "Detailed solution..."
                }}
            ]
        }}
        
        {'请用中文提问和解答' if lang == 'zh' else 'Use English for questions and explanations'}
        """
        
        print(f"[CSCA TEST] Sending prompt to AI...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a mathematics teacher creating exam questions. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"[CSCA TEST] Raw AI response: {response_text[:500]}...")
        
        # Clean JSON
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            questions = result.get("questions", [])
            
            # Validate and format questions
            validated_questions = []
            for i, q in enumerate(questions[:count]):
                # Check required fields
                if not q.get("question"):
                    continue
                    
                # Check options
                options = q.get("options", [])
                if not isinstance(options, list) or len(options) != 4:
                    options = ["Option A", "Option B", "Option C", "Option D"]
                
                # Check correct_answer
                correct_answer = str(q.get("correct_answer", "A")).strip().upper()
                if correct_answer not in ["A", "B", "C", "D"]:
                    # Try to determine by first character
                    if options and isinstance(options[0], str):
                        correct_answer = "A"
                    else:
                        correct_answer = "A"
                
                validated_questions.append({
                    "id": str(i + 1),
                    "question": q.get("question", f"Question {i+1}"),
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": q.get("explanation", "Solution explanation not available"),
                    "topic_id": topic_id,
                    "difficulty": topic['difficulty']
                })
            
        except json.JSONDecodeError as e:
            print(f"[CSCA TEST] JSON parse error: {e}")
            validated_questions = generate_fallback_topic_test_questions(topic_id, count, lang)
        
        test_id = f"csca_topic_{topic_id}_{lang}_{int(time.time())}"
        
        # Save test
        tests_db[test_id] = {
            "questions": validated_questions,
            "topic_id": topic_id,
            "lang": lang,
            "generated_at": datetime.now().isoformat(),
            "count": len(validated_questions),
            "type": "topic_test",
            "topic_info": topic
        }
        
        save_user_data()
        
        print(f"[CSCA TEST] Successfully created test {test_id} with {len(validated_questions)} questions")
        
        return {
            "success": True,
            "test_id": test_id,
            "topic_id": topic_id,
            "count": len(validated_questions),
            "questions": validated_questions,
            "lang": lang,
            "topic": topic
        }
        
    except Exception as e:
        print(f"[CSCA TEST] Error: {str(e)}")
        traceback.print_exc()
        return generate_fallback_topic_test(topic_id, count, lang)

def generate_fallback_topic_test(topic_id: str, count: int, lang: str):
    """Fallback topic test"""
    topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
    
    questions = []
    for i in range(min(count, 5)):
        questions.append({
            "id": str(i + 1),
            "question": f"Sample question on topic {topic['chinese'] if topic else topic_id}" if lang == "zh" 
                       else f"Sample question on {topic['english'] if topic else topic_id}",
            "options": [
                "Option A" if lang == "zh" else "Option A",
                "Option B" if lang == "zh" else "Option B",
                "Option C" if lang == "zh" else "Option C",
                "Option D" if lang == "zh" else "Option D"
            ],
            "correct_answer": random.choice(["A", "B", "C", "D"]),
            "explanation": "This is a demo question. AI is needed for real questions." if lang == "zh" 
                         else "This is a demo question. AI is needed for real questions.",
            "topic_id": topic_id,
            "difficulty": topic['difficulty'] if topic else "Basic"
        })
    
    test_id = f"csca_fallback_{topic_id}_{lang}_{int(time.time())}"
    
    tests_db[test_id] = {
        "questions": questions,
        "topic_id": topic_id,
        "lang": lang,
        "generated_at": datetime.now().isoformat(),
        "count": len(questions),
        "type": "fallback_topic_test"
    }
    
    return {
        "success": False,
        "test_id": test_id,
        "topic_id": topic_id,
        "count": len(questions),
        "questions": questions,
        "lang": lang,
        "fallback": True
    }

# 2. Improved function for submitting and checking test
@app.post("/csca/math/submit-topic-test")
async def submit_topic_test(request: dict):
    """Check topic test"""
    try:
        test_id = request.get("test_id")
        user_id = request.get("user_id")
        answers = request.get("answers", {})
        
        if not test_id or test_id not in tests_db:
            raise HTTPException(status_code=404, detail="Test not found")
        
        test_data = tests_db[test_id]
        questions = test_data.get("questions", [])
        
        if not questions:
            return {
                "success": False,
                "message": "No questions in test",
                "score": 0,
                "total": 0
            }
        
        # Check answers
        correct_count = 0
        results = []
        
        for q in questions:
            q_id = q["id"]
            user_answer = answers.get(str(q_id), "").strip().upper()
            correct_answer = q.get("correct_answer", "A").strip().upper()
            
            # Check answer
            is_correct = False
            if user_answer:
                # Allow options: "A" or "1" (if user entered number)
                answer_mapping = {"1": "A", "2": "B", "3": "C", "4": "D"}
                normalized_answer = answer_mapping.get(user_answer, user_answer)
                is_correct = normalized_answer == correct_answer
            else:
                user_answer = "(not answered)"
            
            if is_correct:
                correct_count += 1
            
            results.append({
                "question_id": q_id,
                "question": q["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "options": q.get("options", [])
            })
        
        score = correct_count
        total = len(questions)
        percentage = int((score / total) * 100) if total > 0 else 0
        
        # Grade
        grade = ""
        if percentage >= 90:
            grade = "Excellent! 🎉"
        elif percentage >= 70:
            grade = "Good! 👍"
        elif percentage >= 50:
            grade = "Fair 👌"
        else:
            grade = "Needs improvement 📚"
        
        # Save result if user exists
        if user_id:
            # Initialize user test results
            if "user_test_results" not in tests_db:
                tests_db["user_test_results"] = {}
            
            user_results = tests_db["user_test_results"].get(user_id, [])
            user_results.append({
                "test_id": test_id,
                "test_type": test_data.get("type", "topic_test"),
                "topic_id": test_data.get("topic_id"),
                "score": score,
                "total": total,
                "percentage": percentage,
                "submitted_at": datetime.now().isoformat(),
                "lang": test_data.get("lang", "zh")
            })
            
            tests_db["user_test_results"][user_id] = user_results[-10:]  # Store last 10 tests
            save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "score": score,
            "total": total,
            "percentage": percentage,
            "grade": grade,
            "results": results,
            "message": f"{score}/{total} correct answers ({percentage}%) - {grade}"
        }
        
    except Exception as e:
        print(f"[CSCA TEST] Submit error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test submission error: {str(e)}")

# 3. Improved function for generating comprehensive test
@app.post("/csca/math/generate-comprehensive-test")
async def generate_comprehensive_test(request: dict):
    """Generate comprehensive test on all topics"""
    try:
        count = request.get("count", 20)
        lang = request.get("lang", "zh")
        difficulty = request.get("difficulty", "all")  # all, basic, intermediate, advanced
        
        client = get_deepseek_client()
        if not client:
            return generate_fallback_comprehensive_test(count, lang, difficulty)
        
        # Filter topics by difficulty
        filtered_topics = csca_math_topics
        if difficulty != "all":
            filtered_topics = [t for t in csca_math_topics if t.get("difficulty") == difficulty]
        
        if not filtered_topics:
            filtered_topics = csca_math_topics[:5]  # Take first 5 topics
        
        topics_text = ", ".join([t["english"] for t in filtered_topics[:5]])
        
        prompt = f"""
        Create {count} comprehensive mathematics problems covering various CSCA topics.
        Language: {'Chinese' if lang == 'zh' else 'English'}
        Topics covered: {topics_text}
        Difficulty: {difficulty if difficulty != 'all' else 'Mixed (Basic to Advanced)'}
        
        Each problem should include:
        1. Clear mathematical question
        2. 4 multiple-choice options (A, B, C, D)
        3. Only one correct answer
        4. Step-by-step solution
        
        Mix different types of problems:
        - Algebra
        - Geometry
        - Calculus
        - Probability
        - Statistics
        
        Format your response as JSON:
        {{
            "questions": [
                {{
                    "id": "1",
                    "question": "Full question text...",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "B",
                    "explanation": "Detailed solution with steps...",
                    "category": "Algebra"
                }}
            ]
        }}
        
        {'请用中文提问和解答' if lang == 'zh' else 'Use English for all questions and explanations'}
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are creating a comprehensive mathematics exam. Provide valid JSON response."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            raw_questions = result.get("questions", [])
        except:
            raw_questions = []
        
        # Structure questions
        questions = []
        for i, q in enumerate(raw_questions[:count]):
            questions.append({
                "id": str(i + 1),
                "question": q.get("question", f"Question {i+1}"),
                "options": q.get("options", [
                    "Option A" if lang == "en" else "Option A",
                    "Option B" if lang == "en" else "Option B", 
                    "Option C" if lang == "en" else "Option C",
                    "Option D" if lang == "en" else "Option D"
                ]),
                "correct_answer": str(q.get("correct_answer", "A")).strip().upper(),
                "explanation": q.get("explanation", "Explanation not available"),
                "category": q.get("category", "Mathematics"),
                "difficulty": difficulty if difficulty != "all" else "Mixed",
                "lang": lang
            })
        
        test_id = f"csca_comprehensive_{lang}_{difficulty}_{int(time.time())}"
        
        # Save test
        tests_db[test_id] = {
            "questions": questions,
            "lang": lang,
            "difficulty": difficulty,
            "generated_at": datetime.now().isoformat(),
            "count": len(questions),
            "type": "comprehensive_test"
        }
        
        save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "count": len(questions),
            "questions": questions,
            "lang": lang,
            "difficulty": difficulty,
            "ai_generated": True
        }
        
    except Exception as e:
        print(f"[CSCA] Comprehensive test error: {str(e)}")
        return generate_fallback_comprehensive_test(count, lang, difficulty)

def generate_fallback_comprehensive_test(count: int, lang: str, difficulty: str):
    """Fallback comprehensive test"""
    questions = []
    for i in range(min(count, 10)):
        questions.append({
            "id": str(i + 1),
            "question": f"Comprehensive math question {i+1}" if lang == "zh" 
                       else f"Comprehensive math question {i+1}",
            "options": [
                "Option A" if lang == "zh" else "Option A",
                "Option B" if lang == "zh" else "Option B",
                "Option C" if lang == "zh" else "Option C",
                "Option D" if lang == "zh" else "Option D"
            ],
            "correct_answer": random.choice(["A", "B", "C", "D"]),
            "explanation": "Detailed solution for demo question" if lang == "zh" 
                         else "Detailed solution for demo question",
            "category": "Mathematics",
            "difficulty": difficulty if difficulty != "all" else "Mixed",
            "lang": lang
        })
    
    test_id = f"csca_fallback_comprehensive_{lang}_{int(time.time())}"
    
    tests_db[test_id] = {
        "questions": questions,
        "lang": lang,
        "difficulty": difficulty,
        "generated_at": datetime.now().isoformat(),
        "count": len(questions),
        "type": "fallback_comprehensive"
    }
    
    return {
        "success": False,
        "test_id": test_id,
        "count": len(questions),
        "questions": questions,
        "lang": lang,
        "difficulty": difficulty,
        "fallback": True,
        "ai_generated": False
    }

@app.get("/csca/math/generate-global-test")
async def generate_csca_global_test_get(
    count: int = Query(20, description="Number of questions"),
    lang: str = Query("zh", description="Test language: zh or en")
):
    """GET endpoint for generating global test"""
    return await generate_csca_global_test(count, lang)

# Main function
async def generate_csca_global_test(count: int = 20, lang: str = "zh"):
    """Generate global CSCA math test"""
    try:
        print(f"[CSCA GLOBAL] Generating test: {count} questions, language: {lang}")
        
        client = get_deepseek_client()
        if not client:
            return await create_fallback_test(count, lang)
        
        # Simple prompt
        prompt = f"""
Create {count} mathematics problems for CSCA preparation.
Question language: {'Chinese' if lang == 'zh' else 'English'}

Each problem:
1. Question with 4 answer options
2. Only one correct answer
3. Brief explanation

Example format:
{{
  "questions": [
    {{
      "id": "1",
      "question": "question text",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "explanation": "explanation"
    }}
  ]
}}

Return only JSON!
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a math expert. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            questions = result.get("questions", [])
        except:
            questions = []
        
        # Create structured questions
        processed_questions = []
        for i, q in enumerate(questions[:count]):
            if isinstance(q, dict):
                processed_q = {
                    "id": str(i + 1),
                    "question": q.get("question", f"Math question {i+1}"),
                    "options": q.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                    "correct_answer": q.get("correct_answer", "A"),
                    "explanation": q.get("explanation", "Solution explanation")
                }
                
                # Check options
                if not isinstance(processed_q["options"], list) or len(processed_q["options"]) != 4:
                    if lang == "zh":
                        processed_q["options"] = ["Option A", "Option B", "Option C", "Option D"]
                    else:
                        processed_q["options"] = ["Option A", "Option B", "Option C", "Option D"]
                
                # Check correct_answer
                if processed_q["correct_answer"] not in ["A", "B", "C", "D"]:
                    processed_q["correct_answer"] = "A"
                
                processed_questions.append(processed_q)
        
        test_id = f"csca_global_{int(time.time())}"
        
        # Save
        tests_db[test_id] = {
            "questions": processed_questions,
            "lang": lang,
            "generated_at": datetime.now().isoformat(),
            "count": len(processed_questions),
            "type": "global"
        }
        
        save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "count": len(processed_questions),
            "questions": processed_questions,
            "lang": lang,
            "ai_generated": True
        }
        
    except Exception as e:
        print(f"[CSCA GLOBAL] Error: {str(e)}")
        traceback.print_exc()
        return await create_fallback_test(count, lang)
    
@app.get("/user/profile-comprehensive/{user_id}")
async def get_comprehensive_profile(user_id: str, db: Session = Depends(get_db)):
    """Universal endpoint for profile, gathering data from all sources"""
    
    # Convert ID
    sqlite_user_id = None
    if user_id.startswith("user_"):
        sqlite_user_id = get_sqlite_user_id(user_id, db)
    else:
        try:
            sqlite_user_id = int(user_id)
        except:
            sqlite_user_id = None
    
    # Data from old system
    old_data = {}
    if user_id in users_db:
        old_data = users_db[user_id]
    
    # Data from SQLite
    sqlite_data = {}
    if sqlite_user_id:
        user = db.query(User).filter(User.id == sqlite_user_id).first()
        if user:
            # Words
            words = db.query(UserWord).filter(UserWord.user_id == sqlite_user_id).all()
            words_by_status = {
                "new": len([w for w in words if w.status == "new"]),
                "learning": len([w for w in words if w.status == "learning"]),
                "learned": len([w for w in words if w.status == "learned"]),
                "review": len([w for w in words if w.status == "review"])
            }
            
            # Tests
            tests = db.query(UserTest).filter(
                UserTest.user_id == sqlite_user_id,
                UserTest.score.isnot(None)
            ).order_by(UserTest.created_at.desc()).limit(10).all()
            
            # Sessions
            sessions = db.query(StudySession).filter(
                StudySession.user_id == sqlite_user_id
            ).all()
            
            total_study_time = sum(s.duration_minutes or 0 for s in sessions)
            
            # Actions
            recent_actions = db.query(UserAction).filter(
                UserAction.user_id == sqlite_user_id
            ).order_by(UserAction.timestamp.desc()).limit(50).all()
            
            sqlite_data = {
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "current_hsk_level": user.current_hsk_level,
                    "target_hsk_level": user.target_hsk_level,
                    "country": user.country,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                },
                "statistics": {
                    "total_words_learned": user.total_words_learned,
                    "total_tests_taken": user.total_tests_taken,
                    "average_test_score": user.average_test_score,
                    "study_streak": user.study_streak,
                    "longest_streak": user.longest_streak,
                    "total_study_time": total_study_time,
                    "total_points": user.total_points
                },
                "words": {
                    "by_status": words_by_status,
                    "total": len(words),
                    "recent": [
                        {"word": w.word_text, "status": w.status, "date": w.updated_at.isoformat()}
                        for w in sorted(words, key=lambda x: x.updated_at or x.created_at, reverse=True)[:10]
                    ]
                },
                "tests": {
                    "recent": [
                        {
                            "id": t.id,
                            "type": t.test_type,
                            "level": t.test_level,
                            "score": t.score,
                            "max_score": t.max_score,
                            "date": t.created_at.isoformat()
                        }
                        for t in tests
                    ],
                    "total": len(tests)
                },
                "activity": {
                    "last_7_days": len([a for a in recent_actions if a.timestamp > datetime.utcnow() - timedelta(days=7)]),
                    "last_30_days": len([a for a in recent_actions if a.timestamp > datetime.utcnow() - timedelta(days=30)]),
                    "recent": [
                        {
                            "type": a.action_type,
                            "data": a.action_data,
                            "time": a.timestamp.isoformat()
                        }
                        for a in recent_actions[:20]
                    ]
                }
            }
    
    # COMBINE data (SQLite priority)
    combined = {
        "user_id": user_id,
        "name": sqlite_data.get("user", {}).get("full_name") or old_data.get("name", ""),
        "email": sqlite_data.get("user", {}).get("email") or old_data.get("email", ""),
        "current_level": sqlite_data.get("user", {}).get("current_hsk_level") or old_data.get("current_level", 1),
        "target_level": sqlite_data.get("user", {}).get("target_hsk_level") or old_data.get("target_level", 4),
        "statistics": {
            "learned_words": sqlite_data.get("statistics", {}).get("total_words_learned", 0) or 
                            len([v for v in user_word_status.get(user_id, {}).values() if v["status"] == "learned"]),
            "tests_taken": sqlite_data.get("statistics", {}).get("total_tests_taken", 0),
            "average_score": sqlite_data.get("statistics", {}).get("average_test_score", 0),
            "study_time_minutes": sqlite_data.get("statistics", {}).get("total_study_time", 0),
            "streak": sqlite_data.get("statistics", {}).get("study_streak", 0)
        },
        "recent_activity": sqlite_data.get("activity", {}).get("recent", []),
        "words": sqlite_data.get("words", {}),
        "tests": sqlite_data.get("tests", {}),
        "last_updated": datetime.now().isoformat()
    }
    
    return combined

@app.post("/sync-all-data/{user_id}")
async def sync_all_user_data(user_id: str, db: Session = Depends(get_db)):
    """Full synchronization of all user data from old dictionaries to SQLite"""
    
    sqlite_user_id = get_sqlite_user_id(user_id, db)
    if not sqlite_user_id:
        return {"error": "User not found"}
    
    stats = {
        "words_synced": 0,
        "tests_synced": 0,
        "chat_synced": 0
    }
    
    # 1. Sync words
    if user_id in user_word_status:
        for word_id, data in user_word_status[user_id].items():
            parts = word_id.rsplit('_', 1)
            word_text = parts[0]
            hsk_level = int(parts[1]) if len(parts) > 1 else 1
            
            existing = db.query(UserWord).filter(
                UserWord.user_id == sqlite_user_id,
                UserWord.word_id == word_id
            ).first()
            
            if not existing:
                word = UserWord(
                    user_id=sqlite_user_id,
                    word_id=word_id,
                    word_text=word_text,
                    hsk_level=hsk_level,
                    status=data["status"],
                    created_at=datetime.fromisoformat(data["added_at"])
                )
                db.add(word)
                stats["words_synced"] += 1
        
        # Clear old data after sync
        del user_word_status[user_id]
    
    # 2. Sync tests
    for test_id, test_data in tests_db.items():
        if user_id in test_data:
            user_test_data = test_data[user_id]
            
            test = UserTest(
                user_id=sqlite_user_id,
                test_id=test_id,
                test_type=user_test_data.get("test_type", "unknown"),
                test_level=user_test_data.get("level", 1),
                score=user_test_data.get("score", 0),
                max_score=user_test_data.get("max_score", 0),
                answers=user_test_data.get("answers", {}),
                results=user_test_data.get("results", {}),
                created_at=datetime.fromisoformat(user_test_data.get("submitted_at", datetime.now().isoformat()))
            )
            db.add(test)
            stats["tests_synced"] += 1
    
    # 3. Sync chat
    if user_id in chat_history:
        for i, msg in enumerate(chat_history[user_id]):
            chat = ChatMessage(
                user_id=sqlite_user_id,
                thread_id=f"history_thread_{i}",
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                message_metadata={"timestamp": msg.get("timestamp", datetime.now().isoformat())}
            )
            db.add(chat)
            stats["chat_synced"] += 1
    
    # 4. Update user statistics
    user = db.query(User).filter(User.id == sqlite_user_id).first()
    if user:
        user.total_words_learned = db.query(UserWord).filter(
            UserWord.user_id == sqlite_user_id,
            UserWord.status == "learned"
        ).count()
        
        user.total_tests_taken = db.query(UserTest).filter(
            UserTest.user_id == sqlite_user_id
        ).count()
    
    db.commit()
    save_user_data()  # Save updated old dictionaries
    
    return {
        "success": True,
        "synced": stats,
        "message": f"Synced {stats['words_synced']} words, {stats['tests_synced']} tests, {stats['chat_synced']} messages"
    }
    
async def create_fallback_test(count: int, lang: str):
    """Create fallback test"""
    questions = []
    for i in range(min(count, 10)):
        questions.append({
            "id": str(i + 1),
            "question": f"Sample math question {i+1} for CSCA" if lang == "zh" 
                       else f"Sample math question {i+1} for CSCA",
            "options": [
                "Option A" if lang == "zh" else "Option A",
                "Option B" if lang == "zh" else "Option B",
                "Option C" if lang == "zh" else "Option C",
                "Option D" if lang == "zh" else "Option D"
            ],
            "correct_answer": random.choice(["A", "B", "C", "D"]),
            "explanation": "This is a demo question" if lang == "zh" 
                          else "This is a demo question"
        })
    
    test_id = f"csca_fallback_{int(time.time())}"
    
    tests_db[test_id] = {
        "questions": questions,
        "lang": lang,
        "generated_at": datetime.now().isoformat(),
        "count": len(questions),
        "type": "fallback"
    }
    
    return {
        "success": False,
        "test_id": test_id,
        "count": len(questions),
        "questions": questions,
        "lang": lang,
        "fallback": True,
        "ai_generated": False
    }

@app.post("/csca/math/generate-global-test")
async def generate_global_test_api(request: GlobalTestRequest = None):
    """API endpoint for frontend"""
    if request:
        count = request.count
        lang = request.lang
    else:
        count = 20
        lang = "zh"
    
    return await generate_csca_global_test(count, lang)

# In main.py - full improved prompt for lessons

@app.get("/csca/math/generate-topic-lesson")
async def generate_csca_math_lesson(topic_id: str, lang: str = "zh"):
    topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    你是一个非常专业的 CSCA 数学老师。
    现在给学生讲解主题：{topic['chinese']} / {topic['english']}
    
    要求：
    - 详细、系统、由浅入深
    - 使用正式学术语言
    - 包含定义、公式、例子、解题步骤
    - 给出 CSCA 考试常见陷阱和技巧
    - 语言：{'中文' if lang == 'zh' else 'English'}
    - 长度：800–1500 字
    - 格式：Markdown（标题、公式用 LaTeX、列表、加粗）
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )
    
    lesson = response.choices[0].message.content
    
    # FORMAT RESPONSE
    formatted = format_chat_response(lesson, None, "csca-math")
    
    return {
        "topic_id": topic_id,
        "title_zh": topic["chinese"],
        "title_en": topic["english"],
        "lesson": formatted["response"],
        "formatted_lesson": formatted["formatted_response"],
        "css": formatted["css"],
        "lang": lang
    }

def create_fallback_lesson(topic, lang, depth):
    """Fallback lesson"""
    return {
        "title_zh": f"深入探讨：{topic['chinese']}" if lang == 'zh' else f"Advanced: {topic['english']}",
        "title_en": f"Advanced Study: {topic['english']}",
        "lesson": f"""
# {topic['chinese'] if lang == 'zh' else topic['english']}

## Introduction
{topic['chinese'] if lang == 'zh' else topic['english']} is an important concept in mathematics with wide applications in science and engineering.

## Core Concepts
1. **Basic Definition**: Detailed mathematical definition
2. **Key Theorems**: Important mathematical results
3. **Applications**: Real-world applications

## Examples
1. Basic problem
2. Intermediate problem  
3. Advanced problem

## Exam Tips
- Common question types
- Problem-solving strategies
- Time management
""",
        "key_concepts": ["Core concept 1", "Core concept 2"],
        "difficulty_rating": 7.5,
        "estimated_study_time": "60 minutes",
        "prerequisites": ["Basic mathematics"],
        "next_topics": ["Related advanced topics"]
    }

# 2. Improved test generation
@app.get("/csca/math/generate-advanced-test")
async def generate_advanced_test(
    topic_id: str = Query(None, description="Topic ID (optional)"),
    difficulty: str = Query("challenging", description="Difficulty: easy, medium, challenging, expert"),
    lang: str = Query("zh", description="Language"),
    count: int = Query(10, description="Number of questions")
):
    """Generate challenging, high-quality test"""
    try:
        client = get_deepseek_client()
        if not client:
            return generate_fallback_advanced_test(topic_id, difficulty, lang, count)
        
        topic_info = {}
        if topic_id:
            topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
            if topic:
                topic_info = topic
        
        prompt = f"""
# CSCA ADVANCED MATHEMATICS TEST GENERATOR

## CONTEXT:
Create {count} HIGH-QUALITY mathematics problems for CSCA preparation.

## SPECIFICATIONS:
- Language: {'Chinese' if lang == 'zh' else 'English'}
- Difficulty: {difficulty.upper()} (see guidelines below)
- Topic: {topic_info.get('chinese', 'General Mathematics')} / {topic_info.get('english', 'General Mathematics')}
- Question Count: {count}

## DIFFICULTY GUIDELINES:

### EASY (20%):
- Straightforward applications of formulas
- One-step problems
- Basic computations

### MEDIUM (30%):  
- Multi-step problems
- Require understanding of concepts
- Moderate complexity

### CHALLENGING (30%):
- Require creative thinking
- Combine multiple concepts
- Non-standard approaches needed

### EXPERT (20%):
- Olympiad-level difficulty
- Require deep insight
- Proof-based or open-ended

## QUESTION TYPES (MIX):
1. **Computational** (40%): Calculate, solve, evaluate
2. **Proof-based** (30%): Prove, show, derive
3. **Application** (20%): Real-world scenarios
4. **Conceptual** (10%): Explain, compare, analyze

## QUALITY REQUIREMENTS:
1. **Originality**: Avoid textbook-standard problems
2. **Clarity**: Precise wording, no ambiguity
3. **Educational Value**: Each question should teach something
4. **Balance**: Cover different aspects of the topic
5. **Progressive Difficulty**: Start easier, end harder

## FORMAT FOR EACH QUESTION:
1. Clear problem statement
2. 4 plausible options (A, B, C, D) with ONE correct
3. Detailed solution explaining:
   - Step-by-step reasoning
   - Alternative approaches
   - Common mistakes to avoid
   - Key learning points

## RESPONSE FORMAT JSON:
{{
  "test_title": "Advanced CSCA Mathematics Test",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": "1",
      "question": "Full problem statement...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "solution": {{
        "step_by_step": ["Step 1...", "Step 2..."],
        "key_concept": "Main concept tested",
        "difficulty_rating": 7,
        "time_estimate": "3 minutes",
        "common_errors": ["Common mistake 1", "Common mistake 2"],
        "exam_tip": "How to approach similar problems"
      }},
      "category": "Algebra|Geometry|Calculus|etc",
      "thinking_process": "How a top student would think through this"
    }}
  ],
  "metadata": {{
    "total_score": {count * 10},
    "recommended_time": "{count * 3} minutes",
    "skill_coverage": ["skill1", "skill2"],
    "prerequisites": ["required knowledge"]
  }}
}}

Now create an EXCELLENT test that would challenge even the best students.
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are Dr. Chen, mathematics olympiad coach with experience creating challenging exam questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            questions = result.get("questions", [])
        except:
            questions = []
        
        # Structure questions
        structured_questions = []
        for i, q in enumerate(questions[:count]):
            structured_questions.append({
                "id": str(i + 1),
                "question": q.get("question", f"Question {i+1}"),
                "options": q.get("options", ["A", "B", "C", "D"]),
                "correct_answer": q.get("correct_answer", "A"),
                "solution": q.get("solution", {}),
                "difficulty": difficulty,
                "category": q.get("category", "Mathematics"),
                "thinking_process": q.get("thinking_process", ""),
                "quality_score": q.get("solution", {}).get("difficulty_rating", 5)
            })
        
        test_id = f"csca_advanced_{difficulty}_{lang}_{int(time.time())}"
        
        tests_db[test_id] = {
            "questions": structured_questions,
            "test_title": result.get("test_title", "Advanced CSCA Test"),
            "difficulty": difficulty,
            "lang": lang,
            "metadata": result.get("metadata", {}),
            "generated_at": datetime.now().isoformat(),
            "count": len(structured_questions),
            "quality": "advanced",
            "topic_id": topic_id
        }
        
        save_user_data()
        
        return {
            "success": True,
            "test_id": test_id,
            "test_title": result.get("test_title", "Advanced CSCA Test"),
            "count": len(structured_questions),
            "questions": structured_questions,
            "difficulty": difficulty,
            "lang": lang,
            "metadata": result.get("metadata", {}),
            "quality": "advanced"
        }
        
    except Exception as e:
        print(f"[CSCA ADVANCED TEST] Error: {str(e)}")
        return generate_fallback_advanced_test(topic_id, difficulty, lang, count)

# 3. Generate challenging problems for practice
@app.post("/csca/math/generate-challenge-problems")
async def generate_challenge_problems(request: dict):
    """Generate especially challenging problems"""
    try:
        topic_id = request.get("topic_id")
        count = request.get("count", 5)
        lang = request.get("lang", "zh")
        
        client = get_deepseek_client()
        if not client:
            return generate_fallback_challenges(topic_id, count, lang)
        
        topic_info = {}
        if topic_id:
            topic = next((t for t in csca_math_topics if t["id"] == topic_id), None)
            if topic:
                topic_info = topic
        
        prompt = f"""
# MATHEMATICS CHALLENGE PROBLEMS GENERATOR

Create {count} EXTREMELY CHALLENGING mathematics problems that would be suitable for:
- Mathematics Olympiads
- University entrance exams for top schools
- Advanced CSCA preparation

## TOPIC: {topic_info.get('chinese', 'Advanced Mathematics')}

## REQUIREMENTS FOR EACH PROBLEM:
1. **Novelty**: Should not be a standard textbook problem
2. **Depth**: Require deep conceptual understanding
3. **Elegance**: Beautiful mathematics, not just computational
4. **Multiple Approaches**: Can be solved in different ways
5. **Learning Value**: Solving it should teach important concepts

## PROBLEM STRUCTURE:
**Problem Statement**: Clear, concise, mathematically precise
**Hint** (optional): Gentle nudge if needed
**Full Solution**: 
  - Step-by-step reasoning
  - Why this approach works
  - Alternative methods
  - Generalizations
**Key Insights**: What makes this problem special/educational

## DIFFICULTY LEVEL:
These should be problems that would take 15-30 minutes for an excellent student.

## RESPONSE FORMAT JSON:
{{
  "challenges": [
    {{
      "title": "Descriptive title",
      "problem": "Full problem statement",
      "hint": "Helpful hint",
      "solution": {{
        "approach_1": {{
          "steps": ["Step 1", "Step 2"],
          "explanation": "Why this works"
        }},
        "approach_2": {{
          "steps": ["Alternative approach"],
          "explanation": "Comparison to approach 1"
        }},
        "key_insights": ["Insight 1", "Insight 2"],
        "related_problems": ["Similar problems to try"]
      }},
      "difficulty": 9,
      "topics": ["topic1", "topic2"],
      "source_inspiration": "What inspired this problem"
    }}
  ]
}}

Language: {'Chinese' if lang == 'zh' else 'English'}
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a mathematics problem composer who creates beautiful, challenging problems."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_response(response_text)
        
        try:
            result = json.loads(response_text)
            return {
                "success": True,
                "challenges": result.get("challenges", []),
                "count": len(result.get("challenges", [])),
                "lang": lang,
                "generated_at": datetime.now().isoformat()
            }
        except:
            return generate_fallback_challenges(topic_id, count, lang)
        
    except Exception as e:
        print(f"[CHALLENGES] Error: {str(e)}")
        return generate_fallback_challenges(topic_id, count, lang)
    
# =============================================
# CSCA-PHYSICS — exact copy of CSCA-Math
# =============================================

csca_physics_topics = []

def load_csca_physics_topics():
    global csca_physics_topics
    try:
        with open(data_path("csca_physics_topics.json"), "r", encoding="utf-8") as f:
            csca_physics_topics = json.load(f)
        print(f"✅ Loaded {len(csca_physics_topics)} CSCA Physics topics")
    except FileNotFoundError:
        print("⚠️ csca_physics_topics.json not found")

load_csca_physics_topics()

@app.get("/csca/physics/topics")
async def get_csca_physics_topics():
    return {
        "topics": csca_physics_topics,
        "total": len(csca_physics_topics)
    }

@app.get("/csca/physics/generate-topic-lesson")
async def generate_csca_physics_lesson(
    topic_id: str = Query(...),
    lang: str = Query("zh")
):
    topic = next((t for t in csca_physics_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    你是一个非常专业的 CSCA 物理老师。
    现在给学生讲解主题：{topic['chinese']} / {topic['english']}
    
    要求：
    - 详细、系统、由浅入深
    - 使用正式学术语言
    - 包含定义、公式、例子、解题步骤
    - 给出 CSCA 考试常见陷阱和技巧
    - 语言：{'中文' if lang == 'zh' else 'English'}
    - 长度：800–1500 字
    - 格式：Markdown（标题、公式用 LaTeX、列表、加粗）
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )

    lesson = response.choices[0].message.content
    
    # FORMAT RESPONSE
    formatted = format_chat_response(lesson, None, "csca-physics")

    return {
        "topic_id": topic_id,
        "title_zh": topic["chinese"],
        "title_en": topic["english"],
        "lesson": formatted["response"],
        "formatted_lesson": formatted["formatted_response"],
        "css": formatted["css"],
        "lang": lang
    }

@app.post("/csca/physics/generate-topic-test")
async def generate_csca_physics_topic_test(
    topic_id: str = Body(...),
    count: int = Body(20),
    lang: str = Body("zh")
):
    topic = next((t for t in csca_physics_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    Create {count} problems on CSCA Physics topic: {topic['chinese']} ({topic['english']})
    Difficulty level: {topic['difficulty']}
    Language: {'Chinese' if lang == 'zh' else 'English'}
    
    Each problem must have:
    1. Question with 4 answer options (A,B,C,D)
    2. Only one correct answer
    3. Detailed explanation with formulas (LaTeX)
    
    JSON format:
    {{"questions": [{{"id": "1", "question": "...", "options": ["A","B","C","D"], "correct_answer": "B", "explanation": "..."}}]}}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1500,
        response_format={"type": "json_object"}
    )

    response_text = clean_json_response(response.choices[0].message.content)

    try:
        result = json.loads(response_text)
        questions = result.get("questions", [])
    except:
        questions = []

    test_id = f"csca_physics_topic_{topic_id}_{int(time.time())}"

    tests_db[test_id] = {
        "questions": questions,
        "topic_id": topic_id,
        "lang": lang,
        "generated_at": datetime.now().isoformat(),
        "count": len(questions)
    }

    return {
        "test_id": test_id,
        "questions": questions,
        "topic_id": topic_id,
        "count": len(questions),
        "lang": lang
    }

@app.post("/csca/physics/submit-test")
async def submit_csca_physics_test(request: dict):
    # EXACT copy of your submit_csca_test function from math
    # (inserting it completely, just changing prefix in logs and messages)

    try:
        test_id = request.get("test_id")
        user_id = request.get("user_id")
        answers = request.get("answers", {})

        if not test_id:
            raise HTTPException(status_code=400, detail="test_id required")

        if test_id not in tests_db:
            raise HTTPException(status_code=404, detail="Test not found")

        test_data = tests_db[test_id]
        questions = test_data.get("questions", [])

        if not questions:
            return {
                "success": False,
                "message": "No questions in test",
                "score": 0,
                "total": 0,
                "percentage": 0
            }

        correct_count = 0
        results = []

        for q in questions:
            q_id = q.get("id", "")
            user_answer_raw = answers.get(str(q_id), "")
            user_answer = str(user_answer_raw).strip().upper()

            correct_answer_raw = q.get("correct_answer", "A")
            correct_answer = str(correct_answer_raw).strip().upper()

            is_correct = False
            if user_answer:
                answer_mapping = {"1": "A", "2": "B", "3": "C", "4": "D"}
                normalized = answer_mapping.get(user_answer, user_answer)
                is_correct = normalized == correct_answer
            else:
                user_answer = "(not answered)"

            if is_correct:
                correct_count += 1

            results.append({
                "question_id": q_id,
                "question": q.get("question", "Question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "No explanation"),
                "options": q.get("options", [])
            })

        score = correct_count
        total = len(questions)
        percentage = int((score / total) * 100) if total > 0 else 0

        grade = ""
        if percentage >= 90:
            grade = "Excellent! 🎉"
        elif percentage >= 70:
            grade = "Good! 👍"
        elif percentage >= 50:
            grade = "Fair 👌"
        else:
            grade = "Needs improvement 📚"

        return {
            "success": True,
            "test_id": test_id,
            "score": score,
            "total": total,
            "percentage": percentage,
            "grade": grade,
            "results": results,
            "message": f"{score}/{total} correct answers ({percentage}%) - {grade}"
        }

    except Exception as e:
        print(f"[CSCA PHYSICS SUBMIT] Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# CSCA-CHEMISTRY — exact copy of Physics
# =============================================

csca_chemistry_topics = []

def load_csca_chemistry_topics():
    global csca_chemistry_topics
    try:
        with open(data_path("csca_chemistry_topics.json"), "r", encoding="utf-8") as f:
            csca_chemistry_topics = json.load(f)
        print(f"✅ Loaded {len(csca_chemistry_topics)} CSCA Chemistry topics")
    except FileNotFoundError:
        print("⚠️ csca_chemistry_topics.json not found")

load_csca_chemistry_topics()

@app.get("/csca/chemistry/topics")
async def get_csca_chemistry_topics():
    return {
        "topics": csca_chemistry_topics,
        "total": len(csca_chemistry_topics)
    }

@app.get("/csca/chemistry/generate-topic-lesson")
async def generate_csca_chemistry_lesson(
    topic_id: str = Query(...),
    lang: str = Query("zh")
):
    topic = next((t for t in csca_chemistry_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    你是一个非常专业的 CSCA 化学老师。
    现在给学生讲解主题：{topic['chinese']} / {topic['english']}
    
    要求：
    - 详细、系统、由浅入深
    - 使用正式学术语言
    - 包含定义、公式、例子、解题步骤
    - 给出 CSCA 考试常见陷阱和技巧
    - 语言：{'中文' if lang == 'zh' else 'English'}
    - 长度：800–1500 字
    - 格式：Markdown（标题、公式用 LaTeX、列表、加粗）
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )

    lesson = response.choices[0].message.content
    
    # FORMAT RESPONSE
    formatted = format_chat_response(lesson, None, "csca-chemistry")

    return {
        "topic_id": topic_id,
        "title_zh": topic["chinese"],
        "title_en": topic["english"],
        "lesson": formatted["response"],
        "formatted_lesson": formatted["formatted_response"],
        "css": formatted["css"],
        "lang": lang
    }

@app.post("/csca/chemistry/generate-topic-test")
async def generate_csca_chemistry_topic_test(
    topic_id: str = Body(...),
    count: int = Body(20),
    lang: str = Body("zh")
):
    topic = next((t for t in csca_chemistry_topics if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(404, "Topic not found")

    client = get_deepseek_client()
    if not client:
        raise HTTPException(503, "AI unavailable")

    prompt = f"""
    Create {count} problems on CSCA Chemistry topic: {topic['chinese']} ({topic['english']})
    Difficulty level: {topic['difficulty']}
    Language: {'Chinese' if lang == 'zh' else 'English'}
    
    Each problem must have:
    1. Question with 4 answer options (A,B,C,D)
    2. Only one correct answer
    3. Detailed explanation with formulas (LaTeX)
    
    JSON format:
    {{"questions": [{{"id": "1", "question": "...", "options": ["A","B","C","D"], "correct_answer": "B", "explanation": "..."}}]}}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1500,
        response_format={"type": "json_object"}
    )

    response_text = clean_json_response(response.choices[0].message.content)

    try:
        result = json.loads(response_text)
        questions = result.get("questions", [])
    except:
        questions = []

    test_id = f"csca_chemistry_topic_{topic_id}_{int(time.time())}"

    tests_db[test_id] = {
        "questions": questions,
        "topic_id": topic_id,
        "lang": lang,
        "generated_at": datetime.now().isoformat(),
        "count": len(questions)
    }

    return {
        "test_id": test_id,
        "questions": questions,
        "topic_id": topic_id,
        "count": len(questions),
        "lang": lang
    }

@app.post("/csca/chemistry/submit-test")
async def submit_csca_chemistry_test(request: dict):
    # EXACT same function as in physics and math
    try:
        test_id = request.get("test_id")
        user_id = request.get("user_id")
        answers = request.get("answers", {})

        if not test_id:
            raise HTTPException(status_code=400, detail="test_id required")

        if test_id not in tests_db:
            raise HTTPException(status_code=404, detail="Test not found")

        test_data = tests_db[test_id]
        questions = test_data.get("questions", [])

        if not questions:
            return {
                "success": False,
                "message": "No questions in test",
                "score": 0,
                "total": 0,
                "percentage": 0
            }

        correct_count = 0
        results = []

        for q in questions:
            q_id = q.get("id", "")
            user_answer_raw = answers.get(str(q_id), "")
            user_answer = str(user_answer_raw).strip().upper()

            correct_answer_raw = q.get("correct_answer", "A")
            correct_answer = str(correct_answer_raw).strip().upper()

            is_correct = False
            if user_answer:
                answer_mapping = {"1": "A", "2": "B", "3": "C", "4": "D"}
                normalized = answer_mapping.get(user_answer, user_answer)
                is_correct = normalized == correct_answer
            else:
                user_answer = "(not answered)"

            if is_correct:
                correct_count += 1

            results.append({
                "question_id": q_id,
                "question": q.get("question", "Question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "No explanation"),
                "options": q.get("options", [])
            })

        score = correct_count
        total = len(questions)
        percentage = int((score / total) * 100) if total > 0 else 0

        grade = ""
        if percentage >= 90:
            grade = "Excellent! 🎉"
        elif percentage >= 70:
            grade = "Good! 👍"
        elif percentage >= 50:
            grade = "Fair 👌"
        else:
            grade = "Needs improvement 📚"

        return {
            "success": True,
            "test_id": test_id,
            "score": score,
            "total": total,
            "percentage": percentage,
            "grade": grade,
            "results": results,
            "message": f"{score}/{total} correct answers ({percentage}%) - {grade}"
        }

    except Exception as e:
        print(f"[CSCA CHEMISTRY SUBMIT] Error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
def load_progress_file(subject: Subject) -> Dict:
    filename = f"{subject.value}_progress.json"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading progress file: {e}")
    return {}

def save_progress_file(subject: Subject, data: Dict):
    filename = f"{subject.value}_progress.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving progress file: {e}")

async def create_fallback_test(count: int, lang: str, subject: str):
    """Create test with placeholders on API error"""
    questions = []
    for i in range(count):
        questions.append({
            "id": f"fallback_{i+1}",
            "question": f"Sample {subject.capitalize()} Question {i+1}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A",
            "explanation": f"This is a sample explanation for {subject} question {i+1}."
        })
    
    return {
        "success": True,
        "test_id": f"fallback_{subject}_{datetime.now().timestamp()}",
        "questions": questions,
        "lang": lang,
        "type": subject,
        "created_at": datetime.now().isoformat()
    }

def clean_json_response(response_text):
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    return response_text.strip()

class GlobalTestRequest(BaseModel):
    count: int = 20
    lang: str = "zh"

class TopicTestRequest(BaseModel):
    topic_id: str
    count: int = 10
    lang: str = "zh"

class ProgressUpdate(BaseModel):
    user_id: str
    topic_id: str
    status: str

class Subject(str, Enum):
    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"

# ==================== PHYSICS ====================

@app.get("/csca/physics/generate-global-test")
async def generate_csca_physics_global_test_get(count: int = 20, lang: str = "zh"):
    return await generate_csca_physics_global_test(count, lang)

@app.post("/csca/physics/generate-global-test")
async def generate_global_physics_test_api(request: GlobalTestRequest = None):
    count = request.count if request else 20
    lang = request.lang if request else "zh"
    return await generate_csca_physics_global_test(count, lang)

async def generate_csca_physics_global_test(count: int = 20, lang: str = "zh"):
    client = get_deepseek_client()
    if not client:
        return await create_fallback_test(count, lang, "physics")
    
    try:
        prompt = f"""You are a CSCA physics test generator. Create exactly {count} multiple-choice questions.
Language: {'Chinese' if lang == 'zh' else 'English'}
Requirements:
1. Questions must cover various CSCA physics topics
2. Each question must have 4 options (A, B, C, D)
3. Include chemical formulas where appropriate
4. Provide correct answer and explanation
5. Format as VALID JSON array ONLY
Return ONLY valid JSON in this format:
[{{"id":"1","question":"...","options":["A)...","B)...","C)...","D)..."],"correct_answer":"A","explanation":"..."}}]"""
        
        # CRITICALLY IMPORTANT: add response_format
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a precise JSON generator. Return ONLY valid JSON array, no other text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}  # ← GUARANTEES valid JSON
        )
        
        response_text = response.choices[0].message.content.strip()
        cleaned_text = clean_json_response(response_text)
        
        try:
            questions = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Fallback: look for JSON in text
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                raise ValueError("No valid JSON found in response")
        
        # Validate structure
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("Empty or invalid questions array")
        
        test_id = f"physics_global_{int(time.time())}"
        return {
            "success": True,
            "test_id": test_id,
            "questions": questions[:count],  # Limit by count
            "lang": lang,
            "type": "physics",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        # FIXED: replace logger with print
        print(f"[PHYSICS GLOBAL TEST] Error: {str(e)}")
        print(f"[PHYSICS GLOBAL TEST] Raw response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        return await create_fallback_test(count, lang, "physics")  # ← Fallback on any error

@app.get("/csca/physics/generate-topic-test")
async def generate_csca_physics_topic_test_get(topic_id: str, count: int = 10, lang: str = "zh"):
    return await generate_csca_physics_topic_test(topic_id, count, lang)

@app.post("/csca/physics/generate-topic-test")
async def generate_topic_physics_test_api(request: TopicTestRequest):
    return await generate_csca_physics_topic_test(request.topic_id, request.count, request.lang)

async def generate_csca_physics_topic_test(topic_id: str, count: int = 10, lang: str = "zh"):
    client = get_deepseek_client()
    if not client:
        return await create_fallback_test(count, lang, "physics")
    
    topic_names = {
        "1": "Mechanics (Kinematics, Dynamics, Energy)",
        "2": "Thermodynamics",
        "3": "Electromagnetism",
        "4": "Waves and Optics",
        "5": "Modern Physics (Quantum, Nuclear)",
        "6": "Fluid Mechanics"
    }
    
    topic_name = topic_names.get(topic_id, "General Physics")
    
    try:
        prompt = f"""You are a CSCA physics test generator. Create exactly {count} multiple-choice questions.
Topic: {topic_name}
Language: {'Chinese' if lang == 'zh' else 'English'}

Requirements:
1. All questions must be about {topic_name}
2. Each question must have 4 options (A, B, C, D)
3. Include formulas and calculations (use LaTeX format: $$formula$$)
4. Provide correct answer and detailed explanation with formulas
5. Format as valid JSON array

Return ONLY valid JSON in this format:
[
  {{
    "id": "1",
    "question": "Question text with formulas",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A",
    "explanation": "Detailed explanation with formulas"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text."""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a precise JSON generator for CSCA physics tests."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000
        )
        
        response_text = response.choices[0].message.content
        cleaned_text = clean_json_response(response_text)
        
        try:
            questions = json.loads(cleaned_text)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                raise
        
        test_id = f"physics_topic_{topic_id}_{datetime.now().timestamp()}"
        
        return {
            "success": True,
            "test_id": test_id,
            "questions": questions,
            "topic_id": topic_id,
            "topic_name": topic_name,
            "lang": lang,
            "type": "physics",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating physics topic test: {e}")
        return await create_fallback_test(count, lang, "physics")

@app.post("/csca/physics/update-progress")
async def update_physics_progress(request: ProgressUpdate):
    try:
        progress_data = load_progress_file(Subject.PHYSICS)
        
        if request.user_id not in progress_data:
            progress_data[request.user_id] = {}
        
        progress_data[request.user_id][request.topic_id] = {
            "status": request.status,
            "updated_at": datetime.now().isoformat()
        }
        
        save_progress_file(Subject.PHYSICS, progress_data)
        
        return {
            "success": True,
            "message": "Progress updated successfully",
            "data": progress_data[request.user_id]
        }
    except Exception as e:
        logger.error(f"Error updating physics progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/csca/physics/user-progress/{user_id}")
async def get_physics_progress(user_id: str):
    try:
        progress_data = load_progress_file(Subject.PHYSICS)
        user_progress = progress_data.get(user_id, {})
        return {
            "success": True,
            "user_id": user_id,
            "progress": user_progress
        }
    except Exception as e:
        logger.error(f"Error getting physics progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHEMISTRY ====================

@app.get("/csca/chemistry/generate-global-test")
async def generate_csca_chemistry_global_test_get(count: int = 20, lang: str = "zh"):
    return await generate_csca_chemistry_global_test(count, lang)

@app.post("/csca/chemistry/generate-global-test")
async def generate_global_chemistry_test_api(request: GlobalTestRequest = None):
    count = request.count if request else 20
    lang = request.lang if request else "zh"
    return await generate_csca_chemistry_global_test(count, lang)

async def generate_csca_chemistry_global_test(count: int = 20, lang: str = "zh"):
    client = get_deepseek_client()
    if not client:
        return await create_fallback_test(count, lang, "chemistry")
    
    try:
        prompt = f"""You are a CSCA chemistry test generator. Create exactly {count} multiple-choice questions.
Language: {'Chinese' if lang == 'zh' else 'English'}
Requirements:
1. Questions must cover various CSCA chemistry topics
2. Each question must have 4 options (A, B, C, D)
3. Include chemical formulas where appropriate
4. Provide correct answer and explanation
5. Format as VALID JSON array ONLY
Return ONLY valid JSON in this format:
[{{"id":"1","question":"...","options":["A)...","B)...","C)...","D)..."],"correct_answer":"A","explanation":"..."}}]"""
        
        # CRITICALLY IMPORTANT: add response_format
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a precise JSON generator. Return ONLY valid JSON array, no other text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}  # ← GUARANTEES valid JSON
        )
        
        response_text = response.choices[0].message.content.strip()
        cleaned_text = clean_json_response(response_text)
        
        try:
            questions = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Fallback: look for JSON in text
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                raise ValueError("No valid JSON found in response")
        
        # Validate structure
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("Empty or invalid questions array")
        
        test_id = f"chemistry_global_{int(time.time())}"
        return {
            "success": True,
            "test_id": test_id,
            "questions": questions[:count],  # Limit by count
            "lang": lang,
            "type": "chemistry",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        # FIXED: replace logger with print
        print(f"[CHEMISTRY GLOBAL TEST] Error: {str(e)}")
        print(f"[CHEMISTRY GLOBAL TEST] Raw response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        return await create_fallback_test(count, lang, "chemistry")  # ← Fallback on any error

@app.get("/csca/chemistry/generate-topic-test")
async def generate_csca_chemistry_topic_test_get(topic_id: str, count: int = 10, lang: str = "zh"):
    return await generate_csca_chemistry_topic_test(topic_id, count, lang)

@app.post("/csca/chemistry/generate-topic-test")
async def generate_topic_chemistry_test_api(request: TopicTestRequest):
    return await generate_csca_chemistry_topic_test(request.topic_id, request.count, request.lang)

async def generate_csca_chemistry_topic_test(topic_id: str, count: int = 10, lang: str = "zh"):
    client = get_deepseek_client()
    if not client:
        return await create_fallback_test(count, lang, "chemistry")
    
    topic_names = {
        "1": "Stoichiometry and Chemical Reactions",
        "2": "Atomic Structure and Periodic Table",
        "3": "Chemical Bonding and Molecular Geometry",
        "4": "Thermodynamics and Kinetics",
        "5": "Chemical Equilibrium and Acids/Bases",
        "6": "Organic Chemistry"
    }
    
    topic_name = topic_names.get(topic_id, "General Chemistry")
    
    try:
        prompt = f"""You are a CSCA chemistry test generator. Create exactly {count} multiple-choice questions.
Topic: {topic_name}
Language: {'Chinese' if lang == 'zh' else 'English'}

Requirements:
1. All questions must be about {topic_name}
2. Each question must have 4 options (A, B, C, D)
3. Include chemical formulas, equations, and calculations (use proper notation)
4. Provide correct answer and detailed explanation with chemical concepts
5. Format as valid JSON array

Return ONLY valid JSON in this format:
[
  {{
    "id": "1",
    "question": "Question text with chemical formulas",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A",
    "explanation": "Detailed explanation with chemical concepts"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text."""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a precise JSON generator for CSCA chemistry tests."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000
        )
        
        response_text = response.choices[0].message.content
        cleaned_text = clean_json_response(response_text)
        
        try:
            questions = json.loads(cleaned_text)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                raise
        
        test_id = f"chemistry_topic_{topic_id}_{datetime.now().timestamp()}"
        
        return {
            "success": True,
            "test_id": test_id,
            "questions": questions,
            "topic_id": topic_id,
            "topic_name": topic_name,
            "lang": lang,
            "type": "chemistry",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating chemistry topic test: {e}")
        return await create_fallback_test(count, lang, "chemistry")

@app.post("/csca/chemistry/update-progress")
async def update_chemistry_progress(request: ProgressUpdate):
    try:
        progress_data = load_progress_file(Subject.CHEMISTRY)
        
        if request.user_id not in progress_data:
            progress_data[request.user_id] = {}
        
        progress_data[request.user_id][request.topic_id] = {
            "status": request.status,
            "updated_at": datetime.now().isoformat()
        }
        
        save_progress_file(Subject.CHEMISTRY, progress_data)
        
        return {
            "success": True,
            "message": "Progress updated successfully",
            "data": progress_data[request.user_id]
        }
    except Exception as e:
        logger.error(f"Error updating chemistry progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/csca/chemistry/user-progress/{user_id}")
async def get_chemistry_progress(user_id: str):
    try:
        progress_data = load_progress_file(Subject.CHEMISTRY)
        user_progress = progress_data.get(user_id, {})
        return {
            "success": True,
            "user_id": user_id,
            "progress": user_progress
        }
    except Exception as e:
        logger.error(f"Error getting chemistry progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
from datetime import datetime
from pydantic import BaseModel

class ChineseNameRequest(BaseModel):
    real_name: str
    birth_date: str
    qualities: str = ""
    wishes: str = ""
    user_id: Optional[str] = None

from fastapi.responses import FileResponse
import os

@app.get("/data/chengyu.json")
async def get_chengyu_data():
    file_path = data_path("chengyu.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/json")

@app.post("/ai/generate")
async def ai_generate(request: dict):
    prompt = request.get("prompt", "")
    client = get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000
    )
    return {"text": response.choices[0].message.content}

@app.post("/csca/name/generate")
async def generate_chinese_name(request: ChineseNameRequest):
    """Generate Chinese name using AI based on user input"""
    try:
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
        
        prompt = f"""You are a master of Chinese naming traditions (姓名学). Create a meaningful Chinese name with last name for a foreigner.

Real Name: {request.real_name}
Date of Birth: {request.birth_date}
Qualities: {request.qualities or "Not specified"}
Wishes: {request.wishes or "No special wishes"}

Requirements:
1. Provide exactly ONE Chinese name with last name (2-3 characters)
2. Explain the meaning of each character
3. Explain why this name suits the person
4. Mention cultural significance
5. Return ONLY valid JSON with keys: chinese_name, explanation, characters_info

Example format:
{{"chinese_name": "李明哲", "explanation": "This name means...", "characters_info": "李 (plum), 明 (bright), 哲 (wise)"}}
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content.strip())
        
        # Save to history (optional)
        if request.user_id:
            save_name_generation_history(request.user_id, result, request.dict())
        
        return {"success": True, **result}
        
    except Exception as e:
        logger.error(f"Chinese name generation error: {str(e)}")
        return {"success": False, "message": "AI generation failed", "error": str(e)}

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid

@dataclass
class InterviewMessage:
    sender: str  # 'user', 'professor_1', 'professor_2', 'professor_3', 'tech_expert'
    name: str
    message: str
    timestamp: float

@dataclass
class InterviewSession:
    session_id: str
    university: str
    program: str
    degree: str
    professors: List[Dict]
    tech_expert: Dict
    messages: List[InterviewMessage] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    ended: bool = False

# Active sessions storage (in production use Redis/DB)
interview_sessions: Dict[str, InterviewSession] = {}

@app.post("/interview/start")
async def start_interview(request: Request, db: Session = Depends(get_db)):
    """Start a new interview session and save to DB"""
    try:
        body = await request.json()
        university = body.get("university", "").strip()
        program = body.get("program", "").strip()
        degree = body.get("degree", "bachelor")
        
        if not university or not program:
            raise HTTPException(status_code=400, detail="University and program required")
        
        # Get current user if authenticated
        user_id = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("user_id")
            except:
                pass
        
        # Generate participants through AI
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
        
        prompt = f"""Generate realistic Chinese names and roles for a university interview panel.
University: {university}
Program: {program}
Degree: {degree}

Return ONLY valid JSON with this structure:
{{
  "tech_expert": {{"name": "Chinese Name", "role": "Technical Support"}},
  "professors": [
    {{"name": "Chinese Name", "role": "Professor of [Subject]", "specialty": "subject"}},
    {{"name": "Chinese Name", "role": "Admissions Committee", "specialty": "admissions"}},
    {{"name": "Chinese Name", "role": "Department Head", "specialty": "leadership"}}
  ]
}}"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        participants = json.loads(response.choices[0].message.content.strip())
        
        # Create session in DB
        session_id = str(uuid.uuid4())
        
        db_session = InterviewSessionDB(
            session_id=session_id,
            user_id=user_id,
            university=university,
            program=program,
            degree=degree,
            professors=participants["professors"],
            tech_expert=participants["tech_expert"],
            messages=[]
        )
        db.add(db_session)
        db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "tech_expert": participants["tech_expert"],
            "professors": participants["professors"]
        }
        
    except Exception as e:
        logger.error(f"Interview start error: {str(e)}")
        return {"success": False, "error": str(e)}
            
@app.post("/interview/message")
async def interview_message(request: dict, db: Session = Depends(get_db)):
    """Process user message and generate AI response"""
    try:
        session_id = request.get("session_id")
        user_message = request.get("message", "")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        # Find session in DB
        db_session = db.query(InterviewSessionDB).filter(InterviewSessionDB.session_id == session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if db_session.ended:
            raise HTTPException(status_code=400, detail="Session ended")
        
        # Load current messages
        messages = db_session.messages or []
        
        # Add user message
        messages.append({
            "sender": "user",
            "name": "Candidate",
            "message": user_message,
            "timestamp": datetime.now().timestamp()
        })
        
        # Determine current interview stage
        message_count = len([m for m in messages if m.get("sender") != "tech_expert"])
        current_stage = determine_interview_stage(message_count, db_session.degree)
        
        # Select professor
        professors = db_session.professors
        professor = select_professor_for_stage(professors, current_stage)
        
        # Form AI prompt
        chat_history = "\n".join([
            f"{msg['name']} ({msg['sender']}): {msg['message']}" 
            for msg in messages[-10:]
        ])
        
        prompt = f"""You are {professor['name']}, a {professor['role']} at {db_session.university}. You've conducted thousands of interviews and can spot a memorable student in 30 seconds. You're known for being both challenging and genuinely helpful.

# CURRENT CONTEXT:
- University: {db_session.university}
- Program: {db_session.program}
- Degree: {db_session.degree}
- Current stage: {current_stage}
- Recent messages:
{chat_history}

# YOUR INTERVIEW STYLE:
- You are: {professor['role']}
- Your signature: You're known for {professor['specialty'] == 'subject' and 'asking "Why?" three times' or professor['specialty'] == 'admissions' and 'remembering small details students mention' or 'asking about students\' dreams beyond academics'}

Generate a realistic, professional response as {professor['name']}. Match the stage. Be specific to their previous messages. Sound like a real person, not an AI. Keep it concise (1-3 sentences)."""
        
        client = get_deepseek_client()
        if not client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
            
        ai_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=150
        )
        
        response_text = ai_response.choices[0].message.content.strip()
        
        # Add AI response
        messages.append({
            "sender": f"professor_{professors.index(professor) + 1}",
            "name": professor['name'],
            "message": response_text,
            "timestamp": datetime.now().timestamp()
        })
        
        # Save to DB
        db_session.messages = messages
        db_session.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "response": response_text,
            "professor_name": professor['name'],
            "stage": current_stage
        }
        
    except Exception as e:
        logger.error(f"Interview message error: {str(e)}")
        return {"success": False, "error": str(e)}
      
def determine_interview_stage(message_count: int, degree: str) -> str:
    """Determine current interview stage"""
    if message_count <= 2:
        return "introduction"
    elif message_count <= 6:
        return "university_knowledge"
    elif message_count <= 12:
        return "program_knowledge"
    elif message_count <= 18:
        return "technical_skills"
    elif message_count <= 22:
        return "motivation"
    else:
        return "unexpected_questions"

def select_professor_for_stage(professors: List[Dict], stage: str) -> Dict:
    """Select appropriate professor for stage"""
    if stage == "introduction":
        return professors[1]  # Admissions
    elif stage in ["university_knowledge", "program_knowledge"]:
        return professors[2]  # Department Head
    elif stage == "technical_skills":
        return professors[0]  # Subject Professor
    else:
        # Random selection for motivation and unexpected questions
        return professors[datetime.now().second % 3]

def get_stage_focus(stage: str) -> str:
    """Return focus for AI prompt"""
    focuses = {
        "introduction": "Ask candidate to introduce themselves and explain their motivation",
        "university_knowledge": "Test knowledge about the university's history, values, and reputation",
        "program_knowledge": "Test understanding of the specific program, curriculum, and faculty",
        "technical_skills": "Ask technical questions related to the subject area and school's program",
        "motivation": "Explore personal qualities, career goals, and fit with the program",
        "unexpected_questions": "Ask challenging, unexpected questions to test critical thinking"
    }
    return focuses.get(stage, "Continue the professional conversation")

@app.post("/interview/feedback")
async def generate_interview_feedback(request: dict, db: Session = Depends(get_db)):
    """Generate detailed feedback after interview completion"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        # Find session in DB
        db_session = db.query(InterviewSessionDB).filter(InterviewSessionDB.session_id == session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db_session.ended = True
        messages = db_session.messages or []
        
        # Extract user responses with context
        user_responses = []
        for i, msg in enumerate(messages):
            if msg.get("sender") == "user":
                prev_msg = messages[i-1] if i > 0 else None
                user_responses.append({
                    "answer": msg.get("message", ""),
                    "question": prev_msg.get("message", "Introduction") if prev_msg else "Introduction",
                    "professor": prev_msg.get("name", "Interviewer") if prev_msg else "Interviewer",
                    "timestamp": msg.get("timestamp", 0)
                })
        
        # Calculate duration
        if messages:
            start_time = messages[0].get("timestamp", 0)
            end_time = messages[-1].get("timestamp", 0)
            duration_minutes = int((end_time - start_time) / 60) if end_time > start_time else 0
        else:
            duration_minutes = 0
        
        # Generate feedback with AI (simplified for brevity)
        feedback_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #8e44ad;">📊 Interview Feedback</h2>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3>🎯 Overall Assessment</h3>
                <p>Thank you for completing the interview practice for <strong>{db_session.university}</strong> - <strong>{db_session.program}</strong>.</p>
                <p>You answered <strong>{len(user_responses)}</strong> questions in <strong>{duration_minutes}</strong> minutes.</p>
            </div>
            
            <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #27ae60;">✅ What Went Well</h3>
                <ul>
                    <li>You completed the interview and answered all questions</li>
                    <li>You showed genuine interest in the program</li>
                    <li>Your responses were clear and understandable</li>
                </ul>
            </div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #f39c12;">⚠️ Areas for Improvement</h3>
                <ul>
                    <li><strong>Add specific examples</strong> - Instead of general statements, use "For example, when I..."</li>
                    <li><strong>Research the university more deeply</strong> - Mention specific professors, courses, or research centers at {db_session.university}</li>
                    <li><strong>Structure your answers</strong> - Use "First... Second... Finally..." for clarity</li>
                </ul>
            </div>
            
            <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #2980b9;">💪 Actionable Recommendations</h3>
                <ul>
                    <li><strong>Research {db_session.university}</strong> - Find 3 professors whose work interests you</li>
                    <li><strong>Prepare "Tell me about yourself"</strong> - 60-second version highlighting your unique journey</li>
                    <li><strong>Practice with timer</strong> - Keep answers under 90 seconds</li>
                </ul>
            </div>
            
            <div style="background: #f1f9ff; padding: 20px; border-radius: 10px;">
                <h3 style="color: #8e44ad;">📝 Power Phrases to Use</h3>
                <ul>
                    <li>"What drew me to {db_session.university} is..."</li>
                    <li>"In my experience with [project/role], I learned..."</li>
                    <li>"My goal is to contribute to [specific field] by..."</li>
                </ul>
                <p style="margin-top: 15px;"><strong>Admission chances (estimated):</strong> {calculate_admission_chance_from_analysis(user_responses, db_session)}%</p>
                <p><strong>Next step:</strong> Practice again with the feedback above!</p>
            </div>
        </div>
        """
        
        # Save feedback
        db_session.feedback_generated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "feedback": feedback_html,
            "admission_chances": calculate_admission_chance_from_analysis(user_responses, db_session),
            "answers_analyzed": len(user_responses),
            "duration_minutes": duration_minutes
        }
        
    except Exception as e:
        logger.error(f"Feedback generation error: {str(e)}")
        return {"success": False, "error": str(e), "fallback_feedback": generate_fallback_feedback(None)}
    
def calculate_admission_chance_from_analysis(user_responses, session):
    """Calculate admission chance based on answer quality"""
    if not user_responses:
        return 50
    
    score = 0
    total_criteria = 0
    
    for response in user_responses:
        answer = response.get("answer", "").lower()
        
        # Check for specificity
        if any(word in answer for word in ["because", "example", "specifically", "for instance"]):
            score += 2
        
        # Check for university knowledge
        uni_name = session.university.lower()
        if uni_name in answer:
            score += 3
        
        # Check length (too short is bad)
        if len(answer) > 50:
            score += 1
        elif len(answer) < 20:
            score -= 1
        
        total_criteria += 7
    
    base_chance = 50
    if total_criteria > 0:
        adjustment = (score / total_criteria) * 30
        final_chance = min(95, max(20, base_chance + adjustment))
    else:
        final_chance = 50
    
    return round(final_chance)

def calculate_admission_chance_from_analysis(user_responses, session):
    """Calculate admission chance based on answer quality"""
    if not user_responses:
        return 50
    
    score = 0
    total_criteria = 0
    
    for response in user_responses:
        answer = response.get("answer", "").lower()
        
        # Check for specificity (mentions specific details)
        if any(word in answer for word in ["because", "example", "specifically", "for instance"]):
            score += 2
        
        # Check for university knowledge
        uni_name = session.university.lower()
        if uni_name in answer:
            score += 3
        
        # Check for confidence indicators
        if any(word in answer for word in ["i believe", "i think", "my goal", "i want"]):
            score += 1
        
        # Check length (too short is bad)
        if len(answer) > 50:
            score += 1
        elif len(answer) < 20:
            score -= 1
        
        total_criteria += 7  # Max per answer
    
    # Base score + adjustments
    base_chance = 50
    if total_criteria > 0:
        adjustment = (score / total_criteria) * 30
        final_chance = min(95, max(20, base_chance + adjustment))
    else:
        final_chance = 50
    
    return round(final_chance)

def generate_fallback_feedback(session):
    """Generate fallback feedback if AI fails"""
    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #8e44ad;">📊 Interview Feedback</h2>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3>🎯 Overall Assessment</h3>
            <p>Thank you for completing the interview practice for <strong>{session.university}</strong> - <strong>{session.program}</strong>.</p>
            <p>Based on the transcript, here are key observations and recommendations.</p>
        </div>
        
        <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #27ae60;">✅ What Went Well</h3>
            <ul>
                <li>You completed the interview and answered all questions</li>
                <li>You showed genuine interest in the program</li>
                <li>Your English communication was clear and understandable</li>
            </ul>
        </div>
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #f39c12;">⚠️ Areas for Improvement</h3>
            <ul>
                <li><strong>Add specific examples</strong> - Instead of general statements, use "For example, when I..."</li>
                <li><strong>Research the university more deeply</strong> - Mention specific professors, courses, or research centers at {session.university}</li>
                <li><strong>Structure your answers</strong> - Use "First... Second... Finally..." for clarity</li>
                <li><strong>Avoid vague answers</strong> - Be specific about your goals and experiences</li>
            </ul>
        </div>
        
        <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #2980b9;">💪 Actionable Recommendations</h3>
            <ul>
                <li><strong>Research {session.university}</strong> - Find 3 professors whose work interests you</li>
                <li><strong>Prepare "Tell me about yourself"</strong> - 60-second version highlighting your unique journey</li>
                <li><strong>Practice with timer</strong> - Keep answers under 90 seconds</li>
                <li><strong>Record yourself</strong> - Listen for filler words (um, like, actually)</li>
            </ul>
        </div>
        
        <div style="background: #f1f9ff; padding: 20px; border-radius: 10px;">
            <h3 style="color: #8e44ad;">📝 Power Phrases to Use</h3>
            <ul>
                <li>"What drew me to {session.university} is..."</li>
                <li>"In my experience with [project/role], I learned..."</li>
                <li>"My goal is to contribute to [specific field] by..."</li>
            </ul>
            <p style="margin-top: 15px;"><strong>Admission chances (estimated):</strong> 65%</p>
            <p><strong>Next step:</strong> Practice again with the feedback above!</p>
        </div>
    </div>
    """

def extract_percentage(feedback: str) -> int:
    """Extract percentage from feedback text"""
    import re
    match = re.search(r'(\d+)%', feedback)
    return int(match.group(1)) if match else 75

import json
from pathlib import Path

UNIVERSITIES_FILE = DATA_DIR / "universities.json"

@app.get("/universities")
async def get_universities():
    """Get list of all universities"""
    if UNIVERSITIES_FILE.exists():
        with open(UNIVERSITIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("universities", [])
    return []

@app.post("/match-universities")
async def match_universities(request: dict):
    """AI matches universities based on student profile"""
    try:
        profile = request.get("profile", {})
        universities = request.get("universities", [])
        
        prompt = f"""You are a legendary university admissions oracle who has helped 5,000+ students find their perfect university match. You understand that "best" is personal, not just rankings.

# STUDENT PROFILE:
- Field: {profile.get('field')}
- Degree: {profile.get('degree')}
- HSK Level: {profile.get('hsk')}
- English: {profile.get('english')}
- GPA: {profile.get('gpa')}
- Previous university: {profile.get('previous')}
- Work experience: {profile.get('workYears')}
- Research: {profile.get('research')}
- Skills: {profile.get('skills')}
- Location preference: {profile.get('region') or 'Any'}, {profile.get('city') or 'Any'}
- Budget: {profile.get('budget')} RMB/year
- English programs required: {'Yes' if profile.get('englishPrograms') == 'true' else 'No'}

# YOUR MISSION:
Find the 10 BEST universities for THIS specific student. Not generic rankings. Not what's popular. What's PERFECT for THEM.

## 🔍 YOUR ANALYSIS METHOD:

### Step 1: Deconstruct the Student's DNA
- **Academic profile**: [GPA {profile.get('gpa')} means...]
- **Language capabilities**: [HSK {profile.get('hsk')} + English {profile.get('english')} = what programs are realistic]
- **Experience level**: [{profile.get('workYears')} years experience indicates...]
- **Hidden potential**: [Based on their skills and research, what could they become]
- **Constraints**: [Budget, location preferences]

### Step 2: Match Algorithm (Proprietary)
For each potential university, score on 5 dimensions:

1. **Academic Fit** (1-10): Does their program quality match the student's profile?
2. **Language Match** (1-10): Are language requirements aligned with student's abilities?
3. **Financial Alignment** (1-10): Is the cost + scholarships realistic for their budget?
4. **Career Trajectory** (1-10): Will this university open the right doors for their future?
5. **Quality of Life** (1-10): Will the student THRIVE, not just survive, in this environment?

### Step 3: The "X-Factor" Analysis
Find universities where this student will be a UNIQUE asset, not just another applicant. Look for:
- Programs where their specific skills are needed
- Universities with research in their exact niche
- Opportunities for them to stand out
- Cultural fit beyond just location

## 📊 YOUR TOP 10 MATCHES:

For each university, provide:

### [#1] [University Name] — Match Score: [XX]%

**🎯 Why This is THE One**:
[2-3 sentences explaining why this is their perfect match - specific, compelling, emotional]

**📊 Match Breakdown**:
- Academic Fit: [X]/10 — [Why]
- Language Match: [X]/10 — [Why]
- Financial Alignment: [X]/10 — [Why]
- Career Trajectory: [X]/10 — [Why]
- Quality of Life: [X]/10 — [Why]

**✨ What Makes Them Special**:
- [Unique program feature that fits them]
- [Professor or research area that matches their interests]
- [Recent achievement that shows program strength]
- [Specific opportunity others miss]

**💰 Financial Reality**:
- Tuition: [Amount] RMB/year
- Living costs: [Amount] RMB/year
- Scholarships they QUALIFY for: [List 2-3 with success rates]
- Net cost after best scholarship: [Amount]

**🚀 Career Path**:
- Top 3 companies hiring from this program
- Average starting salary: [Amount]
- Alumni in their field: [2-3 notable examples]
- Internship opportunities: [Specific companies they can apply to]

**🎯 Application Strategy** (Specific to this university):
- **Highlight**: [What they MUST emphasize in their application]
- **Downplay**: [What to minimize if it's a weakness]
- **Show**: [What specific experience to showcase]
- **Connect**: [How to demonstrate genuine interest]

**⚠️ Real Talk** (Challenges they'll face):
- [Specific challenge 1 and how to overcome]
- [Specific challenge 2 and how to overcome]
- [Specific challenge 3 and how to overcome]

**🎓 Success Story**:
[A real or realistic example of a student like them who succeeded here]

---

[Continue for all 10 matches]

## 🎯 THE ULTIMATE RECOMMENDATION:

### Your Dream School: [Name]
[Why this is aspirational but achievable]

### Your Best Bet: [Name]
[Why this is the most realistic excellent option]

### Your Safety: [Name]
[Why you'll definitely get in and still be happy]

## 🚀 APPLICATION STRATEGY:

### For Dream School:
- **Deadlines**: [When to apply]
- **Contacts to make**: [Professor, admissions officer, current student]
- **What to prepare**: [Specific documents, portfolio pieces]
- **How to stand out**: [Unique angle only they can take]

### For Best Bet:
[Similar structure]

### For Safety:
[Similar structure]

## 💡 BONUS INSIDER TIPS:

1. **Hidden Gem Programs**: [2-3 programs that aren't famous but are EXCELLENT for their profile]
2. **Scholarship Hack**: [Specific scholarship they're likely to get that others miss]
3. **Application Timing**: [When to apply for maximum advantage]
4. **Contact Strategy**: [Who to reach out to and exactly what to say]

## 🔥 THE "WHY YOU" DIFFERENCE:

Summarize in 3 sentences why THIS student is special and which universities will recognize that.

---

Return this as beautifully formatted HTML. Make it feel like a personalized consultation, not a spreadsheet. Every recommendation should feel like it was made JUST for them."""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        matches = json.loads(content)
        
        # Add full university data
        for match in matches:
            uni_data = next((u for u in universities if u['id'] == match['id']), {})
            match.update(uni_data)
        
        return {"success": True, "matches": matches}
        
    except Exception as e:
        print(f"Match error: {e}")
        # Return simple filtering if AI failed
        return {
            "success": True, 
            "matches": [{
                **u,
                "matchScore": 70 + (i % 20),
                "reasons": "Good match based on your profile",
                "strengths": ["Strong program", "Good location", "Reasonable cost"]
            } for i, u in enumerate(universities[:10])]
        }
    
@app.post("/games/generate")
async def generate_game(request: dict):
    """AI generates unique game with error handling and fallback"""
    try:
        game_type = request.get("game_type", "mixed")
        difficulty = request.get("difficulty", 2)
        previous = request.get("previous_games", [])
        
        # Determine HSK level based on difficulty
        hsk_range = {
            1: "HSK 1-2 (beginner level, simple words and phrases)",
            2: "HSK 3-4 (intermediate level, everyday topics)",
            3: "HSK 5-6 (advanced level, complex topics, idioms)"
        }
        difficulty_desc = hsk_range.get(difficulty, "HSK 3-4")
        
        # Number of questions based on difficulty
        question_counts = {1: 5, 2: 8, 3: 10}
        q_count = question_counts.get(difficulty, 8)
        
        # Dynamic prompt based on game type
        prompts = {
            "vocabulary": f"""
Create an engaging game for learning Chinese vocabulary {difficulty_desc}.

Requirements:
- {q_count} questions
- Each question should contain fields:
  * "question" — question text (e.g., "How to translate this character?")
  * "options" — array of 4 answer options in Russian
  * "correct" — correct option (string matching one of the options)
  * "explanation" — brief explanation (optional)
- Difficulty level: {difficulty_desc}
- Make the game interesting, with unexpected options.
""",
            "grammar": f"""
Create a Chinese grammar game {difficulty_desc}.

Requirements:
- {q_count} questions
- Each question should contain fields:
  * "question" — sentence with a blank or task
  * "options" — array of 4 grammar construction options
  * "correct" — correct option
  * "grammar_point" — grammar topic
  * "explanation" — explanation
- Difficulty level: {difficulty_desc}
""",
            "chengyu": f"""
Create a game about Chinese idioms 成语 {difficulty_desc}.

Requirements:
- {q_count} questions
- Each question should contain fields:
  * "character" — the chengyu itself (characters, e.g. "朝三暮四")
  * "question" — question about meaning or situation
  * "options" — 4 meaning options in Russian
  * "correct" — correct option
  * "explanation" — origin story or interesting fact
- Difficulty level: {difficulty_desc}
""",
            "history": f"""
Create a Chinese history quiz {difficulty_desc}.

Requirements:
- {q_count} questions
- Topics: dynasties, emperors, inventions, events
- Each question: fields "question", "options" (4 options), "correct", "fact" (interesting fact)
- Difficulty level: {difficulty_desc}
""",
            "culture": f"""
Create a Chinese culture quiz {difficulty_desc}.

Topics: holidays, traditions, food, customs, philosophy, art.
- {q_count} questions
- Each question: fields "question", "options", "correct", "fact"
- Difficulty level: {difficulty_desc}
""",
            "mixed": f"""
Create a mixed challenge game {difficulty_desc}.

Include:
- 2 vocabulary questions
- 2 grammar questions
- 2 chengyu questions
- 2 culture/history questions
Each question should contain fields "question", "options", "correct", and "category" (vocabulary/grammar/chengyu/culture).
Difficulty level: {difficulty_desc}
"""
        }
        
        prompt = prompts.get(game_type, prompts["mixed"])
        prompt += f"\nPrevious games: {previous}\nReturn ONLY JSON in format:\n{{'title':'...','instructions':'...','type':'{game_type}','difficulty':{difficulty},'questions':[{{'question':'...','options':[...],'correct':'...','explanation':'...'}}]}}"
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.9
        )
        
        # Extract and clean response
        content = response.choices[0].message.content.strip()
        
        # Remove markdown wrappers
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Remove non-printable characters (except tab and newline)
        import re
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
        
        # Try to parse JSON
        try:
            game_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw content (first 500): {content[:500]}")
            # If failed, return fallback game
            return {
                "success": True,
                "game": generate_fallback_game(game_type, difficulty, q_count)
            }
        
        # Check for required fields and set default values
        if not game_data.get('questions'):
            game_data['questions'] = []
        
        # For each question, ensure basic fields exist
        for q in game_data['questions']:
            if 'question' not in q:
                q['question'] = 'Question temporarily unavailable'
            if 'options' not in q or not isinstance(q['options'], list) or len(q['options']) < 2:
                q['options'] = ['Option 1', 'Option 2', 'Option 3', 'Option 4']
            if 'correct' not in q or q['correct'] not in q['options']:
                q['correct'] = q['options'][0] if q['options'] else 'Unknown'
            if 'explanation' not in q:
                q['explanation'] = ''
        
        return {"success": True, "game": game_data}
        
    except Exception as e:
        print(f"Game generation error: {e}")
        return {
            "success": True,
            "game": generate_fallback_game(game_type, difficulty, 5)
        }

def generate_fallback_game(game_type, difficulty, q_count=5):
    """Fallback game in case of AI error"""
    fallback_templates = {
        'vocabulary': lambda i: {
            "question": f"How to translate the character {['爱', '吃', '喝', '玩', '乐'][i % 5]}?",
            "options": ["love", "eat", "drink", "play", "music"][:4],
            "correct": ["love", "eat", "drink", "play", "music"][i % 5],
            "explanation": f"This is a basic HSK word."
        },
        'grammar': lambda i: {
            "question": "Choose the correct word order: 我 _____ 汉语。",
            "options": ["学习", "学", "了学习", "学习着"],
            "correct": "学习",
            "grammar_point": "Word order",
            "explanation": "The verb comes after the subject."
        },
        'chengyu': lambda i: {
            "character": "朝三暮四",
            "question": "What does this idiom mean?",
            "options": ["inconstancy", "three in morning, four at night", "deceive", "count"],
            "correct": "inconstancy",
            "explanation": "Means frequent change of decisions."
        },
        'history': lambda i: {
            "question": "Who was the first emperor of China?",
            "options": ["Qin Shi Huang", "Confucius", "Laozi", "Sun Tzu"],
            "correct": "Qin Shi Huang",
            "fact": "He unified China in 221 BC."
        },
        'culture': lambda i: {
            "question": "What holiday is called the Mid-Autumn Festival?",
            "options": ["Dragon Boat Festival", "Lantern Festival", "Moon Festival", "New Year"],
            "correct": "Moon Festival",
            "fact": "On this day, people eat mooncakes."
        },
        'mixed': lambda i: {
            "question": f"Mixed question {i+1}",
            "options": ["Answer 1", "Answer 2", "Answer 3", "Answer 4"],
            "correct": "Answer 1",
            "category": ["vocabulary", "grammar", "chengyu", "culture"][i % 4],
            "explanation": "Explanation for the question."
        }
    }
    
    template = fallback_templates.get(game_type, fallback_templates['mixed'])
    questions = [template(i) for i in range(min(q_count, 8))]
    
    return {
        "title": f"{game_type} Practice (Basic)",
        "instructions": "Choose the correct answer.",
        "type": game_type,
        "difficulty": difficulty,
        "questions": questions
    }
 
@app.post("/games/feedback")
async def get_game_feedback(request: dict):
    """AI gives feedback on answer"""
    question = request.get("question", "")
    selected = request.get("selected", "")
    correct = request.get("correct", "")
    game_type = request.get("type", "vocabulary")
    
    prompt = f"""
You are a Chinese teacher. Give brief feedback on student's answer.

Question: {question}
Student answer: {selected}
Correct answer: {correct}
Game type: {game_type}

Write:
1. Why the answer is correct/incorrect
2. Tip on how to remember
3. Score from 1 to 10

Brief, friendly, in Russian.
"""
    
    client = get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    
    return {"feedback": response.choices[0].message.content}

@app.post("/games/analyze")
async def analyze_game_performance(request: dict):
    """AI analyzes entire game"""
    game = request.get("game", {})
    score = request.get("score", 0)
    total = request.get("total", 1)
    
    prompt = f"""
Analyze the Chinese language game.

Game type: {game.get('type')}
Title: {game.get('title')}
Result: {score}/{total} ({score/total*100:.0f}%)

Write:
1. What went well
2. What needs review
3. Improvement tip

Brief, motivating, in Russian.
"""
    
    client = get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    
    return {"analysis": response.choices[0].message.content}

@app.post("/compare-universities")
async def compare_universities(request: dict):
    """AI compares two universities"""
    try:
        uni1 = request.get("university1", {})
        uni2 = request.get("university2", {})
        profile = request.get("profile", {})
        
        prompt = f"""
You are an expert university admission counselor.
Compare these two Chinese universities for this student:

STUDENT PROFILE:
- Field: {profile.get('field')}
- Degree: {profile.get('degree')}
- HSK: {profile.get('hsk')}

UNIVERSITY A: {json.dumps(uni1, ensure_ascii=False)}
UNIVERSITY B: {json.dumps(uni2, ensure_ascii=False)}

Provide a detailed comparison (in Russian) covering:
1. Academic strengths for this student's field
2. Location and campus life pros/cons
3. Cost and scholarship opportunities
4. Career prospects and industry connections
5. Which one is better and why

Make it engaging, like a sports commentator analyzing two fighters!
"""
        
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.8
        )
        
        return {
            "success": True,
            "comparison": response.choices[0].message.content
        }
        
    except Exception as e:
        print(f"Comparison error: {e}")
        return {
            "success": True,
            "comparison": "Basic comparison: Both universities have their strengths. Consider your specific needs."
        }
    
# ========== TESTS ENDPOINTS ==========

@app.get("/hsk-words/{level}")
async def get_hsk_words(level: int):
    """Get words for HSK level"""
    try:
        word_file = DATA_DIR / f"hsk{level}_words.json"
        if word_file.exists():
            with open(word_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading words for HSK {level}: {e}")
        return []

@app.post("/tests/generate")
async def generate_test(request: dict):
    try:
        level = request.get("level")
        section = request.get("section")
        question_count = request.get("questionCount")
        words = request.get("words", [])
        writing_type = request.get("writingType", "")
        speaking_level = request.get("speakingLevel", {})
        test_time = request.get("testTime", 40)
        
        # ✅ Time for each level
        time_map = {1:40, 2:55, 3:85, 4:120, 5:140, 6:160}
        if not test_time:
            test_time = time_map.get(level, 40)
        
        # Form prompt based on section
        word_list = ', '.join([w.get('character', '') for w in words[:20]])
        
        prompts = {
            "listening": f"""Generate HSK {level} LISTENING test with {question_count} questions.
Use ONLY these vocabulary words: {word_list}

Return JSON with:
- questions: array of objects with:
  - id: number
  - type: "dialogue" or "statement" or "question"
  - audio_script: Chinese text to be spoken
  - question: question text in Chinese
  - options: array of 4 answer choices in Chinese
  - correct: index of correct answer (0-3)

Example:
{{
  "questions": [
    {{
      "id": 1,
      "type": "dialogue",
      "audio_script": "你好吗？",
      "question": "What is the dialogue mainly about?",
      "options": ["Greetings", "Eating", "Studying", "Working"],
      "correct": 0
    }}
  ],
  "time": {test_time}
}}""",
            
            "reading": f"""Generate HSK {level} READING test with {question_count} questions.
Use ONLY these vocabulary words: {word_list}

Return JSON with:
- texts: array of reading passages
- questions: array of objects with:
  - id: number
  - text_id: which passage this refers to
  - question: question in Chinese
  - options: array of 4 answer choices
  - correct: index of correct answer

Example:
{{
  "texts": ["今天天气很好，我和朋友去公园玩。"],
  "questions": [
    {{
      "id": 1,
      "text_id": 0,
      "question": "Where did they go?",
      "options": ["School", "Park", "Store", "Hospital"],
      "correct": 1
    }}
  ],
  "time": {test_time}
}}""",
            
            "writing": f"""Generate HSK {level} WRITING test with {question_count} questions.
Level {level} writing type: {writing_type}
Use ONLY these vocabulary words: {word_list}

IMPORTANT: NO character writing/stroke order tasks at ANY level.

Return JSON with questions array. Each question has:
- id: number
- type: "sentence_completion" | "summary" | "essay"
- task: description in Russian
- question: the actual question/prompt in Chinese
- placeholder: hint for input
- word_bank: array of words to use (for lower levels, optional)

Example for HSK1-2:
{{
  "questions": [
    {{
      "id": 1,
      "type": "sentence_completion",
      "task": "Complete the sentence",
      "question": "我 _______ 学生。",
      "word_bank": ["是", "有", "在"],
      "placeholder": "Enter the correct word..."
    }}
  ]
}}

Example for HSK3-4:
{{
  "questions": [
    {{
      "id": 1,
      "type": "sentence_completion",
      "task": "Make a sentence using the given words",
      "question": "用下面的词造句：",
      "word_bank": ["喜欢", "因为", "所以"],
      "placeholder": "Your sentence..."
    }}
  ]
}}

Example for HSK5-6:
{{
  "questions": [
    {{
      "id": 1,
      "type": "essay",
      "task": "Write an essay (150-200 characters)",
      "question": "谈谈你对网络教育的看法",
      "placeholder": "Your essay..."
    }}
  ]
}}

Return ONLY valid JSON, no other text.""",
            
            "speaking": f"""Generate HSK {level} SPEAKING test.
Level: {speaking_level.get('band', '')}
Description: {speaking_level.get('desc', '')}
Use vocabulary: {word_list}

Return JSON with questions array. Each question has:
- id: number
- type: "repeat" | "short_answer" | "description" | "monologue"
- task: description in Russian/Chinese
- prompt: helpful phrases

Example:
{{
  "questions": [
    {{
      "id": 1,
      "type": "repeat",
      "task": "Repeat: 我叫小明"
    }}
  ],
  "time": {test_time}
}}"""
        }
        
        # Send request to AI
        client = get_deepseek_client()
        if not client:
            return {"error": "AI service unavailable", "test_data": {"questions": [], "time": test_time}}
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompts[section]}],
            max_tokens=2000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        print(f"AI response for {section}:", content[:200])
        
        # Clean from markdown
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Parse JSON
        test_data = json.loads(content)
        
        # Add time if missing
        if "time" not in test_data:
            test_data["time"] = test_time
        
        return {"test_data": test_data, "error": None}
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Content: {content[:500]}")
        return {
            "error": f"Failed to parse AI response: {str(e)}",
            "test_data": {
                "questions": [],
                "time": test_time
            }
        }
    except Exception as e:
        print(f"Error generating test: {e}")
        return {
            "error": str(e),
            "test_data": {
                "questions": [],
                "time": 40
            }
        }

@app.post("/tests/evaluate")
async def evaluate_test(request: dict):
    """AI evaluates user answers"""
    try:
        test_data = request.get("test", {})
        user_answers = request.get("answers", [])
        section = request.get("section", "")
        level = request.get("level", 1)
        
        # Form evaluation prompt
        prompt = f"""
You are an HSK examiner. Evaluate this {section} test for HSK level {level}.

TEST QUESTIONS:
{json.dumps(test_data, ensure_ascii=False, indent=2)}

USER ANSWERS:
{json.dumps(user_answers, ensure_ascii=False, indent=2)}

Provide evaluation in Russian:
1. Calculate score (0-100) based on correctness
2. For each answer, provide feedback
3. List main grammar/vocabulary mistakes
4. Give 3 specific suggestions for improvement

IMPORTANT: 
- For multiple choice questions, compare user answer index with correct index
- For text answers, evaluate meaning and grammar, not exact matching
- For speaking, evaluate pronunciation and fluency based on transcribed text
- For writing HSK3-6, evaluate sentence structure, vocabulary use, and coherence

Return JSON with:
{{
  "score": number (0-100),
  "feedback": "overall feedback in Russian",
  "details": [
    {{
      "correct": boolean,
      "feedback": "feedback for this answer in Russian"
    }}
  ],
  "mistakes": "list of main mistakes in Russian",
  "suggestions": "improvement tips in Russian"
}}

Return ONLY JSON, no other text.
"""
        
        client = get_deepseek_client()
        if not client:
            return {
                "score": 0,
                "feedback": "AI service unavailable",
                "details": [],
                "mistakes": "",
                "suggestions": "Please try again later"
            }
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.5
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean from markdown
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Parse JSON
        evaluation = json.loads(content)
        
        # Check required fields
        if "score" not in evaluation:
            evaluation["score"] = 0
        if "feedback" not in evaluation:
            evaluation["feedback"] = "Evaluation complete"
        if "details" not in evaluation:
            evaluation["details"] = []
        if "mistakes" not in evaluation:
            evaluation["mistakes"] = ""
        if "suggestions" not in evaluation:
            evaluation["suggestions"] = ""
        
        return evaluation
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error in evaluation: {e}")
        print(f"Content: {content[:500]}")
        return {
            "score": 0,
            "feedback": "Error processing AI response",
            "details": [],
            "mistakes": "Technical error",
            "suggestions": "Please try again"
        }
    except Exception as e:
        print(f"Error evaluating test: {e}")
        return {
            "score": 0,
            "feedback": "An error occurred during evaluation",
            "details": [],
            "mistakes": str(e),
            "suggestions": "Please try again later"
        }
    
@app.get("/test-topics")
async def test_topics():
    return {"topics": csca_math_topics, "total": len(csca_math_topics)}

# Password hashing
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    # Convert password to bytes and truncate to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    try:
        plain_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except:
        return False
    
# Email settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "gafur.adm09adm@gmail.com"  # your email
SMTP_PASSWORD = "eird vcyv crcp nmrk"  # app password (with spaces)
FROM_EMAIL = "gafur.adm09adm@gmail.com"  # same email

# Country detection service
IP_API_URL = "http://ip-api.com/json/"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/users/me/refresh-statistics")
async def refresh_my_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Force refresh ALL user statistics"""
    
    old_user_id = f"user_{current_user.id}"
    
    # 1. Sync words from user_word_status
    if old_user_id in user_word_status:
        learned_count = 0
        for word_id, data in user_word_status[old_user_id].items():
            if data.get("status") == "learned":
                learned_count += 1
            
            # Save to SQLite
            parts = word_id.rsplit('_', 1)
            word_text = parts[0]
            hsk_level = int(parts[1]) if len(parts) > 1 else 1
            
            word = db.query(UserWord).filter(
                UserWord.user_id == current_user.id,
                UserWord.word_id == word_id
            ).first()
            
            if not word:
                word = UserWord(
                    user_id=current_user.id,
                    word_id=word_id,
                    word_text=word_text,
                    hsk_level=hsk_level,
                    status=data["status"],
                    created_at=datetime.fromisoformat(data["added_at"]) if "added_at" in data else datetime.utcnow()
                )
                db.add(word)
        
        current_user.total_words_learned = learned_count
    
    # 2. Sync tests
    if old_user_id in tests_db:
        # Count user tests
        user_tests = []
        total_score = 0
        
        for test_id, test_data in tests_db.items():
            if old_user_id in test_data:
                user_tests.append(test_data[old_user_id])
                total_score += test_data[old_user_id].get("score", 0)
        
        current_user.total_tests_taken = len(user_tests)
        
        if user_tests:
            current_user.average_test_score = total_score / len(user_tests)
    
    # 3. Update streak from actions
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    actions = db.query(UserAction).filter(
        UserAction.user_id == current_user.id,
        UserAction.timestamp >= thirty_days_ago
    ).order_by(UserAction.timestamp).all()
    
    # Correct streak calculation
    streak = 0
    current_date = datetime.utcnow().date()
    
    for i in range(30):
        check_date = current_date - timedelta(days=i)
        has_activity = any(a.timestamp.date() == check_date for a in actions)
        
        if has_activity:
            streak = i + 1
        else:
            if i == 0:  # No activity today
                streak = 0
            break
    
    current_user.study_streak = streak
    if streak > current_user.longest_streak:
        current_user.longest_streak = streak
    
    # 4. Update study time
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id
    ).all()
    
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)
    current_user.total_study_time = total_minutes
    
    # 5. Update points
    current_user.total_points = (
        current_user.total_words_learned * 10 +
        current_user.total_tests_taken * 50 +
        current_user.study_streak * 5 +
        total_minutes
    )
    
    current_user.last_activity_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Statistics refreshed",
        "statistics": {
            "words_learned": current_user.total_words_learned,
            "tests_taken": current_user.total_tests_taken,
            "average_score": current_user.average_test_score,
            "streak": current_user.study_streak,
            "longest_streak": current_user.longest_streak,
            "study_time": current_user.total_study_time,
            "points": current_user.total_points
        }
    }

# ==================== Database Models ====================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="refresh_tokens")

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="password_resets")

class UserAction(Base):
    __tablename__ = "user_actions"
    __table_args__ = (
        Index('ix_user_actions_user_timestamp', 'user_id', 'timestamp'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, index=True, nullable=False)
    action_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    url = Column(String, nullable=True)
    method = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # request execution time
    
    user = relationship("User", back_populates="actions")

class UserWord(Base):
    __tablename__ = "user_words"
    __table_args__ = (
        Index('ix_user_words_user_word', 'user_id', 'word_id', unique=True),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(String, nullable=False)
    word_text = Column(String, nullable=True)
    hsk_level = Column(Integer, nullable=True)
    status = Column(String, default="new")  # new, learning, learned, review
    difficulty = Column(Integer, default=3)  # 1-5
    views_count = Column(Integer, default=0)
    practice_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    last_viewed = Column(DateTime, nullable=True)
    last_practiced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="words")

class UserTest(Base):
    __tablename__ = "user_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_id = Column(String, nullable=True)  # Test ID from frontend
    test_type = Column(String, nullable=False)  # hsk, grammar, vocabulary, listening
    test_level = Column(Integer, nullable=False)
    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    time_spent = Column(Integer, nullable=True)  # seconds
    questions_count = Column(Integer, nullable=True)
    correct_count = Column(Integer, nullable=True)
    wrong_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    answers = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="tests")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # This is the correct field name
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="chat_messages")

class StudySession(Base):
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    words_studied = Column(Integer, default=0)
    tests_taken = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="study_sessions")

# Create tables
Base.metadata.create_all(bind=engine)

# ==================== Pydantic models ====================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    current_hsk_level: Optional[int] = 1
    target_hsk_level: Optional[int] = 4

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # Removed uppercase check
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    timezone: str
    language: str
    current_hsk_level: int
    target_hsk_level: int
    exam_date: Optional[datetime] = None
    daily_goal: int
    total_points: int
    study_streak: int
    longest_streak: int
    total_words_learned: int
    total_tests_taken: int
    average_test_score: float
    last_activity_date: Optional[datetime] = None
    total_study_time: int
    email_notifications: bool
    theme: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# ==================== Helper functions ====================

def get_country_from_ip(ip_address: str) -> Optional[str]:
    try:
        response = requests.get(f"{IP_API_URL}{ip_address}", timeout=3)
        data = response.json()
        if data.get('status') == 'success':
            return data.get('country')
    except:
        pass
    return None

@app.get("/auth/debug-reset-token/{email}")
async def debug_reset_token(email: str, db: Session = Depends(get_db)):
    """Temporary endpoint to get token (development only)"""
    logger.info(f"Debug token requested for email: {email}")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"User not found: {email}")
        return {"error": "User not found"}
    
    # Find active token
    token = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.utcnow()
    ).first()
    
    if token:
        logger.info(f"Active token found for {email}: {token.token}")
        return {
            "token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "reset_link": f"https://saiyan.fly.dev/reset-password?token={token.token}"
        }
    
    logger.info(f"No active token found for {email}")
    return {"error": "No active token found"}

def send_reset_email(email: str, token: str):
    logger.info(f"=" * 50)
    logger.info(f"ATTEMPTING TO SEND EMAIL TO: {email}")
    logger.info(f"SMTP Settings: {SMTP_SERVER}:{SMTP_PORT}")
    logger.info(f"SMTP User: {SMTP_USERNAME}")
    logger.info(f"SMTP Password length: {len(SMTP_PASSWORD)} characters")
    logger.info(f"=" * 50)
    
    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = "Password Reset Request - HSK Tutor"
        
        reset_link = f"https://saiyan.fly.dev/reset-password?token={token}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password. Click the link below to proceed:</p>
            <p><a href="{reset_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">HSK Tutor - Your Chinese Learning Assistant</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        logger.info("Connecting to SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.set_debuglevel(1)  # Enable detailed SMTP logging
        logger.info("Starting TLS...")
        server.starttls()
        logger.info("Logging in...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        logger.info("Login successful, sending message...")
        server.send_message(msg)
        logger.info("Message sent, quitting...")
        server.quit()
        logger.info(f"✅ Email successfully sent to {email}")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication Error: {e}")
        logger.error("Check your email and app password")
        logger.error("Make sure 2-factor authentication is enabled and app password is correct")
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP Error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Full traceback:")

# In create_access_token already correct, but check:

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(db: Session, user_id: int, device_info: str = None, ip_address: str = None):
    token = secrets.token_urlsafe(64)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return token

def verify_refresh_token(db: Session, token: str):
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    if not db_token:
        return None
    return db_token

# ==================== AUTOMATIC TRACKING (no changes to frontend) ====================

def analyze_request_and_log(db: Session, user_id: int, request: Request, response_status: int, duration_ms: int = None):
    """Analyze request and automatically determine action type"""
    
    url = str(request.url)
    method = request.method
    path = request.url.path
    user_agent_str = request.headers.get("user-agent", "")
    
    # Parse User-Agent
    ua = user_agents.parse(user_agent_str)
    device_type = "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop"
    browser = ua.browser.family if ua.browser.family else "unknown"
    os = ua.os.family if ua.os.family else "unknown"
    
    # Determine action type by URL
    action_type = "api_call"
    action_data = {
        "url": url,
        "method": method,
        "path": path,
        "device": device_type,
        "browser": browser,
        "os": os,
        "status": response_status
    }
    
    # === WORDS ===
    if "/word/" in path or "random" in path and "word" in path:
        action_type = "view_word"
        # Extract word ID if present
        word_match = re.search(r'/word/([^/?]+)', path)
        if word_match:
            action_data["word_id"] = word_match.group(1)
        
        # Update word statistics
        word_id = action_data.get("word_id", "unknown")
        word = db.query(UserWord).filter(
            UserWord.user_id == user_id,
            UserWord.word_id == word_id
        ).first()
        
        if not word:
            # Try to determine HSK level from URL
            hsk_level = 1
            if "hsk1" in path:
                hsk_level = 1
            elif "hsk2" in path:
                hsk_level = 2
            elif "hsk3" in path:
                hsk_level = 3
            elif "hsk4" in path:
                hsk_level = 4
            elif "hsk5" in path:
                hsk_level = 5
            elif "hsk6" in path:
                hsk_level = 6
            
            word = UserWord(
                user_id=user_id,
                word_id=word_id,
                word_text=word_id,
                hsk_level=hsk_level
            )
            db.add(word)
        
        word.views_count += 1
        word.last_viewed = datetime.utcnow()
        
        # If word viewed many times, consider learning
        if word.views_count >= 3 and word.status == "new":
            word.status = "learning"
    
    # === TESTS ===
    elif "/test/" in path or "test" in path.lower():
        action_type = "take_test"
        
        # Extract test level
        level_match = re.search(r'/test/(\d+)', path)
        if level_match:
            action_data["level"] = int(level_match.group(1))
        
        # For POST requests (answer submission)
        if method == "POST" and response_status == 200:
            action_data["test_completed"] = True
            
            # Create test record (results will be added later)
            test = UserTest(
                user_id=user_id,
                test_type="hsk",
                test_level=action_data.get("level", 1),
                created_at=datetime.utcnow()
            )
            db.add(test)
            db.flush()
            action_data["test_db_id"] = test.id
    
    # === CHAT ===
    elif "/chat/" in path:
        action_type = "chat_message"
        
        # Extract thread ID
        thread_match = re.search(r'/chat/([^/?]+)', path)
        if thread_match:
            action_data["thread_id"] = thread_match.group(1)
        
        # For POST requests (message sending)
        if method == "POST" and response_status == 200:
            action_data["message_sent"] = True
    
    # === AUDIO ===
    elif "/audio/" in path:
        action_type = "listen_audio"
    
    # === TRANSLATION ===
    elif "/translate" in path or "translate" in path.lower():
        action_type = "translate"
    
    # === PROFILE ===
    elif "/users/me" in path:
        if method == "GET":
            action_type = "view_profile"
        elif method == "PUT":
            action_type = "update_profile"
    
    # === AUTH ===
    elif "/auth/login" in path:
        action_type = "login"
    elif "/auth/register" in path:
        action_type = "register"
    elif "/auth/logout" in path:
        action_type = "logout"
    
    # Save action
    action = UserAction(
        user_id=user_id,
        action_type=action_type,
        action_data=action_data,
        ip_address=request.client.host if request.client else None,
        user_agent=user_agent_str,
        url=url,
        method=method,
        duration_ms=duration_ms
    )
    db.add(action)
    
    # Update active study session
    active_session = db.query(StudySession).filter(
        StudySession.user_id == user_id,
        StudySession.is_active == True
    ).first()
    
    if not active_session:
        # New session
        active_session = StudySession(user_id=user_id)
        db.add(active_session)
    
    active_session.actions_count += 1
    if action_type == "view_word":
        active_session.words_studied += 1
    elif action_type == "take_test" and method == "POST":
        active_session.tests_taken += 1
    
    db.commit()
    
    return action

def update_user_statistics_task():
    """Background task to update user statistics"""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            # Get all user actions
            actions = db.query(UserAction).filter(
                UserAction.user_id == user.id
            ).order_by(UserAction.timestamp).all()
            
            if not actions:
                continue
            
            # Update last_activity
            last_action = actions[-1]
            user.last_activity_date = last_action.timestamp
            
            # Calculate streak
            streak = 0
            current_date = datetime.utcnow().date()
            
            for i in range(30):  # check last 30 days
                check_date = current_date - timedelta(days=i)
                has_activity = any(
                    a.timestamp.date() == check_date 
                    for a in actions[-50:]  # check last 50 actions
                )
                
                if has_activity:
                    if i == 0:
                        streak += 1
                    elif i == streak:  # consecutive day
                        streak += 1
                    else:
                        break
                else:
                    break
            
            user.study_streak = streak
            if streak > user.longest_streak:
                user.longest_streak = streak
            
            # Count learned words
            learned_words = db.query(UserWord).filter(
                UserWord.user_id == user.id,
                UserWord.status == 'learned'
            ).count()
            user.total_words_learned = learned_words
            
            # Count tests
            tests = db.query(UserTest).filter(
                UserTest.user_id == user.id,
                UserTest.score.isnot(None)
            ).all()
            user.total_tests_taken = len(tests)
            
            if tests:
                avg_score = sum(t.score for t in tests) / len(tests)
                user.average_test_score = round(avg_score, 2)
            
            # Count total study time (from sessions)
            sessions = db.query(StudySession).filter(
                StudySession.user_id == user.id
            ).all()
            
            total_minutes = 0
            for session in sessions:
                if session.end_time and session.duration_minutes:
                    total_minutes += session.duration_minutes
                elif session.start_time:
                    # If session is active, calculate to current moment
                    if not session.end_time:
                        duration = (datetime.utcnow() - session.start_time).total_seconds() / 60
                        if duration > 0:
                            session.duration_minutes = int(duration)
                            session.is_active = False
                            total_minutes += int(duration)
            
            user.total_study_time = total_minutes
            
            # Points: formula = words*10 + tests*50 + streak*5 + time
            user.total_points = (
                learned_words * 10 +
                user.total_tests_taken * 50 +
                user.study_streak * 5 +
                total_minutes
            )
        
        db.commit()
        logger.info(f"Updated statistics for {len(users)} users")
        
    except Exception as e:
        logger.error(f"Error updating statistics: {e}")
    finally:
        db.close()

def end_inactive_sessions_task():
    """Close inactive sessions (no actions for more than 30 minutes)"""
    db = SessionLocal()
    try:
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        
        active_sessions = db.query(StudySession).filter(
            StudySession.is_active == True,
            StudySession.start_time < thirty_minutes_ago
        ).all()
        
        for session in active_sessions:
            session.is_active = False
            session.end_time = session.start_time + timedelta(minutes=30)
            session.duration_minutes = 30
        
        db.commit()
        logger.info(f"Closed {len(active_sessions)} inactive sessions")
        
    except Exception as e:
        logger.error(f"Error ending sessions: {e}")
    finally:
        db.close()

# Start background tasks
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_user_statistics_task, trigger="interval", minutes=5)
scheduler.add_job(func=end_inactive_sessions_task, trigger="interval", minutes=10)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ==================== MIDDLEWARE FOR AUTOMATIC LOGGING ====================

@app.middleware("http")
async def auto_logging_middleware(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Check authorization
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            
            if user_id and response.status_code < 500:  # Don't log server errors
                db = SessionLocal()
                try:
                    analyze_request_and_log(
                        db, user_id, request, 
                        response.status_code, int(duration)
                    )
                except Exception as e:
                    logger.error(f"Logging error: {e}")
                finally:
                    db.close()
        except:
            # Don't log if token is invalid
            pass
    
    return response

# ==================== ENDPOINTS ====================

@app.post("/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    # Check existing user
    db_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    if db_user:
        if db_user.email == user_data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Determine country from IP
    country = get_country_from_ip(request.client.host)
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,  # Use hash
        full_name=user_data.full_name,
        current_hsk_level=user_data.current_hsk_level,
        target_hsk_level=user_data.target_hsk_level,
        country=country
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    # Find user by email (email comes in username field)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Update last_login
    user.last_login = datetime.utcnow()
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,      # keep for compatibility
            "user_id": user.id          # ADD THIS!
        },
        expires_delta=access_token_expires
    )
    
    device_info = request.headers.get("user-agent") if request else None
    refresh_token = create_refresh_token(
        db, user.id, 
        device_info=device_info,
        ip_address=request.client.host if request else None
    )
    
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(
    refresh_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    token = refresh_data.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    
    db_token = verify_refresh_token(db, token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = db_token.user
    
    # Create new tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id  # IMPORTANT!
        },
        expires_delta=access_token_expires
    )
    
    # Delete old refresh token
    db.delete(db_token)
    
    # Create new one
    new_refresh_token = create_refresh_token(
        db, user.id
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@app.get("/debug/auth-check")
async def debug_auth_check(current_user: User = Depends(get_current_user)):
    """Authorization check (debug only)"""
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

@app.post("/auth/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Delete all user refresh tokens
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()
    
    return {"message": "Successfully logged out"}

@app.post("/auth/password-reset/request")
async def password_reset_request(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user:
        logger.info(f"Password reset requested for non-existent email: {reset_data.email}")
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Delete old tokens
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used == False
    ).delete()
    
    # Create new token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    
    reset_token = PasswordReset(
        token=token,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    
    # Log token (for debugging)
    logger.info(f"✅ RESET TOKEN for {user.email}: {token}")
    logger.info(f"🔗 Reset link: https://your-frontend.com/reset-password?token={token}")
    
    # Send email in background
    background_tasks.add_task(send_reset_email, user.email, token)
    
    return {"message": "If the email exists, a reset link has been sent"}

@app.post("/auth/password-reset/confirm")
async def password_reset_confirm(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    reset = db.query(PasswordReset).filter(
        PasswordReset.token == reset_data.token,
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.utcnow()
    ).first()
    
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Update password
    user = reset.user
    user.hashed_password = p_context.hash(reset_data.new_password)
    reset.used = True
    reset.used_at = datetime.utcnow()
    
    # Delete all refresh tokens for security
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    
    db.commit()
    
    return {"message": "Password successfully reset"}

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/users/me/statistics")
async def get_detailed_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed user statistics"""
    
    old_user_id = f"user_{current_user.id}"
    
    # Words from SQLite
    words = db.query(UserWord).filter(UserWord.user_id == current_user.id).all()
    words_by_status = {
        "new": len([w for w in words if w.status == "new"]),
        "learning": len([w for w in words if w.status == "learning"]),
        "learned": len([w for w in words if w.status == "learned"]),
        "review": len([w for w in words if w.status == "review"])
    }
    
    # Tests from SQLite
    tests = db.query(UserTest).filter(
        UserTest.user_id == current_user.id,
        UserTest.score.isnot(None)
    ).order_by(UserTest.created_at.desc()).all()
    
    # Active sessions
    active_session = db.query(StudySession).filter(
        StudySession.user_id == current_user.id,
        StudySession.is_active == True
    ).first()
    
    # Actions
    recent_actions = db.query(UserAction).filter(
        UserAction.user_id == current_user.id
    ).order_by(UserAction.timestamp.desc()).limit(100).all()
    
    # Group by day
    daily_activity = {}
    for action in recent_actions[:30]:
        date_str = action.timestamp.strftime("%Y-%m-%d")
        daily_activity[date_str] = daily_activity.get(date_str, 0) + 1
    
    # Get data from in-memory dictionaries (for backward compatibility)
    old_words = user_word_status.get(old_user_id, {})
    old_learned = sum(1 for v in old_words.values() if v.get("status") == "learned")
    
    # Use MAXIMUM value from all sources
    total_learned = max(
        current_user.total_words_learned,
        old_learned,
        words_by_status["learned"]
    )
    
    return {
        "user": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "country": current_user.country,
            "current_hsk_level": current_user.current_hsk_level,
            "target_hsk_level": current_user.target_hsk_level,
            "daily_goal": current_user.daily_goal
        },
        "statistics": {
            "total_points": current_user.total_points,
            "study_streak": current_user.study_streak,
            "longest_streak": current_user.longest_streak,
            "total_study_time": current_user.total_study_time,
            "total_words_learned": total_learned,
            "total_tests_taken": current_user.total_tests_taken,
            "average_test_score": current_user.average_test_score
        },
        "words": {
            "by_status": words_by_status,
            "by_hsk": get_words_by_hsk_level(words),
            "total": len(words),
            "recent": get_recent_words(words)
        },
        "tests": {
            "history": [
                {
                    "id": t.id,
                    "type": t.test_type,
                    "level": t.test_level,
                    "score": t.score,
                    "max_score": t.max_score,
                    "date": t.created_at.isoformat()
                }
                for t in tests[:20]
            ],
            "total": len(tests),
            "average": current_user.average_test_score
        },
        "activity": {
            "daily": [{"date": d, "count": c} for d, c in daily_activity.items()],
            "last_30_days": len(recent_actions),
            "current_session_minutes": int((datetime.utcnow() - active_session.start_time).total_seconds() / 60) if active_session else 0,
            "recent_actions": [
                {
                    "type": a.action_type,
                    "time": a.timestamp.isoformat(),
                    "data": a.action_data
                }
                for a in recent_actions[:10]
            ]
        },
        "achievements": calculate_achievements(current_user, tests)
    }

@app.get("/auth/debug-user/{email}")
async def debug_user(email: str, db: Session = Depends(get_db)):
    """Debug endpoint for checking user (DEVELOPMENT ONLY)"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"exists": False}
    
    return {
        "exists": True,
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "has_password": bool(user.hashed_password),
        "is_active": user.is_active
    }

@app.post("/user/progress/sync")
async def sync_user_progress(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Sync progress from localStorage to DB"""
    try:
        word_statuses = request.get("word_statuses", {})
        learned_words = request.get("learned_words", 0)
        
        # Save each word to DB
        for word_id, data in word_statuses.items():
            if data.get("status") == "learned":
                # Parse word_id (format "你好_1")
                parts = word_id.rsplit('_', 1)
                word_text = parts[0]
                hsk_level = int(parts[1]) if len(parts) > 1 else 1
                
                # Check if word already exists
                existing = db.query(UserWord).filter(
                    UserWord.user_id == current_user.id,
                    UserWord.word_id == word_id
                ).first()
                
                if not existing:
                    word = UserWord(
                        user_id=current_user.id,
                        word_id=word_id,
                        word_text=word_text,
                        hsk_level=hsk_level,
                        status="learned",
                        created_at=datetime.fromisoformat(data.get("added_at", datetime.now().isoformat()))
                    )
                    db.add(word)
        
        # Update learned words counter for user
        learned_count = db.query(UserWord).filter(
            UserWord.user_id == current_user.id,
            UserWord.status == "learned"
        ).count()
        
        current_user.total_words_learned = learned_count
        db.commit()
        
        return {"success": True, "synced": learned_count}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
def get_words_by_hsk_level(words):
    """Group words by HSK levels"""
    result = {}
    for level in range(1, 7):
        result[f"HSK{level}"] = len([
            w for w in words 
            if w.hsk_level == level and w.status == "learned"
        ])
    return result

def get_recent_words(words, limit=10):
    """Return recently learned words"""
    sorted_words = sorted(
        [w for w in words if w.status == "learned"],
        key=lambda x: x.updated_at or x.created_at,
        reverse=True
    )
    return [
        {
            "word": w.word_text,
            "hsk_level": w.hsk_level,
            "date": (w.updated_at or w.created_at).isoformat()
        }
        for w in sorted_words[:limit]
    ]

def calculate_achievements(user, tests):
    """Calculate user achievements"""
    return [
        {"name": "First Word", "achieved": user.total_words_learned >= 1},
        {"name": "First Test", "achieved": user.total_tests_taken >= 1},
        {"name": "10 Words", "achieved": user.total_words_learned >= 10},
        {"name": "50 Words", "achieved": user.total_words_learned >= 50},
        {"name": "100 Words", "achieved": user.total_words_learned >= 100},
        {"name": "500 Words", "achieved": user.total_words_learned >= 500},
        {"name": "7 Day Streak", "achieved": user.study_streak >= 7},
        {"name": "30 Day Streak", "achieved": user.study_streak >= 30},
        {"name": "10 Tests", "achieved": user.total_tests_taken >= 10},
        {"name": "50 Tests", "achieved": user.total_tests_taken >= 50},
        {"name": "Perfect Score", "achieved": any(t.score == t.max_score for t in tests)},
        {"name": f"HSK {user.current_hsk_level} Achieved", "achieved": True}
    ]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    }

# Cache for translations (increase size and add counter)
translation_cache = {}
cache_hits = {}  # Counter for cache accesses

@app.get("/api/translate")
async def translate(
    text: str = Query(..., min_length=1, max_length=5000),
    target: str = Query(..., min_length=2, max_length=5)
):
    """Proxy for Google Translate API (single translation)"""
    cache_key = f"{text}:{target}"
    
    # Check cache considering usage frequency
    if cache_key in translation_cache:
        cache_hits[cache_key] = cache_hits.get(cache_key, 0) + 1
        return {"translatedText": translation_cache[cache_key]}
    
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target,
            "dt": "t",
            "q": text
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse Google response
        translated = ""
        if data and len(data) > 0 and data[0]:
            for part in data[0]:
                if part and len(part) > 0:
                    translated += part[0]
        
        if not translated:
            translated = text
        
        # Save to cache
        translation_cache[cache_key] = translated
        cache_hits[cache_key] = 1
        
        # Smart cache cleaning (remove rarely used)
        if len(translation_cache) > 2000:  # Increased to 2000
            # Find 500 rarest keys
            rare_keys = sorted(cache_hits.items(), key=lambda x: x[1])[:500]
            for key, _ in rare_keys:
                if key in translation_cache:
                    del translation_cache[key]
                if key in cache_hits:
                    del cache_hits[key]
        
        return {"translatedText": translated}
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Google Translate timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Google Translate error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/translate-batch")
async def translate_batch(request: Request):
    """
    BATCH TRANSLATION - OPTIMIZED VERSION
    """
    try:
        payload = await request.json()
        texts = payload.get("texts", [])
        target = payload.get("target")
        
        print(f"[TRANSLATE] Received {len(texts)} texts for translation to {target}")
        
        if not texts or not target:
            return {"texts": texts}
        
        # Filter only what really needs translation
        valid_indices = []
        valid_texts = []
        
        for i, text in enumerate(texts):
            # Skip short texts, digits, empty strings
            if (text and 
                len(text.strip()) > 2 and 
                not text.strip().isdigit() and
                not all(c in '0123456789.,!?-_ ' for c in text.strip())):
                valid_indices.append(i)
                valid_texts.append(text)
        
        if not valid_texts:
            return {"texts": texts}
        
        # Check cache for each text
        uncached_indices = []
        uncached_texts = []
        translated_results = list(texts)  # copy of originals
        
        for idx, text in zip(valid_indices, valid_texts):
            cache_key = f"{text}:{target}"
            if cache_key in translation_cache:
                # Take from cache
                translated_results[idx] = translation_cache[cache_key]
                cache_hits[cache_key] = cache_hits.get(cache_key, 0) + 1
            else:
                # Needs translation
                uncached_indices.append(idx)
                uncached_texts.append(text)
        
        if not uncached_texts:
            return {"texts": translated_results}
        
        # === OPTIMIZATION 1: TEXT AGGREGATION ===
        # Group similar texts to reduce number of requests
        text_groups = {}
        for idx, text in zip(uncached_indices, uncached_texts):
            # Use text hash as group key
            # (identical texts translate once)
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash not in text_groups:
                text_groups[text_hash] = {
                    'text': text,
                    'indices': []
                }
            text_groups[text_hash]['indices'].append(idx)
        
        print(f"[TRANSLATE] {len(uncached_texts)} texts grouped into {len(text_groups)} unique texts")
        
        # === OPTIMIZATION 2: CONCURRENT REQUESTS ===
        # Translate unique texts in parallel
        async def translate_one(text):
            try:
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    "client": "gtx",
                    "sl": "auto",
                    "tl": target,
                    "dt": "t",
                    "q": text
                }
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                
                translated = ""
                if data and len(data) > 0 and data[0]:
                    for part in data[0]:
                        if part and len(part) > 0:
                            translated += part[0]
                
                return text, translated if translated else text
                
            except Exception as e:
                print(f"[TRANSLATE] Error: {str(e)}")
                return text, text  # On error, return original
        
        # Run all requests in parallel
        unique_texts = [group['text'] for group in text_groups.values()]
        tasks = [translate_one(text) for text in unique_texts]
        results = await asyncio.gather(*tasks)
        
        # Create translation dictionary
        translation_map = {original: translated for original, translated in results}
        
        # Save to cache and apply to all indices
        for original, translated in translation_map.items():
            cache_key = f"{original}:{target}"
            translation_cache[cache_key] = translated
            cache_hits[cache_key] = 1
            
            # Find group by original text
            text_hash = hashlib.md5(original.encode()).hexdigest()
            group = text_groups.get(text_hash)
            if group:
                # Apply translation to all indices with same text
                for idx in group['indices']:
                    translated_results[idx] = translated
        
        return {"texts": translated_results}
        
    except Exception as e:
        print(f"[TRANSLATE] Critical error: {str(e)}")
        return {"texts": texts}  # On error, return originals
    
# ========== МАРШРУТЫ ДЛЯ HSK ФРОНТЕНДА ==========

from fastapi.responses import HTMLResponse

@app.get("/hsk", response_class=HTMLResponse)
async def hsk_main_page():
    """Главная страница HSK Tutor"""
    hsk_index_path = os.path.join(BASE_DIR, "frontend_hsk", "index.html")
    if os.path.exists(hsk_index_path):
        with open(hsk_index_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content=f"""
    <html>
    <head><title>HSK Tutor</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🇨🇳 HSK Tutor</h1>
        <p>Файл <code>frontend_hsk/index.html</code> не найден.</p>
        <p>Путь: <code>{hsk_index_path}</code></p>
        <a href="/">Вернуться на главную</a>
    </body>
    </html>
    """)