"""Input validation for Telegram bot with enhanced Cyrillic support."""

import re
from typing import Optional, Tuple
from datetime import datetime
from ...core.localization import _


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
            return False, _('validation.name_required')
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Имя слишком короткое (минимум 2 символа)"
        
        if len(name) > 50:
            return False, "Имя слишком длинное (максимум 50 символов)"
        
        # Check for valid characters (Cyrillic, Latin letters, spaces, hyphens)
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$', name):
            return False, _('validation.name_invalid')
        
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
            return False, _('validation.age_number')
        
        if age < 0:
            return False, _('validation.age_invalid')
        
        if age > 18:
            return False, _('validation.age_invalid')
        
        return True, None
    
    @staticmethod
    def validate_emotion_description(description: str) -> Tuple[bool, Optional[str]]:
        """
        Validate emotion description input.
        
        Args:
            description: Emotion description to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not description or not description.strip():
            return False, _('validation.message_required')
        
        description = description.strip()
        
        if len(description) < 10:
            return False, "Описание слишком короткое. Пожалуйста, будьте более подробными."
        
        if len(description) > 1000:
            return False, "Описание слишком длинное. Пожалуйста, сократите до 1000 символов."
        
        return True, None
    
    @staticmethod
    def sanitize_russian_text(text: str) -> str:
        """
        Sanitize Russian text input for processing.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return text
            
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove potentially harmful characters but keep Cyrillic
        text = re.sub(r'[^\w\s\u0430-\u044f\u0410-\u042f\u0451\u0401.,!?;:()\"\'-]', '', text)
        
        return text
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Simple language detection for Russian vs other languages.
        
        Args:
            text: Text to analyze
            
        Returns:
            'ru' for Russian, 'other' for other languages
        """
        if not text:
            return 'other'
        
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r'[\u0430-\u044f\u0410-\u042f\u0451\u0401]', text))
        total_letters = len(re.findall(r'[a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u0401]', text))
        
        if total_letters == 0:
            return 'other'
            
        cyrillic_ratio = cyrillic_count / total_letters
        
        return 'ru' if cyrillic_ratio > 0.5 else 'other'
    
    @staticmethod
    def validate_personality_traits(traits: str) -> Tuple[bool, Optional[str]]:
        """
        Validate personality traits input.
        
        Args:
            traits: Personality traits description
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not traits or not traits.strip():
            return True, None  # Optional field
        
        traits = traits.strip()
        
        if len(traits) > 500:
            return False, "Описание характера слишком длинное (максимум 500 символов)."
        
        return True, None