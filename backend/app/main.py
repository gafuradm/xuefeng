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
from fastapi.responses import RedirectResponse

# backend/app/main.py - добавьте импорты в начало файла

from .models import (
    User, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance  # <--- ВАЖНО: добавить эти две модели
)

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

# backend/app/main.py (добавить новые эндпоинты)

from .models import UserCourse, CourseModule, CourseLesson, UserLesson
from .schemas import UserCourseCreate, UserCourseResponse, UserLessonCreate, UserLessonResponse

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КУРСЫ ==========

# backend/app/main.py - исправленный эндпоинт

@app.post("/api/courses/generate")  # убрали response_model
async def generate_course(
    course_data: UserCourseCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Сгенерировать новый курс (структуру) на основе названия и описания"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    # Генерируем структуру через AI
    structure = await ai_service.generate_course_structure(
        course_data.name,
        course_data.description,
        course_data.success_criteria
    )
    
    if "error" in structure:
        raise HTTPException(400, structure["error"])
    
    # Создаём курс
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
    
    # Создаём модули и уроки
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
    
    # Возвращаем словарь вручную (без response_model)
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
async def get_user_courses(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получить все курсы пользователя"""
    courses = db.query(UserCourse).filter(UserCourse.user_id == user_id).all()
    return courses

@app.get("/api/courses/{course_id}")
async def get_course_details(
    course_id: int,
    db: Session = Depends(get_db)
):
    """Получить курс с модулями и уроками"""
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    # Подгружаем модули и уроки
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
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "order": lesson.order,
                "content": lesson.content,
                "success_criteria": lesson.success_criteria
            }
            module_data["lessons"].append(lesson_data)
        result["modules"].append(module_data)
    return result

@app.post("/api/courses/{course_id}/generate_lesson_content/{lesson_id}")
async def generate_lesson_content(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db)
):
    """Сгенерировать полное содержание для конкретного урока курса"""
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id, CourseLesson.module.has(course_id=course_id)).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    # Получаем тему и описание из lesson.content
    subject = "общий предмет"  # можно определить из контекста курса
    title = lesson.title
    description = lesson.content.get("description", "")
    
    content = await ai_service.generate_lesson_content(title, subject, description)
    if "error" in content:
        raise HTTPException(400, content["error"])
    
    lesson.content = content
    lesson.success_criteria = content.get("success_criteria", "")
    lesson.youtube_urls = content.get("youtube_urls", [])
    # presentation_url можно сохранить отдельно (сгенерировать ссылку)
    db.commit()
    
    return {"status": "ok", "message": "Содержание урока сгенерировано"}

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ УРОКИ (отдельные) ==========

@app.post("/api/lessons/generate", response_model=UserLessonResponse)
async def generate_lesson(
    lesson_data: UserLessonCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Сгенерировать отдельный урок (не в составе курса)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    content = await ai_service.generate_lesson_content(
        lesson_data.title,
        lesson_data.subject,
        lesson_data.description
    )
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
async def get_user_lessons(
    user_id: int,
    db: Session = Depends(get_db)
):
    lessons = db.query(UserLesson).filter(UserLesson.user_id == user_id).all()
    return lessons

@app.get("/api/lessons/{lesson_id}")
async def get_lesson_details(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

# ========== ГЕНЕРАЦИЯ ПРЕЗЕНТАЦИИ ==========
@app.post("/api/lessons/{lesson_id}/generate_presentation")
async def generate_presentation(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    """Сгенерировать HTML-презентацию для урока и вернуть ссылку"""
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    # Если презентация уже есть, вернуть существующую ссылку
    if lesson.presentation_url:
        return {"presentation_url": lesson.presentation_url}
    
    # Генерируем HTML из content
    content = lesson.content
    theory = content.get("theory", "")
    practice = content.get("practice", [])
    homework = content.get("homework", [])
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{lesson.title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .slide {{ margin-bottom: 40px; page-break-after: always; }}
        h1 {{ color: #667eea; }}
        .task {{ background: #f5f5f5; padding: 15px; border-radius: 10px; margin: 10px 0; }}
        .answer {{ color: #2c3e50; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="slide">
        <h1>{lesson.title}</h1>
        <p><strong>Предмет:</strong> {lesson.subject}</p>
        <p>{lesson.description or ''}</p>
    </div>
    <div class="slide">
        <h2>📖 Теория</h2>
        {theory}
    </div>
    <div class="slide">
        <h2>✍️ Практические задания</h2>
        {''.join(f'<div class="task"><strong>Задача {i+1}:</strong> {p["task"]}<br><span class="answer">Ответ: {p["answer"]}</span></div>' for i, p in enumerate(practice))}
    </div>
    <div class="slide">
        <h2>🏠 Домашнее задание</h2>
        {''.join(f'<div class="task"><strong>Задача {i+1}:</strong> {h["task"]}<br><span class="answer">Ответ: {h["answer"]}</span></div>' for i, h in enumerate(homework))}
    </div>
    <div class="slide">
        <h2>🎯 Критерии успеха</h2>
        <p>{lesson.success_criteria}</p>
    </div>
</body>
</html>
    """
    # Сохраняем HTML во временный файл и возвращаем ссылку
    import os
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

# backend/app/main.py - добавить

@app.delete("/api/courses/{course_id}")
async def delete_course(
    course_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    course = db.query(UserCourse).filter(UserCourse.id == course_id, UserCourse.user_id == user_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    db.delete(course)
    db.commit()
    return {"status": "ok"}

# backend/app/main.py - добавить эндпоинты

# Получить урок из курса по ID
@app.get("/api/course_lessons/{lesson_id}")
async def get_course_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

# Удалить самостоятельный урок
@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id, UserLesson.user_id == user_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден или не принадлежит вам")
    db.delete(lesson)
    db.commit()
    return {"status": "ok", "message": "Урок удалён"}

# Удалить курс
@app.delete("/api/courses/{course_id}")
async def delete_course(
    course_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    course = db.query(UserCourse).filter(UserCourse.id == course_id, UserCourse.user_id == user_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден или не принадлежит вам")
    db.delete(course)
    db.commit()
    return {"status": "ok", "message": "Курс удалён"}

# Генерация содержания для урока курса (если ещё нет)
@app.post("/api/courses/{course_id}/generate_lesson_content/{lesson_id}")
async def generate_course_lesson_content(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db)
):
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id,
        CourseLesson.module.has(course_id=course_id)
    ).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    
    # Если контент уже есть, не перезаписываем
    if lesson.content and lesson.content.get("theory"):
        return {"status": "already_exists", "message": "Контент уже сгенерирован"}
    
    # Получаем контекст курса для лучшей генерации
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    subject = "общий предмет"
    title = lesson.title
    description = lesson.content.get("description", "") if lesson.content else ""
    
    content = await ai_service.generate_lesson_content(title, subject, description)
    
    if "error" in content:
        raise HTTPException(400, content["error"])
    
    lesson.content = content
    lesson.success_criteria = content.get("success_criteria", "")
    lesson.youtube_urls = content.get("youtube_urls", [])
    db.commit()
    
    return {"status": "ok", "message": "Содержание урока сгенерировано"}

@app.post("/api/courses/{course_id}/generate_all_lessons_content")
async def generate_all_lessons_content(
    course_id: int,
    db: Session = Depends(get_db)
):
    """Сгенерировать содержание для всех уроков курса"""
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    
    generated_count = 0
    errors = []
    
    # Проходим по всем модулям и урокам
    for module in course.modules:
        for lesson in module.lessons:
            # Пропускаем, если контент уже есть
            if lesson.content and lesson.content.get("theory"):
                continue
            
            try:
                # Получаем контекст
                subject = "общий предмет"
                title = lesson.title
                description = lesson.content.get("description", "") if lesson.content else ""
                
                content = await ai_service.generate_lesson_content(title, subject, description)
                
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
    
    return {
        "status": "ok",
        "generated_count": generated_count,
        "errors": errors
    }

# backend/app/main.py – добавить эндпоинты

@app.get("/api/user/statistics")
async def get_user_statistics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получить статистику пользователя"""
    stats = await ai_service.get_user_statistics(db, user_id)
    return stats

@app.get("/api/user/performance")
async def get_user_performance(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получить статистику успеваемости пользователя"""
    performances = db.query(UserPerformance).filter(UserPerformance.user_id == user_id).all()
    return [
        {
            "topic": p.topic,
            "correct_count": p.correct_count,
            "total_count": p.total_count,
            "mastery_level": p.mastery_level,
            "last_attempt": p.last_attempt
        }
        for p in performances
    ]

@app.get("/api/user/interactions")
async def get_user_interactions(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Получить историю взаимодействий с ИИ"""
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

@app.get("/conference")
async def conference_redirect():
    return RedirectResponse(url="http://localhost:8000")

@app.get("/conference/teacher")
async def conference_teacher_redirect():
    return RedirectResponse(url="http://localhost:8000/teacher")

@app.get("/conference/student")
async def conference_student_redirect():
    return RedirectResponse(url="http://localhost:8000/student")

# backend/app/main.py (добавить в конец)

@app.post("/api/video/transcribe")
async def transcribe_video(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    url = data.get("url")
    target_language = data.get("language", "ru")
    if not url:
        raise HTTPException(400, "URL видео не указан")
    result = await ai_service.process_video(url, target_language)
    return result