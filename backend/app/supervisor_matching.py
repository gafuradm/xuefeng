# backend/app/supervisor_matching.py

import json
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from .models import User, Supervisor, UserSupervisor, UserPerformance, UserAchievement
from .deepseek_client import deepseek_client

class SupervisorMatcher:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    async def get_user_profile_text(self) -> str:
        """Формирует текстовое представление профиля пользователя для сравнения"""
        # Собираем данные
        roles = [role.name for role in self.user.roles]
        education = self.user.education_background or ""
        research_interests = self.user.research_interests or ""
        technical_skills = self.user.technical_skills or ""
        projects = self.user.projects or ""
        
        # Сильные и слабые темы из успеваемости
        performances = self.db.query(UserPerformance).filter(UserPerformance.user_id == self.user.id).all()
        strong_topics = [p.topic for p in performances if p.mastery_level >= 70][:5]
        weak_topics = [p.topic for p in performances if p.mastery_level < 40][:5]
        
        # Достижения
        achievements = self.db.query(UserAchievement).filter(UserAchievement.user_id == self.user.id).limit(10).all()
        achievement_types = list(set(a.achievement_type for a in achievements))
        
        profile_text = f"""
        Роли: {', '.join(roles)}
        Образование: {education}
        Научные интересы: {research_interests}
        Технические навыки: {technical_skills}
        Проекты: {projects}
        Сильные темы: {', '.join(strong_topics)}
        Слабые темы: {', '.join(weak_topics)}
        Достижения: {', '.join(achievement_types)}
        """
        return profile_text.strip()

    async def get_supervisor_profile_text(self, supervisor: Supervisor) -> str:
        """Формирует текстовое представление профиля научного руководителя"""
        research_areas = ", ".join(supervisor.research_areas) if supervisor.research_areas else ""
        keywords = ", ".join(supervisor.keywords) if supervisor.keywords else ""
        return f"""
        Имя: {supervisor.name}
        Должность: {supervisor.position or ''}
        Кафедра: {supervisor.department or ''}
        Университет: {supervisor.university or ''}
        Научные направления: {research_areas}
        Ключевые слова: {keywords}
        Публикации: {supervisor.publications_summary or ''}
        Биография: {supervisor.bio or ''}
        """.strip()

    async def compute_single_match(self, supervisor: Supervisor) -> float:
        """Вычисляет процент совпадения между пользователем и конкретным руководителем через AI"""
        user_text = await self.get_user_profile_text()
        supervisor_text = await self.get_supervisor_profile_text(supervisor)
        
        prompt = f"""
Ты – эксперт по подбору научных руководителей. Оцени степень соответствия между студентом и потенциальным научным руководителем.

ПРОФИЛЬ СТУДЕНТА:
{user_text}

ПРОФИЛЬ РУКОВОДИТЕЛЯ:
{supervisor_text}

Оцени по шкале от 0 до 100, насколько руководитель подходит студенту. Учитывай:
- Совпадение научных интересов
- Соответствие навыков студента направлениям руководителя
- Возможность развития слабых сторон студента под руководством
- Перспективность совместной работы

Верни ТОЛЬКО целое число от 0 до 100, без пояснений.
"""
        try:
            response = await deepseek_client.chat_completion([
                {"role": "system", "content": "Ты эксперт по подбору научных руководителей. Отвечай только числом."},
                {"role": "user", "content": prompt}
            ], max_tokens=10, temperature=0.3)
            # Извлекаем число
            match = re.search(r'\d+', response.strip())
            score = int(match.group()) if match else 50
            return min(100, max(0, score))
        except Exception as e:
            print(f"Ошибка вычисления match: {e}")
            return 50.0

    async def match_top_supervisors(self, limit: int = 10) -> List[Dict]:
        """Находит топ N подходящих руководителей для пользователя"""
        supervisors = self.db.query(Supervisor).filter(Supervisor.is_active == True).all()
        if not supervisors:
            return []
        
        # Сначала быстрый отбор по ключевым словам (опционально, для скорости)
        user_interests = (self.user.research_interests or "").lower()
        user_skills = (self.user.technical_skills or "").lower()
        
        scored = []
        for sup in supervisors:
            # Быстрая предфильтрация: если нет общих ключевых слов, можно пропустить,
            # но для демонстрации считаем для всех
            score = await self.compute_single_match(sup)
            scored.append({
                "supervisor_id": sup.id,
                "name": sup.name,
                "position": sup.position,
                "department": sup.department,
                "university": sup.university,
                "research_areas": sup.research_areas,
                "avatar_url": sup.avatar_url,
                "matching_score": score
            })
        # Сортировка по убыванию
        scored.sort(key=lambda x: x["matching_score"], reverse=True)
        return scored[:limit]

    async def save_match(self, supervisor_id: int, score: float, status: str = "favorited") -> UserSupervisor:
        """Сохраняет результат сопоставления в базу (избранное)"""
        existing = self.db.query(UserSupervisor).filter(
            UserSupervisor.user_id == self.user.id,
            UserSupervisor.supervisor_id == supervisor_id
        ).first()
        if existing:
            existing.matching_score = score
            existing.status = status
            existing.updated_at = datetime.utcnow()
        else:
            us = UserSupervisor(
                user_id=self.user.id,
                supervisor_id=supervisor_id,
                matching_score=score,
                status=status
            )
            self.db.add(us)
        self.db.commit()
        return existing or us