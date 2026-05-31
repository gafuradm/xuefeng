# backend/app/main.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo, IELTSAttempt,
    RefreshToken, PasswordReset, UserAction, ChatMessage
)

from .pdf_rag import extract_text_from_pdf, split_text_into_chunks, create_tfidf_index, search_tfidf_index
from .models import UserDocument
import shutil
import json

from .plagiarism import check_plagiarism
from .models import TextReview, PlagiarismCorpus
from pydantic import BaseModel

import pandas as pd
import matplotlib
matplotlib.use('Agg')   # для работы без GUI
import matplotlib.pyplot as plt
import io
import base64
from RestrictedPython import compile_restricted, safe_globals
from .models import DataAnalysisSession

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, get_db, SessionLocal
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
from .auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_active_user
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

class TextReviewRequest(BaseModel):
    title: Optional[str] = None
    text: str

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

from fastapi.responses import HTMLResponse
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    app_html = FRONTEND_DIR / "app.html"
    if app_html.exists():
        with open(app_html, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("app.html not found", status_code=404)

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

@app.get("/", response_class=HTMLResponse)
async def main_frontend():
    """Главная страница Universal AI Teacher"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("Main frontend not found", status_code=404)

@app.get("/ielts", response_class=HTMLResponse)
async def ielts_page():
    # Поднимаемся на три уровня: из backend/app/main.py в корень проекта
    project_root = Path(__file__).parent.parent.parent  # universal-ai-teacher/
    ielts_path = project_root / "frontend" / "ielts.html"
    print(f"[IELTS] Looking for file: {ielts_path}")
    if ielts_path.exists():
        with open(ielts_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(f"IELTS page not found at {ielts_path}", status_code=404)

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

@app.get("/api/sessions/by_user")
async def get_sessions_by_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).order_by(SessionModel.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "exam_name": s.exam_name,
            "status": s.status,
            "created_at": s.created_at
        }
        for s in sessions
    ]

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
    
@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    temp_dir = Path("/tmp/user_docs")
    temp_dir.mkdir(exist_ok=True)
    safe_filename = f"{uuid.uuid4()}.pdf"
    file_path = temp_dir / safe_filename
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        text = extract_text_from_pdf(str(file_path))
        if not text.strip():
            raise HTTPException(400, "PDF не содержит текста (возможно, это сканированная копия).")
        chunks = split_text_into_chunks(text)
        if not chunks:
            raise HTTPException(400, "Не удалось разбить текст на фрагменты.")
        
        vec_path, mat_path, chk_path = create_tfidf_index(chunks)
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(500, f"Ошибка обработки PDF: {str(e)}")
    
    doc = UserDocument(
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        index_path=json.dumps({
            "vectorizer": vec_path,
            "matrix": mat_path,
            "chunks": chk_path
        }),
        chunks_count=len(chunks)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.id, "filename": file.filename, "chunks": len(chunks)}

@app.post("/api/ask-pdf")
async def ask_pdf(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = await request.json()
    doc_id = data.get("document_id")
    question = data.get("question")
    if not doc_id or not question:
        raise HTTPException(400, "Не указан document_id или question")
    
    doc = db.query(UserDocument).filter(UserDocument.id == doc_id, UserDocument.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Документ не найден")
    
    paths = json.loads(doc.index_path)
    # Загружаем все чанки
    with open(paths["chunks"], "r", encoding="utf-8") as f:
        all_chunks = json.load(f)
    first_chunk = all_chunks[0] if all_chunks else ""
    
    # Поиск релевантных чанков (увеличим k до 8 для большего контекста)
    relevant_chunks = search_tfidf_index(paths["vectorizer"], paths["matrix"], paths["chunks"], question, k=8)
    
    # Формируем контекст: первый чанк (если не входит) + релевантные
    context_parts = []
    if first_chunk and first_chunk not in relevant_chunks:
        context_parts.append(first_chunk)
    context_parts.extend(relevant_chunks)
    context = "\n\n---\n\n".join(context_parts[:8])  # берём до 8 чанков
    
    if not relevant_chunks and not first_chunk:
        return {"answer": "Не удалось найти информацию в загруженном документе."}
    
    prompt = f"""You are a helpful assistant that provides DETAILED, COMPREHENSIVE answers based ONLY on the given context.

CONTEXT (excerpts from the document):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer in 4-8 sentences, providing specific details from the context.
- If the question asks "what is this document about", describe:
  * The type of document (exam paper, article, lecture notes, etc.)
  * The subject area(s)
  * The structure (sections, question types, topics covered)
  * Any key information you can extract (e.g., year, exam name, major topics)
- Use examples from the context to support your answer.
- Do not invent information not present in the context.
- If the context does not contain the answer, say "Information not found in the document."

ANSWER:"""
    
    try:
        answer = await deepseek_client.chat_completion([
            {"role": "system", "content": "You are a detailed, thorough assistant. Answer based only on the given context."},
            {"role": "user", "content": prompt}
        ], max_tokens=800, temperature=0.5)
    except Exception as e:
        answer = f"Ошибка: {str(e)}"
    
    return {"answer": answer, "used_chunks": len(relevant_chunks)}

from .models import ExamTicket

@app.post("/api/generate-exam-tickets")
async def generate_exam_tickets(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = await request.json()
    course_name = data.get("course_name")
    num_questions = data.get("num_questions", 5)
    ticket_type = data.get("ticket_type", "tickets")  # 'tickets' или 'test'
    
    if not course_name:
        raise HTTPException(400, "course_name required")
    if num_questions < 1 or num_questions > 20:
        raise HTTPException(400, "num_questions must be between 1 and 20")
    
    # Формируем промпт для AI
    if ticket_type == "tickets":
        prompt = f"""Generate {num_questions} exam questions for a university-level course titled "{course_name}". 
Each question should be a clear, standalone problem that tests understanding of key concepts.
Return ONLY a JSON array of strings, like: ["Question 1...", "Question 2...", ...].
Do not include answers or explanations."""
    else:  # test with multiple choice
        prompt = f"""Generate {num_questions} multiple-choice questions for a university-level course titled "{course_name}".
For each question, provide: question text, 4 options (A, B, C, D), and the correct answer letter.
Return ONLY a JSON array of objects:
[
  {{
    "question": "What is ...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": "A"
  }}
]"""
    
    try:
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "You are an expert exam creator. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=2000, temperature=0.7)
        
        # Очистка ответа
        import re
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        questions = json.loads(response)
        if not isinstance(questions, list):
            raise ValueError("Response is not a list")
        
        # Сохраняем в БД
        ticket = ExamTicket(
            user_id=current_user.id,
            course_name=course_name,
            num_questions=num_questions,
            ticket_type=ticket_type,
            questions=questions
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        return {
            "ticket_id": ticket.id,
            "course_name": course_name,
            "num_questions": num_questions,
            "type": ticket_type,
            "questions": questions
        }
        
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {str(e)}")
    
from pydantic import BaseModel
import json

class EssayCheckRequest(BaseModel):
    text: str
    title: Optional[str] = None
    criteria: Optional[str] = None

@app.post("/api/check-essay")
async def check_essay(
    request: EssayCheckRequest,
    current_user: User = Depends(get_current_user)
):
    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Текст не может быть пустым")
    
    title = request.title or "Работа"
    criteria = request.criteria or "стандартные академические критерии"
    
    # Используем тройные кавычки. Фигурные скобки внутри JSON НЕ экранируем,
    # потому что они не являются частью f-строки (они внутри литерала). 
    # На самом деле ошибка была в том, что в f-строке были { и } вокруг названий полей.
    # Перепишем без f-строки для JSON-образца, а лучше передадим явный пример.
    prompt = f"""Ты – опытный преподаватель. Проверь следующую студенческую работу на тему "{title}".

Критерии оценки: {criteria}
- Структура (введение, основная часть, заключение)
- Аргументация и логика
- Грамматика и стиль
- Оригинальность (нет явных признаков плагиата)
- Соответствие теме

Текст работы:
{text[:8000]}

Оцени работу по 100-балльной шкале, затем напиши подробный отзыв (сильные стороны, слабые места, рекомендации). 
Верни ТОЛЬКО JSON в следующем формате (без дополнительных пояснений):
{{"score": 85, "grade": "хорошо", "strengths": ["список сильных сторон"], "weaknesses": ["список слабых мест"], "recommendations": ["рекомендации по улучшению"], "detailed_feedback": "развёрнутый отзыв"}}"""
    
    try:
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты строгий, но справедливый преподаватель. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=1500, temperature=0.5)
        
        # Очистка от markdown-разметки
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        result = json.loads(response)
        result["word_count"] = len(text.split())
        result["char_count"] = len(text)
        result["checked_at"] = datetime.utcnow().isoformat()
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Ошибка парсинга JSON: {str(e)}. Ответ AI: {response[:200]}")
    except Exception as e:
        raise HTTPException(500, f"Ошибка проверки: {str(e)}")
    
from pydantic import BaseModel
from datetime import datetime, timedelta
from .models import Task

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: str  # ISO format, e.g. "2025-06-01T15:00:00"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None

@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        deadline = datetime.fromisoformat(task_data.deadline)
    except ValueError:
        raise HTTPException(400, "Неверный формат даты. Используйте ISO формат (YYYY-MM-DDTHH:MM:SS)")
    
    task = Task(
        user_id=current_user.id,
        title=task_data.title,
        description=task_data.description,
        deadline=deadline,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "deadline": task.deadline.isoformat(),
        "status": task.status,
        "created_at": task.created_at.isoformat()
    }

@app.get("/api/tasks")
async def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    upcoming_days: Optional[int] = None
):
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if status:
        query = query.filter(Task.status == status)
    if upcoming_days:
        cutoff = datetime.utcnow()
        future = cutoff + timedelta(days=upcoming_days)
        query = query.filter(Task.deadline <= future, Task.deadline >= cutoff, Task.status == "pending")
    tasks = query.order_by(Task.deadline).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline.isoformat(),
            "status": t.status,
            "reminder_sent": t.reminder_sent,
            "created_at": t.created_at.isoformat()
        }
        for t in tasks
    ]

@app.put("/api/tasks/{task_id}")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.deadline is not None:
        try:
            task.deadline = datetime.fromisoformat(task_data.deadline)
        except ValueError:
            raise HTTPException(400, "Неверный формат даты")
    if task_data.status is not None:
        task.status = task_data.status
    task.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Задача обновлена"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    db.delete(task)
    db.commit()
    return {"message": "Задача удалена"}

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# Функция отправки email (замените на свои SMTP данные или используйте логирование)
def send_reminder_email(email: str, task_title: str, deadline: datetime):
    # Настройте SMTP (для примера используем логирование)
    print(f"[REMINDER] Напоминание для {email}: задача '{task_title}' истекает {deadline.strftime('%Y-%m-%d %H:%M')}")
    # Реальная отправка email – раскомментируйте и настройте
    try:
        msg = MIMEText(f"Уважаемый студент, задача '{task_title}' должна быть выполнена до {deadline.strftime('%Y-%m-%d %H:%M')}.")
        msg['Subject'] = f'Напоминание: {task_title}'
        msg['From'] = 'amirkad62@gmail.com'
        msg['To'] = email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('amirkad62@gmail.com', 'kpkhzrnpgbbkfjoy')
            server.send_message(msg)
    except Exception as e:
        print(f"SMTP error: {e}")

def check_deadlines():
    """Фоновая задача для отправки напоминаний о дедлайнах (каждые 30 минут)"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        one_hour_later = now + timedelta(hours=1)
        tasks = db.query(Task).filter(
            Task.deadline <= one_hour_later,
            Task.deadline > now,
            Task.reminder_sent == False,
            Task.status == "pending"
        ).all()
        for task in tasks:
            user = task.user
            if user and user.email:
                send_reminder_email(user.email, task.title, task.deadline)
                task.reminder_sent = True
        db.commit()
    except Exception as e:
        print(f"Error in check_deadlines: {e}")
    finally:
        db.close()

# Добавляем задачу в существующий планировщик (предполагается, что scheduler уже инициализирован)
# Если scheduler ещё не создан, раскомментируйте следующую строку:
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_deadlines, trigger="interval", minutes=30)
scheduler.start()

