"""Translation system for the Family Emotions Bot."""

import logging
from typing import Dict, Optional, Any, Union
from pathlib import Path
import json

from .languages import Language, CULTURAL_CONTEXTS

logger = logging.getLogger(__name__)


class Translator:
    """Main translator class for the bot."""
    
    def __init__(self):
        self._translations: Dict[Language, Dict[str, Any]] = {}
        self._current_language = Language.RUSSIAN  # Default to Russian
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files."""
        translations_dir = Path(__file__).parent / "translations"
        
        for lang in Language:
            translation_file = translations_dir / f"{lang.value}.json"
            if translation_file.exists():
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        self._translations[lang] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load translations for {lang.value}: {e}")
                    self._translations[lang] = {}
            else:
                logger.warning(f"Translation file not found: {translation_file}")
                self._translations[lang] = {}
    
    def set_language(self, language: Union[Language, str]):
        """Set the current language."""
        if isinstance(language, str):
            language = Language.from_code(language)
        self._current_language = language
        logger.info(f"Language set to: {language.value}")
    
    def get_language(self) -> Language:
        """Get current language."""
        return self._current_language
    
    def translate(self, key: str, language: Optional[Language] = None, **kwargs) -> str:
        """
        Translate a key to the current or specified language.
        
        Args:
            key: Translation key in dot notation (e.g., 'welcome.title')
            language: Optional language override
            **kwargs: Parameters for string formatting
        
        Returns:
            Translated string
        """
        lang = language or self._current_language
        
        # Get translation from nested dictionary
        translation = self._get_nested_value(
            self._translations.get(lang, {}), 
            key
        )
        
        # Fallback to Russian if not found in current language
        if translation is None and lang != Language.RUSSIAN:
            translation = self._get_nested_value(
                self._translations.get(Language.RUSSIAN, {}), 
                key
            )
        
        # Final fallback to the key itself
        if translation is None:
            logger.warning(f"Translation not found for key: {key}")
            translation = key
        
        # Format with parameters if provided
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.error(f"Translation formatting error for key {key}: {e}")
        
        return translation
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        """Get value from nested dictionary using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_cultural_context(self, language: Optional[Language] = None) -> Dict[str, str]:
        """Get cultural context for the current or specified language."""
        lang = language or self._current_language
        return CULTURAL_CONTEXTS.get(lang, CULTURAL_CONTEXTS[Language.RUSSIAN])
    
    def pluralize_ru(self, count: int, forms: tuple) -> str:
        """
        Russian pluralization helper.
        
        Args:
            count: Number for pluralization
            forms: Tuple of (singular, few, many) forms
            
        Returns:
            Correct plural form
        """
        if len(forms) != 3:
            return forms[0]
        
        if count % 10 == 1 and count % 100 != 11:
            return forms[0]  # 1, 21, 31, etc.
        elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
            return forms[1]  # 2-4, 22-24, 32-34, etc.
        else:
            return forms[2]  # 5-20, 25-30, etc.


# Global translator instance
_translator = Translator()


def _(key: str, language: Optional[Language] = None, **kwargs) -> str:
    """Shorthand function for translation."""
    return _translator.translate(key, language, **kwargs)


def set_language(language: Union[Language, str]):
    """Set the global language."""
    _translator.set_language(language)


def get_language() -> Language:
    """Get the current global language."""
    return _translator.get_language()


def get_cultural_context(language: Optional[Language] = None) -> Dict[str, str]:
    """Get cultural context for psychology approach."""
    return _translator.get_cultural_context(language)


def pluralize_ru(count: int, forms: tuple) -> str:
    """Russian pluralization helper."""
    return _translator.pluralize_ru(count, forms)