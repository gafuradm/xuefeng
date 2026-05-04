# backend/app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_courses = relationship('UserCourse', back_populates='user', cascade='all, delete-orphan')
    user_lessons = relationship('UserLesson', back_populates='user', cascade='all, delete-orphan')
    sessions = relationship('Session', back_populates='user', cascade="all, delete-orphan")
    custom_tests = relationship('CustomTest', back_populates='user', cascade="all, delete-orphan")  # НОВОЕ

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    exam_name = Column(String, nullable=False)
    exam_details = Column(JSON, default={})
    target_profile = Column(JSON, default={})
    current_profile = Column(JSON, default={})
    time_available_days = Column(Integer)
    study_plan = Column(JSON, default={})
    status = Column(String, default='init')  # init, testing, planning, learning, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='sessions')
    test_results = relationship('TestResult', back_populates='session', cascade="all, delete-orphan")
    lessons = relationship('Lesson', back_populates='session', cascade="all, delete-orphan")
    progress_history = relationship('ProgressHistory', back_populates='session', cascade="all, delete-orphan")

class TestResult(Base):
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'))
    test_type = Column(String)  # initial, progress, module_test, custom
    questions = Column(JSON, default=[])
    answers = Column(JSON, default={})
    evaluation = Column(JSON, default={})
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship('Session', back_populates='test_results')

class Lesson(Base):
    __tablename__ = 'lessons'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'))
    topic = Column(String, nullable=False)
    content = Column(Text, default='')
    tasks = Column(JSON, default=[])
    completed = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    video = relationship('LessonVideo', back_populates='lesson', uselist=False, cascade="all, delete-orphan")
    
    session = relationship('Session', back_populates='lessons')

# backend/app/models.py (добавить после класса Lesson)

class LessonVideo(Base):
    __tablename__ = 'lesson_videos'
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id', ondelete='CASCADE'), unique=True)
    video_path = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    lesson = relationship('Lesson', back_populates='video')

class ProgressHistory(Base):
    __tablename__ = 'progress_history'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'))
    profile_snapshot = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship('Session', back_populates='progress_history')

# ========== НОВАЯ МОДЕЛЬ: ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ ==========
class CustomTest(Base):
    __tablename__ = 'custom_tests'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    questions = Column(JSON, nullable=False)  # [{"text": "...", "correct_answer": "...", "explanation": "..."}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='custom_tests')

# backend/app/models.py (добавить в конец)

class UserCourse(Base):
    """Пользовательский курс"""
    __tablename__ = 'user_courses'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    success_criteria = Column(Text, nullable=True)   # критерии успеха (текст или JSON)
    status = Column(String, default='draft')        # draft, generating, ready, active
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='user_courses')
    modules = relationship('CourseModule', back_populates='course', cascade='all, delete-orphan')

class CourseModule(Base):
    """Модуль курса"""
    __tablename__ = 'course_modules'
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey('user_courses.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    
    course = relationship('UserCourse', back_populates='modules')
    lessons = relationship('CourseLesson', back_populates='module', cascade='all, delete-orphan')

class CourseLesson(Base):
    """Урок внутри модуля"""
    __tablename__ = 'course_lessons'
    
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey('course_modules.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    content = Column(JSON, default={})       # теория, примеры, задачи и т.д.
    homework = Column(JSON, default=[])      # домашние задания
    success_criteria = Column(Text, nullable=True)
    youtube_urls = Column(JSON, default=[])   # ссылки на видео
    presentation_url = Column(String, nullable=True)  # ссылка на презентацию
    created_at = Column(DateTime, default=datetime.utcnow)
    
    module = relationship('CourseModule', back_populates='lessons')

class UserLesson(Base):
    """Самостоятельный урок (не в составе курса)"""
    __tablename__ = 'user_lessons'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(JSON, default={})        # теория, практика, ДЗ
    success_criteria = Column(Text, nullable=True)
    youtube_urls = Column(JSON, default=[])
    presentation_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='user_lessons')