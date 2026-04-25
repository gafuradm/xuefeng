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
    
    sessions = relationship('Session', back_populates='user', cascade="all, delete-orphan")

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
    test_type = Column(String)  # initial, progress, final
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
    
    session = relationship('Session', back_populates='lessons')

class ProgressHistory(Base):
    __tablename__ = 'progress_history'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'))
    profile_snapshot = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship('Session', back_populates='progress_history')