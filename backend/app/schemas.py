from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Dict, Any, Optional

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

# Убираем session_id из тела запроса, так как он передаётся через URL
class TestSubmit(BaseModel):
    answers: Dict[str, str]

class TimeSet(BaseModel):
    days: int

class LessonAnswer(BaseModel):
    lesson_id: int
    user_answers: Dict[str, str]