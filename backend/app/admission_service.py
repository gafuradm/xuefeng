# backend/app/admission_service.py
import json
import re
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from .models import User, AdmissionProfile, AdmissionResult, UserPerformance
from .deepseek_client import deepseek_client

class AdmissionMentor:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    async def analyze_and_match(self, country: str, user_data: str) -> AdmissionProfile:
        # Сохраняем профиль
        profile = AdmissionProfile(user_id=self.user.id, country=country, user_data=user_data)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        # Получаем полный контекст пользователя (оценки, проекты, навыки и т.д.)
        context = await self._get_user_context()
        
        # Генерируем подборку вузов через ИИ
        universities_data = await self._generate_universities(country, user_data, context)
        
        # Сохраняем результаты
        for uni in universities_data.get("universities", []):
            result = AdmissionResult(
                profile_id=profile.id,
                university_name=uni.get("name"),
                country=country,
                website=uni.get("website"),
                contact_email=uni.get("contact_email"),
                ranking=uni.get("ranking"),
                match_score=uni.get("match_score"),
                admission_chance=uni.get("admission_chance"),
                strengths=uni.get("strengths", []),
                gaps=uni.get("gaps", []),
                recommendations=uni.get("recommendations", []),
                action_plan=uni.get("action_plan", [])
            )
            self.db.add(result)
        self.db.commit()
        return profile

    async def _get_user_context(self) -> str:
        """Собирает полную информацию о пользователе из БД и профиля"""
        roles = [role.name for role in self.user.roles]
        education = self.user.education_background or ""
        skills = self.user.technical_skills or ""
        projects = self.user.projects or ""
        languages_known = self.user.languages or ""
        achievements = self.user.achievements_text or ""
        # Сильные/слабые темы из успеваемости
        performances = self.db.query(UserPerformance).filter(UserPerformance.user_id == self.user.id).all()
        strong_topics = [p.topic for p in performances if p.mastery_level >= 70][:5]
        weak_topics = [p.topic for p in performances if p.mastery_level < 40][:5]
        return f"""
        Роли: {', '.join(roles)}
        Образование: {education}
        Технические навыки: {skills}
        Проекты: {projects}
        Языки: {languages_known}
        Достижения: {achievements}
        Сильные темы: {', '.join(strong_topics)}
        Слабые темы: {', '.join(weak_topics)}
        """

    async def _generate_universities(self, country: str, user_data: str, context: str) -> Dict:
        prompt = f"""
Ты – AI-ментор по поступлению в вузы. Твоя задача – найти реальные, подходящие университеты в стране {country} для конкретного пользователя.
Профиль пользователя (его собственные данные): {user_data}
Контекст из платформы (оценки, проекты, навыки): {context}

ВАЖНО:
- Для каждого найденного университета укажи **его реальную страну** (например, Польша, Чехия, Германия, Франция и т.д.). НЕ используй страну поиска.
- Рейтинг (если неизвестен – поставь 0, можно приблизительно на основе мировых рейтингов).
- Процент совпадения (match_score) – насколько профиль пользователя соответствует требованиям вуза (0-100)
- Шанс поступления (admission_chance) – вероятность быть зачисленным (0-100), учитывая текущий уровень пользователя
- Сильные стороны (strengths) – что у пользователя уже хорошо для этого вуза (3-5 пунктов)
- Пробелы (gaps) – чего не хватает (3-5 пунктов)
- Рекомендации (recommendations) – что конкретно нужно сделать, чтобы закрыть пробелы (3-5 пунктов)
- Детальный алгоритм действий (action_plan) – пошаговый план, начиная с сегодняшнего дня, включая: что учить, какие экзамены сдавать, какие документы подготовить, сколько грамот собрать, какие проекты реализовать, с кем связаться, как повысить оценки, дедлайны и т.д. (8-12 шагов)

План должен быть максимально конкретным, реалистичным и персонализированным.
Верни ТОЛЬКО JSON...
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты эксперт по поступлению в вузы. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=4000, temperature=0.5)
        response = response.strip()
        # Очистка от markdown
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return json.loads(response)
    
    async def get_saved_results(self, profile_id: int) -> List[Dict]:
        results = self.db.query(AdmissionResult).filter(AdmissionResult.profile_id == profile_id).all()
        return [
            {
                "university_name": r.university_name,
                "country": r.country,
                "website": r.website,
                "contact_email": r.contact_email,
                "ranking": r.ranking,
                "match_score": r.match_score,
                "admission_chance": r.admission_chance,
                "strengths": r.strengths,
                "gaps": r.gaps,
                "recommendations": r.recommendations,
                "action_plan": r.action_plan
            }
            for r in results
        ]