# backend/app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text, Index, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# ========== ТАБЛИЦА СВЯЗИ ПОЛЬЗОВАТЕЛЬ-РОЛЬ (МНОГИЕ КО МНОГИМ) ==========
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

# ========== СЛУЖЕБНЫЕ ТАБЛИЦЫ (REFRESH TOKENS, PASSWORD RESETS) ==========

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="refresh_tokens")

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="password_resets")

class UserAction(Base):
    __tablename__ = "user_actions"
    __table_args__ = (
        Index('ix_user_actions_user_timestamp', 'user_id', 'timestamp'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, index=True, nullable=False)
    action_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    url = Column(String, nullable=True)
    method = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    module_name = Column(String, nullable=True)
    
    user = relationship("User", back_populates="actions")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="chat_messages")

# ========== РОЛИ ==========
class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    can_be_assigned_by_user = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    
    users = relationship("User", secondary=user_roles, back_populates="roles")

# ========== ОСНОВНАЯ ТАБЛИЦА ПОЛЬЗОВАТЕЛЯ ==========

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    hypotheses = relationship("Hypothesis", back_populates="user", cascade="all, delete-orphan")
    research_interests = Column(Text, nullable=True)
    supervisor_requests = relationship("UserSupervisor", back_populates="user", cascade="all, delete-orphan")
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")

    vacancy_applications = relationship("UserVacancy", back_populates="user", cascade="all, delete-orphan")
    cv_summary = Column(Text, nullable=True)
    desired_position = Column(String, nullable=True)
    desired_salary = Column(Integer, nullable=True)
    work_experience_years = Column(Float, default=0.0)
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)

    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)

    roles = relationship("Role", secondary=user_roles, back_populates="users")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

    text_reviews = relationship("TextReview", back_populates="user", cascade="all, delete-orphan")
    data_analysis_sessions = relationship("DataAnalysisSession", back_populates="user", cascade="all, delete-orphan")
    scientific_articles = relationship("ScientificArticle", back_populates="user", cascade="all, delete-orphan")

    syllabus_courses = relationship("SyllabusCourse", back_populates="user", cascade="all, delete-orphan")
    exam_tickets = relationship("ExamTicket", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    current_hsk_level = Column(Integer, default=1)
    target_hsk_level = Column(Integer, default=4)
    exam_date = Column(DateTime, nullable=True)
    daily_goal = Column(Integer, default=20)
    
    total_points = Column(Integer, default=0)
    study_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    total_study_time = Column(Integer, default=0)
    total_words_learned = Column(Integer, default=0)
    total_tests_taken = Column(Integer, default=0)
    average_test_score = Column(Float, default=0.0)
    
    email_notifications = Column(Boolean, default=True)
    theme = Column(String, default="light")
    
    education_background = Column(Text, nullable=True)
    university_target = Column(String, nullable=True)
    program_target = Column(String, nullable=True)
    department_target = Column(String, nullable=True)
    work_experience = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    technical_skills = Column(Text, nullable=True)
    achievements_text = Column(Text, nullable=True)
    letter_style = Column(JSON, nullable=True)

    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    
    user_courses = relationship('UserCourse', back_populates='user', cascade='all, delete-orphan')
    user_lessons = relationship('UserLesson', back_populates='user', cascade='all, delete-orphan')
    sessions = relationship('Session', back_populates='user', cascade="all, delete-orphan")
    custom_tests = relationship('CustomTest', back_populates='user', cascade="all, delete-orphan")
    interactions = relationship('UserInteraction', back_populates='user', cascade='all, delete-orphan')
    performances = relationship('UserPerformance', back_populates='user', cascade='all, delete-orphan')
    topic_time_stats = relationship('TopicTimeStats', back_populates='user', cascade='all, delete-orphan')
    auth = relationship('UserAuth', back_populates='user', uselist=False, cascade='all, delete-orphan')
    school_members = relationship('SchoolMember', back_populates='user', cascade='all, delete-orphan')
    owned_schools = relationship('School', foreign_keys='School.owner_id', cascade='all, delete-orphan')
    
    interview_sessions = relationship('InterviewSessionDB', back_populates='user', cascade='all, delete-orphan')
    refresh_tokens = relationship('RefreshToken', back_populates='user', cascade='all, delete-orphan')
    password_resets = relationship('PasswordReset', back_populates='user', cascade='all, delete-orphan')
    actions = relationship('UserAction', back_populates='user', cascade='all, delete-orphan', order_by='desc(UserAction.timestamp)')
    words = relationship('UserWord', back_populates='user', cascade='all, delete-orphan')
    tests = relationship('UserTest', back_populates='user', cascade='all, delete-orphan')
    chat_messages = relationship('ChatMessage', back_populates='user', cascade='all, delete-orphan')
    study_sessions = relationship('StudySession', back_populates='user', cascade='all, delete-orphan')
    
    sent_messages = relationship(
        "SchoolChatMessage",
        foreign_keys="SchoolChatMessage.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "SchoolChatMessage",
        foreign_keys="SchoolChatMessage.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan"
    )

    # Корпоративное обучение
    course_assignments = relationship("CourseAssignment", back_populates="user", foreign_keys="CourseAssignment.user_id", cascade="all, delete-orphan")
    assigned_courses = relationship("CourseAssignment", back_populates="assigner", foreign_keys="CourseAssignment.assigned_by")

# ========== ДОСТИЖЕНИЯ И ОПЫТ ==========
class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_type = Column(String, nullable=False)
    module_name = Column(String, nullable=True)
    xp_awarded = Column(Integer, default=0)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="achievements")
    
