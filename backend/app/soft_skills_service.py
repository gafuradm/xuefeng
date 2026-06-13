# backend/app/soft_skills_service.py

import json
import uuid
from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime
from .models import User, SoftSkillAssessment, SoftSkillResponse, UserPerformance
from .deepseek_client import deepseek_client
import whisper
from gtts import gTTS
from pydub import AudioSegment
import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent.parent   # папка backend

class SoftSkillsInterview:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.audio_dir = BASE_DIR / "static" / "soft_skills_audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
    
    async def start_interview(self, scenario: str = "job_interview") -> Dict:
        """Начинает новое интервью – создаёт сессию, генерирует приветствие бота"""
        session_id = str(uuid.uuid4())
        
        # Системный промпт для бота (инструкция)
        system_prompt = f"""Ты – HR-эксперт, проводящий собеседование на оценку soft skills. Сценарий: {scenario}.
Твоя задача – провести естественное интервью, задавая вопросы и оценивая ответы пользователя.
Оценивай: коммуникабельность, стрессоустойчивость, уверенность, эмоциональный интеллект.
После того как получишь достаточно информации (обычно 3-5 ответов), ты должен завершить интервью.
В конце ты должен дать развёрнутую оценку по каждому критерию и рекомендации.

Важно: 
- Никогда не говори пользователю, что интервью закончилось. 
- В своём последнем сообщении (когда решишь завершить) напиши в самом начале [COMPLETE], а затем сразу итоговый JSON.
Формат итогового сообщения: 
[COMPLETE]{{"communication": число, "stress_resistance": число, "confidence": число, "emotional_intelligence": число, "overall": число, "feedback": "текст", "recommendations": ["рекомендация1", "рекомендация2"]}}

Веди диалог естественно. Всегда отвечай на русском. Первое сообщение – приветствие и первый вопрос."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Генерируем первое сообщение бота
        bot_response = await self._get_bot_response(messages)
        messages.append({"role": "assistant", "content": bot_response})
        
        # Сохраняем сессию
        assessment = SoftSkillAssessment(
            user_id=self.user.id,
            session_id=session_id,
            scenario=scenario,
            status="in_progress",
            messages=messages
        )
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        # Синтезируем голос
        audio_url = await self._text_to_speech(bot_response, assessment.id, 0)
        
        return {
            "session_id": session_id,
            "assessment_id": assessment.id,
            "bot_message": bot_response,
            "audio_url": audio_url,
            "is_completed": False
        }
    
    async def continue_interview(self, assessment_id: int, user_audio_path: str) -> Dict:
        """Продолжает интервью – распознаёт ответ, добавляет в историю, получает ответ бота"""
        assessment = self.db.query(SoftSkillAssessment).filter(SoftSkillAssessment.id == assessment_id).first()
        if not assessment:
            raise ValueError("Assessment not found")
        
        messages = assessment.messages or []
        
        # 1. Распознаём речь
        user_text = await self._speech_to_text(user_audio_path)
        print(f"[DEBUG] Recognized user text: {user_text}")
        
        # 2. Анализируем аудио (уверенность, паузы, громкость)
        analysis = await self._analyze_audio(user_audio_path)
        
        # 3. Добавляем ответ пользователя в историю
        messages.append({"role": "user", "content": user_text, "analysis": analysis})
        
        # 4. Получаем ответ бота (DeepSeek)
        bot_response = await self._get_bot_response(messages)
        
        # 5. Проверяем, не завершил ли бот интервью
        is_completed = False
        final_feedback = None
        if bot_response.startswith("[COMPLETE]"):
            is_completed = True
            json_part = bot_response.replace("[COMPLETE]", "").strip()
            try:
                final_feedback = json.loads(json_part)
            except:
                final_feedback = {"overall": 70, "feedback": "Интервью завершено"}
            # Убираем маркер для отображения
            bot_response = final_feedback.get("feedback", "Спасибо за интервью!")
            # Обновляем сессию
            assessment.status = "completed"
            assessment.completed_at = datetime.utcnow()
            assessment.overall_score = final_feedback.get("overall", 70)
        
        # 6. Добавляем ответ бота в историю
        messages.append({"role": "assistant", "content": bot_response})
        
        # 7. Сохраняем обновлённую историю
        assessment.messages = messages
        self.db.commit()
        
        # 8. Генерируем аудио для ответа бота
        turn = len([m for m in messages if m["role"] == "assistant"]) - 1
        audio_url = await self._text_to_speech(bot_response, assessment_id, turn)
        
        # 9. Сохраняем отдельную запись в SoftSkillResponse для отчётов
        response_record = SoftSkillResponse(
            assessment_id=assessment_id,
            question=messages[-2]["content"] if len(messages) >= 2 else "",
            user_answer_text=user_text,
            user_audio_path=user_audio_path,
            analysis=analysis,
            ai_response_text=bot_response,
            ai_audio_path=audio_url
        )
        self.db.add(response_record)
        self.db.commit()
        
        return {
            "is_completed": is_completed,
            "bot_message": bot_response,
            "audio_url": audio_url,
            "final_feedback": final_feedback
        }
    
    async def _get_bot_response(self, messages: List[Dict]) -> str:
        # Убеждаемся, что системный промпт всегда присутствует
        if not messages or messages[0].get("role") != "system":
            system_prompt = """Ты – HR-эксперт, проводящий собеседование на оценку soft skills. Сценарий: job_interview.
    Твоя задача – вести естественное интервью, задавая вопросы и оценивая ответы пользователя.
    Оценивай: коммуникабельность, стрессоустойчивость, уверенность, эмоциональный интеллект.
    После 3-5 ответов заверши интервью, выдав JSON с итогами.

    В конце (когда решишь завершить) напиши в самом начале [COMPLETE], затем JSON:
    {"communication": число, "stress_resistance": число, "confidence": число, "emotional_intelligence": число, "overall": число, "feedback": "текст", "recommendations": ["рекомендация1", "рекомендация2"]}

    Всегда отвечай на русском. Учитывай всю предыдущую историю диалога."""
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        response = await deepseek_client.chat_completion(messages, max_tokens=500, temperature=0.7)
        return response.strip()

    async def _speech_to_text(self, audio_path: str) -> str:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language="ru")
        return result["text"]
    
    async def _analyze_audio(self, audio_path: str) -> Dict:
        """Анализирует аудио (без librosa)"""
        try:
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_channels(1)
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if np.max(np.abs(samples)) > 0:
                samples = samples / np.max(np.abs(samples))
            
            rms = np.sqrt(np.mean(samples**2))
            volume = min(100, rms * 100)
            
            frame_len = int(audio.frame_rate * 0.05)
            energy = []
            for start in range(0, len(samples) - frame_len, frame_len):
                frame = samples[start:start+frame_len]
                eng = np.sum(frame**2) / frame_len
                energy.append(eng)
            
            if len(energy) > 0:
                threshold = np.percentile(energy, 15)
                silence_frames = [e < threshold for e in energy]
                pause_ratio = sum(silence_frames) / len(energy)
            else:
                pause_ratio = 0
            
            if len(energy) > 1:
                energy_diff = np.diff(energy)
                pitch_variation = min(100, np.std(energy_diff) * 10)
            else:
                pitch_variation = 0
            
            confidence = max(0, min(100, 100 * (1 - pause_ratio) * (volume / 50 if volume < 50 else 1)))
            
            return {
                "duration_seconds": float(round(len(samples)/audio.frame_rate, 1)),
                "volume": float(round(volume, 1)),
                "pause_ratio": float(round(pause_ratio, 2)),
                "pitch_variation": float(round(pitch_variation, 1)),
                "confidence": float(round(confidence, 1))
            }
        except Exception as e:
            print(f"Audio analysis error: {e}")
            return {"duration_seconds": 0, "volume": 50, "pause_ratio": 0.1, "pitch_variation": 50, "confidence": 70}
    
    async def _text_to_speech(self, text: str, assessment_id: int, turn: int) -> str:
        filename = f"assessment_{assessment_id}_turn_{turn}_{uuid.uuid4().hex}.mp3"
        filepath = self.audio_dir / filename
        tts = gTTS(text=text, lang='ru')
        tts.save(str(filepath))
        return f"/static/soft_skills_audio/{filename}"