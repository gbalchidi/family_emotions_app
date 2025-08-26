"""Message templates for the Telegram bot."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from ...core.localization import _


@dataclass
class Messages:
    """Bot message templates."""
    
    # Welcome & Onboarding - Now using localization
    @property
    def WELCOME(self):
        return _('welcome.title') + "\n\n" + _('welcome.description')
    
    def ONBOARDING_NAME_RECEIVED(self, name: str):
        return f"Приятно познакомиться, {name}!\n\nРасскажите о ваших детях. Сколько у вас детей?"
    
    def ONBOARDING_CHILD_NAME(self, number: str):
        return f"Как зовут {number} ребенка?"
    
    def ONBOARDING_CHILD_AGE(self, name: str):
        return f"Сколько лет {name}?"
    
    @property
    def ONBOARDING_PROBLEMS(self):
        return "Отлично! Теперь выберите области, где чаще всего возникают сложности:\n\nВыберите одну или несколько областей из списка ниже."
    
    def ONBOARDING_COMPLETE(self, name: str, children_info: str):
        return f"✅ Спасибо, {name}!\n\nТеперь я знаю вашу семью:\n{children_info}\n\nЯ буду учитывать эту информацию в своих советах.\n\nГотовы начать? Выберите, что вы хотите сделать:"