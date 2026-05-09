# conference/app.py
import os
import sys
import json
import time
import threading
import queue as q
import base64
import hmac
import hashlib
import urllib.parse
import requests
import logging
import re
import numpy as np
import sounddevice as sd
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit
from dotenv import load_dotenv
from collections import Counter, OrderedDict
import signal
import sys
import secrets
import qrcode
import io
import fitz  # PyMuPDF

# Загрузка переменных окружения
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Конфигурация
APPID = os.getenv("XF_APPID", "")
APIKey = os.getenv("XF_API_KEY", "")
APISecret = os.getenv("XF_API_SECRET", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
WS_URL = "ws://ist-api-sg.xf-yun.com/v2/ist"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "conference_secret_key_2024")

# SocketIO с CORS
socketio = SocketIO(app, 
                    cors_allowed_origins=["http://localhost:8080", "http://localhost:8081", "http://localhost:8000"],
                    async_mode='threading',
                    logger=True,
                    engineio_logger=False)

# ================= Глобальные переменные =================
STUDENTS = {}
ATTENDANCE = {}
ACTIVE_SESSION_CODES = {}
VERIFIED_STUDENTS = {}
CONNECTED_CLIENTS = set()
PHRASE_COUNT = 0
CURRENT_SESSION_CODE = None
CODE_EXPIRES_AT = 0

# Для WebRTC
current_teacher_sid = None
TEACHER_ROOM = "teacher_room"
STUDENTS_ROOM = "students_room"

# Для аудио
audio_queue = q.Queue(maxsize=100)
clients_lang = {}
clients_name = {}
FULL_LECTURE_TEXT = []
translation_cache = OrderedDict()
MAX_CACHE = 1000
ws_connection = None
is_running = True

# Для статистики
LAST_SEGMENTS = []
LAST_SEGMENT_TIME = time.time()
REPAIR_CACHE = OrderedDict()
PERF_METRICS = {
    'translation_times': [],
    'recognition_times': [],
    'errors': Counter(),
}

# История лекции
LECTURE_HISTORY = []
LECTURE_INDEX = {}
MAX_HISTORY_SIZE = 10000

# Камера учителя
camera_stream_active = False

# ================= Math Terms Dictionary =================
MATH_TERMS_EN = {
    "plus": "+", "add": "+", "addition": "+",
    "minus": "-", "subtract": "-", "subtraction": "-",
    "times": "×", "multiply": "×", "multiplication": "×",
    "divided by": "÷", "divide": "÷", "division": "÷",
    "equals": "=", "equal": "=",
    "not equal": "≠", "does not equal": "≠",
    "approximately": "≈", "approx": "≈",
    "greater than": ">",
    "less than": "<",
    "greater than or equal": "≥",
    "less than or equal": "≤",
    "squared": "²", "square": "²", "to the power of 2": "²",
    "cubed": "³", "cube": "³", "to the power of 3": "³",
    "square root": "√", "sqrt": "√",
    "integral": "∫",
    "infinity": "∞",
    "sine": "sin", "sin": "sin",
    "cosine": "cos", "cos": "cos",
    "tangent": "tan", "tan": "tan",
    "logarithm": "log", "log": "log",
    "natural log": "ln",
    "pi": "π",
    "degrees": "°",
}

# ================= Вспомогательные функции =================
def add_to_lecture_history(text, text_type='recognition', language='zh', translation=None, speaker='teacher', metadata=None):
    global LECTURE_HISTORY, LECTURE_INDEX
    if not hasattr(add_to_lecture_history, "counter"):
        add_to_lecture_history.counter = 0
    
    entry = {
        'id': add_to_lecture_history.counter,
        'text': text,
        'timestamp': time.time(),
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'speaker': speaker,
        'type': text_type,
        'language': language,
        'translation': translation,
        'metadata': metadata or {}
    }
    
    LECTURE_HISTORY.append(entry)
    LECTURE_INDEX[entry['id']] = entry
    add_to_lecture_history.counter += 1
    
    if len(LECTURE_HISTORY) > MAX_HISTORY_SIZE:
        old_entry = LECTURE_HISTORY.pop(0)
        if old_entry['id'] in LECTURE_INDEX:
            del LECTURE_INDEX[old_entry['id']]
    
    return entry['id']

