import time
from fastapi import Request
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import UserAction
from .auth import decode_token

async def log_all_actions_middleware(request: Request, call_next):
    """Middleware для логирования всех HTTP запросов авторизованных пользователей"""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Извлекаем user_id из токена, если он есть
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                user_id = int(user_id)
        except Exception:
            pass
    
    if user_id:
        db = SessionLocal()
        try:
            # Получаем название модуля из заголовка X-Module (можно установить на фронтенде)
            module_name = request.headers.get("X-Module")
            if not module_name:
                # Пытаемся определить по пути
                path = request.url.path
                if "/api/sessions" in path:
                    module_name = "learning"
                elif "/api/custom_tests" in path:
                    module_name = "tests"
                elif "/api/courses" in path or "/api/lessons" in path:
                    module_name = "courses_create"
                elif "/api/schools" in path:
                    module_name = "schools"
                elif "/api/chat" in path:
                    module_name = "schools"
                elif "/api/video/transcribe" in path:
                    module_name = "video"
                elif "/api/ask-pdf" in path or "/api/upload-pdf" in path:
                    module_name = "pdf_chat"
                elif "/api/generate-exam-tickets" in path:
                    module_name = "exam_tickets"
                elif "/api/check-essay" in path or "/api/review-text" in path:
                    module_name = "essay_check"
                elif "/api/tasks" in path:
                    module_name = "planner"
                elif "/api/scientific" in path:
                    module_name = "scientific"
                elif "/api/syllabus" in path:
                    module_name = "syllabus"
                elif "/api/data" in path:
                    module_name = "data_analysis"
                elif "/api/ielts" in path:
                    module_name = "ielts"
                elif "/api/ocr" in path:
                    module_name = "ocr"
                elif "/api/soft_skills" in path:
                    module_name = "soft_skills"
                elif "/api/coding" in path:
                    module_name = "coding_interviews"
                elif "/api/supervisor" in path:
                    module_name = "supervisor_search"
                elif "/api/internship" in path:
                    module_name = "internship_match"
                elif "/api/hypothesis" in path:
                    module_name = "hypothesis_generator"
                elif "/api/rating" in path:
                    module_name = "rating_view"
                elif "/api/corporate" in path:
                    module_name = "corporate_training"
                elif "/api/developer" in path:
                    module_name = "api_access"
                else:
                    module_name = "other"
            
            # Сохраняем действие
            action = UserAction(
                user_id=user_id,
                action_type=request.method,
                action_data={
                    "url": str(request.url),
                    "headers": dict(request.headers.items()),
                    "query_params": dict(request.query_params),
                    "client_host": request.client.host if request.client else None
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                url=str(request.url),
                method=request.method,
                duration_ms=duration_ms,
                module_name=module_name
            )
            db.add(action)
            db.commit()
        except Exception as e:
            print(f"[Middleware] Failed to log action: {e}")
        finally:
            db.close()
    
    return response