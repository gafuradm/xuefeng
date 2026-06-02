# backend/seed_supervisors.py
from app.database import SessionLocal
from app.models import Supervisor
import json

def seed():
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже записи
        if db.query(Supervisor).count() > 0:
            print("Руководители уже есть, пропускаем сидинг")
            return
        
        supervisors_data = [
            {
                "name": "Иванов Иван Иванович",
                "email": "ivanov@university.ru",
                "department": "Кафедра искусственного интеллекта",
                "university": "МГУ",
                "position": "Профессор",
                "research_areas": ["машинное обучение", "глубокое обучение", "компьютерное зрение"],
                "keywords": ["ML", "CV", "Neural Networks"],
                "publications_summary": "Более 100 публикаций в ведущих журналах, индекс Хирша 35",
                "bio": "Заведует лабораторией AI, руководит 5 аспирантами",
                "avatar_url": "https://randomuser.me/api/portraits/men/1.jpg"
            },
            {
                "name": "Петрова Мария Сергеевна",
                "email": "petrova@university.ru",
                "department": "Кафедра биоинформатики",
                "university": "СПбГУ",
                "position": "Доцент",
                "research_areas": ["биоинформатика", "геномика", "анализ медицинских данных"],
                "keywords": ["bioinformatics", "genomics", "healthcare AI"],
                "publications_summary": "50+ публикаций, редактор в журнале Bioinformatics",
                "bio": "Член международного общества вычислительной биологии",
                "avatar_url": "https://randomuser.me/api/portraits/women/2.jpg"
            },
            {
                "name": "Сидоров Алексей Викторович",
                "email": "sidorov@university.ru",
                "department": "Кафедра прикладной математики",
                "university": "НГУ",
                "position": "Профессор",
                "research_areas": ["численные методы", "математическое моделирование", "физика плазмы"],
                "keywords": ["numerical analysis", "plasma physics"],
                "publications_summary": "200+ публикаций, ведущий учёный в области плазмы",
                "bio": "Лауреат премии Правительства РФ в области науки",
                "avatar_url": "https://randomuser.me/api/portraits/men/3.jpg"
            }
        ]
        
        for data in supervisors_data:
            sup = Supervisor(**data)
            db.add(sup)
        
        db.commit()
        print(f"Добавлено {len(supervisors_data)} руководителей")
    finally:
        db.close()

if __name__ == "__main__":
    seed()