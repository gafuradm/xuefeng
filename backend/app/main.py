# backend/app/main.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo, IELTSAttempt,
    RefreshToken, PasswordReset, UserAction, ChatMessage,
    Role, UserAchievement, ApiKey, AdminLog
)

from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo, IELTSAttempt,
    RefreshToken, PasswordReset, UserAction, ChatMessage,
    Role, UserAchievement, ApiKey, AdminLog,
    ExamTicket, Task, SyllabusCourse, ScientificArticle,
    UserLessonProgress, CourseAssignment   # ← добавлено
)

from .pdf_rag import extract_text_from_pdf, split_text_into_chunks, create_tfidf_index, search_tfidf_index
from .models import UserDocument
import shutil
import json

from .hypothesis_service import HypothesisGenerator
from .models import Hypothesis

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
from .supervisor_matching import SupervisorMatcher
from .models import Supervisor, UserSupervisor

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, get_db, SessionLocal
from sqlalchemy.orm import Session, joinedload
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
    School, SchoolMember, LessonVideo, SchoolChatMessage
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
from .auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_active_user, decode_token, is_government_user, get_current_government_user
from .deepseek_client import deepseek_client
from .schemas import *
from .services import AITeacherService
from .config import settings
from .role_service import get_visible_tabs, check_module_access, get_default_roles
from .xp_service import award_xp, award_lesson_completion, award_test_passed, award_course_created, award_lesson_created
from .middleware_logging import log_all_actions_middleware

# ========== OCR РАСПОЗНАВАНИЕ РУКОПИСНОГО ТЕКСТА ==========
import easyocr
import numpy as np
from PIL import Image
import io
import uuid

from pathlib import Path
import os

# backend/app/main.py – все импорты (исправленные)

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from .models import (
    Base, User, UserAuth, Session as SessionModel, TestResult, Lesson, ProgressHistory,
    UserCourse, CourseModule, CourseLesson, UserLesson,
    UserInteraction, UserPerformance, CustomTest,
    School, SchoolMember, LessonVideo, IELTSAttempt,
    RefreshToken, PasswordReset, UserAction, ChatMessage,
    Role, UserAchievement, ApiKey, AdminLog,
    ExamTicket, Task, SyllabusCourse, ScientificArticle
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
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from RestrictedPython import compile_restricted, safe_globals
from .models import DataAnalysisSession

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, get_db, SessionLocal
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from fastapi import Body
import concurrent.futures
from datetime import datetime, timedelta
import asyncio
from fastapi import UploadFile, File
from fastapi.responses import RedirectResponse

from .auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_active_user, decode_token, is_government_user, get_current_government_user
from .deepseek_client import deepseek_client
from .schemas import *
from .services import AITeacherService
from .config import settings
from .role_service import get_visible_tabs, check_module_access, get_default_roles
from .xp_service import award_xp, award_lesson_completion, award_test_passed, award_course_created, award_lesson_created
from .middleware_logging import log_all_actions_middleware

import easyocr
import numpy as np
from PIL import Image
import uuid
from pathlib import Path

import whisper
import tempfile
import json
from app.tasks.audio_tasks import transcribe_and_analyze
from celery.result import AsyncResult
from app.celery import celery_app

import httpx
import feedparser

from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
import secrets

from .vacancy_matching import VacancyMatcher
from .models import Company, Vacancy, UserVacancy

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
BASE_DIR = BACKEND_ROOT

# Инициализируем EasyOCR один раз при старте
ocr_reader = None

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Universal AI Teacher", version="2.0.0")

# Подключаем middleware для логирования
app.middleware("http")(log_all_actions_middleware)

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

# ========== ИНИЦИАЛИЗАЦИЯ РОЛЕЙ ПРИ СТАРТЕ ==========
def init_roles(db: Session):
    roles_data = [
        ('schoolchild', 'Школьник', 'Учащийся школы', True, True),
        ('applicant', 'Абитуриент', 'Поступающий в вуз', True, True),
        ('student', 'Студент', 'Студент вуза/колледжа', True, True),
        ('master', 'Магистр', 'Студент магистратуры', True, True),
        ('phd', 'Докторант', 'Аспирант/докторант', True, True),
        ('researcher', 'Исследователь', 'Научный сотрудник', False, True),
        ('professor', 'Профессор', 'Преподаватель вуза', False, True),
        ('school_teacher', 'Школьный учитель', 'Учитель школы', False, True),
        ('private_tutor', 'Частный репетитор', 'Индивидуальный преподаватель', True, True),
        ('employer', 'Работодатель', 'Компания, ищущая сотрудников', False, False),
        ('job_seeker', 'Соискатель', 'Человек в поиске работы', True, True),
        ('freelancer', 'Фрилансер', 'Поставщик услуг', True, True),
        ('customer', 'Заказчик', 'Заказчик услуг', True, True),
        ('startup_founder', 'Стартапер', 'Основатель стартапа', True, True),
        ('investor', 'Инвестор', 'Инвестор проектов', False, False),
        ('government', 'Государство', 'Администратор платформы', False, False),
        ('developer', 'Разработчик API', 'Сторонний разработчик', True, True)
    ]
    for name, display, desc, can_self, need_approval in roles_data:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(
                name=name,
                display_name=display,
                description=desc,
                can_be_assigned_by_user=can_self,
                requires_approval=need_approval,
                is_default=(name in ['schoolchild', 'student'])
            )
            db.add(role)
    db.commit()

@app.on_event("startup")
async def startup_event():
    print("🚀 Запуск Universal AI Teacher v2.0...")
    
    # Инициализация ролей
    db = SessionLocal()
    try:
        init_roles(db)
        print("✅ Роли инициализированы")
    finally:
        db.close()
    
    if ai_service.rag_available:
        print("✅ RAG система готова")
    
    # Инициализация OCR
    global ocr_reader
    try:
        ocr_reader = easyocr.Reader(['ru', 'en'], gpu=False)
        print("✅ EasyOCR загружен")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки EasyOCR: {e}")
    
    # Загрузка Whisper для IELTS
    global whisper_model
    try:
        whisper_model = whisper.load_model("base")
        print("✅ Whisper model loaded for IELTS")
    except Exception as e:
        print(f"⚠️ Failed to load Whisper: {e}")

from fastapi.responses import HTMLResponse
from pathlib import Path

@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    app_html = FRONTEND_DIR / "app.html"
    if app_html.exists():
        with open(app_html, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("app.html not found", status_code=404)

# ========== ПОЛЬЗОВАТЕЛИ (ОБНОВЛЕНО С РОЛЯМИ) ==========
@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, role: str = "student", db: Session = Depends(get_db)):
    try:
        user_obj = await ai_service.create_user(db, user.email, user.name)
        # Назначаем роли по умолчанию
        default_role_names = get_default_roles()
        default_roles = db.query(Role).filter(Role.name.in_(default_role_names)).all()
        user_obj.roles = default_roles
        db.commit()
        db.refresh(user_obj)
        return user_obj
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    project_root = Path(__file__).parent.parent.parent
    ielts_path = project_root / "frontend" / "ielts.html"
    print(f"[IELTS] Looking for file: {ielts_path}")
    if ielts_path.exists():
        with open(ielts_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(f"IELTS page not found at {ielts_path}", status_code=404)

if HSK_DIR.exists():
    @app.get("/hsk", response_class=HTMLResponse)
    async def hsk_frontend():
        index_path = HSK_DIR / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("HSK frontend not found", status_code=404)

# ========== НОВЫЕ ЭНДПОИНТЫ ДЛЯ РОЛЕЙ И ВКЛАДОК ==========
@app.get("/api/user/roles")
async def get_my_roles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список своих ролей и доступные для назначения"""
    my_role_names = [role.name for role in current_user.roles]
    available_roles = db.query(Role).filter(Role.can_be_assigned_by_user == True).all()
    return {
        "my_roles": my_role_names,
        "available_roles": [{"name": r.name, "display_name": r.display_name, "requires_approval": r.requires_approval} for r in available_roles]
    }

@app.post("/api/user/roles/assign")
async def assign_role_to_myself(role_name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Пользователь запрашивает добавление себе роли"""
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(404, "Роль не найдена")
    if not role.can_be_assigned_by_user:
        raise HTTPException(403, "Эту роль нельзя назначить самостоятельно")
    if role in current_user.roles:
        return {"message": "Роль уже есть"}
    if role.requires_approval:
        admin_log = AdminLog(
            admin_user_id=current_user.id,
            target_user_id=current_user.id,
            action="request_role",
            details={"role": role_name, "status": "pending"}
        )
        db.add(admin_log)
        db.commit()
        return {"message": "Запрос на роль отправлен администратору"}
    else:
        current_user.roles.append(role)
        db.commit()
        return {"message": f"Роль {role.display_name} добавлена"}

@app.get("/api/user/tabs")
async def get_user_tabs(current_user: User = Depends(get_current_user)):
    """Получить список вкладок для отображения на фронтенде"""
    tabs = get_visible_tabs(current_user)
    return tabs

# ========== АДМИНИСТРАТИВНЫЕ ЭНДПОИНТЫ (ТОЛЬКО ДЛЯ ГОСУДАРСТВА) ==========
@app.get("/api/admin/users")
async def admin_list_users(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_government_user)
):
    users = db.query(User).options(joinedload(User.roles)).offset(skip).limit(limit).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "roles": [r.name for r in u.roles], "total_xp": u.total_xp, "level": u.level} for u in users]

