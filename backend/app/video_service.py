# backend/app/video_service.py
import json
from typing import Dict, List
from sqlalchemy.orm import Session
from .models import User, VideoSession, VideoChatMessage
from .deepseek_client import deepseek_client

class VideoService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    async def process_video(self, url: str, original_text: str, translated_text: str) -> VideoSession:
        # Генерируем саммари и ключевые выводы
        summary_data = await self._generate_summary(original_text, translated_text)
        session = VideoSession(
            user_id=self.user.id,
            url=url,
            original_text=original_text,
            translated_text=translated_text,
            summary=summary_data["summary"],
            key_points=summary_data["key_points"]
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    async def _generate_summary(self, original: str, translated: str) -> Dict:
        prompt = f"""
Ты – аналитик. На основе транскрипции видео (оригинал и перевод) составь краткое саммари и выдели 5-7 ключевых выводов, которые можно извлечь из видео.
Оригинал: {original[:3000]}
Перевод: {translated[:3000]}
Верни JSON:
{{
  "summary": "краткое саммари (2-3 предложения)",
  "key_points": ["вывод 1", "вывод 2", ...]
}}
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты аналитик. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=800, temperature=0.5)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        return json.loads(response)

    async def ask_question(self, session_id: int, question: str) -> str:
        session = self.db.query(VideoSession).filter(VideoSession.id == session_id, VideoSession.user_id == self.user.id).first()
        if not session:
            raise ValueError("Сессия не найдена")
        # Добавляем вопрос пользователя в историю
        user_msg = VideoChatMessage(session_id=session_id, role="user", content=question)
        self.db.add(user_msg)
        self.db.commit()
        # Генерируем ответ на основе контекста видео (оригинал + перевод + саммари)
        context = f"Оригинал видео: {session.original_text[:3000]}\nПеревод: {session.translated_text[:3000]}\nСаммари: {session.summary}\nКлючевые выводы: {', '.join(session.key_points)}"
        prompt = f"""
Ты – ассистент, который отвечает на вопросы по содержимому видео.
Контекст видео:
{context}
Вопрос: {question}
Ответь подробно, опираясь только на контекст. Если ответа нет в видео, скажи об этом.
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты ассистент по видео-контенту."},
            {"role": "user", "content": prompt}
        ], max_tokens=500, temperature=0.7)
        # Сохраняем ответ бота
        bot_msg = VideoChatMessage(session_id=session_id, role="assistant", content=response)
        self.db.add(bot_msg)
        self.db.commit()
        return response