# backend/app/rating_service.py
from typing import List, Dict
from sqlalchemy.orm import Session
from .models import User, UserRating, UserAchievement, UserCourse, CustomTest
from datetime import datetime

class RatingService:
    @staticmethod
    def update_user_rating(db: Session, user_id: int):
        """Обновляет рейтинг пользователя для всех его ролей"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        total_xp = user.total_xp or 0
        level = user.level or 1
        achievements_count = db.query(UserAchievement).filter(UserAchievement.user_id == user_id).count()
        courses_completed = db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.status == "completed"
        ).count()
        tests_passed = db.query(CustomTest).filter(
            CustomTest.user_id == user_id
        ).count()
        
        rating_score = (
            total_xp * 0.3 +
            level * 10 +
            achievements_count * 20 +
            courses_completed * 50 +
            tests_passed * 10
        )
        
        for role in user.roles:
            rating = db.query(UserRating).filter(
                UserRating.user_id == user_id,
                UserRating.role_name == role.name
            ).first()
            if not rating:
                rating = UserRating(user_id=user_id, role_name=role.name)
                db.add(rating)
            rating.total_xp = total_xp
            rating.level = level
            rating.achievements_count = achievements_count
            rating.courses_completed = courses_completed
            rating.tests_passed = tests_passed
            rating.rating_score = rating_score
            rating.updated_at = datetime.utcnow()
        db.commit()
    
    @staticmethod
    def get_ranking_by_role(db: Session, role_name: str, limit: int = 100) -> List[Dict]:
        """Возвращает топ пользователей по роли"""
        rankings = db.query(UserRating).filter(UserRating.role_name == role_name).order_by(
            UserRating.rating_score.desc()
        ).limit(limit).all()
        
        result = []
        for idx, r in enumerate(rankings, 1):
            result.append({
                "rank": idx,
                "user_id": r.user_id,
                "name": r.user.name,
                "level": r.level,
                "total_xp": r.total_xp,
                "achievements": r.achievements_count,
                "rating_score": r.rating_score
            })
        return result
    
    @staticmethod
    def get_my_rank(db: Session, user_id: int, role_name: str) -> Dict:
        """Позиция пользователя в рейтинге по конкретной роли"""
        user_rating = db.query(UserRating.rating_score).filter(
            UserRating.user_id == user_id,
            UserRating.role_name == role_name
        ).scalar()
        if user_rating is None:
            return {"rank": 0, "total": 0}
        better = db.query(UserRating).filter(
            UserRating.role_name == role_name,
            UserRating.rating_score > user_rating
        ).count()
        rank = better + 1
        total = db.query(UserRating).filter(UserRating.role_name == role_name).count()
        return {"rank": rank, "total": total}