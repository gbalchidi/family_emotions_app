"""Language definitions and configuration."""

from enum import Enum
from typing import Dict, Any


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    RUSSIAN = "ru"
    
    @classmethod
    def from_code(cls, code: str) -> 'Language':
        """Get language from code."""
        for lang in cls:
            if lang.value == code:
                return lang
        return cls.RUSSIAN  # Default to Russian for target audience
    
    @property
    def display_name(self) -> str:
        """Get display name for the language."""
        names = {
            Language.ENGLISH: "English",
            Language.RUSSIAN: "Русский"
        }
        return names.get(self, "Русский")
    
    @property
    def flag_emoji(self) -> str:
        """Get flag emoji for the language."""
        flags = {
            Language.ENGLISH: "🇺🇸",
            Language.RUSSIAN: "🇷🇺"
        }
        return flags.get(self, "🇷🇺")


# Cultural context mappings for psychology approaches
CULTURAL_CONTEXTS = {
    Language.RUSSIAN: {
        "parenting_style": "authoritative_with_respect",
        "communication_directness": "moderate",
        "emotional_expression": "balanced",
        "family_values": "traditional_modern_blend",
        "psychological_approach": "practical_with_empathy",
        "formality_level": "polite_informal"
    },
    Language.ENGLISH: {
        "parenting_style": "democratic",
        "communication_directness": "high", 
        "emotional_expression": "open",
        "family_values": "individualistic",
        "psychological_approach": "therapeutic",
        "formality_level": "casual"
    }
}