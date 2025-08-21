"""Message templates for the Telegram bot."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Messages:
    """Bot message templates."""
    
    # Welcome & Onboarding
    WELCOME = """
👋 Привет! Я Family Emotions Bot.

Я помогу вам лучше понимать эмоции вашего ребенка и находить правильные слова в сложных ситуациях.

🎯 Что я умею:
• Переводить детские эмоции на "взрослый" язык
• Проводить ежедневные чек-ины
• Давать персонализированные советы

Давайте начнем с знакомства! Как вас зовут?
"""
    
    ONBOARDING_NAME_RECEIVED = """
Приятно познакомиться, {name}! 

Расскажите о ваших детях. Сколько у вас детей?
"""
    
    ONBOARDING_CHILD_NAME = """
Как зовут {number} ребенка?
"""
    
    ONBOARDING_CHILD_AGE = """
Сколько лет {name}?
"""
    
    ONBOARDING_PROBLEMS = """
Отлично! Теперь выберите области, где чаще всего возникают сложности:

Выберите одну или несколько областей из списка ниже.
"""
    
    ONBOARDING_COMPLETE = """
✅ Спасибо, {name}!

Теперь я знаю вашу семью:
{children_info}

Я буду учитывать эту информацию в своих советах.

Готовы начать? Выберите, что вы хотите сделать:
"""