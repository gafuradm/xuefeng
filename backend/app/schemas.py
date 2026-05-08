# backend/app/schemas.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Dict, Any, Optional, List

class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionCreate(BaseModel):
    exam_name: str

class SessionResponse(BaseModel):
    id: int
    user_id: int
    exam_name: str
    exam_details: Dict[str, Any]
    target_profile: Dict[str, Any]
    current_profile: Dict[str, Any]
    time_available_days: Optional[int] = None
    study_plan: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestSubmit(BaseModel):
    answers: Dict[str, str]

class TimeSet(BaseModel):
    days: int

# ========== ОБНОВЛЕННАЯ СХЕМА ДЛЯ ОТПРАВКИ УРОКА (с временем) ==========
class LessonAnswer(BaseModel):
    lesson_id: int
    user_answers: Dict[str, str]
    time_spent_seconds: Optional[float] = 0.0
    task_times: Optional[Dict[str, float]] = {}
    
# ========== НОВЫЕ СХЕМЫ ДЛЯ ДЕТАЛЬНОЙ СТАТИСТИКИ ПОЛЬЗОВАТЕЛЯ ==========
class TopicTimeStatsResponse(BaseModel):
    topic: str
    total_seconds: int
    sessions_count: int
    last_updated: datetime

class UserDetailedStatsResponse(BaseModel):
    topic: str
    mastery_level: float
    correct_count: int
    total_count: int
    total_time_spent_minutes: float
    last_attempt: datetime

class StudentProgressResponse(BaseModel):
    user_id: int
    name: str
    average_mastery: float
    total_time_spent_hours: float
    topics_progress: Dict[str, float]   # topic -> mastery
    weak_topics: List[str]

class SchoolStatsResponse(BaseModel):
    school_name: str
    total_students: int
    students: List[StudentProgressResponse]

# ========== СХЕМЫ ДЛЯ ПОЛЬЗОВАТЕЛЬСКИХ ТЕСТОВ ==========
class QuestionItem(BaseModel):
    text: str
    correct_answer: str
    explanation: Optional[str] = None

class CustomTestCreate(BaseModel):
    name: str
    description: Optional[str] = None
    questions: List[QuestionItem]

class CustomTestResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    questions: List[QuestionItem]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CustomTestSubmit(BaseModel):
    test_id: int
    answers: Dict[str, str]

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КУРСЫ ==========
class CourseModuleCreate(BaseModel):
    title: str
    order: int
    description: Optional[str] = None

class CourseLessonCreate(BaseModel):
    title: str
    order: int
    content: Optional[Dict] = None
    homework: Optional[List] = None
    success_criteria: Optional[str] = None
    youtube_urls: Optional[List[str]] = None
    presentation_url: Optional[str] = None

class UserCourseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    success_criteria: Optional[str] = None

class UserCourseResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    success_criteria: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    modules: List[Any] = []

    model_config = ConfigDict(from_attributes=True)

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ УРОКИ ==========
class UserLessonCreate(BaseModel):
    title: str
    subject: str
    description: Optional[str] = None

class UserLessonResponse(BaseModel):
    id: int
    user_id: int
    title: str
    subject: str
    description: Optional[str]
    content: Dict
    success_criteria: Optional[str]
    youtube_urls: List[str]
    presentation_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)