def float32_to_pcm16(audio):
    if len(audio) == 0:
        return b''
    return (audio * 32767).astype(np.int16).tobytes()

def generate_session_code():
    global CURRENT_SESSION_CODE, CODE_EXPIRES_AT
    timestamp = int(time.time() / 45)
    secret = os.getenv("SESSION_SECRET", "lecture_secret_2024")
    CURRENT_SESSION_CODE = hashlib.sha256(f"{secret}_{timestamp}".encode()).hexdigest()[:6].upper()
    CODE_EXPIRES_AT = time.time() + 45
    ACTIVE_SESSION_CODES.clear()
    ACTIVE_SESSION_CODES[CURRENT_SESSION_CODE] = {"expires": CODE_EXPIRES_AT, "used_by": []}
    return CURRENT_SESSION_CODE

def verify_student_code(student_id, code):
    code = code.upper().strip()
    if code not in ACTIVE_SESSION_CODES:
        return False, "Code expired or invalid"
    code_data = ACTIVE_SESSION_CODES[code]
    if time.time() > code_data["expires"]:
        del ACTIVE_SESSION_CODES[code]
        return False, "Code expired"
    if student_id in code_data["used_by"]:
        return True, "Already verified"
    code_data["used_by"].append(student_id)
    VERIFIED_STUDENTS[student_id] = {"verified": True, "verified_at": time.time(), "session_code": code, "expires_at": code_data["expires"] + 3600}
    return True, "Verification successful"

def build_auth_url():
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    host = "ist-api-sg.xf-yun.com"
    path = "/v2/ist"
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_hmac = hmac.new(APISecret.encode('utf-8'), signature_origin.encode('utf-8'), hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_hmac).decode('utf-8')
    authorization_origin = f'api_key="{APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    url_params = {"host": host, "date": date, "authorization": authorization}
    query_string = urllib.parse.urlencode(url_params)
    return f"ws://{host}{path}?{query_string}"

