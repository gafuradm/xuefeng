import os
import json
import tempfile
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment
import whisper
from ..celery import celery_app
from ..deepseek_client import deepseek_client
from ..database import SessionLocal
from ..models import IELTSAttempt

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model

@celery_app.task(bind=True)
def transcribe_and_analyze(self, audio_path: str, task_type: str, user_id: int):
    """Фоновая задача: транскрипция, анализ, сохранение в БД"""
    wav_path = None
    try:
        # Конвертируем в WAV
        wav_path = audio_path + ".wav"
        audio = AudioSegment.from_file(audio_path)
        audio.export(wav_path, format="wav")

        # Транскрипция через Whisper
        model = get_whisper_model()
        result = model.transcribe(wav_path, language="en")
        transcript = result["text"]

        # Анализ аудио (громкость, паузы, скорость)
        samplerate, data = wavfile.read(wav_path)
        if data.dtype == np.int16:
            data = data / 32768.0
        elif data.dtype == np.int32:
            data = data / 2147483648.0
        else:
            data = data.astype(np.float32) / np.max(np.abs(data))

        duration = len(data) / samplerate
        rms = np.sqrt(np.mean(data**2))
        volume_normalized = min(100, rms * 100)

        frame_len = int(samplerate * 0.05)
        hop = frame_len
        energy = []
        for start in range(0, len(data) - frame_len, hop):
            frame = data[start:start+frame_len]
            eng = np.sum(frame**2) / frame_len
            energy.append(eng)

        if len(energy) > 0:
            threshold = np.percentile(energy, 15)
            is_speech = np.array(energy) > threshold
            pause_frames = (~is_speech).sum()
            pause_duration = pause_frames * (frame_len / samplerate)
            pause_ratio = pause_duration / duration if duration > 0 else 0
        else:
            pause_ratio = 0

        words = transcript.split()
        word_count = len(words)
        speaking_rate = (word_count / duration) * 60 if duration > 0 else 0

        if len(energy) > 1:
            energy_diff = np.diff(energy)
            intonation_variation = min(100, np.std(energy_diff) * 10)
        else:
            intonation_variation = 50

        # Промпт для DeepSeek (синхронный вызов)
        prompt = f"""You are an official IELTS examiner. Evaluate the speaking response (Part {task_type}) strictly.

TRANSCRIPT: "{transcript}"

AUDIO METRICS:
- Speaking rate: {speaking_rate:.0f} wpm (target 120-150)
- Pause ratio: {pause_ratio:.2f} (target 0.15-0.25)
- Volume consistency: {volume_normalized:.0f}%
- Intonation variation: {intonation_variation:.0f}%

Evaluate on 7 scales (0-9): task_achievement, fluency_coherence, lexical_resource, grammatical_range_accuracy, pronunciation, intonation, accent_impact.
Return JSON:
{{
  "task_achievement": number,
  "fluency_coherence": number,
  "lexical_resource": number,
  "grammatical_range_accuracy": number,
  "pronunciation": number,
  "intonation": number,
  "accent_impact": number,
  "overall_band": number,
  "feedback": "detailed feedback",
  "suggestions": ["s1","s2","s3"]
}}"""

        ai_response = deepseek_client.chat_completion_sync([
            {"role": "system", "content": "You are an official IELTS examiner. Respond only with JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=1000)

        try:
            evaluation = json.loads(ai_response)
        except:
            evaluation = {
                "task_achievement": 6,
                "fluency_coherence": 6,
                "lexical_resource": 6,
                "grammatical_range_accuracy": 6,
                "pronunciation": 6,
                "intonation": 6,
                "accent_impact": 6,
                "overall_band": 6.0,
                "feedback": "Automatic evaluation",
                "suggestions": ["Practice more"]
            }

        # Сохраняем в БД
        db = SessionLocal()
        attempt = IELTSAttempt(
            user_id=user_id,
            task_type=f"speaking_{task_type}",
            audio_path=wav_path,
            transcript=transcript,
            scores={
                "task_achievement": evaluation["task_achievement"],
                "fluency_coherence": evaluation["fluency_coherence"],
                "lexical_resource": evaluation["lexical_resource"],
                "grammatical_range_accuracy": evaluation["grammatical_range_accuracy"],
                "pronunciation": evaluation["pronunciation"],
                "intonation": evaluation.get("intonation", 6),
                "accent_impact": evaluation.get("accent_impact", 6),
                "speaking_rate_wpm": round(speaking_rate, 1),
                "pause_ratio": round(pause_ratio, 2)
            },
            overall_band=evaluation["overall_band"],
            feedback=evaluation["feedback"],
            suggestions=evaluation["suggestions"]
        )
        db.add(attempt)
        db.commit()
        db.close()

        # Возвращаем результат
        return {
            "task_id": self.request.id,
            "transcript": transcript,
            "scores": attempt.scores,
            "overall_band": attempt.overall_band,
            "feedback": attempt.feedback,
            "suggestions": attempt.suggestions,
            "audio_metrics": {
                "duration_seconds": duration,
                "speaking_rate_wpm": round(speaking_rate, 1),
                "pause_ratio": round(pause_ratio, 2),
                "volume_consistency": round(volume_normalized, 1),
                "intonation_variation": round(intonation_variation, 1)
            }
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Удаляем временные файлы
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)