# ========== API КЛЮЧИ ==========
class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    permissions = Column(JSON, default=list)
    rate_limit_per_minute = Column(Integer, default=60)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="api_keys")

# ========== ЛОГИ ДЕЙСТВИЙ АДМИНИСТРАТОРА ==========
class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("User", foreign_keys=[admin_user_id])
    target = relationship("User", foreign_keys=[target_user_id])

# ========== ОСТАЛЬНЫЕ СУЩЕСТВУЮЩИЕ МОДЕЛИ ==========

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


class StudentPerformance(Base):
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
    time_spent_seconds = Column(Integer, default=0)
    question_times = Column(JSON, default={})
    
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


# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КУРСЫ (ДОБАВЛЕНА ШКОЛА И НАЗНАЧЕНИЯ) ==========
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
    
    # Привязка к школе для корпоративного обучения
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=True)
    
    user = relationship('User', back_populates='user_courses')
    school = relationship("School", back_populates="courses")
    modules = relationship('CourseModule', back_populates='course', cascade='all, delete-orphan')
    assignments = relationship("CourseAssignment", back_populates="course", cascade="all, delete-orphan")


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
    user_progress = relationship("UserLessonProgress", back_populates="lesson", cascade="all, delete-orphan")


# ========== ПРОГРЕСС ПО УРОКАМ КУРСА ==========
class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id", ondelete="CASCADE"), nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)
    
    user = relationship("User")
    lesson = relationship("CourseLesson", back_populates="user_progress")


# ========== НАЗНАЧЕНИЕ КУРСОВ УЧЕНИКАМ ==========
class CourseAssignment(Base):
    __tablename__ = "course_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("user_courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # pending, in_progress, completed
    completed_at = Column(DateTime, nullable=True)
    certificate_url = Column(String, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    course = relationship("UserCourse", back_populates="assignments")
    user = relationship("User", foreign_keys=[user_id], back_populates="course_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by], back_populates="assigned_courses")


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
    __tablename__ = 'user_performances'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    topic = Column(String, nullable=False)
    correct_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    mastery_level = Column(Float, default=0.0)
    total_time_spent = Column(Integer, default=0)
    
    user = relationship('User', back_populates='performances')


class TopicTimeStats(Base):
    __tablename__ = 'topic_time_stats'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    topic = Column(String, nullable=False)
    total_seconds = Column(Integer, default=0)
    sessions_count = Column(Integer, default=0)
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
    courses = relationship("UserCourse", back_populates="school", cascade="all, delete-orphan")


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
    is_private = Column(Boolean, default=False)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    school = relationship("School")
    user = relationship("User", foreign_keys=[user_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")


# ========== СЛОВА, ТЕСТЫ, СЕССИИ (HSK TUTOR) ==========

class UserWord(Base):
    __tablename__ = "user_words"
    __table_args__ = (
        Index('ix_user_words_user_word', 'user_id', 'word_id', unique=True),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(String, nullable=False)
    word_text = Column(String, nullable=True)
    hsk_level = Column(Integer, nullable=True)
    status = Column(String, default="new")
    difficulty = Column(Integer, default=3)
    views_count = Column(Integer, default=0)
    practice_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    last_viewed = Column(DateTime, nullable=True)
    last_practiced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="words")


class UserTest(Base):
    __tablename__ = "user_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_id = Column(String, nullable=True)
    test_type = Column(String, nullable=False)
    test_level = Column(Integer, nullable=False)
    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    percentage = Column(Float, nullable=True)
    time_spent = Column(Integer, nullable=True)
    questions_count = Column(Integer, nullable=True)
    correct_count = Column(Integer, nullable=True)
    wrong_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    answers = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="tests")


class StudySession(Base):
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    words_studied = Column(Integer, default=0)
    tests_taken = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="study_sessions")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(String, unique=True, index=True, nullable=False)
    name_zh = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    name_ru = Column(String, nullable=True)
    level = Column(String, nullable=False)
    category = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    examples = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class HSKWord(Base):
    __tablename__ = "hsk_words"
    
    id = Column(Integer, primary_key=True, index=True)
    character = Column(String, nullable=False)
    pinyin = Column(String, nullable=False)
    translation_ru = Column(String, nullable=True)
    translation_en = Column(String, nullable=True)
    hsk_level = Column(Integer, nullable=False)
    part_of_speech = Column(String, nullable=True)
    example = Column(String, nullable=True)
    example_translation = Column(String, nullable=True)


class CSCATopic(Base):
    __tablename__ = "csca_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(String, unique=True, index=True, nullable=False)
    name_zh = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    difficulty = Column(String, default="Intermediate")
    order = Column(Integer, default=0)


class InterviewSessionDB(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    university = Column(String, nullable=False)
    program = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    professors = Column(JSON, nullable=True)
    tech_expert = Column(JSON, nullable=True)
    messages = Column(JSON, nullable=True, default=list)
    ended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="interview_sessions")


class University(Base):
    __tablename__ = "universities"
    
    id = Column(Integer, primary_key=True, index=True)
    name_zh = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    ranking = Column(Integer, nullable=True)
    type = Column(String, nullable=True)
    website = Column(String, nullable=True)
    tuition_cny = Column(Integer, nullable=True)
    scholarships = Column(JSON, default=[])
    programs = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class IELTSAttempt(Base):
    __tablename__ = "ielts_attempts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_type = Column(String)
    audio_path = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)
    scores = Column(JSON, default={})
    overall_band = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    suggestions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    index_path = Column(String, nullable=True)
    chunks_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="documents")

