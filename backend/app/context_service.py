# backend/app/context_service.py
from sqlalchemy.orm import Session
from typing import List, Dict
from .models import UserInteraction, UserPerformance, User
from datetime import datetime, timedelta

class ContextService:
    """Сервис для сбора контекста для персонализации ИИ"""
    
    @staticmethod
    async def add_interaction(
        db: Session,
        user_id: int,
        interaction_type: str,
        user_input: str,
        ai_response: str,
        session_id: int = None,
        topic: str = None
    ):
        """Сохраняет взаимодействие пользователя с ИИ"""
        interaction = UserInteraction(
            user_id=user_id,
            session_id=session_id,
            interaction_type=interaction_type,
            user_input=user_input[:2000],
            ai_response=ai_response[:2000],
            topic=topic
        )
        db.add(interaction)
        db.commit()
    
    @staticmethod
    async def update_performance(
        db: Session,
        user_id: int,
        topic: str,
        is_correct: bool
    ):
        """Обновляет статистику успеваемости по теме"""
        perf = db.query(UserPerformance).filter(
            UserPerformance.user_id == user_id,
            UserPerformance.topic == topic
        ).first()
        
        if not perf:
            perf = UserPerformance(user_id=user_id, topic=topic)
            db.add(perf)
        
        perf.total_count += 1
        if is_correct:
            perf.correct_count += 1
        
        # Вычисляем уровень владения (на основе процента правильных ответов и количества попыток)
        percentage = (perf.correct_count / perf.total_count) * 100 if perf.total_count > 0 else 0
        # Уровень владения растёт быстрее при большом количестве правильных ответов
        perf.mastery_level = min(100, percentage + (perf.correct_count * 0.5))
        perf.last_attempt = datetime.utcnow()
        db.commit()
    
    @staticmethod
    async def get_user_context(
        db: Session,
        user_id: int,
        limit: int = 20,
        current_topic: str = None
    ) -> str:
        """Собирает контекст для промпта на основе истории"""
        # Получаем последние взаимодействия
        interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).order_by(UserInteraction.created_at.desc()).limit(limit).all()
        
        # Получаем статистику по темам
        performances = db.query(UserPerformance).filter(
            UserPerformance.user_id == user_id
        ).all()
        
        context_parts = []
        
        # Добавляем статистику по темам
        if performances:
            weak_topics = [p for p in performances if p.mastery_level < 50]
            strong_topics = [p for p in performances if p.mastery_level >= 70]
            
            if weak_topics:
                context_parts.append(f"Слабые темы ученика: {', '.join([p.topic for p in weak_topics[:5]])}")
            if strong_topics:
                context_parts.append(f"Сильные темы ученика: {', '.join([p.topic for p in strong_topics[:5]])}")
        
        # Добавляем историю вопроса/ответа
        if interactions:
            context_parts.append("\nИстория взаимодействий:")
            for i in interactions[:10]:
                context_parts.append(f"- [{i.interaction_type}] Вопрос: {i.user_input[:200]}")
                context_parts.append(f"  Ответ ИИ: {i.ai_response[:200]}")
        
        # Добавляем информацию о текущей теме
        if current_topic:
            topic_perf = next((p for p in performances if p.topic == current_topic), None)
            if topic_perf:
                context_parts.append(f"\nУровень владения темой '{current_topic}': {topic_perf.mastery_level:.0f}%")
                context_parts.append(f"Правильных ответов: {topic_perf.correct_count}/{topic_perf.total_count}")
        
        return "\n".join(context_parts) if context_parts else "Нет истории взаимодействий."
    
    @staticmethod
    async def add_lesson_quality_feedback(
        db: Session,
        user_id: int,
        lesson_id: int,
        score: float
    ):
        """Обратная связь о качестве урока (на основе оценки ученика)"""
        # Можно реализовать позже – сохранять feedback для улучшения генерации
        pass