def deepseek_translate(text, target_lang):
    if not DEEPSEEK_API_KEY:
        return f"[Translation: {text}]"
    
    lang_names = {"en": "English", "ru": "Russian", "kk": "Kazakh", "de": "German", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
    target_lang_name = lang_names.get(target_lang, target_lang)
    
    # ИЗМЕНЁННЫЙ ПРОМПТ - только перевод, без лишних слов
    prompt = f"""Translate the following text to {target_lang_name}. 
Return ONLY the translated text, nothing else. No explanations, no comments, no additional words.

Text: {text}

Translation:"""
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    body = {
        "model": "deepseek-chat", 
        "messages": [
            {"role": "system", "content": "You are a translator. Return ONLY the translation, no additional text."},
            {"role": "user", "content": prompt}
        ], 
        "max_tokens": 1024, 
        "temperature": 0.1  # снижаем температуру для более точного перевода
    }
    
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        translated = resp.json()["choices"][0]["message"]["content"].strip()
        
        # Удаляем возможные кавычки и лишние пробелы
        if translated.startswith('"') and translated.endswith('"'):
            translated = translated[1:-1]
        if translated.startswith("'") and translated.endswith("'"):
            translated = translated[1:-1]
        
        return translated
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text
    
# ================= WebSocket обработчики =================
def on_message(ws, message):
    global PHRASE_COUNT, LAST_SEGMENT_TIME, LAST_SEGMENTS
    try:
        data = json.loads(message)
        if data.get('code') == 0:
            result_data = data.get('data', {})
            result = result_data.get('result', {})
            if result and 'ws' in result:
                text_parts = []
                for ws_item in result['ws']:
                    for cw in ws_item.get('cw', []):
                        text_parts.append(cw.get('w', ''))
                text = ''.join(text_parts)
                status = result_data.get('status')
                is_final = (status == 2)
                
                if text and len(text.strip()) > 0:
                    add_to_lecture_history(text=text, text_type='recognition_final' if is_final else 'recognition_interim', language='zh', speaker='teacher')
                
                if text and len(text.strip()) > 0 and clients_lang:
                    for sid, lang in list(clients_lang.items()):
                        try:
                            translated = deepseek_translate(text, lang)
                            socketio.emit("new_translation", {"original": text, "translation": translated, "is_final": is_final}, to=sid)
                        except Exception as e:
                            logger.error(f"Translation error for {sid}: {e}")
                
                if is_final:
                    FULL_LECTURE_TEXT.append(text)
                    PHRASE_COUNT += 1
                    emit_stats()
    except Exception as e:
        logger.error(f"Message handling error: {e}")

def on_error(ws, error):
    logger.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.info(f"WebSocket closed: {close_msg}")

def on_open(ws):
    global ws_connection
    logger.info("✅ WebSocket connected")
    ws_connection = ws
    init_params = {"common": {"app_id": APPID}, "business": {"language": "zh_cn", "domain": "ist_ed", "accent": "mandarin", "punc": 1}, "data": {"status": 0, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": ""}}
    ws.send(json.dumps(init_params))

# ================= Аудио захват =================
def audio_callback(indata, frames, time_info, status):
    if is_running:
        try:
            audio_queue.put(indata.copy().flatten(), timeout=0.1)
        except q.Full:
            pass

def audio_thread():
    try:
        with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=2048, callback=audio_callback):
            while is_running:
                time.sleep(0.1)
    except Exception as e:
        logger.error(f"Audio error: {e}")

def ws_thread():
    global ws_connection, is_running
    while is_running:
        try:
            import websocket
            ws = websocket.WebSocketApp(build_auth_url(), on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
            wst = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10})
            wst.daemon = True
            wst.start()
            time.sleep(1)
            while is_running:
                try:
                    if not ws.sock or not ws.sock.connected:
                        break
                    chunk = audio_queue.get(timeout=0.1)
                    if len(chunk) > 0:
                        chunk_pcm16 = float32_to_pcm16(chunk)
                        ws.send(json.dumps({"data": {"status": 1, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": base64.b64encode(chunk_pcm16).decode("utf-8")}}))
                except q.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Audio sending error: {e}")
                    break
            if is_running:
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            if is_running:
                time.sleep(1)

def emit_stats():
    socketio.emit("stats", {"connected": len(CONNECTED_CLIENTS), "phrases": PHRASE_COUNT})

# ================= Socket.IO обработчики =================
@socketio.on("connect")
def handle_connect():
    sid = request.sid
    CONNECTED_CLIENTS.add(sid)
    ATTENDANCE[sid] = {"join_time": time.time(), "active": 0, "inactive": 0, "last_seen": time.time(), "verified": False, "student_id": None}
    join_room(STUDENTS_ROOM, sid=sid)
    if current_teacher_sid is not None:
        socketio.emit("screen_share_started", to=sid)
    emit_stats()

@socketio.on("disconnect")
def handle_disconnect():
    global current_teacher_sid
    sid = request.sid
    leave_room(STUDENTS_ROOM, sid=sid)
    leave_room(TEACHER_ROOM, sid=sid)
    CONNECTED_CLIENTS.discard(sid)
    if sid in ATTENDANCE:
        del ATTENDANCE[sid]
    if current_teacher_sid == sid:
        current_teacher_sid = None
        for student_sid in CONNECTED_CLIENTS:
            socketio.emit("screen_share_stopped", to=student_sid)
    emit_stats()

@socketio.on("set_language")
def handle_set_language(data):
    sid = request.sid
    lang = data.get("lang", "en")
    clients_lang[sid] = lang
    logger.info(f"Client {sid[:8]} set language to {lang}")
    socketio.emit("language_set", {"lang": lang}, to=sid)

@socketio.on("set_name")
def handle_set_name(data):
    sid = request.sid
    name = data.get("name", "")
    if name:
        clients_name[sid] = name
        logger.info(f"Client {sid[:8]} set name to {name}")

@socketio.on("send_message")
def handle_send_message(data):
    sid = request.sid
    message = data.get('message', '')
    if not message:
        return
    sender_lang = clients_lang.get(sid, 'en')
    sender_name = clients_name.get(sid, 'Учитель' if sid == current_teacher_sid else 'Студент')
    
    add_to_lecture_history(text=message, text_type='chat', language=sender_lang, 
                           speaker=sender_name, translation=None)
    
    for target_sid, target_lang in clients_lang.items():
        if target_sid == sid:
            socketio.emit('chat_message', {
                'sender': 'me',
                'original': message,
                'translated': message,
                'language': target_lang
            }, to=target_sid)
        else:
            try:
                translated = deepseek_translate(message, target_lang)
                socketio.emit('chat_message', {
                    'sender': sender_name,
                    'original': message,
                    'translated': translated,
                    'language': target_lang
                }, to=target_sid)
            except Exception as e:
                logger.error(f"Chat translation error: {e}")
                socketio.emit('chat_message', {
                    'sender': sender_name,
                    'original': message,
                    'translated': f"[Translation error] {message}",
                    'language': target_lang
                }, to=target_sid)

@socketio.on("request_verification")
def handle_verification_request():
    socketio.emit("verification_required", {"message": "Attendance confirmation required", "timeout": 45}, to=request.sid)

@socketio.on("verify_code")
def handle_code_verification(data):
    if not CURRENT_SESSION_CODE or time.time() > CODE_EXPIRES_AT:
        generate_session_code()
    sid = request.sid
    code = data.get("code", "").strip().upper()
    student_id = data.get("student_id")
    if not student_id:
        socketio.emit("verification_result", {"success": False, "message": "student_id_required", "requires_id": True}, to=sid)
        return
    success, message = verify_student_code(student_id, code)
    if success:
        if sid not in ATTENDANCE:
            ATTENDANCE[sid] = {}
        ATTENDANCE[sid]["student_id"] = student_id
        ATTENDANCE[sid]["verified"] = True
    socketio.emit("verification_result", {"success": success, "message": message, "requires_id": False}, to=sid)

@socketio.on("start_screen_share")
def handle_start_screen_share():
    global current_teacher_sid
    sid = request.sid
    if current_teacher_sid is not None and current_teacher_sid != sid:
        socketio.emit("screen_share_error", {"message": "Другой учитель уже транслирует экран"}, to=sid)
        return
    current_teacher_sid = sid
    join_room(TEACHER_ROOM, sid=sid)
    for student_sid in CONNECTED_CLIENTS:
        if student_sid != sid:
            socketio.emit("screen_share_started", to=student_sid)

@socketio.on("stop_screen_share")
def handle_stop_screen_share():
    global current_teacher_sid
    sid = request.sid
    if current_teacher_sid == sid:
        current_teacher_sid = None
        leave_room(TEACHER_ROOM, sid=sid)
        for student_sid in CONNECTED_CLIENTS:
            if student_sid != sid:
                socketio.emit("screen_share_stopped", to=student_sid)

@socketio.on("student_active")
def handle_student_active(data):
    sid = request.sid
    if sid in ATTENDANCE:
        ATTENDANCE[sid]["last_seen"] = time.time()
        ATTENDANCE[sid]["active"] = ATTENDANCE[sid].get("active", 0) + 5
        if data.get("student_id"):
            ATTENDANCE[sid]["student_id"] = data.get("student_id")

@socketio.on("get_full_lecture_history")
def handle_get_full_history(data):
    sid = request.sid
    student_id = data.get("student_id")
    if not student_id or student_id not in VERIFIED_STUDENTS:
        socketio.emit("history_error", {"error": "Not verified"}, to=sid)
        return
    history_formatted = [{'time': entry['datetime'], 'text': entry['text'], 'translation': entry.get('translation', ''), 'type': entry['type']} for entry in LECTURE_HISTORY[-500:]]
    socketio.emit("full_lecture_history", {"history": history_formatted, "total": len(LECTURE_HISTORY)}, to=sid)

@socketio.on("camera_toggled")
def handle_camera_toggle(data):
    global camera_stream_active
    sid = request.sid
    if sid != current_teacher_sid:
        return
    camera_stream_active = data.get('enabled', False)
    for student_sid in CONNECTED_CLIENTS:
        if student_sid != sid:
            socketio.emit('camera_state', {'enabled': camera_stream_active}, to=student_sid)

# ================= Маршруты Flask =================
@app.route("/")
def index():
    return render_template("teacher.html")

@app.route("/teacher")
def teacher():
    return render_template("teacher.html")

@app.route("/student")
def student():
    return render_template("student.html")

@app.route("/api/current_code")
def api_current_code():
    if not CURRENT_SESSION_CODE or time.time() > CODE_EXPIRES_AT:
        generate_session_code()
    return jsonify({"code": CURRENT_SESSION_CODE, "expires_in": int(CODE_EXPIRES_AT - time.time())})

@app.route("/api/verified_students")
def api_verified_students():
    verified_list = [{"id": sid, "name": f"Student_{sid[-4:]}", "time": datetime.fromtimestamp(data["verified_at"]).strftime("%H:%M:%S")} for sid, data in VERIFIED_STUDENTS.items()]
    return jsonify({"students": verified_list, "count": len(verified_list)})

@app.route("/api/screen_share_status")
def api_screen_share_status():
    return jsonify({"active": current_teacher_sid is not None})

@app.route("/api/assistant", methods=["POST"])
def assistant_query():
    data = request.json
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400
    
    context = "\n".join([entry.get('translation', entry['text']) for entry in LECTURE_HISTORY[-20:]])
    
    prompt = f"""
Ты Xiao Shu, умный ассистент по математике.
Контекст лекции: {context}
Вопрос студента: {query}
Дай краткий, понятный ответ (не более 3-4 предложений).
"""
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", 
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0.5},
            timeout=15
        )
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        return jsonify({"answer": answer, "status": "success"})
    except Exception as e:
        return jsonify({"answer": "Xiao Shu временно недоступен", "status": "error"})

# ================= WebRTC сигналинг =================
@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    student_sid = None
    for sid, att in ATTENDANCE.items():
        if att.get('student_id') == data.get('studentId') and att.get('verified'):
            student_sid = sid
            break
    if student_sid:
        socketio.emit('webrtc_offer', data, to=student_sid)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    if current_teacher_sid:
        socketio.emit('webrtc_answer', data, to=current_teacher_sid)

@socketio.on('webrtc_ice_candidate')
def handle_ice_candidate(data):
    target = data.get('target', 'teacher')
    if target == 'teacher' and current_teacher_sid:
        socketio.emit('webrtc_ice_candidate', data, to=current_teacher_sid)
    else:
        student_sid = None
        for sid, att in ATTENDANCE.items():
            if att.get('student_id') == data.get('studentId') and att.get('verified'):
                student_sid = sid
                break
        if student_sid:
            socketio.emit('webrtc_ice_candidate', data, to=student_sid)

@socketio.on('join_teacher_room')
def handle_join_teacher_room(data):
    join_room('teacher_room')

@socketio.on('join_student_room')
def handle_join_student_room(data):
    join_room('teacher_room')

@socketio.on('request_webrtc_restart')
def handle_webrtc_restart(data):
    if current_teacher_sid:
        socketio.emit('request_webrtc_restart', {'studentId': data.get('studentId')}, to=current_teacher_sid)

@socketio.on('whiteboard_draw')
def handle_whiteboard_draw(data):
    room = data.get('room', 'teacher_room')
    # Отправляем всем кроме отправителя? Но мы отправляем всем в комнате
    socketio.emit('whiteboard_draw', data, to=room, skip_sid=request.sid)

@socketio.on('whiteboard_clear')
def handle_whiteboard_clear(data):
    room = data.get('room', 'teacher_room')
    socketio.emit('whiteboard_clear', data, to=room, skip_sid=request.sid)

@socketio.on('whiteboard_page_added')
def handle_whiteboard_page_added(data):
    room = data.get('room', 'teacher_room')
    socketio.emit('whiteboard_page_added', data, to=room, skip_sid=request.sid)

@socketio.on('whiteboard_change_page')
def handle_whiteboard_change_page(data):
    room = data.get('room', 'teacher_room')
    socketio.emit('whiteboard_change_page', data, to=room, skip_sid=request.sid)

# ================= Запуск =================
if __name__ == "__main__":
    generate_session_code()
    
    threading.Thread(target=audio_thread, daemon=True).start()
    threading.Thread(target=ws_thread, daemon=True).start()
    
    logger.info("🎥 Conference server starting on port 8000...")
    socketio.run(app, host="0.0.0.0", port=8000, debug=False, allow_unsafe_werkzeug=True)