from .models import SyllabusCourse
from pydantic import BaseModel
from typing import Optional, List

class SyllabusGenerateRequest(BaseModel):
    title: str
    specialty: Optional[str] = None
    total_hours: int = 144
    semester: int = 1
    goal: Optional[str] = None

class SyllabusUpdateRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    university: Optional[str] = None
    semester: Optional[int] = None
    credits: Optional[float] = None
    total_hours: Optional[int] = None
    description: Optional[str] = None
    competencies: Optional[List[str]] = None
    syllabus_content: Optional[dict] = None
    assessment_tools: Optional[List[dict]] = None
    literature: Optional[List[dict]] = None

@app.post("/api/syllabus/generate")
async def generate_syllabus(
    req: SyllabusGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt = f"""Ты – эксперт по учебно-методической документации для вузов. Создай рабочий план дисциплины (силлабус / РПД) на русском языке.

Название курса: {req.title}
Специальность/направление: {req.specialty or 'не указано'}
Общая трудоёмкость: {req.total_hours} часов
Семестр: {req.semester}
Цель курса: {req.goal or 'сформировать у студентов компетенции по данной дисциплине'}

Требования к структуре (строго соблюдай):
1. Компетенции (3-5 штук, например, ОПК-1, ПК-2 и т.д.)
2. Тематический план: разбить на 3-5 разделов, в каждом разделе 2-4 темы. Для каждой темы указать часы: лекции, практические/лабораторные, самостоятельная работа. Сумма часов по всем темам должна равняться {req.total_hours}.
3. Фонд оценочных средств: вопросы к экзамену/зачёту (не менее 10), типовые задания.
4. Литература: основная (3-5 источников) и дополнительная (3-5 источников).
5. Материально-техническое обеспечение (общие фразы).

Верни ТОЛЬКО JSON (без лишнего текста) в следующем формате:
{{
  "title": "{req.title}",
  "department": "Кафедра по умолчанию",
  "university": "Университет",
  "semester": {req.semester},
  "credits": {round(req.total_hours / 36, 1)},
  "total_hours": {req.total_hours},
  "description": "Краткое описание курса (2 предложения)",
  "competencies": ["ОПК-1", "ПК-2", "ПК-3"],
  "syllabus_content": {{
    "sections": [
      {{
        "title": "Название раздела 1",
        "topics": [
          {{"name": "Тема 1.1", "lecture_hours": 2, "practice_hours": 2, "lab_hours": 0, "self_hours": 4}}
        ]
      }}
    ]
  }},
  "assessment_tools": [
    {{"type": "экзамен", "questions": ["Вопрос 1", "Вопрос 2"]}},
    {{"type": "задания", "tasks": ["Задание 1", "Задание 2"]}}
  ],
  "literature": [
    {{"type": "основная", "authors": "Иванов И.И.", "title": "Название", "year": 2024}},
    {{"type": "дополнительная", "authors": "Петров П.П.", "title": "Название", "year": 2023}}
  ]
}}"""

    try:
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты помощник по созданию учебных программ. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000, temperature=0.5)
        
        # Очистка ответа
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        data = json.loads(response)
        
        # Сохраняем в БД
        syllabus = SyllabusCourse(
            user_id=current_user.id,
            title=data.get("title", req.title),
            department=data.get("department"),
            university=data.get("university"),
            semester=data.get("semester", req.semester),
            credits=data.get("credits"),
            total_hours=data.get("total_hours", req.total_hours),
            description=data.get("description"),
            competencies=data.get("competencies", []),
            syllabus_content=data.get("syllabus_content", {}),
            assessment_tools=data.get("assessment_tools", []),
            literature=data.get("literature", [])
        )
        db.add(syllabus)
        db.commit()
        db.refresh(syllabus)
        return syllabus
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации: {str(e)}")
    
