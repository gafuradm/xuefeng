# backend/app/role_service.py

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import User, Role

# Матрица доступа: роль -> список модулей
ROLE_MODULE_ACCESS = {
    'schoolchild': ['learning', 'tests', 'schools_student', 'video', 'pdf_chat', 'exam_tickets', 'essay_check', 'planner', 'ielts', 'ocr', 'video_generation', 'soft_skills', 'coding_interviews', 'aidouble', 'rating_view'],
    'applicant': ['learning', 'tests', 'video', 'pdf_chat', 'exam_tickets', 'essay_check', 'planner', 'ielts', 'ocr', 'video_generation', 'aidouble', 'rating_view'],
    'student': ['learning', 'tests', 'courses_create', 'schools_student', 'video', 'pdf_chat', 'exam_tickets', 'essay_check', 'planner', 'scientific', 'data_analysis', 'ielts', 'ocr', 'video_generation', 'supervisor_search', 'internship_match', 'soft_skills', 'coding_interviews', 'aidouble', 'rating_view'],
    'master': ['learning', 'tests', 'courses_create', 'scientific', 'data_analysis', 'hypothesis_generator', 'supervisor_search', 'soft_skills', 'coding_interviews', 'planner', 'internship_match', 'aidouble', 'rating_view'],
    'phd': ['learning', 'tests', 'courses_create', 'scientific', 'data_analysis', 'hypothesis_generator', 'supervisor_search', 'peer_review', 'soft_skills', 'coding_interviews', 'planner', 'internship_match', 'aidouble', 'rating_view'],
    'researcher': ['scientific', 'data_analysis', 'hypothesis_generator', 'publications', 'peer_review', 'planner', 'supervisor_search', 'internship_match', 'aidouble', 'rating_view'],
    'professor': ['courses_create', 'schools_teacher', 'essay_check_reviewer', 'scientific', 'supervisor_as_mentor', 'soft_skills', 'planner', 'aidouble', 'rating_view'],
    'school_teacher': ['courses_create', 'schools_teacher', 'exam_tickets', 'essay_check_reviewer', 'planner', 'soft_skills', 'aidouble', 'rating_view'],
    'private_tutor': ['courses_create', 'tests', 'video', 'pdf_chat', 'exam_tickets', 'essay_check', 'planner', 'soft_skills', 'aidouble', 'rating_view'],
    'employer': ['internship_match', 'corporate_training', 'soft_skills_assessor', 'coding_interviews_creator', 'rating_view', 'aidouble'],
    'job_seeker': ['soft_skills', 'coding_interviews', 'internship_match', 'planner', 'essay_check_resume', 'aidouble', 'rating_view'],
    'freelancer': ['courses_create', 'tests', 'essay_check', 'planner', 'rating_participant', 'soft_skills', 'aidouble', 'rating_view'],
    'customer': ['freelancer_search', 'essay_check_order', 'planner', 'aidouble', 'rating_view'],
    'startup_founder': ['hypothesis_generator', 'business_models', 'investor_search', 'rating_view', 'planner', 'aidouble'],
    'investor': ['startup_rating', 'investment_analytics', 'planner', 'aidouble', 'rating_view'],
    'government': ['admin_all'],
    'developer': ['api_access', 'aidouble', 'rating_view']
}

