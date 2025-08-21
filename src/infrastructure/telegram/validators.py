"""Input validation for Telegram bot."""

import re
from typing import Optional, Tuple
from datetime import datetime


class InputValidator:
    """Validates user input."""
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate person name.
        
        Args:
            name: Name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, "Имя не может быть пустым"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Имя слишком короткое (минимум 2 символа)"
        
        if len(name) > 50:
            return False, "Имя слишком длинное (максимум 50 символов)"
        
        # Check for valid characters (letters, spaces, hyphens)
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-]+$', name):
            return False, "Имя может содержать только буквы, пробелы и дефисы"
        
        return True, None
    
    @staticmethod
    def validate_age(age_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate child age.
        
        Args:
            age_str: Age string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            age = int(age_str.strip())
        except (ValueError, AttributeError):
            return False, "Возраст должен быть числом"
        
        if age < 1:
            return False, "Возраст должен быть больше 0"
        
        if age > 18:
            return False, "Этот бот предназначен для детей до 18 лет"
        
        return True, None