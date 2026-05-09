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
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

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

@app.get("/")
async def root():
    return {"message": "Universal AI Teacher API", "status": "running"}

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