# Соответствие модуля -> идентификатор вкладки и название на UI
MODULE_TO_TAB = {
    'learning': ('learning', 'Обучение', 'fa-home'),
    'tests': ('tests', 'Тесты', 'fa-pen-alt'),
    'courses_create': ('courses', 'Курсы', 'fa-book-open'),
    'schools_student': ('schools', 'Школы', 'fa-school'),
    'schools_teacher': ('schools', 'Школы', 'fa-school'),
    'video': ('video', 'Видео → текст', 'fa-video'),
    'pdf_chat': ('pdfchat', 'PDF чат', 'fa-file-pdf'),
    'exam_tickets': ('examtickets', 'Билеты', 'fa-ticket-alt'),
    'essay_check': ('essaycheck', 'Проверка работ', 'fa-file-alt'),
    'planner': ('planner', 'Планировщик', 'fa-calendar-alt'),
    'scientific': ('scientific', 'Научные статьи', 'fa-flask'),
    'syllabus': ('syllabus', 'Конструктор курсов', 'fa-chalkboard-user'),
    'data_analysis': ('dataanalysis', 'Анализ данных', 'fa-chart-line'),
    'ielts': ('ielts', 'IELTS', 'fa-language'),
    'soft_skills': ('softskills', 'Soft Skills', 'fa-comments'),
    'coding_interviews': ('coding', 'Техсобеседования', 'fa-code'),
    'supervisor_search': ('supervisor', 'Научный руководитель', 'fa-user-graduate'),
    'internship_match': ('internship', 'Стажировки', 'fa-briefcase'),
    'hypothesis_generator': ('hypothesis', 'Генератор гипотез', 'fa-lightbulb'),
    'rating_view': ('rating', 'Рейтинг', 'fa-trophy'),
    'corporate_training': ('corporate', 'Корп. обучение', 'fa-building'),
    'api_access': ('api', 'API', 'fa-plug'),
    'aidouble': ('aidouble', 'AI-двойник', 'fa-robot'),
    'essay_check_reviewer': ('essaycheck', 'Проверка работ', 'fa-file-alt'),
    'peer_review': ('scientific', 'Научные статьи', 'fa-flask'),
    'publications': ('scientific', 'Научные статьи', 'fa-flask'),
    'startup_rating': ('rating', 'Рейтинг', 'fa-trophy'),
    'investment_analytics': ('dataanalysis', 'Анализ данных', 'fa-chart-line'),
    'freelancer_search': ('freelance', 'Фриланс', 'fa-handshake'),
    'rating_participant': ('rating', 'Рейтинг', 'fa-trophy'),
    'business_models': ('startup', 'Стартап', 'fa-rocket'),
    'investor_search': ('startup', 'Стартап', 'fa-rocket'),
    'supervisor_as_mentor': ('supervisor', 'Научный руководитель', 'fa-user-graduate'),
    'coding_interviews_creator': ('coding', 'Техсобеседования', 'fa-code'),
    'soft_skills_assessor': ('softskills', 'Soft Skills', 'fa-comments'),
    'essay_check_order': ('essaycheck', 'Проверка работ', 'fa-file-alt'),
    'essay_check_resume': ('essaycheck', 'Проверка работ', 'fa-file-alt'),
}

def get_user_module_access(user: User) -> List[str]:
    """Возвращает список уникальных модулей, доступных пользователю на основе его ролей"""
    if not user.roles:
        return []
    modules = set()
    for role in user.roles:
        modules.update(ROLE_MODULE_ACCESS.get(role.name, []))
    return list(modules)

def check_module_access(user: User, module_name: str) -> bool:
    """Проверяет, имеет ли пользователь доступ к данному модулю"""
    if is_government(user):
        return True
    return module_name in get_user_module_access(user)

def is_government(user: User) -> bool:
    """Проверяет, является ли пользователь государственным администратором"""
    return any(role.name == 'government' for role in user.roles)

def get_visible_tabs(user: User) -> List[Dict[str, str]]:
    """Возвращает список вкладок (id, название, иконка) для отображения на фронтенде"""
    modules = get_user_module_access(user)
    tabs_dict = {}
    for module in modules:
        if module in MODULE_TO_TAB:
            tab_id, tab_name, icon = MODULE_TO_TAB[module]
            if tab_id not in tabs_dict:
                tabs_dict[tab_id] = {'id': tab_id, 'name': tab_name, 'icon': icon}
    return list(tabs_dict.values())

def get_default_roles() -> List[str]:
    """Возвращает имена ролей, которые назначаются новому пользователю по умолчанию"""
    return ['schoolchild', 'student']