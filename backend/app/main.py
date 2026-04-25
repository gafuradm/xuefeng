# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json

from .database import engine, get_db
from .models import Base
from .schemas import *
from .services import AITeacherService
from .config import settings

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

# Монтируем статику (фронтенд)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Инициализация сервиса
ai_service = AITeacherService()

@app.on_event("startup")
async def startup_event():
    """Загрузка данных при старте"""
    print("🚀 Запуск Universal AI Teacher...")
    if ai_service.rag_available:
        print("✅ RAG система готова")

@app.get("/")
async def root():
    return {"message": "Universal AI Teacher API", "status": "running"}

@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Создание нового пользователя"""
    try:
        return await ai_service.create_user(db, user.email, user.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(user_id: int, session_data: SessionCreate, db: Session = Depends(get_db)):
    """Создание новой учебной сессии"""
    try:
        return await ai_service.create_session(db, user_id, session_data.exam_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_test")
async def submit_test(session_id: int, test_data: TestSubmit, db: Session = Depends(get_db)):
    """Отправка ответов на начальный тест"""
    try:
        result = await ai_service.submit_test(db, session_id, test_data.answers)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/set_time")
async def set_time(session_id: int, time_data: TimeSet, db: Session = Depends(get_db)):
    """Установка времени подготовки и создание плана"""
    try:
        plan = await ai_service.set_time_and_plan(db, session_id, time_data.days)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/next_lesson")
async def get_next_lesson(session_id: int, db: Session = Depends(get_db)):
    """Получение следующего урока"""
    try:
        return await ai_service.get_next_lesson(db, session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_lesson")
async def submit_lesson(session_id: int, lesson_data: LessonAnswer, db: Session = Depends(get_db)):
    """Отправка ответов на урок"""
    try:
        result = await ai_service.submit_lesson(
            db, session_id, lesson_data.lesson_id, lesson_data.user_answers
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/progress_test")
async def create_progress_test(session_id: int, db: Session = Depends(get_db)):
    """Создание промежуточного теста"""
    try:
        questions = await ai_service.generate_progress_test(db, session_id)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/lessons/{lesson_id}/chat")
async def lesson_chat(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    session_id = data.get("session_id")
    question = data.get("question")
    if not session_id or not question:
        raise HTTPException(status_code=400, detail="session_id and question required")
    answer = await ai_service.chat_with_bot(db, session_id, lesson_id, question)
    return {"answer": answer}

# backend/app/main.py - замените существующий эндпоинт get_session

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Получение информации о сессии с тестами"""
    from .models import Session as SessionModel
    from .models import TestResult
    
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Получаем тесты для этой сессии
    test_results = db.query(TestResult).filter(
        TestResult.session_id == session_id
    ).all()
    
    # Преобразуем в словарь
    result = {
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
                "created_at": t.created_at
            }
            for t in test_results
        ]
    }
    
    return result

@app.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: int, db: Session = Depends(get_db)):
    """Получение истории прогресса"""
    from .models import ProgressHistory
    history = db.query(ProgressHistory).filter(
        ProgressHistory.session_id == session_id
    ).order_by(ProgressHistory.timestamp).all()
    return history

# RAG эндпоинты

@app.get("/api/exams/{exam_type}/search")
async def search_problems(
    exam_type: str,
    query: str = Query(..., description="Поисковый запрос"),
    k: int = Query(5, ge=1, le=50, description="Количество результатов"),
    year: Optional[int] = Query(None, description="Год"),
    topic: Optional[str] = Query(None, description="Тема"),
    subject: Optional[str] = Query(None, description="Предмет (физика, химия, биология...)")  # НОВОЕ
):
    """Поиск задач в векторной базе с фильтрацией по предмету"""
    try:
        filters = {}
        if year:
            filters['year'] = year
        if topic:
            filters['topic'] = topic
        if subject:
            filters['subject'] = subject   # добавляем фильтр по предмету
        
        if exam_type not in ai_service.exam_manager.active_exams:
            return {"results": [], "message": f"Экзамен {exam_type} не найден"}
        
        results = ai_service.exam_manager.search_problems(
            exam_type, query, k, filters
        )
        
        clean_results = []
        for r in results:
            clean = {
                'id': r.get('id'),
                'topic': r.get('topic'),
                'year': r.get('year'),
                'subject': r.get('subject'),          # добавим предмет в вывод
                'text': (r.get('text') or r.get('question') or r.get('raw_text') or '')[:2000],
                'answer': r.get('answer', ''),
                'solution': r.get('solution', ''),
                'difficulty': r.get('difficulty', 'medium')
            }
            clean_results.append(clean)
        
        return {
            "query": query,
            "count": len(clean_results),
            "results": clean_results
        }
        
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/api/exams/{exam_type}/stats")
async def get_exam_stats(exam_type: str):
    """Статистика по экзамену"""
    try:
        if exam_type not in ai_service.exam_manager.active_exams:
            return {"error": f"Экзамен {exam_type} не найден"}
        
        store = ai_service.exam_manager.active_exams[exam_type]
        metadata = store.get('metadata', [])
        
        stats = {
            "total_problems": len(metadata),
            "topics": {},
            "years": {},
            "difficulties": {}
        }
        
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
    """Тестовый эндпоинт для отладки поиска"""
    try:
        results = ai_service.exam_manager.search_problems('gaokao', query, k)
        return {
            "query": query,
            "count": len(results),
            "results": results[:k]
        }
    except Exception as e:
        return {"error": str(e)}