@app.get("/api/admin/user/{user_id}")
async def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_government_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    admin_log = AdminLog(
        admin_user_id=admin_user.id,
        target_user_id=user.id,
        action="view_user_data",
        details={"viewed_fields": "all"}
    )
    db.add(admin_log)
    db.commit()
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": [{"id": r.id, "name": r.name, "display_name": r.display_name} for r in user.roles],
        "total_xp": user.total_xp,
        "level": user.level,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "actions": [{"action_type": a.action_type, "timestamp": a.timestamp, "module_name": a.module_name} for a in user.actions[:50]]
    }

@app.post("/api/admin/user/{user_id}/roles")
async def admin_set_user_roles(
    user_id: int,
    role_names: List[str],
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_government_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    roles = db.query(Role).filter(Role.name.in_(role_names)).all()
    user.roles = roles
    db.commit()
    
    admin_log = AdminLog(
        admin_user_id=admin_user.id,
        target_user_id=user.id,
        action="change_role",
        details={"new_roles": role_names}
    )
    db.add(admin_log)
    db.commit()
    
    return {"message": "Roles updated"}

# ========== API КЛЮЧИ ДЛЯ РАЗРАБОТЧИКОВ ==========
class ApiKeyCreateRequest(BaseModel):
    name: str
    permissions: List[str] = []
    rate_limit_per_minute: int = 60
    expires_at: Optional[datetime] = None

@app.post("/api/developer/api_keys")
async def create_api_key(
    key_data: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not any(role.name == 'developer' for role in current_user.roles):
        raise HTTPException(403, "Only developers can create API keys")
    
    key_value = secrets.token_urlsafe(32)
    api_key = ApiKey(
        user_id=current_user.id,
        key=key_value,
        name=key_data.name,
        permissions=key_data.permissions,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        expires_at=key_data.expires_at
    )
    db.add(api_key)
    db.commit()
    return {"key": key_value, "message": "API key created. Store it securely."}

@app.get("/api/developer/api_keys")
async def list_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return [{"id": k.id, "name": k.name, "last_used_at": k.last_used_at, "is_active": k.is_active} for k in keys]

import secrets

# ========== СЕССИИ И ТЕСТЫ (С ПРОВЕРКОЙ ДОСТУПА) ==========
@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(user_id: int, session_data: SessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        return await ai_service.create_session(db, user_id, session_data.exam_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_test")
async def submit_test(session_id: int, test_data: TestSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        result = await ai_service.submit_test(db, session_id, test_data.answers)
        # Начисляем XP за прохождение теста
        if result.get("overall_score", 0) > 0:
            await award_test_passed(db, current_user.id, f"session_{session_id}", result.get("overall_score", 0))
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/set_time")
async def set_time(session_id: int, time_data: TimeSet, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        plan = await ai_service.set_time_and_plan(db, session_id, time_data.days)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/next_lesson")
async def get_next_lesson(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        return await ai_service.get_next_lesson(db, session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/submit_lesson")
async def submit_lesson(session_id: int, lesson_data: LessonAnswer, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        result = await ai_service.submit_lesson(
            db, session_id, lesson_data.lesson_id, lesson_data.user_answers,
            lesson_data.time_spent_seconds, lesson_data.task_times
        )
        # Начисляем XP за завершение урока
        if result.get("status") == "success":
            await award_lesson_completion(db, current_user.id, f"lesson_{lesson_data.lesson_id}", result.get("score", 0))
        return result
    except Exception as e:
        print(f"Error in submit_lesson endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/progress_test")
async def create_progress_test(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
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
    if current_user.id != user_id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
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
async def get_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
    
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
async def get_study_plan(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    try:
        plan = await ai_service.get_study_plan(db, session_id)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
    history = db.query(ProgressHistory).filter(
        ProgressHistory.session_id == session_id
    ).order_by(ProgressHistory.timestamp).all()
    return history

# ========== СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ ==========
@app.get("/api/user/statistics")
async def get_user_statistics(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
    stats = await ai_service.get_user_statistics(db, user_id)
    return stats

@app.get("/api/user/performance")
async def get_user_performance(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
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
async def get_detailed_stats(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
    stats = await ai_service.get_user_statistics(db, user_id)
    return stats

@app.get("/api/user/interactions")
async def get_user_interactions(user_id: int, limit: int = 50, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and not is_government_user(current_user):
        raise HTTPException(403, "Доступ запрещён")
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
async def lesson_chat(lesson_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ к модулю 'Обучение' запрещён")
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
    subject: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ запрещён")
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
async def get_exam_stats(exam_type: str, current_user: User = Depends(get_current_user)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ запрещён")
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
async def test_search(query: str = "тригонометрия", k: int = 3, current_user: User = Depends(get_current_user)):
    if not check_module_access(current_user, 'learning'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        results = ai_service.exam_manager.search_problems('gaokao', query, k)
        return {"query": query, "count": len(results), "results": results[:k]}
    except Exception as e:
        return {"error": str(e)}

# ========== ВИДЕО ==========
@app.post("/api/lessons/{lesson_id}/generate_video")
async def generate_video_for_lesson(lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'video_generation'):
        raise HTTPException(403, "Доступ к модулю 'Генерация видео' запрещён")
    
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
async def transcribe_video(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'video'):
        raise HTTPException(403, "Доступ к модулю 'Видео → текст' запрещён")
    data = await request.json()
    url = data.get("url")
    target_language = data.get("language", "ru")
    if not url:
        raise HTTPException(400, "URL видео не указан")
    result = await ai_service.process_video(url, target_language)
    return result

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ ==========
@app.post("/api/custom_tests")
async def create_custom_test(test_data: CustomTestCreate, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
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
async def get_user_tests(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
    tests = db.query(CustomTest).filter(CustomTest.user_id == user_id).all()
    return tests

@app.get("/api/custom_tests/{test_id}")
async def get_custom_test(test_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
    test = db.query(CustomTest).filter(CustomTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден")
    return test

@app.delete("/api/custom_tests/{test_id}")
async def delete_custom_test(test_id: int, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
    test = db.query(CustomTest).filter(CustomTest.id == test_id, CustomTest.user_id == user_id).first()
    if not test:
        raise HTTPException(404, "Тест не найден или не принадлежит вам")
    db.delete(test)
    db.commit()
    return {"status": "ok", "message": "Тест удалён"}

@app.post("/api/custom_tests/{test_id}/train")
async def train_ai_on_custom_test(test_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
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
async def submit_custom_test(test_id: int, submission: CustomTestSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
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
async def generate_similar_questions(test_id: int, num_questions: int = 5, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'tests'):
        raise HTTPException(403, "Доступ к модулю 'Тесты' запрещён")
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
async def generate_course(course_data: UserCourseCreate, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Курсы' запрещён")
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
    
    # Начисляем XP за создание курса
    await award_course_created(db, user_id, course_data.name)
    
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
async def get_user_courses(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Курсы' запрещён")
    # Если запрашивает свои курсы
    if current_user.id == user_id:
        # Ученик: курсы, привязанные к его школам (через назначения)
        student_schools = [m.school_id for m in current_user.school_members]
        if student_schools:
            courses = db.query(UserCourse).filter(
                (UserCourse.user_id == user_id) | (UserCourse.school_id.in_(student_schools))
            ).all()
        else:
            courses = db.query(UserCourse).filter(UserCourse.user_id == user_id).all()
    else:
        # Если смотрит другой пользователь (например, учитель – нужно добавить проверку)
        if not is_government_user(current_user):
            raise HTTPException(403, "Доступ запрещён")
        courses = db.query(UserCourse).filter(UserCourse.user_id == user_id).all()
    return courses

@app.get("/api/courses/{course_id}")
async def get_course_details(course_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Курсы' запрещён")
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
async def delete_course(course_id: int, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Курсы' запрещён")
    course = db.query(UserCourse).filter(UserCourse.id == course_id, UserCourse.user_id == user_id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    db.delete(course)
    db.commit()
    return {"status": "ok"}

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ УРОКИ ==========
@app.post("/api/lessons/generate", response_model=UserLessonResponse)
async def generate_lesson(lesson_data: UserLessonCreate, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Уроки' запрещён")
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
    
    # Начисляем XP за создание урока
    await award_lesson_created(db, user_id, lesson_data.title)
    
    return new_lesson

@app.get("/api/lessons")
async def get_user_lessons(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Уроки' запрещён")
    lessons = db.query(UserLesson).filter(UserLesson.user_id == user_id).all()
    return lessons

@app.get("/api/lessons/{lesson_id}")
async def get_lesson_details(lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Уроки' запрещён")
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(lesson_id: int, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ к модулю 'Уроки' запрещён")
    lesson = db.query(UserLesson).filter(UserLesson.id == lesson_id, UserLesson.user_id == user_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден или не принадлежит вам")
    db.delete(lesson)
    db.commit()
    return {"status": "ok", "message": "Урок удалён"}

# ========== ПРЕЗЕНТАЦИИ ==========
@app.post("/api/lessons/{lesson_id}/generate_presentation")
async def generate_presentation(lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ запрещён")
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
async def create_school_endpoint(name: str, description: str = None, user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён. Только учителя могут создавать школы.")
    try:
        result = await ai_service.create_school(db, user_id, name, description)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/schools/join")
async def join_school_endpoint(invite_code: str, user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_student'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        result = await ai_service.join_school(db, user_id, invite_code)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/schools/my")
async def get_my_schools(user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
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
async def get_school_details(school_id: int, user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
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
async def get_school_stats_endpoint(school_id: int, teacher_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        result = await ai_service.get_school_stats(db, school_id, teacher_id)
        return result
    except ValueError as e:
        raise HTTPException(403, str(e))

@app.delete("/api/schools/{school_id}")
async def leave_school(school_id: int, user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_student'):
        raise HTTPException(403, "Доступ запрещён")
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
async def delete_school(school_id: int, user_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
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
    school_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        result = await ai_service.build_target_graph(db, user_id, school_id, exam_name)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/sync_performance")
async def sync_performance_to_school(user_id: int, school_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        await ai_service.sync_student_performance(db, user_id, school_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/users/{user_id}/coefficient")
async def get_coefficient_endpoint(user_id: int, school_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        result = await ai_service.get_coefficient(db, user_id, school_id)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/users/{user_id}/learning_graphs")
async def get_learning_graphs_endpoint(user_id: int, school_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'schools_teacher') and not check_module_access(current_user, 'rating_view'):
        raise HTTPException(403, "Доступ запрещён")
    try:
        result = await ai_service.get_learning_graphs(db, user_id, school_id)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

# ========== КУРСЫ И УРОКИ (дополнительные эндпоинты) ==========
@app.get("/api/course_lessons/{lesson_id}")
async def get_course_lesson(lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ запрещён")
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    return lesson

@app.post("/api/courses/{course_id}/generate_lesson_content/{lesson_id}")
async def generate_course_lesson_content(course_id: int, lesson_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ запрещён")
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
async def generate_all_lessons_content(course_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_module_access(current_user, 'courses_create'):
        raise HTTPException(403, "Доступ запрещён")
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

# Регистрация (обновлено с ролями)
@app.post("/api/auth/register")
async def register(username: str, password: str, name: str, email: str, role: str = "student", db: Session = Depends(get_db)):
    existing = db.query(UserAuth).filter(UserAuth.username == username).first()
    if existing:
        raise HTTPException(400, "Username already exists")
    
    # Создаём пользователя (без поля role, теперь через связи)
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Назначаем роли по умолчанию
    default_role_names = get_default_roles()
    default_roles = db.query(Role).filter(Role.name.in_(default_role_names)).all()
    user.roles = default_roles
    db.commit()
    
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "roles": [r.name for r in user.roles],
        "name": user.name,
        "avatar_url": user_auth.avatar_url
    }

# Логин (обновлено)
@app.post("/api/auth/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user_auth = db.query(UserAuth).filter(UserAuth.username == username).first()
    if not user_auth or not verify_password(password, user_auth.password_hash):
        raise HTTPException(401, "Неверное имя пользователя или пароль")
    
    user = user_auth.user
    user_auth.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token(data={"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "roles": [r.name for r in user.roles],
        "name": user.name,
        "avatar_url": user_auth.avatar_url
    }

# Получить профиль текущего пользователя (обновлено с XP и roles)
@app.get("/api/auth/profile")
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_auth = db.query(UserAuth).filter(UserAuth.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "roles": [r.name for r in current_user.roles],
        "total_xp": current_user.total_xp,
        "level": current_user.level,
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
@app.get("/api/chat/school/{school_id}/messages")
async def get_school_chat_messages(
    school_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    
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
        "user_role": m.user.roles[0].display_name if m.user.roles else "Пользователь",
        "avatar_url": db.query(UserAuth).filter(UserAuth.user_id == m.user_id).first().avatar_url if db.query(UserAuth).filter(UserAuth.user_id == m.user_id).first() else None,
        "message": m.message,
        "created_at": m.created_at.isoformat()
    } for m in reversed(messages)]

@app.post("/api/chat/school/{school_id}/send")
async def send_school_chat_message(
    school_id: int,
    message: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    
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

@app.get("/api/chat/private/{other_user_id}")
async def get_private_messages(
    other_user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    
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

@app.post("/api/chat/private/send")
async def send_private_message(
    recipient_id: int = Body(...),
    message: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'schools_student') and not check_module_access(current_user, 'schools_teacher'):
        raise HTTPException(403, "Доступ запрещён")
    
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(404, "Получатель не найден")
    
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

# ========== OCR ==========
@app.post("/api/ocr/recognize")
async def recognize_handwriting(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'ocr'):
        raise HTTPException(403, "Доступ к модулю OCR запрещён")
    if ocr_reader is None:
        raise HTTPException(503, "OCR сервис не инициализирован")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        img_array = np.array(image)
        
        result = ocr_reader.readtext(img_array, detail=1)
        
        if not result:
            return {"text": "", "confidence": 0}
        
        full_text = ' '.join([item[1] for item in result])
        avg_confidence = sum(item[2] for item in result) / len(result)
        
        corrected = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты эксперт по исправлению OCR-ошибок. Исправь распознанный текст, сохранив смысл."},
            {"role": "user", "content": f"Распознанный текст:\n{full_text}\n\nИсправь ошибки распознавания и верни только исправленный текст:"}
        ])
        full_text = corrected.strip()
        
        return {"text": full_text, "confidence": round(avg_confidence, 2)}
        
    except Exception as e:
        print(f"OCR ошибка: {e}")
        raise HTTPException(400, f"Ошибка распознавания: {str(e)}")

# ========== PDF ЧАТ ==========
@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'pdf_chat'):
        raise HTTPException(403, "Доступ к PDF чату запрещён")
    
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
    if not check_module_access(current_user, 'pdf_chat'):
        raise HTTPException(403, "Доступ к PDF чату запрещён")
    
    data = await request.json()
    doc_id = data.get("document_id")
    question = data.get("question")
    if not doc_id or not question:
        raise HTTPException(400, "Не указан document_id или question")
    
    doc = db.query(UserDocument).filter(UserDocument.id == doc_id, UserDocument.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Документ не найден")
    
    paths = json.loads(doc.index_path)
    with open(paths["chunks"], "r", encoding="utf-8") as f:
        all_chunks = json.load(f)
    first_chunk = all_chunks[0] if all_chunks else ""
    
    relevant_chunks = search_tfidf_index(paths["vectorizer"], paths["matrix"], paths["chunks"], question, k=8)
    
    context_parts = []
    if first_chunk and first_chunk not in relevant_chunks:
        context_parts.append(first_chunk)
    context_parts.extend(relevant_chunks)
    context = "\n\n---\n\n".join(context_parts[:8])
    
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

# ========== ГЕНЕРАЦИЯ ЭКЗАМЕНАЦИОННЫХ БИЛЕТОВ ==========
@app.post("/api/generate-exam-tickets")
async def generate_exam_tickets(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'exam_tickets'):
        raise HTTPException(403, "Доступ к модулю 'Билеты' запрещён")
    
    data = await request.json()
    course_name = data.get("course_name")
    num_questions = data.get("num_questions", 5)
    ticket_type = data.get("ticket_type", "tickets")
    
    if not course_name:
        raise HTTPException(400, "course_name required")
    if num_questions < 1 or num_questions > 20:
        raise HTTPException(400, "num_questions must be between 1 and 20")
    
    if ticket_type == "tickets":
        prompt = f"""Generate {num_questions} exam questions for a university-level course titled "{course_name}". 
Each question should be a clear, standalone problem that tests understanding of key concepts.
Return ONLY a JSON array of strings, like: ["Question 1...", "Question 2...", ...].
Do not include answers or explanations."""
    else:
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
        
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        questions = json.loads(response)
        if not isinstance(questions, list):
            raise ValueError("Response is not a list")
        
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

# ========== ПРОВЕРКА ЭССЕ ==========
class EssayCheckRequest(BaseModel):
    text: str
    title: Optional[str] = None
    criteria: Optional[str] = None

@app.post("/api/check-essay")
async def check_essay(
    request: EssayCheckRequest,
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'essay_check'):
        raise HTTPException(403, "Доступ к модулю 'Проверка работ' запрещён")
    
    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Текст не может быть пустым")
    
    title = request.title or "Работа"
    criteria = request.criteria or "стандартные академические критерии"
    
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

# ========== ПЛАНИРОВЩИК ЗАДАЧ ==========
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: str

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
    if not check_module_access(current_user, 'planner'):
        raise HTTPException(403, "Доступ к модулю 'Планировщик' запрещён")
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
    if not check_module_access(current_user, 'planner'):
        raise HTTPException(403, "Доступ к модулю 'Планировщик' запрещён")
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
    if not check_module_access(current_user, 'planner'):
        raise HTTPException(403, "Доступ к модулю 'Планировщик' запрещён")
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
    if not check_module_access(current_user, 'planner'):
        raise HTTPException(403, "Доступ к модулю 'Планировщик' запрещён")
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    db.delete(task)
    db.commit()
    return {"message": "Задача удалена"}

# ========== ПЛАНИРОВЩИК НАПОМИНАНИЙ ==========
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

def send_reminder_email(email: str, task_title: str, deadline: datetime):
    print(f"[REMINDER] Напоминание для {email}: задача '{task_title}' истекает {deadline.strftime('%Y-%m-%d %H:%M')}")
    try:
        msg = MIMEText(f"Уважаемый пользователь, задача '{task_title}' должна быть выполнена до {deadline.strftime('%Y-%m-%d %H:%M')}.")
        msg['Subject'] = f'Напоминание: {task_title}'
        msg['From'] = 'noreply@ai-teacher.com'
        msg['To'] = email
        # Раскомментировать при наличии SMTP
        # with smtplib.SMTP('smtp.gmail.com', 587) as server:
        #     server.starttls()
        #     server.login('your_email@gmail.com', 'your_password')
        #     server.send_message(msg)
    except Exception as e:
        print(f"SMTP error: {e}")

def check_deadlines():
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

scheduler = BackgroundScheduler()
scheduler.add_job(func=check_deadlines, trigger="interval", minutes=30)
scheduler.start()

# ========== КОНСТРУКТОР СИЛЛАБУСОВ ==========
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
    if not check_module_access(current_user, 'syllabus'):
        raise HTTPException(403, "Доступ к модулю 'Конструктор курсов' запрещён")
    
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
        
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        data = json.loads(response)
        
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
    if not check_module_access(current_user, 'syllabus'):
        raise HTTPException(403, "Доступ к модулю 'Конструктор курсов' запрещён")
    courses = db.query(SyllabusCourse).filter(SyllabusCourse.user_id == current_user.id).order_by(SyllabusCourse.created_at.desc()).all()
    return courses

@app.get("/api/syllabus/courses/{course_id}")
async def get_syllabus_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'syllabus'):
        raise HTTPException(403, "Доступ к модулю 'Конструктор курсов' запрещён")
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
    if not check_module_access(current_user, 'syllabus'):
        raise HTTPException(403, "Доступ к модулю 'Конструктор курсов' запрещён")
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
    if not check_module_access(current_user, 'syllabus'):
        raise HTTPException(403, "Доступ к модулю 'Конструктор курсов' запрещён")
    course = db.query(SyllabusCourse).filter(SyllabusCourse.id == course_id, SyllabusCourse.user_id == current_user.id).first()
    if not course:
        raise HTTPException(404, "Курс не найден")
    db.delete(course)
    db.commit()
    return {"message": "Курс удалён"}

# ========== НАУЧНЫЕ СТАТЬИ ==========
import httpx
import feedparser

@app.get("/api/scientific/search")
async def search_arxiv(
    query: str,
    max_results: int = 10,
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'scientific'):
        raise HTTPException(403, "Доступ к модулю 'Научные статьи' запрещён")
    if not query:
        raise HTTPException(400, "Query is required")
    
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
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

@app.get("/api/scientific/bibtex")
async def get_bibtex(
    arxiv_id: str,
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'scientific'):
        raise HTTPException(403, "Доступ к модулю 'Научные статьи' запрещён")
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
    if not check_module_access(current_user, 'scientific'):
        raise HTTPException(403, "Доступ к модулю 'Научные статьи' запрещён")
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

@app.post("/api/scientific/favorite")
async def save_article(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'scientific'):
        raise HTTPException(403, "Доступ к модулю 'Научные статьи' запрещён")
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

@app.get("/api/scientific/favorites")
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'scientific'):
        raise HTTPException(403, "Доступ к модулю 'Научные статьи' запрещён")
    articles = db.query(ScientificArticle).filter(
        ScientificArticle.user_id == current_user.id,
        ScientificArticle.is_favorite == True
    ).order_by(ScientificArticle.created_at.desc()).all()
    return articles

# ========== АНАЛИЗ ДАННЫХ ==========
def safe_execute_code(code: str, local_vars: dict) -> tuple:
    allowed_modules = {
        'pandas': pd,
        'np': np,
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

    local_vars.update({
        '__name__': '__main__',
        '_output': '',
        '_images': [],
    })

    try:
        byte_code = compile_restricted(code, '<string>', 'exec')
    except SyntaxError as e:
        return "", [], f"Синтаксическая ошибка: {str(e)}"

    class PrintCollector:
        def write(self, text):
            local_vars['_output'] += str(text)
    import sys
    original_stdout = sys.stdout
    sys.stdout = PrintCollector()

    try:
        exec(byte_code, safe_globals_dict, local_vars)
        if 'result' in local_vars:
            local_vars['_output'] += str(local_vars['result'])
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
    if not check_module_access(current_user, 'data_analysis'):
        raise HTTPException(403, "Доступ к модулю 'Анализ данных' запрещён")
    
    import pandas as pd
    import io
    import uuid

    content = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(content))
    elif file.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(400, "Only CSV and Excel files are supported")
    
    df_json = df.to_json(orient='records', date_format='iso')
    
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
    if not check_module_access(current_user, 'data_analysis'):
        raise HTTPException(403, "Доступ к модулю 'Анализ данных' запрещён")
    
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
    
    analysis_session.code = code
    db.commit()
    
    if analysis_session.dataframe_json:
        df = pd.read_json(analysis_session.dataframe_json, orient='records')
    else:
        df = pd.DataFrame()
    
    safe_builtins = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
        'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'print': print, 'range': range,
        'round': round, 'str': str, 'sum': sum, 'tuple': tuple, 'zip': zip,
        'type': type, 'isinstance': isinstance, 'issubclass': issubclass,
        'True': True, 'False': False, 'None': None
    }
    
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
    if not check_module_access(current_user, 'data_analysis'):
        raise HTTPException(403, "Доступ к модулю 'Анализ данных' запрещён")
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
    if not check_module_access(current_user, 'data_analysis'):
        raise HTTPException(403, "Доступ к модулю 'Анализ данных' запрещён")
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

# ========== AI-РЕЦЕНЗЕНТ С ПРОВЕРКОЙ НА ПЛАГИАТ ==========
@app.post("/api/review-text")
async def review_text(
    req: TextReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'essay_check'):
        raise HTTPException(403, "Доступ к модулю 'Проверка работ' запрещён")
    
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Текст не может быть пустым")
    title = req.title or "Без названия"
    
    plagiarism_percent, similar_parts = check_plagiarism(db, current_user.id, title, text)
    
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
}}"""
    
    try:
        ai_response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты научный рецензент. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=1500, temperature=0.4)
        
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
        feedback = {
            "score": 50, "grade": "удовлетворительно",
            "strengths": ["Текст содержит интересные идеи"],
            "weaknesses": ["Не хватает структуры", "Стиль не научный"],
            "recommendations": ["Улучшить аргументацию", "Переписать введение"],
            "detailed_feedback": "Автоматическая проверка не удалась. Рекомендуется доработать текст."
        }
    
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
    if not check_module_access(current_user, 'essay_check'):
        raise HTTPException(403, "Доступ к модулю 'Проверка работ' запрещён")
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

@app.post("/api/hypothesis/generate")
async def generate_hypotheses(
    domain: Optional[str] = None,
    num_hypotheses: int = 3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерирует персонализированные исследовательские гипотезы на основе профиля пользователя"""
    if not check_module_access(current_user, 'hypothesis_generator'):
        raise HTTPException(403, "Доступ к модулю 'Генератор гипотез' запрещён")
    
    if num_hypotheses < 1 or num_hypotheses > 10:
        raise HTTPException(400, "num_hypotheses должно быть от 1 до 10")
    
    generator = HypothesisGenerator(db, current_user)
    hypotheses_data = await generator.generate_hypotheses(domain, num_hypotheses)
    saved_hypotheses = await generator.save_hypotheses(hypotheses_data)
    
    return {
        "hypotheses": [
            {
                "id": h.id,
                "text": h.text,
                "domain": h.domain,
                "confidence_score": h.confidence_score,
                "relevance_score": h.relevance_score,
                "created_at": h.created_at.isoformat()
            }
            for h in saved_hypotheses
        ]
    }

@app.get("/api/hypothesis/list")
async def list_hypotheses(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает список ранее сгенерированных гипотез текущего пользователя"""
    if not check_module_access(current_user, 'hypothesis_generator'):
        raise HTTPException(403, "Доступ запрещён")
    
    hypotheses = db.query(Hypothesis).filter(
        Hypothesis.user_id == current_user.id
    ).order_by(Hypothesis.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": h.id,
            "text": h.text,
            "domain": h.domain,
            "confidence_score": h.confidence_score,
            "relevance_score": h.relevance_score,
            "user_rating": h.user_rating,
            "is_accepted": h.is_accepted,
            "created_at": h.created_at.isoformat()
        }
        for h in hypotheses
    ]

@app.post("/api/hypothesis/{hypothesis_id}/rate")
async def rate_hypothesis(
    hypothesis_id: int,
    rating: int = Body(..., embed=True),  # 1-5
    accept: bool = Body(False, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Оценивает полезность гипотезы (для улучшения рекомендаций)"""
    if not check_module_access(current_user, 'hypothesis_generator'):
        raise HTTPException(403, "Доступ запрещён")
    if rating < 1 or rating > 5:
        raise HTTPException(400, "Оценка должна быть от 1 до 5")
    
    hypothesis = db.query(Hypothesis).filter(
        Hypothesis.id == hypothesis_id,
        Hypothesis.user_id == current_user.id
    ).first()
    if not hypothesis:
        raise HTTPException(404, "Гипотеза не найдена")
    
    hypothesis.user_rating = rating
    hypothesis.is_accepted = accept
    db.commit()
    
    return {"message": "Оценка сохранена"}

@app.post("/api/hypothesis/{hypothesis_id}/accept")
async def accept_hypothesis(
    hypothesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Принимает гипотезу в работу (можно использовать для старта исследования)"""
    if not check_module_access(current_user, 'hypothesis_generator'):
        raise HTTPException(403, "Доступ запрещён")
    
    hypothesis = db.query(Hypothesis).filter(
        Hypothesis.id == hypothesis_id,
        Hypothesis.user_id == current_user.id
    ).first()
    if not hypothesis:
        raise HTTPException(404, "Гипотеза не найдена")
    
    hypothesis.is_accepted = True
    db.commit()
    
    # Можно начислить XP за принятие гипотезы
    from .xp_service import award_hypothesis_generated
    await award_hypothesis_generated(db, current_user.id, hypothesis.domain or "research")
    
    return {"message": "Гипотеза принята в работу"}

@app.post("/api/supervisor/match")
async def match_supervisors(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Находит топ научных руководителей, наиболее подходящих пользователю"""
    if not check_module_access(current_user, 'supervisor_search'):
        raise HTTPException(403, "Доступ к модулю 'Поиск научного руководителя' запрещён")
    
    matcher = SupervisorMatcher(db, current_user)
    results = await matcher.match_top_supervisors(limit)
    return {"supervisors": results}

@app.post("/api/supervisor/{supervisor_id}/save")
async def save_supervisor(
    supervisor_id: int,
    request_message: str = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохраняет руководителя в избранное или отправляет запрос на руководство"""
    if not check_module_access(current_user, 'supervisor_search'):
        raise HTTPException(403, "Доступ запрещён")
    
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if not supervisor:
        raise HTTPException(404, "Руководитель не найден")
    
    matcher = SupervisorMatcher(db, current_user)
    score = await matcher.compute_single_match(supervisor)  # пересчёт для точности
    status = "favorited" if not request_message else "pending"
    us = await matcher.save_match(supervisor_id, score, status)
    
    if request_message:
        us.request_message = request_message
        db.commit()
    
    return {"message": "Руководитель сохранён", "matching_score": score}

@app.get("/api/supervisor/favorites")
async def get_favorite_supervisors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает список избранных руководителей пользователя"""
    if not check_module_access(current_user, 'supervisor_search'):
        raise HTTPException(403, "Доступ запрещён")
    
    favorites = db.query(UserSupervisor).filter(
        UserSupervisor.user_id == current_user.id,
        UserSupervisor.status.in_(['favorited', 'pending', 'accepted'])
    ).order_by(UserSupervisor.matching_score.desc()).all()
    
    result = []
    for fav in favorites:
        sup = fav.supervisor
        result.append({
            "supervisor_id": sup.id,
            "name": sup.name,
            "position": sup.position,
            "department": sup.department,
            "university": sup.university,
            "research_areas": sup.research_areas,
            "avatar_url": sup.avatar_url,
            "status": fav.status,
            "matching_score": fav.matching_score,
            "request_message": fav.request_message,
            "created_at": fav.created_at.isoformat()
        })
    return result

@app.post("/api/supervisor/{supervisor_id}/request")
async def request_supervision(
    supervisor_id: int,
    message: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправляет запрос на научное руководство"""
    if not check_module_access(current_user, 'supervisor_search'):
        raise HTTPException(403, "Доступ запрещён")
    
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if not supervisor:
        raise HTTPException(404, "Руководитель не найден")
    
    matcher = SupervisorMatcher(db, current_user)
    score = await matcher.compute_single_match(supervisor)
    us = await matcher.save_match(supervisor_id, score, "pending")
    us.request_message = message
    db.commit()
    
    # Здесь можно отправить уведомление руководителю (email/telegram)
    return {"message": "Запрос отправлен", "matching_score": score}

# --- Для компаний и работодателей ---
@app.post("/api/company")
async def create_company(
    name: str, description: str = None, industry: str = None,
    website: str = None, logo_url: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание компании (доступно работодателю)"""
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    # Проверяем, есть ли роль employer
    if not any(role.name == 'employer' for role in current_user.roles):
        raise HTTPException(403, "Только работодатели могут создавать компании")
    company = Company(
        user_id=current_user.id,
        name=name, description=description, industry=industry,
        website=website, logo_url=logo_url
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@app.post("/api/company/{company_id}/vacancy")
async def create_vacancy(
    company_id: int,
    title: str, description: str, requirements: str = None,
    skills: List[str] = [], experience_years: float = 0.0,
    salary_min: int = None, salary_max: int = None,
    location: str = None, employment_type: str = "full",
    expires_at: datetime = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Компания не найдена")
    if company.user_id != current_user.id:
        raise HTTPException(403, "Вы не владелец компании")
    vacancy = Vacancy(
        company_id=company_id,
        title=title, description=description, requirements=requirements,
        skills=skills, experience_years=experience_years,
        salary_min=salary_min, salary_max=salary_max,
        location=location, employment_type=employment_type,
        expires_at=expires_at
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return vacancy

@app.get("/api/vacancies/my")
async def get_my_vacancies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Список вакансий компаний, созданных текущим работодателем"""
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    companies = db.query(Company).filter(Company.user_id == current_user.id).all()
    vacancies = []
    for c in companies:
        for v in c.vacancies:
            vacancies.append({
                "id": v.id, "company_name": c.name, "title": v.title,
                "location": v.location, "is_active": v.is_active,
                "posted_at": v.posted_at, "applications_count": len(v.user_vacancies)
            })
    return vacancies

# --- Для студентов (поиск вакансий) ---
@app.post("/api/vacancies/match")
async def match_vacancies_for_student(
    limit: int = 20, min_score: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ к модулю 'Стажировки' запрещён")
    # Проверяем, что пользователь имеет роль соискателя (student, job_seeker, master, phd)
    allowed_roles = ['student', 'job_seeker', 'master', 'phd']
    if not any(role.name in allowed_roles for role in current_user.roles):
        raise HTTPException(403, "Доступ только для соискателей")
    matcher = VacancyMatcher(db, current_user)
    results = await matcher.match_vacancies_for_student(limit, min_score)
    return {"vacancies": results}

@app.post("/api/vacancies/{vacancy_id}/apply")
async def apply_to_vacancy(
    vacancy_id: int,
    cover_letter: str = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    matcher = VacancyMatcher(db, current_user)
    try:
        result = await matcher.apply_to_vacancy(vacancy_id, cover_letter)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/user/applications")
async def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Список откликов текущего студента"""
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    apps = db.query(UserVacancy).filter(UserVacancy.user_id == current_user.id).all()
    return [
        {
            "vacancy_id": a.vacancy_id,
            "company_name": a.vacancy.company.name,
            "title": a.vacancy.title,
            "status": a.status,
            "matching_score": a.matching_score,
            "applied_at": a.applied_at
        }
        for a in apps
    ]

# --- Для работодателя: поиск кандидатов по вакансии ---
@app.post("/api/vacancies/{vacancy_id}/candidates")
async def find_candidates_for_vacancy(
    vacancy_id: int,
    limit: int = 20, min_score: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not check_module_access(current_user, 'internship_match'):
        raise HTTPException(403, "Доступ запрещён")
    # Проверяем, что пользователь владеет компанией этой вакансии
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(404, "Вакансия не найдена")
    if vacancy.company.user_id != current_user.id:
        raise HTTPException(403, "Вы не владелец этой вакансии")
    matcher = VacancyMatcher(db, current_user)  # current_user – работодатель, но для поиска студентов он не используется напрямую
    # Создаём временного студента? В матчере есть отдельный метод для поиска студентов по вакансии
    results = await matcher.match_students_for_vacancy(vacancy_id, limit, min_score)
    return {"candidates": results}

# ========== КОРПОРАТИВНОЕ ОБУЧЕНИЕ (ПРИВЯЗКА КУРСОВ К ШКОЛЕ) ==========

@app.post("/api/schools/{school_id}/courses")
async def create_school_course(
    school_id: int,
    course_data: UserCourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать курс для школы (доступно владельцу школы или school_teacher/professor)"""
    # проверка прав
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(404, "Школа не найдена")
    if school.owner_id != current_user.id and not any(role.name in ['school_teacher', 'professor'] for role in current_user.roles):
        raise HTTPException(403, "Доступ запрещён")
    new_course = UserCourse(
        user_id=current_user.id,
        name=course_data.name,
        description=course_data.description,
        success_criteria=course_data.success_criteria,
        school_id=school_id,
        status="published"
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@app.get("/api/schools/{school_id}/courses")
async def get_school_courses(
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все курсы школы (доступ участникам школы)"""
    member = db.query(SchoolMember).filter(SchoolMember.school_id == school_id, SchoolMember.user_id == current_user.id).first()
    if not member:
        raise HTTPException(403, "Вы не участник этой школы")
    courses = db.query(UserCourse).filter(UserCourse.school_id == school_id).all()
    return courses

@app.post("/api/courses/{course_id}/assign")
async def assign_course_to_students(
    course_id: int,
    student_ids: List[int] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Назначить курс ученикам (только учитель школы)"""
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course or not course.school:
        raise HTTPException(404, "Курс не привязан к школе")
    school = course.school
    if school.owner_id != current_user.id and not any(role.name in ['school_teacher', 'professor'] for role in current_user.roles):
        raise HTTPException(403, "Только учитель может назначать курсы")
    assigned = 0
    for uid in student_ids:
        existing = db.query(CourseAssignment).filter(CourseAssignment.course_id == course_id, CourseAssignment.user_id == uid).first()
        if not existing:
            assign = CourseAssignment(course_id=course_id, user_id=uid, assigned_by=current_user.id, status="pending")
            db.add(assign)
            assigned += 1
    db.commit()
    return {"message": f"Курс назначен {assigned} ученикам"}

@app.get("/api/courses/{course_id}/progress")
async def get_course_progress(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Просмотр прогресса учеников по курсу (только для учителя)"""
    course = db.query(UserCourse).filter(UserCourse.id == course_id).first()
    if not course or not course.school or (course.school.owner_id != current_user.id and not any(role.name in ['school_teacher', 'professor'] for role in current_user.roles)):
        raise HTTPException(403, "Доступ запрещён")
    assignments = db.query(CourseAssignment).filter(CourseAssignment.course_id == course_id).all()
    result = []
    total_lessons = db.query(CourseLesson).join(CourseModule).filter(CourseModule.course_id == course_id).count()
    for ass in assignments:
        completed_lessons = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == ass.user_id,
            UserLessonProgress.lesson_id.in_(
                db.query(CourseLesson.id).join(CourseModule).filter(CourseModule.course_id == course_id)
            ),
            UserLessonProgress.completed == True
        ).count()
        progress = (completed_lessons / total_lessons * 100) if total_lessons else 0
        result.append({
            "user_id": ass.user_id,
            "name": ass.user.name,
            "status": ass.status,
            "progress": round(progress, 1),
            "completed_at": ass.completed_at,
            "certificate_url": ass.certificate_url
        })
    return result

@app.post("/api/courses/{course_id}/certificate/{user_id}")
async def generate_certificate(
    course_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сгенерировать PDF-сертификат для ученика (учитель или сам ученик)"""
    assignment = db.query(CourseAssignment).filter(
        CourseAssignment.course_id == course_id,
        CourseAssignment.user_id == user_id,
        CourseAssignment.status == "completed"
    ).first()
    if not assignment:
        raise HTTPException(404, "Завершённое назначение не найдено")
    course = assignment.course
    school = course.school
    is_teacher = school and (school.owner_id == current_user.id or any(role.name in ['school_teacher', 'professor'] for role in current_user.roles))
    if not (is_teacher or current_user.id == user_id):
        raise HTTPException(403, "Доступ запрещён")
    if assignment.certificate_url:
        return {"certificate_url": assignment.certificate_url}
    # Генерация PDF (требуется библиотека reportlab)
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from pathlib import Path
    cert_dir = Path("static/certificates")
    cert_dir.mkdir(parents=True, exist_ok=True)
    filename = f"cert_{course_id}_{user_id}.pdf"
    filepath = cert_dir / filename
    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height-100, "СЕРТИФИКАТ")
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height-150, "Настоящим подтверждается, что")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height-200, assignment.user.name)
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height-250, f"успешно завершил(а) курс")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height-300, course.name)
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height-350, f"Дата: {datetime.now().strftime('%d.%m.%Y')}")
    if school:
        c.drawCentredString(width/2, height-400, school.name)
    c.save()
    assignment.certificate_url = f"/static/certificates/{filename}"
    db.commit()
    return {"certificate_url": assignment.certificate_url}

@app.get("/api/schools/{school_id}/export")
async def export_school_stats(
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Экспорт статистики школы в Excel (только учитель)"""
    school = db.query(School).filter(School.id == school_id, School.owner_id == current_user.id).first()
    if not school:
        raise HTTPException(403, "Доступ запрещён")
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    data = []
    members = db.query(SchoolMember).filter(SchoolMember.school_id == school_id, SchoolMember.role == 'student').all()
    for member in members:
        user = member.user
        row = {"Имя": user.name, "Email": user.email}
        for course in school.courses:
            assignment = db.query(CourseAssignment).filter(CourseAssignment.course_id == course.id, CourseAssignment.user_id == user.id).first()
            row[f"Курс: {course.name}"] = assignment.status if assignment else "Не назначен"
        data.append(row)
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Статистика школы', index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename=school_{school_id}_stats.xlsx"})

@app.get("/api/user/assigned-courses")
async def get_my_assigned_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    assignments = db.query(CourseAssignment).filter(CourseAssignment.user_id == current_user.id).all()
    return [
        {
            "assignment_id": a.id,
            "course_id": a.course_id,
            "name": a.course.name,
            "description": a.course.description,
            "status": a.status,
            "assigned_at": a.assigned_at,
            "certificate_url": a.certificate_url
        }
        for a in assignments
    ]

@app.post("/api/courses/{course_id}/complete")
async def complete_course_assignment(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    assignment = db.query(CourseAssignment).filter(CourseAssignment.course_id == course_id, CourseAssignment.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(404, "Курс не назначен")
    if assignment.status == "completed":
        return {"message": "Курс уже завершён"}
    # Проверка, что все уроки курса пройдены
    total_lessons = db.query(CourseLesson).join(CourseModule).filter(CourseModule.course_id == course_id).count()
    completed_lessons = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == current_user.id,
        UserLessonProgress.lesson_id.in_(
            db.query(CourseLesson.id).join(CourseModule).filter(CourseModule.course_id == course_id)
        ),
        UserLessonProgress.completed == True
    ).count()
    if completed_lessons < total_lessons:
        raise HTTPException(400, "Не все уроки курса пройдены")
    assignment.status = "completed"
    assignment.completed_at = datetime.utcnow()
    db.commit()
    return {"message": "Курс отмечен как завершённый"}

@app.post("/api/course-lessons/{lesson_id}/complete")
async def complete_course_lesson(
    lesson_id: int,
    score: float = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Урок не найден")
    # Проверяем, что курс назначен пользователю
    course_id = lesson.module.course_id
    assignment = db.query(CourseAssignment).filter(CourseAssignment.course_id == course_id, CourseAssignment.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(403, "Курс не назначен")
    progress = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == current_user.id,
        UserLessonProgress.lesson_id == lesson_id
    ).first()
    if not progress:
        progress = UserLessonProgress(user_id=current_user.id, lesson_id=lesson_id)
        db.add(progress)
    progress.completed = True
    progress.completed_at = datetime.utcnow()
    if score is not None:
        progress.score = score
    db.commit()
    return {"message": "Урок отмечен пройденным"}

# ========== IELTS МОДУЛЬ ==========
import whisper
import tempfile
import json

whisper_model = None

from app.tasks.audio_tasks import transcribe_and_analyze

@app.post("/ielts/speaking/analyze")
async def analyze_ielts_speaking(
    file: UploadFile = File(...),
    task_type: str = "part1",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_module_access(current_user, 'ielts'):
        raise HTTPException(403, "Доступ к модулю IELTS запрещён")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "webm"
    safe_filename = f"{uuid.uuid4()}.{ext}"
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, safe_filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
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
    if not check_module_access(current_user, 'ielts'):
        raise HTTPException(403, "Доступ к модулю IELTS запрещён")
    
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
    if not check_module_access(current_user, 'ielts'):
        raise HTTPException(403, "Доступ к модулю IELTS запрещён")
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
    if not check_module_access(current_user, 'ielts'):
        raise HTTPException(403, "Доступ к модулю IELTS запрещён")
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