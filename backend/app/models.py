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
    custom_tests = relationship('CustomTest', back_populates='user', cascade="all, delete-orphan")
    interactions = relationship('UserInteraction', back_populates='user', cascade='all, delete-orphan')
    performances = relationship('UserPerformance', back_populates='user', cascade='all, delete-orphan')
    topic_time_stats = relationship('TopicTimeStats', back_populates='user', cascade='all, delete-orphan')
    auth = relationship('UserAuth', back_populates='user', uselist=False, cascade='all, delete-orphan')
    role = Column(String, default='student')
    school_members = relationship('SchoolMember', back_populates='user', cascade='all, delete-orphan')
    owned_schools = relationship('School', foreign_keys='School.owner_id', cascade='all, delete-orphan')

# Добавить после класса User
class UserAuth(Base):
    __tablename__ = 'user_auth'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='auth')

# В классе User добавить:
auth = relationship('UserAuth', back_populates='user', uselist=False, cascade='all, delete-orphan')

class StudentPerformance(Base):
    """Расширенная статистика ученика с графами знаний"""
    __tablename__ = 'student_performances'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    school_id = Column(Integer, ForeignKey('schools.id', ondelete='SET NULL'), nullable=True)
    
    target_graph = Column(JSON, default={})
    current_graph = Column(JSON, default={})
    topics_progress = Column(JSON, default={})
    total_time_spent = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User')
    school = relationship('School')


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
    status = Column(String, default='init')
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
    test_type = Column(String)
    questions = Column(JSON, default=[])
    answers = Column(JSON, default={})
    evaluation = Column(JSON, default={})
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    time_spent_seconds = Column(Integer, default=0)      # общее время на тест
    question_times = Column(JSON, default={})            # {question_index: seconds}
    
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
    time_spent_seconds = Column(Integer, default=0)
    task_times = Column(JSON, default={})
    video = relationship('LessonVideo', back_populates='lesson', uselist=False, cascade="all, delete-orphan")
    
    session = relationship('Session', back_populates='lessons')


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


class CustomTest(Base):
    __tablename__ = 'custom_tests'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='custom_tests')


class UserCourse(Base):
    __tablename__ = 'user_courses'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    success_criteria = Column(Text, nullable=True)
    status = Column(String, default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='user_courses')
    modules = relationship('CourseModule', back_populates='course', cascade='all, delete-orphan')


class CourseModule(Base):
    __tablename__ = 'course_modules'
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey('user_courses.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    
    course = relationship('UserCourse', back_populates='modules')
    lessons = relationship('CourseLesson', back_populates='module', cascade='all, delete-orphan')


class CourseLesson(Base):
    __tablename__ = 'course_lessons'
    
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey('course_modules.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    content = Column(JSON, default={})
    homework = Column(JSON, default=[])
    success_criteria = Column(Text, nullable=True)
    youtube_urls = Column(JSON, default=[])
    presentation_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    module = relationship('CourseModule', back_populates='lessons')


class UserLesson(Base):
    __tablename__ = 'user_lessons'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(JSON, default={})
    success_criteria = Column(Text, nullable=True)
    youtube_urls = Column(JSON, default=[])
    presentation_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='user_lessons')


class UserInteraction(Base):
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True)
    interaction_type = Column(String)
    topic = Column(String, nullable=True)
    user_input = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    feedback_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='interactions')


class UserPerformance(Base):
    """Статистика успеваемости пользователя по темам"""
    __tablename__ = 'user_performances'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    topic = Column(String, nullable=False)
    correct_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    mastery_level = Column(Float, default=0.0)
    total_time_spent = Column(Integer, default=0)          # секунды, потраченные на эту тему
    
    user = relationship('User', back_populates='performances')


class TopicTimeStats(Base):
    """Детальная статистика времени по темам"""
    __tablename__ = 'topic_time_stats'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    topic = Column(String, nullable=False)
    total_seconds = Column(Integer, default=0)
    sessions_count = Column(Integer, default=0)            # сколько раз занимался
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='topic_time_stats')


class School(Base):
    __tablename__ = 'schools'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)
    invite_code = Column(String, unique=True, nullable=True)
    owner = relationship('User', foreign_keys=[owner_id], back_populates='owned_schools')
    members = relationship('SchoolMember', back_populates='school', cascade='all, delete-orphan')


class SchoolMember(Base):
    __tablename__ = 'school_members'
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey('schools.id', ondelete='CASCADE'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    role = Column(String, default='student')
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    school = relationship('School', back_populates='members')
    user = relationship('User', back_populates='school_members')

class SchoolChatMessage(Base):
    __tablename__ = "school_chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_private = Column(Boolean, default=False)  # False = общий чат школы, True = личное сообщение
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # для личных сообщений
    
    school = relationship("School")
    user = relationship("User", foreign_keys=[user_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="received_messages")