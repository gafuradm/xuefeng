#!/usr/bin/env python3
# start_services.py
import subprocess
import time
import sys
import os
import signal

def signal_handler(sig, frame):
    print("\n🛑 Получен сигнал остановки...")
    sys.exit(0)

def start_services():
    print("=" * 60)
    print("🚀 Universal AI Teacher - Запуск всех сервисов")
    print("=" * 60)
    
    # Запуск FastAPI (бэкенд обучения)
    print("\n1. Запуск FastAPI (порт 8080)...")
    fastapi_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8080"],
        cwd=os.path.join(os.path.dirname(__file__), "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(2)
    print("   ✅ FastAPI запущен")
    
    # Запуск Flask конференции (порт 8000)
    print("\n2. Запуск Flask конференции (порт 8000)...")
    flask_process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=os.path.join(os.path.dirname(__file__), "conference"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(2)
    print("   ✅ Конференция запущена")
    
    # Запуск фронтенда обучения (порт 8081)
    print("\n3. Запуск фронтенда обучения (порт 8081)...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8081"],
        cwd=os.path.join(os.path.dirname(__file__), "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(1)
    print("   ✅ Фронтенд обучения запущен")
    
    print("\n" + "=" * 60)
    print("📌 ДОСТУПНЫЕ АДРЕСА:")
    print("=" * 60)
    print("   🌐 Обучение (API):        http://localhost:8080")
    print("   🌐 Фронтенд обучения:     http://localhost:8081")
    print("   🎥 Конференция:           http://localhost:8000")
    print("   👨‍🏫 Конференция (учитель): http://localhost:8000/teacher")
    print("   👨‍🎓 Конференция (студент): http://localhost:8000/student")
    print("=" * 60)
    print("\n💡 Для остановки нажмите Ctrl+C\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Остановка всех сервисов...")
        fastapi_process.terminate()
        flask_process.terminate()
        frontend_process.terminate()
        time.sleep(1)
        print("✅ Все сервисы остановлены")
        sys.exit(0)

if __name__ == "__main__":
    start_services()