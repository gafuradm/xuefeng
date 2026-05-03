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

class LessonAnswer(BaseModel):
    lesson_id: int
    user_answers: Dict[str, str]

# ========== НОВЫЕ СХЕМЫ ДЛЯ ПОЛЬЗОВАТЕЛЬСКИХ ТЕСТОВ ==========
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