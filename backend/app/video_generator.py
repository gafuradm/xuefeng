# backend/app/video_generator.py
import os
import sys
import tempfile
import asyncio
import edge_tts
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import textwrap
import numpy as np
import re
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Отключаем использование внешнего LaTeX, используем встроенный mathtext
rcParams['text.usetex'] = False
rcParams['mathtext.fontset'] = 'stix'  # красивый математический шрифт

class VideoGenerator:
    def __init__(self, output_dir="data/videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Папка со шрифтами (backend/fonts)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
        self.fonts_dir = os.path.join(backend_dir, "fonts")
        print(f"📁 Папка со шрифтами: {self.fonts_dir}")
        print(f"   Существует: {os.path.exists(self.fonts_dir)}")
        
        # Доступные шрифты с их путями
        self.fonts = {}
        self._load_fonts()
        
        # Путь к фоновой музыке
        self.music_path = os.path.join(backend_dir, "data", "music", "background.mp3")
        self.width, self.height = 1920, 1080
        
        # Вывод информации о загруженных шрифтах
        print("✅ Загруженные шрифты:")
        for name, path in self.fonts.items():
            print(f"   {name}: {path}")

    def _load_fonts(self):
        """Загружает все TTF шрифты из папки fonts"""
        if not os.path.exists(self.fonts_dir):
            print(f"⚠️ Папка {self.fonts_dir} не найдена!")
            return
        
        # Ищем все .ttf файлы
        ttf_files = [f for f in os.listdir(self.fonts_dir) if f.endswith('.ttf')]
        for fname in ttf_files:
            # Извлекаем название шрифта без расширения и суффиксов
            base = fname.replace('.ttf', '')
            # Убираем -Regular, -Bold и т.д. для группировки
            family = re.sub(r'-(Regular|Bold|Light|Medium|Black|Thin|Italic|SemiBold|ExtraBold|ExtraLight|Variable.*)$', '', base)
            if family not in self.fonts:
                self.fonts[family] = []
            self.fonts[family].append(os.path.join(self.fonts_dir, fname))
        
        # Если не нашли нужные, добавим fallback на системные
        if not self.fonts:
            print("⚠️ Шрифты не найдены, используем системные")
            self.fonts = {
                'Montserrat': [],
                'Roboto': [],
                'Caveat': []
            }
    
    def get_font(self, size, family='Roboto', weight='Regular'):
        """
        Загружает шрифт по семейству и начертанию.
        weight: 'Regular', 'Bold', 'Light', 'Medium', 'Black', 'Italic' и т.д.
        """
        # Пытаемся найти точное совпадение
        if family in self.fonts:
            for path in self.fonts[family]:
                if weight in os.path.basename(path):
                    try:
                        return ImageFont.truetype(path, size)
                    except Exception as e:
                        print(f"   Не удалось загрузить {path}: {e}")
        
        # Fallback: ищем любой шрифт этого семейства
        if family in self.fonts and self.fonts[family]:
            try:
                return ImageFont.truetype(self.fonts[family][0], size)
            except:
                pass
        
        # Fallback на системные шрифты macOS
        system_fonts = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        for path in system_fonts:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
        
        # Последний fallback
        return ImageFont.load_default()

    async def text_to_speech(self, text: str, output_path: str):
        """Синтез речи с очисткой LaTeX команд"""
        # Удаляем всё между $...$, но оставляем читаемый текст
        clean_text = re.sub(r'\$[^$]+\$', '', text)
        clean_text = re.sub(r'\\[a-z]+(?:\{[^}]*\})?', '', clean_text)
        clean_text = re.sub(r'[{}]', '', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if len(clean_text) < 5:
            clean_text = "Продолжение урока."
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."
        
        try:
            communicate = edge_tts.Communicate(clean_text, "ru-RU-DariyaNeural")
            await communicate.save(output_path)
            if os.path.getsize(output_path) > 1000:
                return output_path
            raise Exception("Empty audio")
        except Exception as e:
            print(f"Edge TTS error: {e}, using gTTS")
            try:
                from gtts import gTTS
                tts = gTTS(text=clean_text, lang='ru')
                tts.save(output_path)
                return output_path
            except:
                return None

    def create_background(self):
        """Градиентный фон"""
        img = Image.new('RGB', (self.width, self.height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        for i in range(self.height):
            r = 26 + int(i * 30 / self.height)
            g = 26 + int(i * 30 / self.height)
            b = 46 + int(i * 40 / self.height)
            draw.rectangle([(0, i), (self.width, i+1)], fill=(r, g, b))
        return img

    def render_latex_to_image(self, expr: str, fontsize=60):
        """
        Рендерит математическое выражение (LaTeX) в PNG с помощью matplotlib.
        Возвращает путь к временному файлу или None.
        """
        try:
            fig = plt.figure(figsize=(8, 2), facecolor='#1a1a2e')
            fig.patch.set_alpha(0)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            # Оборачиваем в $, если нет
            if not expr.startswith('$'):
                expr = f'${expr}$'
            # Используем mathtext (без внешнего LaTeX)
            ax.text(0.5, 0.5, expr, fontsize=fontsize, ha='center', va='center',
                    color='#ffd700', family='serif')
            # Сохраняем с прозрачным фоном, но потом наложим на наш фон
            temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            fig.savefig(temp_path, bbox_inches='tight', facecolor='#1a1a2e', dpi=150, transparent=False)
            plt.close(fig)
            return temp_path
        except Exception as e:
            print(f"Ошибка рендеринга формулы '{expr}': {e}")
            return None

    def create_text_slide(self, text: str, title: str = None):
        """Создаёт слайд с текстом, рендеря формулы из $...$ отдельно"""
        # Разбиваем на части: текст и формулы
        parts = re.split(r'(\$[^$]+\$)', text)
        
        img = self.create_background()
        draw = ImageDraw.Draw(img)
        
        y = 200 if title else 120
        if title:
            font_title = self.get_font(55, family='Montserrat', weight='Bold')
            draw.text((self.width//2, 100), title, fill='#ffd700', font=font_title, anchor='mm')
        
        for part in parts:
            if part.startswith('$') and part.endswith('$'):
                # Рендерим формулу
                formula_img_path = self.render_latex_to_image(part[1:-1], fontsize=50)
                if formula_img_path:
                    formula_img = Image.open(formula_img_path)
                    # Масштабируем, если слишком широко
                    if formula_img.width > self.width - 200:
                        scale = (self.width - 200) / formula_img.width
                        new_w = int(formula_img.width * scale)
                        new_h = int(formula_img.height * scale)
                        formula_img = formula_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    x = (self.width - formula_img.width) // 2
                    img.paste(formula_img, (x, y), formula_img if formula_img.mode == 'RGBA' else None)
                    y += formula_img.height + 20
                    os.unlink(formula_img_path)
                else:
                    # Если не отрендерилось, пишем как текст
                    font = self.get_font(45, family='Roboto', weight='Regular')
                    draw.text((100, y), part, fill='#ffffff', font=font)
                    y += 65
            else:
                # Обычный текст
                if not part.strip():
                    continue
                font = self.get_font(45, family='Roboto', weight='Regular')
                wrapped = textwrap.wrap(part, width=45)
                for line in wrapped:
                    draw.text((100, y), line, fill='#ffffff', font=font)
                    y += 65
        
        draw.rectangle([(50, 50), (self.width-50, self.height-50)], outline='#ffd700', width=2)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        img.save(temp_path)
        return temp_path

    def create_title_slide(self, title: str, subtitle: str = ""):
        """Красивый заглавный слайд с Montserrat"""
        img = self.create_background()
        draw = ImageDraw.Draw(img)
        
        font_title = self.get_font(85, family='Montserrat', weight='Black')
        # Тень
        draw.text((self.width//2 + 4, self.height//2 - 76), title, fill='#000000', font=font_title, anchor='mm')
        draw.text((self.width//2, self.height//2 - 80), title, fill='#ffd700', font=font_title, anchor='mm')
        
        if subtitle:
            font_sub = self.get_font(40, family='Roboto', weight='Light')
            draw.text((self.width//2, self.height//2 + 100), subtitle, fill='#cccccc', font=font_sub, anchor='mm')
        
        draw.rectangle([(50, 50), (self.width-50, self.height-50)], outline='#ffd700', width=3)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        img.save(temp_path)
        return temp_path

    def create_step_slide(self, step_number: int, step_text: str):
        """Слайд шага с декоративным шрифтом Caveat для номера"""
        img = self.create_background()
        draw = ImageDraw.Draw(img)
        
        font_num = self.get_font(60, family='Caveat', weight='Bold')
        draw.text((100, 80), f"Шаг {step_number}", fill='#e94560', font=font_num)
        
        # Проверяем, есть ли формулы в шаге
        if re.search(r'\$[^$]+\$', step_text):
            # Рендерим через create_text_slide, но вставляем только эту строку
            sub_slide = self.create_text_slide(step_text, title=None)
            sub_img = Image.open(sub_slide)
            # Копируем область с текстом (y от 120 до ...)
            img.paste(sub_img, (0, 0))
            os.unlink(sub_slide)
        else:
            font_text = self.get_font(45, family='Roboto', weight='Regular')
            wrapped = textwrap.wrap(step_text, width=50)
            y = 200
            for line in wrapped:
                draw.text((120, y), line, fill='#ffffff', font=font_text)
                y += 65
        
        draw.rectangle([(50, 50), (self.width-50, self.height-50)], outline='#e94560', width=3)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        img.save(temp_path)
        return temp_path

    def add_background_music(self, video_clip, duration):
        if os.path.exists(self.music_path):
            try:
                music = AudioFileClip(self.music_path).volumex(0.15)
                if music.duration < duration:
                    repeats = int(duration / music.duration) + 1
                    music = concatenate_audioclips([music] * repeats)
                music = music.subclip(0, duration)
                if video_clip.audio:
                    final_audio = CompositeAudioClip([video_clip.audio, music])
                else:
                    final_audio = music
                return video_clip.set_audio(final_audio)
            except Exception as e:
                print(f"Музыка не добавлена: {e}")
        return video_clip

    async def generate_video(self, lesson_title: str, theory_text: str,
                             examples: list, tasks_with_solutions: list,
                             output_filename: str) -> str:
        print(f"🎬 Генерация видео: {lesson_title}")
        clips = []
        
        # Интро
        intro = self.create_title_slide(lesson_title, "AI Teacher")
        clips.append(ImageClip(intro, duration=4).resize((self.width, self.height)))
        os.unlink(intro)
        
        # Теория (абзацы)
        paragraphs = [p.strip() for p in theory_text.split('\n') if len(p.strip()) > 30][:8]
        for i, para in enumerate(paragraphs):
            audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            audio_file = await self.text_to_speech(para, audio_path)
            dur = 6
            if audio_file and os.path.getsize(audio_file) > 1000:
                audio = AudioFileClip(audio_file)
                dur = audio.duration + 0.5
            else:
                audio = None
            
            slide = self.create_text_slide(para, title=f"Теория • Часть {i+1}")
            clip = ImageClip(slide, duration=dur).resize((self.width, self.height))
            if audio:
                clip = clip.set_audio(audio)
            clips.append(clip)
            
            os.unlink(slide)
            if audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
        
        # Примеры
        for ex in examples[:3]:
            problem = ex.get('problem', '')
            solution = ex.get('solution', '')
            slide_prob = self.create_text_slide(f"📌 {problem}", title="Пример")
            clips.append(ImageClip(slide_prob, duration=4).resize((self.width, self.height)))
            os.unlink(slide_prob)
            # Шаги решения
            steps = [s.strip() for s in solution.replace('\n', '. ').split('.') if len(s.strip()) > 15][:4]
            for j, step in enumerate(steps):
                step_slide = self.create_step_slide(j+1, step)
                clips.append(ImageClip(step_slide, duration=5).resize((self.width, self.height)))
                os.unlink(step_slide)
        
        # Задачи
        for task in tasks_with_solutions[:4]:
            problem = task.get('problem', '')
            steps = task.get('steps', [])
            answer = task.get('answer', '')
            slide_task = self.create_text_slide(f"✏️ {problem}", title="Задача")
            clips.append(ImageClip(slide_task, duration=5).resize((self.width, self.height)))
            os.unlink(slide_task)
            for j, step in enumerate(steps[:6]):
                step_slide = self.create_step_slide(j+1, step)
                clips.append(ImageClip(step_slide, duration=5).resize((self.width, self.height)))
                os.unlink(step_slide)
            slide_ans = self.create_text_slide(f"✅ Ответ: {answer}", title="Проверка")
            clips.append(ImageClip(slide_ans, duration=3).resize((self.width, self.height)))
            os.unlink(slide_ans)
        
        # Outro
        outro = self.create_title_slide("🎉 Урок завершён!", "До новых встреч!")
        clips.append(ImageClip(outro, duration=4).resize((self.width, self.height)))
        os.unlink(outro)
        
        # Сборка
        final = concatenate_videoclips(clips, method="compose")
        final = self.add_background_music(final, final.duration)
        
        out_path = os.path.join(self.output_dir, output_filename)
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac',
                              verbose=False, logger=None, preset='fast')
        for c in clips:
            c.close()
        final.close()
        return out_path