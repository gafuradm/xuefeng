# backend/app/video_generator.py
import os
import tempfile
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import textwrap

class VideoGenerator:
    def __init__(self, output_dir="data/videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def text_to_speech(self, text: str, lang: str = 'ru') -> str:
        """Создаёт аудио из текста, возвращает путь к файлу"""
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(temp_audio.name)
        return temp_audio.name
    
    def create_slide_image(self, text: str, width: int = 1280, height: int = 720) -> str:
        """Создаёт изображение-слайд с текстом"""
        img = Image.new('RGB', (width, height), color=(30, 30, 60))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except:
                font = ImageFont.load_default()
        
        wrapped = textwrap.wrap(text, width=60)
        y = 100
        for line in wrapped:
            draw.text((100, y), line, fill=(255, 255, 255), font=font)
            y += 45
        
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_img.name)
        return temp_img.name
    
    def generate_video(self, lesson_title: str, theory_text: str, output_filename: str) -> str:
        """Создаёт видео из заголовка и теории"""
        if not theory_text or len(theory_text.strip()) < 50:
            theory_text = "Видео-урок по теме: " + lesson_title
        
        audio_path = self.text_to_speech(theory_text)
        
        title_img = self.create_slide_image(lesson_title)
        slides = []
        
        chunk_size = 300
        for i in range(0, len(theory_text), chunk_size):
            chunk = theory_text[i:i+chunk_size]
            slide_img = self.create_slide_image(chunk)
            slides.append(slide_img)
        
        clips = []
        title_clip = ImageClip(title_img, duration=4).resize((1280, 720))
        clips.append(title_clip)
        
        for slide in slides:
            slide_clip = ImageClip(slide, duration=6).resize((1280, 720))
            clips.append(slide_clip)
        
        video_clip = concatenate_videoclips(clips, method="compose")
        
        audio_clip = AudioFileClip(audio_path)
        if audio_clip.duration > video_clip.duration:
            audio_clip = audio_clip.subclip(0, video_clip.duration)
        else:
            last_clip = clips[-1]
            extra_duration = audio_clip.duration - video_clip.duration
            if extra_duration > 0:
                extra_clip = ImageClip(last_clip.filename, duration=extra_duration).resize((1280, 720))
                video_clip = concatenate_videoclips([video_clip, extra_clip])
        
        final_clip = video_clip.set_audio(audio_clip)
        
        output_path = os.path.join(self.output_dir, output_filename)
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)
        
        os.unlink(audio_path)
        os.unlink(title_img)
        for slide in slides:
            os.unlink(slide)
        
        return output_path