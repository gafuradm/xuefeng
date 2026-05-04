# backend/app/main.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Отключаем предупреждения tokenizers

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import concurrent.futures
from datetime import datetime
import asyncio

from .database import engine, get_db
from .models import Base, User, CustomTest
from .deepseek_client import deepseek_client
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

video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
os.makedirs(video_dir, exist_ok=True)
app.mount("/static/videos", StaticFiles(directory=video_dir), name="videos")

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
    subject: Optional[str] = Query(None, description="Предмет (физика, химия, биология...)")
):
    """Поиск задач в векторной базе с фильтрацией по предмету"""
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
        
        results = ai_service.exam_manager.search_problems(
            exam_type, query, k, filters
        )
        
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
    
@app.post("/api/exams/custom")
async def add_custom_exam(exam_data: dict, db: Session = Depends(get_db)):
    """Сохраняет пользовательский экзамен (JSON с темами)"""
    from .subject_topics import save_custom_exam
    exam_name = exam_data.get("name")
    if not exam_name:
        raise HTTPException(400, "Не указано название экзамена")
    save_custom_exam(exam_name, exam_data)
    return {"status": "ok", "message": f"Экзамен '{exam_name}' сохранён"}

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ (Custom Tests) ==========

@app.post("/api/custom_tests")
async def create_custom_test(
    test_data: CustomTestCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Создать новый пользовательский тест"""
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
async def get_user_tests(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получить все тесты пользователя"""
    tests = db.query(CustomTest).filter(CustomTest.user_id == user_id).all()
    return tests

@app.get("/api/custom_tests/{test_id}")
async def get_custom_test(
    test_id: int,
    db: Session = Depends(get_db)
):
    """Получить тест по ID"""
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    return test

@app.delete("/api/custom_tests/{test_id}")
async def delete_custom_test(
    test_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Удалить тест (только владелец)"""
    test = db.query(CustomTest).filter(CustomTest.id == test_id, CustomTest.user_id == user_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден или не принадлежит вам")
    db.delete(test)
    db.commit()
    return {"status": "ok", "message": "Тест удалён"}

@app.post("/api/custom_tests/{test_id}/train")
async def train_ai_on_custom_test(
    test_id: int,
    db: Session = Depends(get_db)
):
    """
    Обучить ИИ на основе пользовательского теста.
    DeepSeek сохранит структуру теста и сможет генерировать похожие вопросы.
    """
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    
    # Формируем промпт для обучения ИИ
    prompt = f"""
Ты – ИИ учитель. Пользователь создал тест с названием "{test.name}" и хочет, чтобы ты запомнил его структуру и стиль вопросов.

Вот тест:
ОПИСАНИЕ: {test.description or 'нет описания'}

ВОПРОСЫ:
"""
    for i, q in enumerate(test.questions, 1):
        prompt += f"\n{i}. {q['text']}\n   Правильный ответ: {q['correct_answer']}\n   Пояснение: {q.get('explanation', 'нет')}\n"
    
    prompt += """
Пожалуйста, проанализируй этот тест и запомни его формат, сложность, стиль формулировок. В будущих запросах, когда я попрошу сгенерировать похожие вопросы, используй этот тест как референс.
Ответь коротко: "Тест запомнен. Готов генерировать похожие задачи."
"""
    
    response = await ai_service._custom_train(prompt)
    return {"status": "trained", "message": response, "test_id": test_id}

@app.post("/api/custom_tests/{test_id}/submit")
async def submit_custom_test(
    test_id: int,
    submission: CustomTestSubmit,
    db: Session = Depends(get_db)
):
    """Пройти тест и получить оценку"""
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
    
    # Сохраняем историю прохождения (можно создать таблицу)
    return {
        "test_name": test.name,
        "total": total,
        "correct": score,
        "score": percentage,
        "grade": grade,
        "results": results
    }

@app.post("/api/custom_tests/{test_id}/generate_similar")
async def generate_similar_questions(
    test_id: int,
    num_questions: int = 5,
    db: Session = Depends(get_db)
):
    """
    Генерирует новые вопросы, похожие на стиль и сложность пользовательского теста.
    """
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    
    # Берём первые 3 вопроса как примеры
    examples = test.questions[:3]
    examples_text = "\n".join([f"{i+1}. {q['text']} -> {q['correct_answer']}" for i, q in enumerate(examples)])
    
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
    
    try:
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return {"questions": questions, "count": len(questions)}
        else:
            return {"error": "Не удалось распарсить ответ", "raw": response}
    except Exception as e:
        return {"error": str(e)}

# ========== ЭНДПОИНТ ГЕНЕРАЦИИ ВИДЕО ==========
@app.post("/api/lessons/{lesson_id}/generate_video")
async def generate_video_for_lesson(lesson_id: int, db: Session = Depends(get_db)):
    from .models import Lesson, LessonVideo
    from .video_generator import VideoGenerator
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    # Проверяем, есть ли уже видео
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
    
    # Для каждой задачи генерируем пошаговое решение через DeepSeek
    print(f"Генерация пошаговых решений для {len(tasks)} задач...")
    tasks_with_solutions = []
    for idx, task in enumerate(tasks[:5]):
        problem = task.get('task', '')
        answer = task.get('answer', '')
        if problem and answer:
            print(f"  Задача {idx+1}: {problem[:50]}...")
            steps = await deepseek_client.get_step_by_step_solution(problem, subject="математика")
            tasks_with_solutions.append({
                "problem": problem,
                "steps": steps,
                "answer": answer
            })
    
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