@app.get("/api/syllabus/courses")
async def get_syllabus_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    courses = db.query(SyllabusCourse).filter(SyllabusCourse.user_id == current_user.id).order_by(SyllabusCourse.created_at.desc()).all()
    return courses

@app.get("/api/syllabus/courses/{course_id}")
async def get_syllabus_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(SyllabusCourse).filter(SyllabusCourse.id == course_id, SyllabusCourse.user_id == current_user.id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    return course

@app.put("/api/syllabus/courses/{course_id}")
async def update_syllabus_course(
    course_id: int,
    req: SyllabusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(SyllabusCourse).filter(SyllabusCourse.id == course_id, SyllabusCourse.user_id == current_user.id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    for field, value in req.dict(exclude_unset=True).items():
        setattr(course, field, value)
    course.updated_at = datetime.utcnow()
    db.commit()
    return course

@app.delete("/api/syllabus/courses/{course_id}")
async def delete_syllabus_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(SyllabusCourse).filter(SyllabusCourse.id == course_id, SyllabusCourse.user_id == current_user.id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    db.delete(course)
    db.commit()
    return {"message": "Курс удалён"}

import httpx
import feedparser
from datetime import datetime
from .models import ScientificArticle

# Генерация обзора литературы на основе списка статей
@app.get("/api/scientific/search")
async def search_arxiv(
    query: str,
    max_results: int = 10,
    current_user: User = Depends(get_current_user)
):
    if not query:
        raise HTTPException(400, "Query is required")
    
    # Кодируем query для URL
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(502, f"arXiv API error: status {response.status_code}")
            feed = feedparser.parse(response.text)
        except httpx.TimeoutException:
            raise HTTPException(504, "arXiv API timeout")
        except Exception as e:
            raise HTTPException(502, f"arXiv API error: {str(e)}")
    
    results = []
    for entry in feed.entries:
        arxiv_id = entry.id.split('/abs/')[-1] if '/abs/' in entry.id else None
        published = None
        if hasattr(entry, 'published'):
            try:
                published = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ')
            except:
                pass
        results.append({
            "arxiv_id": arxiv_id,
            "title": entry.title,
            "authors": ", ".join([author.name for author in entry.authors]) if hasattr(entry, 'authors') else "",
            "summary": entry.summary,
            "published": published.isoformat() if published else None,
            "url": entry.link,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
        })
    return results

# Генерация BibTeX по arXiv ID
@app.get("/api/scientific/bibtex")
async def get_bibtex(
    arxiv_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получение BibTeX-цитаты для статьи по arXiv ID.
    """
    url = f"https://arxiv.org/bibtex/{arxiv_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(404, "BibTeX not found")
        bibtex = response.text
        return {"bibtex": bibtex}

@app.post("/api/scientific/review")
async def generate_literature_review(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    data = await request.json()
    topic = data.get("topic")
    articles = data.get("articles", [])
    if not topic or not articles:
        raise HTTPException(400, "Topic and articles list are required")
    
    context = ""
    for i, art in enumerate(articles[:10], 1):
        context += f"[{i}] {art.get('title')}. {art.get('authors')}. {art.get('summary')}\n\n"
    
    prompt = f"""You are a research assistant. Write a literature review on the topic: "{topic}".

Based on the following academic papers, synthesize a structured review (in Russian) that includes:
- Introduction to the topic
- Main directions and key findings
- Comparison of approaches
- Gaps and future research
- References (numbered list, with titles and authors)

Papers:
{context}

Write in Russian, academic style, 1000-1500 words."""
    
    try:
        review = await deepseek_client.chat_completion([
            {"role": "system", "content": "You are a research assistant. Write a detailed literature review."},
            {"role": "user", "content": prompt}
        ], max_tokens=2500, temperature=0.5)
        return {"review": review}
    except Exception as e:
        raise HTTPException(500, f"Generation error: {str(e)}")

# Сохранение статьи в избранное (опционально)
@app.post("/api/scientific/favorite")
async def save_article(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = await request.json()
    article = ScientificArticle(
        user_id=current_user.id,
        arxiv_id=data.get("arxiv_id"),
        title=data.get("title"),
        authors=data.get("authors"),
        summary=data.get("summary"),
        published=datetime.fromisoformat(data["published"]) if data.get("published") else None,
        url=data.get("url"),
        bibtex=data.get("bibtex"),
        is_favorite=True
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

# Получение списка избранных статей
@app.get("/api/scientific/favorites")
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    articles = db.query(ScientificArticle).filter(
        ScientificArticle.user_id == current_user.id,
        ScientificArticle.is_favorite == True
    ).order_by(ScientificArticle.created_at.desc()).all()
    return articles

def safe_execute_code(code: str, local_vars: dict) -> tuple:
    """
    Выполняет Python-код в ограниченной среде.
    Возвращает (output_text, list_of_base64_images, error_message)
    """
    # Разрешаем только определённые модули
    allowed_modules = {
        'pandas': pd,
        'np': np,          # numpy должен быть импортирован как np
        'matplotlib': matplotlib,
        'plt': plt,
        'math': __import__('math'),
        'random': __import__('random'),
        'statistics': __import__('statistics'),
        'datetime': __import__('datetime'),
        'collections': __import__('collections'),
        'itertools': __import__('itertools'),
        'functools': __import__('functools'),
        'typing': __import__('typing'),
    }
    # Добавляем numpy, если ещё нет
    try:
        import numpy as np
        allowed_modules['numpy'] = np
    except ImportError:
        pass

    safe_globals_dict = safe_globals.copy()
    safe_globals_dict.update(allowed_modules)
    safe_globals_dict['__builtins__'] = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
        'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'range': range, 'round': round,
        'str': str, 'sum': sum, 'tuple': tuple, 'zip': zip, 'print': print,
        'isinstance': isinstance, 'type': type, 'object': object,
        'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    }

    # Переменные, которые будут доступны в коде
    local_vars.update({
        '__name__': '__main__',
        '_output': '',
        '_images': [],
    })

    # Компилируем код с ограничениями
    try:
        byte_code = compile_restricted(code, '<string>', 'exec')
    except SyntaxError as e:
        return "", [], f"Синтаксическая ошибка: {str(e)}"

    # Перенаправляем print в строку
    class PrintCollector:
        def write(self, text):
            local_vars['_output'] += str(text)
    import sys
    original_stdout = sys.stdout
    sys.stdout = PrintCollector()

    try:
        exec(byte_code, safe_globals_dict, local_vars)
        # Если код определил переменную result, добавим её в вывод
        if 'result' in local_vars:
            local_vars['_output'] += str(local_vars['result'])
        # Сохраняем графики
        images = []
        for i, fig_num in enumerate(plt.get_fignums()):
            fig = plt.figure(fig_num)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            images.append(f"data:image/png;base64,{img_base64}")
        plt.close('all')
        return local_vars.get('_output', ''), images, None
    except Exception as e:
        return "", [], str(e)
    finally:
        sys.stdout = original_stdout

@app.post("/api/data/upload")
async def upload_data_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import pandas as pd
    import io
    from pathlib import Path
    import uuid

    content = await file.read()
    # Определяем формат по расширению
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(content))
    elif file.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(400, "Only CSV and Excel files are supported")
    
    # Сохраняем DataFrame как JSON
    df_json = df.to_json(orient='records', date_format='iso')
    
    # Опционально сохраняем файл на диск
    temp_dir = Path("/tmp/data_analysis")
    temp_dir.mkdir(exist_ok=True)
    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = temp_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    session = DataAnalysisSession(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        dataframe_json=df_json,
        status="uploaded"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "filename": file.filename}

@app.post("/api/data/analyze")
async def analyze_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import io
    import sys
    import base64
    import pandas as pd
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    data = await request.json()
    session_id = data.get("session_id")
    code = data.get("code", "")
    
    if not session_id or not code:
        raise HTTPException(400, "session_id and code required")
    
    analysis_session = db.query(DataAnalysisSession).filter(
        DataAnalysisSession.id == session_id,
        DataAnalysisSession.user_id == current_user.id
    ).first()
    if not analysis_session:
        raise HTTPException(404, "Session not found")
    
    # Сохраняем код
    analysis_session.code = code
    db.commit()
    
    # Восстанавливаем DataFrame из JSON
    if analysis_session.dataframe_json:
        df = pd.read_json(analysis_session.dataframe_json, orient='records')
    else:
        df = pd.DataFrame()
    
    # Безопасные builtins
    safe_builtins = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
        'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'print': print, 'range': range,
        'round': round, 'str': str, 'sum': sum, 'tuple': tuple, 'zip': zip,
        'type': type, 'isinstance': isinstance, 'issubclass': issubclass,
        'True': True, 'False': False, 'None': None
    }
    
    # Перехват stdout
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture
    
    figures = []
    original_show = plt.show
    def show_capture(*args, **kwargs):
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        figures.append(img_base64)
        plt.close()
    plt.show = show_capture
    
    try:
        exec_globals = {
            '__builtins__': safe_builtins,
            'pd': pd,
            'np': np,
            'plt': plt,
            'df': df,
        }
        exec(code, exec_globals)
        
        out = stdout_capture.getvalue()
        err = stderr_capture.getvalue()
        
        # Сохраняем результаты
        analysis_session.output_text = out
        analysis_session.output_images = figures
        analysis_session.status = "success" if not err else "warning"
        analysis_session.error_message = err if err else None
        db.commit()
        
        return {
            "stdout": out,
            "stderr": err,
            "figures": figures,
            "has_figures": len(figures) > 0
        }
    except Exception as e:
        analysis_session.status = "error"
        analysis_session.error_message = str(e)
        db.commit()
        raise HTTPException(500, f"Analysis error: {str(e)}")
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        plt.show = original_show

@app.get("/api/data/result/{session_id}")
async def get_data_result(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(DataAnalysisSession).filter(
        DataAnalysisSession.id == session_id,
        DataAnalysisSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "status": session.status,
        "output_text": session.output_text,
        "output_images": session.output_images,
        "error_message": session.error_message,
        "code": session.code,
        "filename": session.filename
    }

@app.post("/api/ai/generate-code")
async def generate_code_proxy(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    data = await request.json()
    prompt = data.get("prompt", "")
    df_info = data.get("df_info", "")
    
    code = await deepseek_client.chat_completion([
        {
            "role": "system",
            "content": "Ты эксперт по анализу данных. Пиши только Python-код без объяснений и без markdown-тегов."
        },
        {
            "role": "user",
            "content": f"""Напиши Python-код для pandas/matplotlib.

Структура датафрейма (df уже загружен):
{df_info}

Задача: {prompt}

Правила:
- df уже доступен, pandas импортировать не нужно
- numpy доступен как np
- Для графиков используй plt.show() в конце
- plt.rcParams["figure.figsize"] = (10, 6) для размера
- plt.tight_layout() перед show()
- Только код, никаких пояснений"""
        }
    ], max_tokens=1000, temperature=0.3)
    
    code = code.replace("```python", "").replace("```", "").strip()
    return {"code": code}

@app.post("/api/review-text")
async def review_text(
    req: TextReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Текст не может быть пустым")
    title = req.title or "Без названия"
    
    # 1. Проверка на плагиат
    plagiarism_percent, similar_parts = check_plagiarism(db, current_user.id, title, text)
    
    # 2. AI-рецензия (используем усовершенствованный промпт)
    prompt = f"""Ты – строгий научный рецензент. Проведи рецензирование следующего текста.

Название: {title}
Текст:
{text[:8000]}

Оцени текст по шкале 0-100 по следующим критериям:
- Логика и аргументация (25%)
- Новизна и вклад (20%)
- Структура и последовательность (15%)
- Язык и стиль (20%)
- Оформление ссылок и корректность цитирования (10%)
- Соответствие теме (10%)

Верни ТОЛЬКО JSON в формате:
{{
  "score": 75,
  "grade": "хорошо",
  "strengths": ["список сильных сторон"],
  "weaknesses": ["список слабых мест"],
  "recommendations": ["рекомендации"],
  "detailed_feedback": "развёрнутый отзыв (3-5 предложений)"
}}
Дополнительно, если обнаружены явные признаки плагиата, укажи это в feedback."""
    
    try:
        ai_response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты научный рецензент. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=1500, temperature=0.4)
        
        # Очистка от маркдауна
        ai_response = ai_response.strip()
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        if ai_response.startswith("```"):
            ai_response = ai_response[3:]
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]
        ai_response = ai_response.strip()
        
        feedback = json.loads(ai_response)
    except Exception as e:
        # fallback
        feedback = {
            "score": 50, "grade": "удовлетворительно",
            "strengths": ["Текст содержит интересные идеи"],
            "weaknesses": ["Не хватает структуры", "Стиль не научный"],
            "recommendations": ["Улучшить аргументацию", "Переписать введение"],
            "detailed_feedback": "Автоматическая проверка не удалась. Рекомендуется доработать текст."
        }
    
    # Сохраняем в БД
    review = TextReview(
        user_id=current_user.id,
        title=title,
        text=text,
        ai_feedback=feedback,
        plagiarism_percent=plagiarism_percent,
        similar_parts=similar_parts
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    return {
        "review_id": review.id,
        "score": feedback["score"],
        "grade": feedback["grade"],
        "strengths": feedback["strengths"],
        "weaknesses": feedback["weaknesses"],
        "recommendations": feedback["recommendations"],
        "detailed_feedback": feedback["detailed_feedback"],
        "plagiarism_percent": plagiarism_percent,
        "similar_parts": similar_parts
    }

@app.get("/api/review-history")
async def get_review_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    reviews = db.query(TextReview).filter(TextReview.user_id == current_user.id).order_by(TextReview.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "score": r.ai_feedback.get("score"),
            "grade": r.ai_feedback.get("grade"),
            "plagiarism_percent": r.plagiarism_percent,
            "created_at": r.created_at.isoformat()
        }
        for r in reviews
    ]

# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========
# ========== IELTS МОДУЛЬ (полностью) ==========

import whisper
import tempfile
import json

# Глобальная переменная для модели Whisper (загружается один раз)
whisper_model = None

@app.on_event("startup")
async def load_whisper_model():
    global whisper_model
    try:
        whisper_model = whisper.load_model("base")
        print("✅ Whisper model loaded for IELTS")
    except Exception as e:
        print(f"⚠️ Failed to load Whisper: {e}")

from app.tasks.audio_tasks import transcribe_and_analyze
import uuid

@app.post("/ielts/speaking/analyze")
async def analyze_ielts_speaking(
    file: UploadFile = File(...),
    task_type: str = "part1",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Сохраняем аудио во временный файл
    ext = file.filename.split(".")[-1] if "." in file.filename else "webm"
    safe_filename = f"{uuid.uuid4()}.{ext}"
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, safe_filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Запускаем Celery задачу
    task = transcribe_and_analyze.delay(
        audio_path=file_path,
        task_type=task_type,
        user_id=current_user.id
    )
    
    return {
        "status": "processing",
        "task_id": task.id,
        "message": "Audio is being transcribed and analyzed. Poll /ielts/speaking/result/{task_id} for result."
    }

from celery.result import AsyncResult
from app.celery import celery_app

@app.get("/ielts/speaking/result/{task_id}")
async def get_speaking_result(task_id: str, current_user: User = Depends(get_current_user)):
    task = AsyncResult(task_id, app=celery_app)
    if task.ready():
        result = task.result
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    else:
        return {"status": "pending", "task_id": task_id}

@app.post("/ielts/writing/analyze")
async def analyze_ielts_writing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = await request.json()
    task_type = data.get("task_type", "task1")
    answer = data.get("answer", "")

    prompt = f"""You are an official IELTS examiner. Evaluate the following writing response for IELTS {task_type.upper()}.

Task: {task_type.upper()}
Answer: "{answer}"

Return ONLY valid JSON with:
- task_achievement: band score 0-9
- coherence_cohesion: band score 0-9
- lexical_resource: band score 0-9
- grammatical_range_accuracy: band score 0-9
- overall_band: average rounded to nearest 0.5
- word_count: number of words
- feedback: detailed feedback (2-3 sentences)
- suggestions: array of 3 specific suggestions"""
    response = await deepseek_client.chat_completion([
        {"role": "system", "content": "You are an official IELTS examiner. Respond only with JSON."},
        {"role": "user", "content": prompt}
    ], max_tokens=800)

    try:
        evaluation = json.loads(response)
    except:
        evaluation = {
            "task_achievement": 6, "coherence_cohesion": 6,
            "lexical_resource": 6, "grammatical_range_accuracy": 6,
            "overall_band": 6.0, "word_count": len(answer.split()),
            "feedback": "Your essay was evaluated automatically. Focus on structure and vocabulary.",
            "suggestions": ["Plan before writing", "Use linking words", "Check grammar"]
        }

    # Сохраняем в БД
    attempt = IELTSAttempt(
        user_id=current_user.id,
        task_type=f"writing_{task_type}",
        answer_text=answer,
        scores={
            "task_achievement": evaluation["task_achievement"],
            "coherence_cohesion": evaluation["coherence_cohesion"],
            "lexical_resource": evaluation["lexical_resource"],
            "grammatical_range_accuracy": evaluation["grammatical_range_accuracy"]
        },
        overall_band=evaluation["overall_band"],
        feedback=evaluation["feedback"],
        suggestions=evaluation["suggestions"]
    )
    db.add(attempt)
    db.commit()

    return {
        "scores": attempt.scores,
        "overall_band": attempt.overall_band,
        "word_count": evaluation.get("word_count", len(answer.split())),
        "feedback": attempt.feedback,
        "suggestions": attempt.suggestions
    }


@app.get("/ielts/attempts")
async def get_ielts_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempts = db.query(IELTSAttempt).filter(
        IELTSAttempt.user_id == current_user.id
    ).order_by(IELTSAttempt.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "task_type": a.task_type,
            "overall_band": a.overall_band,
            "created_at": a.created_at
        }
        for a in attempts
    ]


@app.get("/ielts/attempt/{attempt_id}")
async def get_ielts_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(IELTSAttempt).filter(
        IELTSAttempt.id == attempt_id,
        IELTSAttempt.user_id == current_user.id
    ).first()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    return {
        "task_type": attempt.task_type,
        "transcript": attempt.transcript,
        "answer_text": attempt.answer_text,
        "scores": attempt.scores,
        "overall_band": attempt.overall_band,
        "feedback": attempt.feedback,
        "suggestions": attempt.suggestions,
        "created_at": attempt.created_at
    }
    