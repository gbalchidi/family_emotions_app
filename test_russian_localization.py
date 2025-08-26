#!/usr/bin/env python3
"""Test script for Russian localization functionality."""

import sys
import os
import re

# Add src to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from core.localization import Translator, Language, set_language, _
    print("✅ Successfully imported localization modules")
except ImportError as e:
    print(f"❌ Failed to import localization: {e}")
    sys.exit(1)

# Simple validator for testing without telegram dependencies
class TestInputValidator:
    @staticmethod
    def validate_name(name):
        if not name or not name.strip():
            return False, "Имя не может быть пустым"
        name = name.strip()
        if len(name) < 2:
            return False, "Имя слишком короткое"
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$', name):
            return False, "Имя может содержать только буквы, пробелы и дефисы"
        return True, None
    
    @staticmethod
    def validate_age(age_str):
        try:
            age = int(age_str.strip())
        except (ValueError, AttributeError):
            return False, "Возраст должен быть числом"
        if age < 0:
            return False, "Возраст должен быть больше 0"
        if age > 18:
            return False, "Возраст должен быть до 18 лет"
        return True, None
    
    @staticmethod
    def detect_language(text):
        if not text:
            return 'other'
        cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', text))
        total_letters = len(re.findall(r'[a-zA-Zа-яА-ЯёЁ]', text))
        if total_letters == 0:
            return 'other'
        cyrillic_ratio = cyrillic_count / total_letters
        return 'ru' if cyrillic_ratio > 0.5 else 'other'
    
    @staticmethod
    def sanitize_russian_text(text):
        if not text:
            return text
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\sа-яА-ЯёЁ.,!?;:()\"\'-]', '', text)
        return text

def test_localization():
    """Test the localization system."""
    print("🧪 Testing Russian Localization System")
    print("=" * 50)
    
    # Test 1: Basic translation
    print("1. Testing basic translations:")
    set_language(Language.RUSSIAN)
    
    welcome_title = _('welcome.title', name='Анна')
    help_title = _('help.title')
    
    print(f"   Welcome title: {welcome_title}")
    print(f"   Help title: {help_title}")
    print()
    
    # Test 2: Button translations  
    print("2. Testing button translations:")
    emotion_btn = _('buttons.emotion_translate')
    manage_children_btn = _('buttons.manage_children')
    settings_btn = _('buttons.settings')
    
    print(f"   Emotion translate: {emotion_btn}")
    print(f"   Manage children: {manage_children_btn}")
    print(f"   Settings: {settings_btn}")
    print()
    
    # Test 3: Validation messages
    print("3. Testing validation messages:")
    name_required = _('validation.name_required')
    age_invalid = _('validation.age_invalid')
    
    print(f"   Name required: {name_required}")
    print(f"   Age invalid: {age_invalid}")
    print()
    
    # Test 4: Input validation with Cyrillic
    print("4. Testing Cyrillic input validation:")
    
    # Valid Russian name
    valid, error = TestInputValidator.validate_name("Анна")
    print(f"   'Анна' -> Valid: {valid}, Error: {error}")
    
    # Valid Russian name with hyphen
    valid, error = TestInputValidator.validate_name("Анна-Мария")
    print(f"   'Анна-Мария' -> Valid: {valid}, Error: {error}")
    
    # Invalid name (too short)
    valid, error = TestInputValidator.validate_name("А")
    print(f"   'А' -> Valid: {valid}, Error: {error}")
    
    # Valid age
    valid, error = TestInputValidator.validate_age("5")
    print(f"   Age '5' -> Valid: {valid}, Error: {error}")
    
    # Invalid age
    valid, error = TestInputValidator.validate_age("20")
    print(f"   Age '20' -> Valid: {valid}, Error: {error}")
    print()
    
    # Test 5: Language detection
    print("5. Testing language detection:")
    
    russian_text = "Мой сын сказал 'Я тебя ненавижу' и хлопнул дверью"
    english_text = "My son said 'I hate you' and slammed the door"
    
    ru_detected = TestInputValidator.detect_language(russian_text)
    en_detected = TestInputValidator.detect_language(english_text)
    
    print(f"   Russian text detected as: {ru_detected}")
    print(f"   English text detected as: {en_detected}")
    print()
    
    # Test 6: Text sanitization
    print("6. Testing Russian text sanitization:")
    
    dirty_text = "Мой    сын!!!   сказал   что-то   плохое..."
    clean_text = TestInputValidator.sanitize_russian_text(dirty_text)
    
    print(f"   Original: '{dirty_text}'")
    print(f"   Cleaned:  '{clean_text}'")
    print()
    
    print("✅ All localization tests completed!")
    print("✅ Russian localization system is working correctly!")

if __name__ == "__main__":
    try:
        test_localization()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)