class ExamTicket(Base):
    __tablename__ = "exam_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_name = Column(String, nullable=False)
    num_questions = Column(Integer, nullable=False)
    ticket_type = Column(String, default="tickets")
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="exam_tickets")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=False)
    status = Column(String, default="pending")
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tasks")

class SyllabusCourse(Base):
    __tablename__ = "syllabus_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    department = Column(String, nullable=True)
    university = Column(String, nullable=True)
    semester = Column(Integer, nullable=True)
    credits = Column(Float, nullable=True)
    total_hours = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    competencies = Column(JSON, default=[])
    syllabus_content = Column(JSON, default={})
    assessment_tools = Column(JSON, default=[])
    literature = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="syllabus_courses")

class ScientificArticle(Base):
    __tablename__ = "scientific_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    arxiv_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    authors = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    published = Column(DateTime, nullable=True)
    url = Column(String, nullable=True)
    bibtex = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="scientific_articles")

class DataAnalysisSession(Base):
    __tablename__ = "data_analysis_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    dataframe_json = Column(Text, nullable=True)
    code = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    output_images = Column(JSON, default=[])
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="data_analysis_sessions")

class PlagiarismCorpus(Base):
    __tablename__ = "plagiarism_corpus"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text_hash = Column(String(64), unique=True, index=True)
    shingles = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class TextReview(Base):
    __tablename__ = "text_reviews"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    ai_feedback = Column(JSON)
    plagiarism_percent = Column(Float, default=0.0)
    similar_parts = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="text_reviews")

class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    domain = Column(String, nullable=True)
    confidence_score = Column(Float, default=0.0)
    relevance_score = Column(Float, default=0.0)
    context_snapshot = Column(JSON, nullable=True)
    user_rating = Column(Integer, nullable=True)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="hypotheses")

class Supervisor(Base):
    __tablename__ = "supervisors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    department = Column(String, nullable=True)
    university = Column(String, nullable=True)
    position = Column(String, nullable=True)
    research_areas = Column(JSON, default=list)
    keywords = Column(JSON, default=list)
    publications_summary = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    contact_info = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_supervisors = relationship("UserSupervisor", back_populates="supervisor", cascade="all, delete-orphan")

class UserSupervisor(Base):
    __tablename__ = "user_supervisors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("supervisors.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending")
    request_message = Column(Text, nullable=True)
    supervisor_reply = Column(Text, nullable=True)
    matching_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="supervisor_requests")
    supervisor = relationship("Supervisor", back_populates="user_supervisors")

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    vacancies = relationship("Vacancy", back_populates="company", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

class Vacancy(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    skills = Column(JSON, default=list)
    experience_years = Column(Float, default=0.0)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    employment_type = Column(String, default="full")
    is_active = Column(Boolean, default=True)
    posted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    company = relationship("Company", back_populates="vacancies")
    user_vacancies = relationship("UserVacancy", back_populates="vacancy", cascade="all, delete-orphan")

class UserVacancy(Base):
    __tablename__ = "user_vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending")
    matching_score = Column(Float, default=0.0)
    cover_letter = Column(Text, nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="vacancy_applications")
    vacancy = relationship("Vacancy", back_populates="user_vacancies")