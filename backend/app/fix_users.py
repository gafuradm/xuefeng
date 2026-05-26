#!/usr/bin/env python3
import re
import shutil
from pathlib import Path

main_py = Path(__file__).parent / "main.py"
backup_py = Path(__file__).parent / "main_backup.py"

if main_py.exists():
    shutil.copy2(main_py, backup_py)
    print(f"✅ Создана резервная копия: {backup_py}")
else:
    print(f"❌ Файл {main_py} не найден!")
    exit(1)

with open(main_py, "r", encoding="utf-8") as f:
    content = f.read()

# Шаг 2: переименовать второй класс User -> UserLegacy и таблицу
match = re.search(r'(#####################################################\s*)+import sys', content)
if match:
    start_second_block = match.start()
    user_match = re.search(r'\bclass User\(Base\):\s*\n\s*__tablename__\s*=\s*"users"', content[start_second_block:])
    if user_match:
        start = start_second_block + user_match.start()
        end = start + user_match.end() - user_match.start()
        content = content[:start] + content[start:end].replace('class User(Base):', 'class UserLegacy(Base):').replace('__tablename__ = "users"', '__tablename__ = "users_legacy"') + content[end:]
        print("✅ Шаг 2: переименован класс User -> UserLegacy, таблица users -> users_legacy")

# Шаги 3-5: исправить foreign keys и relationships
related_classes = ['RefreshToken', 'PasswordReset', 'UserAction', 'UserWord', 'UserTest', 'ChatMessage', 'StudySession', 'InterviewSessionDB']

for cls in related_classes:
    # Замена ForeignKey("users.id") -> ForeignKey("users_legacy.id")
    pattern = r'(' + re.escape(cls) + r'\(Base\):.*?)(user_id\s*=\s*Column\([^)]*ForeignKey\("users\.id"\))'
    content = re.sub(pattern, lambda m: m.group(1) + m.group(2).replace('"users.id"', '"users_legacy.id"'), content, flags=re.DOTALL)
    
    # Замена relationship("User", ...) -> relationship("UserLegacy", ...)
    pattern = r'(' + re.escape(cls) + r'\(Base\):.*?)(user\s*=\s*relationship\("User",)'
    content = re.sub(pattern, lambda m: m.group(1) + m.group(2).replace('"User"', '"UserLegacy"'), content, flags=re.DOTALL)
    
    # Замена back_populates="user" -> back_populates="user_legacy"
    pattern = r'(' + re.escape(cls) + r'\(Base\):.*?)(back_populates\s*=\s*"user")'
    content = re.sub(pattern, lambda m: m.group(1) + 'back_populates="user_legacy"', content, flags=re.DOTALL)

# В самом классе UserLegacy исправить back_populates
content = re.sub(r'(class UserLegacy\(Base\):.*?)(back_populates\s*=\s*"user")', lambda m: m.group(1) + 'back_populates="user_legacy"', content, flags=re.DOTALL)

print("✅ Шаги 3-5: исправлены внешние ключи и связи")

# Шаг 6: заменить User на UserLegacy в эндпоинтах второго блока
endpoint_section = re.search(r'# ==================== ENDPOINTS ====================', content)
if endpoint_section:
    start_endpoints = endpoint_section.start()
    before = content[:start_endpoints]
    after = content[start_endpoints:]
    after = re.sub(r'\bUser\b(?![^"\']*?[\\]?(?:"|\'))', 'UserLegacy', after)
    content = before + after
    print("✅ Шаг 6: заменён User на UserLegacy в эндпоинтах второго блока")
else:
    print("⚠️ Не найден раздел ENDPOINTS, замена User в эндпоинтах не произведена")

# Шаг 8: удаляем дублирующиеся настройки базы данных
duplicate_pattern = r'SQLALCHEMY_DATABASE_URL = "sqlite:///\./hsk_tutor\.db".*?Base = declarative_base\(\)'
content = re.sub(duplicate_pattern, '', content, flags=re.DOTALL)
print("✅ Шаг 8: удалены дублирующиеся настройки базы данных")

# Удалим повторяющийся import sys
content = re.sub(r'import sys\nfrom fastapi import FastAPI.*?\n\s*import sys', 'import sys', content, flags=re.DOTALL)

with open(main_py, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ Файл {main_py} успешно обновлён!")
print("📌 Запустите сервер заново и проверьте регистрацию.")