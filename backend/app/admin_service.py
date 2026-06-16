# backend/app/admin_service.py
from datetime import datetime
from sqlalchemy.orm import Session
from .models import (
    PlatformModule, ModuleRoleAccess, User, Role, UserAction,
    SoftSkillAssessment, Company, Vacancy, School, UserCourse, CustomTest
)

class AdminService:
    @staticmethod
    def get_all_users(db: Session, limit: int = 100, offset: int = 0):
        return db.query(User).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_user_details(db: Session, user_id: int):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        actions = db.query(UserAction).filter(UserAction.user_id == user_id).order_by(UserAction.timestamp.desc()).limit(50).all()
        return {"user": user, "actions": actions}
    
    @staticmethod
    def get_platform_stats(db: Session):
        total_users = db.query(User).count()
        total_schools = db.query(School).count()
        total_courses = db.query(UserCourse).count()
        total_tests = db.query(CustomTest).count()
        total_companies = db.query(Company).count()
        total_vacancies = db.query(Vacancy).count()
        total_soft_assessments = db.query(SoftSkillAssessment).count()
        return {
            "total_users": total_users,
            "total_schools": total_schools,
            "total_courses": total_courses,
            "total_tests": total_tests,
            "total_companies": total_companies,
            "total_vacancies": total_vacancies,
            "total_soft_assessments": total_soft_assessments
        }
    
    @staticmethod
    def toggle_module(db: Session, module_name: str, is_active: bool):
        module = db.query(PlatformModule).filter(PlatformModule.name == module_name).first()
        if module:
            module.is_active = is_active
            module.updated_at = datetime.utcnow()
            db.commit()
        return module