# backend/app/vacancy_matching.py

import json
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import User, Vacancy, Company, UserVacancy, UserPerformance, UserAchievement, Role
from .deepseek_client import deepseek_client
from datetime import datetime

class VacancyMatcher:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    async def get_student_profile_text(self) -> str:
        """Собирает текстовое представление профиля соискателя"""
        roles = [role.name for role in self.user.roles]
        education = self.user.education_background or ""
        skills = self.user.technical_skills or ""
        projects = self.user.projects or ""
        cv = self.user.cv_summary or ""
        desired_position = self.user.desired_position or ""
        desired_salary = self.user.desired_salary or ""
        experience = self.user.work_experience_years or 0
        
        # Сильные и слабые темы из успеваемости
        performances = self.db.query(UserPerformance).filter(UserPerformance.user_id == self.user.id).all()
        strong_topics = [p.topic for p in performances if p.mastery_level >= 70][:5]
        weak_topics = [p.topic for p in performances if p.mastery_level < 40][:5]
        
        # Достижения
        achievements = self.db.query(UserAchievement).filter(UserAchievement.user_id == self.user.id).limit(10).all()
        achievement_types = list(set(a.achievement_type for a in achievements))
        
        profile = f"""
        Роли: {', '.join(roles)}
        Образование: {education}
        Желаемая должность: {desired_position}
        Желаемая зарплата: {desired_salary}
        Опыт работы (лет): {experience}
        Технические навыки: {skills}
        Проекты: {projects}
        Резюме: {cv}
        Сильные темы: {', '.join(strong_topics)}
        Слабые темы: {', '.join(weak_topics)}
        Достижения: {', '.join(achievement_types)}
        """
        return profile.strip()

    async def get_vacancy_profile_text(self, vacancy: Vacancy) -> str:
        """Собирает текстовое представление вакансии"""
        company = vacancy.company
        skills = ", ".join(vacancy.skills) if vacancy.skills else ""
        return f"""
        Компания: {company.name}
        Отрасль: {company.industry or ''}
        Должность: {vacancy.title}
        Описание: {vacancy.description[:1000]}
        Требования: {vacancy.requirements or ''}
        Необходимые навыки: {skills}
        Опыт (лет): {vacancy.experience_years}
        Зарплата: {vacancy.salary_min} - {vacancy.salary_max}
        Локация: {vacancy.location or ''}
        Тип занятости: {vacancy.employment_type}
        """

    async def compute_match_score(self, vacancy: Vacancy) -> float:
        """Вычисляет процент совпадения между студентом и вакансией"""
        student_text = await self.get_student_profile_text()
        vacancy_text = await self.get_vacancy_profile_text(vacancy)
        
        prompt = f"""
Ты – HR-эксперт по подбору персонала. Оцени степень соответствия кандидата требованиям вакансии.

ПРОФИЛЬ КАНДИДАТА:
{student_text}

ОПИСАНИЕ ВАКАНСИИ:
{vacancy_text}

Оцени по шкале от 0 до 100, насколько кандидат подходит на эту позицию. Учитывай:
- Соответствие навыков
- Опыт работы
- Образование
- Желания кандидата (должность, зарплата)
- Потенциал для развития

Верни ТОЛЬКО целое число от 0 до 100, без пояснений.
"""
        try:
            response = await deepseek_client.chat_completion([
                {"role": "system", "content": "Ты HR-эксперт. Отвечай только числом."},
                {"role": "user", "content": prompt}
            ], max_tokens=10, temperature=0.3)
            match = re.search(r'\d+', response.strip())
            score = int(match.group()) if match else 50
            return min(100, max(0, score))
        except Exception as e:
            print(f"Ошибка вычисления match: {e}")
            return 50.0

    async def match_vacancies_for_student(self, limit: int = 20, min_score: int = 30) -> List[Dict]:
        """Находит топ вакансий для студента"""
        vacancies = self.db.query(Vacancy).filter(Vacancy.is_active == True).all()
        if not vacancies:
            return []
        scored = []
        for vac in vacancies:
            score = await self.compute_match_score(vac)
            if score >= min_score:
                scored.append({
                    "vacancy_id": vac.id,
                    "company_name": vac.company.name,
                    "title": vac.title,
                    "description": vac.description[:300],
                    "skills": vac.skills,
                    "location": vac.location,
                    "salary_min": vac.salary_min,
                    "salary_max": vac.salary_max,
                    "employment_type": vac.employment_type,
                    "matching_score": score
                })
        scored.sort(key=lambda x: x["matching_score"], reverse=True)
        return scored[:limit]

    async def match_students_for_vacancy(self, vacancy_id: int, limit: int = 20, min_score: int = 30) -> List[Dict]:
        """Для работодателя: поиск кандидатов под конкретную вакансию"""
        vacancy = self.db.query(Vacancy).filter(Vacancy.id == vacancy_id, Vacancy.is_active == True).first()
        if not vacancy:
            return []
        # Все студенты, у которых есть role student / job_seeker / master / phd
        users = self.db.query(User).filter(
            User.roles.any(Role.name.in_(['student', 'job_seeker', 'master', 'phd']))
        ).all()
        scored = []
        for student in users:
            # Создаём временный матчер для каждого студента, чтобы не мутировать self.user
            temp_matcher = VacancyMatcher(self.db, student)
            score = await temp_matcher.compute_match_score(vacancy)
            if score >= min_score:
                scored.append({
                    "user_id": student.id,
                    "name": student.name,
                    "education": student.education_background,
                    "skills": student.technical_skills,
                    "desired_position": student.desired_position,
                    "experience_years": student.work_experience_years,
                    "matching_score": score
                })
        scored.sort(key=lambda x: x["matching_score"], reverse=True)
        return scored[:limit]

    async def apply_to_vacancy(self, vacancy_id: int, cover_letter: str = None) -> Dict:
        """Студент откликается на вакансию"""
        vacancy = self.db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
        if not vacancy:
            raise ValueError("Вакансия не найдена")
        existing = self.db.query(UserVacancy).filter(
            UserVacancy.user_id == self.user.id,
            UserVacancy.vacancy_id == vacancy_id
        ).first()
        if existing:
            return {"message": "Вы уже откликались на эту вакансию", "status": existing.status}
        score = await self.compute_match_score(vacancy)
        uv = UserVacancy(
            user_id=self.user.id,
            vacancy_id=vacancy_id,
            status="applied",
            matching_score=score,
            cover_letter=cover_letter
        )
        self.db.add(uv)
        self.db.commit()
        return {"message": "Отклик отправлен", "matching_score": score}