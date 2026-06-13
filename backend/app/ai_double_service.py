# backend/app/ai_double_service.py

import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .models import User, AIDouble, AIDoubleAction, Role, UserRating, UserAchievement
from .deepseek_client import deepseek_client
from datetime import datetime

class AIDoubleService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.ai_double = user.ai_double
    
    async def get_or_create_ai_double(self) -> AIDouble:
        if not self.ai_double:
            self.ai_double = AIDouble(
                user_id=self.user.id,
                name=f"AI Двойник {self.user.name}",
                is_active=True
            )
            self.db.add(self.ai_double)
            self.db.commit()
            self.db.refresh(self.ai_double)
        return self.ai_double
    
    async def process_command(self, command: str) -> str:
        """Обрабатывает команду пользователя через AI-двойника"""
        # Собираем контекст
        context = await self._get_context()
        
        prompt = f"""
Ты – AI-двойник пользователя {self.user.name}. Твоя задача – помогать пользователю, управлять платформой, отвечать на вопросы, анализировать данные.

Твой профиль:
- У тебя есть права: can_manage_roles={self.ai_double.can_manage_roles}, can_view_all_data={self.ai_double.can_view_all_data}, can_assign_achievements={self.ai_double.can_assign_achievements}
- Ты можешь выполнять следующие действия:
  * "показать статистику пользователя [id]"
  * "изменить роль [username] на [role]"
  * "выдать достижение [user_id] за [reason]"
  * "забанить пользователя [username]"
  * "создать отчёт по рейтингу"
  * "показать топ-10 по роли [role]"
  * "управлять платформой" – открыть панель администрирования

Контекст платформы:
{context}

Команда пользователя: {command}

Ответь понятным русским языком. Если команда требует выполнения действия (например, изменение роли), верни JSON в формате:
{{"action": "change_role", "username": "...", "role": "...", "reason": "..."}}
Или просто текстовый ответ, если действие не требуется.

Верни ТОЛЬКО ответ (текст или JSON).
"""
        response = await deepseek_client.chat_completion([
            {"role": "system", "content": "Ты AI-двойник. Отвечай полезно и точно."},
            {"role": "user", "content": prompt}
        ], max_tokens=1000, temperature=0.5)
        
        # Проверяем, не является ли ответ JSON-командой
        response = response.strip()
        if response.startswith("{") and "action" in response:
            try:
                cmd = json.loads(response)
                result = await self._execute_action(cmd)
                return result
            except:
                pass
        return response
    
    async def _get_context(self) -> str:
        """Собирает контекст платформы"""
        total_users = self.db.query(User).count()
        total_roles = self.db.query(Role).count()
        # Дополнительная статистика
        return f"""
Всего пользователей: {total_users}
Всего ролей: {total_roles}
Пользователь имеет права администратора: {self.ai_double.can_view_all_data}
"""
    
    async def _execute_action(self, cmd: Dict) -> str:
        action = cmd.get("action")
        if action == "change_role":
            username = cmd.get("username")
            role_name = cmd.get("role")
            user = self.db.query(User).filter(User.username == username).first()
            if not user:
                return f"Пользователь {username} не найден"
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                return f"Роль {role_name} не найдена"
            if role in user.roles:
                return f"У пользователя {username} уже есть роль {role_name}"
            user.roles.append(role)
            self.db.commit()
            # Логируем действие
            log = AIDoubleAction(
                ai_double_id=self.ai_double.id,
                action_type="change_role",
                target_user_id=user.id,
                details={"new_role": role_name}
            )
            self.db.add(log)
            self.db.commit()
            return f"Роль {role_name} добавлена пользователю {username}"
        elif action == "ban_user":
            username = cmd.get("username")
            user = self.db.query(User).filter(User.username == username).first()
            if not user:
                return f"Пользователь {username} не найден"
            user.is_active = False
            self.db.commit()
            log = AIDoubleAction(
                ai_double_id=self.ai_double.id,
                action_type="ban_user",
                target_user_id=user.id
            )
            self.db.add(log)
            self.db.commit()
            return f"Пользователь {username} заблокирован"
        # Добавить другие действия
        return "Действие не распознано"