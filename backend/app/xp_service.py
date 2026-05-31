import math
from sqlalchemy.orm import Session
from .models import User, UserAchievement

async def award_xp(db: Session, user_id: int, amount: int, reason: str, module_name: str = None, extra_data: dict = None) -> None:
    """Начисляет пользователю опыт, обновляет уровень и записывает достижение"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    
    user.total_xp = (user.total_xp or 0) + amount
    old_level = user.level or 1
    new_level = calculate_level(user.total_xp)
    
    if new_level > old_level:
        user.level = new_level
        # Достижение за повышение уровня
        level_up_extra = {'old_level': old_level, 'new_level': new_level}
        achievement = UserAchievement(
            user_id=user_id,
            achievement_type='level_up',
            module_name='system',
            xp_awarded=0,
            extra_data=level_up_extra
        )
        db.add(achievement)
    
    # Запись основного достижения
    ach = UserAchievement(
        user_id=user_id,
        achievement_type=reason,
        module_name=module_name,
        xp_awarded=amount,
        extra_data=extra_data
    )
    db.add(ach)
    db.commit()

def calculate_level(total_xp: int) -> int:
    """Формула: уровень = floor(sqrt(общий_xp / 100)) + 1"""
    if total_xp <= 0:
        return 1
    return int(math.sqrt(total_xp / 100)) + 1

def get_xp_for_next_level(current_xp: int) -> int:
    """Сколько XP нужно до следующего уровня"""
    level = calculate_level(current_xp)
    xp_for_next = (level ** 2) * 100
    return xp_for_next - current_xp

async def award_lesson_completion(db: Session, user_id: int, lesson_topic: str, score: float) -> None:
    """Начисляет XP за завершение урока (бонус за оценку)"""
    base_xp = 50
    bonus = int(score / 2)  # максимум +50 XP
    total = base_xp + bonus
    await award_xp(db, user_id, total, 'lesson_completed', 'learning', extra_data={'topic': lesson_topic, 'score': score})

async def award_test_passed(db: Session, user_id: int, test_name: str, score: float) -> None:
    """Начисляет XP за успешное прохождение теста"""
    base_xp = 30
    bonus = int(score / 3)
    total = base_xp + bonus
    await award_xp(db, user_id, total, 'test_passed', 'tests', extra_data={'test_name': test_name, 'score': score})

async def award_course_created(db: Session, user_id: int, course_name: str) -> None:
    """Начисляет XP за создание курса"""
    await award_xp(db, user_id, 100, 'course_created', 'courses_create', extra_data={'course_name': course_name})

async def award_lesson_created(db: Session, user_id: int, lesson_title: str) -> None:
    """Начисляет XP за создание урока"""
    await award_xp(db, user_id, 40, 'lesson_created', 'courses_create', extra_data={'lesson_title': lesson_title})

async def award_school_joined(db: Session, user_id: int, school_name: str) -> None:
    """Начисляет XP за вступление в школу"""
    await award_xp(db, user_id, 20, 'school_joined', 'schools_student', extra_data={'school_name': school_name})

async def award_article_saved(db: Session, user_id: int, article_title: str) -> None:
    """Начисляет XP за сохранение научной статьи"""
    await award_xp(db, user_id, 15, 'article_saved', 'scientific', extra_data={'title': article_title})

async def award_hypothesis_generated(db: Session, user_id: int, topic: str) -> None:
    """Начисляет XP за генерацию гипотезы"""
    await award_xp(db, user_id, 25, 'hypothesis_generated', 'hypothesis_generator', extra_data={'topic': topic})

async def award_coding_solution(db: Session, user_id: int, problem_id: str, passed: bool) -> None:
    """Начисляет XP за решение задачи по программированию"""
    if passed:
        await award_xp(db, user_id, 60, 'coding_solved', 'coding_interviews', extra_data={'problem_id': problem_id})
    else:
        await award_xp(db, user_id, 10, 'coding_attempt', 'coding_interviews', extra_data={'problem_id': problem_id})

async def award_soft_skills_assessment(db: Session, user_id: int, score: float) -> None:
    """Начисляет XP за прохождение оценки soft skills"""
    await award_xp(db, user_id, 30, 'soft_skills_assessed', 'soft_skills', extra_data={'score': score})