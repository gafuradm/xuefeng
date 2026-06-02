# backend/app/hypothesis_service.py

import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import User, UserPerformance, UserAchievement, UserInteraction, Hypothesis
from .deepseek_client import deepseek_client

class HypothesisGenerator:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    async def collect_user_context(self) -> Dict[str, Any]:
        """Собирает полный контекст пользователя для генерации гипотез"""
        # Базовый профиль
        context = {
            "name": self.user.name,
            "roles": [role.name for role in self.user.roles],
            "education_background": self.user.education_background or "",
            "technical_skills": self.user.technical_skills or "",
            "projects": self.user.projects or "",
            "university_target": self.user.university_target or "",
            "program_target": self.user.program_target or "",
            "research_interests": self.user.research_interests or "",  # добавим позже поле, пока пусто
        }
        
        # Достижения (XP, уровень, тип достижений)
        achievements = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == self.user.id
        ).order_by(UserAchievement.created_at.desc()).limit(20).all()
        context["achievements"] = [
            {"type": a.achievement_type, "module": a.module_name, "xp": a.xp_awarded}
            for a in achievements
        ]
        context["total_xp"] = self.user.total_xp
        context["level"] = self.user.level
        
        # Успеваемость по темам (сильные и слабые стороны)
        performances = self.db.query(UserPerformance).filter(
            UserPerformance.user_id == self.user.id
        ).all()
        strong_topics = []
        weak_topics = []
        for p in performances:
            if p.mastery_level >= 70:
                strong_topics.append({"topic": p.topic, "mastery": p.mastery_level})
            elif p.mastery_level < 40:
                weak_topics.append({"topic": p.topic, "mastery": p.mastery_level})
        context["strong_topics"] = strong_topics[:10]
        context["weak_topics"] = weak_topics[:10]
        
        # Последние взаимодействия с ИИ (вопросы, темы)
        interactions = self.db.query(UserInteraction).filter(
            UserInteraction.user_id == self.user.id
        ).order_by(UserInteraction.created_at.desc()).limit(15).all()
        context["recent_questions"] = [
            {"topic": i.topic, "question": i.user_input[:200]}
            for i in interactions if i.user_input
        ]
        
        # Статистика обучения
        context["total_topics_studied"] = len(performances)
        context["average_mastery"] = sum(p.mastery_level for p in performances) / len(performances) if performances else 0
        
        return context

    async def generate_hypotheses(self, domain: str = None, num_hypotheses: int = 3) -> List[Dict]:
        """Генерирует гипотезы на основе контекста пользователя"""
        context = await self.collect_user_context()
        
        domain_hint = f" в области '{domain}'" if domain else ""
        
        prompt = f"""Ты – научный руководитель и эксперт по генерации исследовательских гипотез. 
На основе профиля пользователя сгенерируй {num_hypotheses} оригинальных, научно обоснованных гипотез для начала исследования{domain_hint}.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Имя: {context['name']}
- Роли: {', '.join(context['roles'])}
- Образование: {context['education_background'][:300]}
- Технические навыки: {context['technical_skills'][:300]}
- Проекты: {context['projects'][:300]}
- Целевой университет/программа: {context['university_target']} {context['program_target']}

ДОСТИЖЕНИЯ:
- Уровень: {context['level']}, Опыт: {context['total_xp']} XP
- Недавние достижения: {context['achievements'][:5]}

СИЛЬНЫЕ ТЕМЫ (уровень владения >70%):
{json.dumps(context['strong_topics'], ensure_ascii=False, indent=2)}

СЛАБЫЕ ТЕМЫ (уровень <40%):
{json.dumps(context['weak_topics'], ensure_ascii=False, indent=2)}

НЕДАВНИЕ ИНТЕРЕСЫ/ВОПРОСЫ:
{json.dumps(context['recent_questions'][:5], ensure_ascii=False, indent=2)}

ОБЩАЯ СТАТИСТИКА:
- Изучено тем: {context['total_topics_studied']}
- Средний уровень знаний: {context['average_mastery']:.1f}%

Требования к гипотезам:
1. Каждая гипотеза должна быть конкретной, проверяемой, с указанием предполагаемого механизма или взаимосвязи.
2. Учитывай сильные стороны пользователя – предлагай гипотезы, где он может применить свои навыки.
3. Учитывай слабые стороны – предлагай гипотезы, которые помогут закрыть пробелы и развить недостающие компетенции.
4. Для каждой гипотезы укажи:
   - Название
   - Полное описание
   - Область (domain)
   - Уверенность (0-1) – насколько ты уверен в обоснованности гипотезы
   - Релевантность (0-1) – насколько гипотеза соответствует профилю пользователя
   - Необходимые ресурсы (данные, инструменты, литература)
   - Сложность реализации (low/medium/high)
   - Потенциальное влияние (low/medium/high)

Верни ТОЛЬКО JSON массив из {num_hypotheses} объектов.
Формат:
[
  {{
    "title": "Название гипотезы",
    "text": "Полное описание",
    "domain": "область",
    "confidence_score": 0.85,
    "relevance_score": 0.9,
    "resources": ["ресурс1", "ресурс2"],
    "complexity": "medium",
    "impact": "high"
  }}
]
"""
        try:
            response = await deepseek_client.chat_completion([
                {"role": "system", "content": "Ты генератор научных гипотез. Отвечай только JSON массивом."},
                {"role": "user", "content": prompt}
            ], max_tokens=2500, temperature=0.7)
            
            # Очистка ответа
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            hypotheses = json.loads(response)
            if not isinstance(hypotheses, list):
                hypotheses = []
            return hypotheses[:num_hypotheses]
        except Exception as e:
            print(f"Ошибка генерации гипотез: {e}")
            return []

    async def save_hypotheses(self, hypotheses: List[Dict]) -> List[Hypothesis]:
        """Сохраняет сгенерированные гипотезы в БД"""
        saved = []
        context_snapshot = await self.collect_user_context()
        for h in hypotheses:
            hyp = Hypothesis(
                user_id=self.user.id,
                text=h.get("text", ""),
                domain=h.get("domain"),
                confidence_score=h.get("confidence_score", 0.5),
                relevance_score=h.get("relevance_score", 0.5),
                context_snapshot={
                    "strong_topics": context_snapshot.get("strong_topics", []),
                    "weak_topics": context_snapshot.get("weak_topics", []),
                    "level": context_snapshot.get("level"),
                    "total_xp": context_snapshot.get("total_xp")
                }
            )
            self.db.add(hyp)
            saved.append(hyp)
        self.db.commit()
        for hyp in saved:
            self.db.refresh(hyp)
        return saved