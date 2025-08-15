# Family Emotions App - Developer Guide

## Содержание
1. [Архитектурные принципы](#архитектурные-принципы)
2. [Стандарты кода](#стандарты-кода)
3. [Настройка среды разработки](#настройка-среды-разработки)
4. [Тестирование](#тестирование)
5. [Code Review процесс](#code-review-процесс)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Debugging и профилирование](#debugging-и-профилирование)
8. [Best Practices](#best-practices)

---

## Архитектурные принципы

### Domain-Driven Design (DDD)

Проект следует принципам DDD с четким разделением на bounded contexts:

```
src/
├── domain/                    # Доменная логика
│   ├── family/               # Family Context
│   │   ├── aggregates/       # Агрегаты
│   │   ├── entities/         # Сущности
│   │   ├── value_objects/    # Объекты-значения
│   │   ├── services/         # Доменные сервисы
│   │   └── events/           # Доменные события
│   ├── emotion/              # Emotion Context
│   └── checkin/              # Check-in Context
├── application/              # Слой приложения
│   ├── commands/             # Command handlers
│   ├── queries/              # Query handlers
│   └── services/             # Application services
├── infrastructure/           # Инфраструктурный слой
│   ├── database/
│   ├── cache/
│   ├── external/
│   └── telegram/
└── presentation/             # Слой представления
    ├── api/
    └── bot/
```

### Hexagonal Architecture

```python
# Порты (интерфейсы)
from abc import ABC, abstractmethod

class EmotionAnalysisPort(ABC):
    """Порт для анализа эмоций"""
    @abstractmethod
    async def analyze_emotion(
        self, 
        text: str, 
        child_profile: ChildProfile
    ) -> EmotionAnalysis:
        pass

# Адаптеры (реализации)
class ClaudeEmotionAdapter(EmotionAnalysisPort):
    """Адаптер для Claude API"""
    def __init__(self, claude_client: ClaudeClient):
        self.client = claude_client
    
    async def analyze_emotion(
        self, 
        text: str, 
        child_profile: ChildProfile
    ) -> EmotionAnalysis:
        # Реализация через Claude API
        response = await self.client.analyze(text, child_profile)
        return self._parse_response(response)
```

### Event Sourcing для критических данных

```python
# Доменные события
@dataclass
class EmotionAnalyzed(DomainEvent):
    child_id: UUID
    original_phrase: str
    analysis_result: Dict
    created_at: datetime
    
# Event Store
class EventStore:
    async def append_event(
        self, 
        aggregate_id: UUID, 
        event: DomainEvent
    ) -> None:
        # Сохраняем событие в базу
        pass
    
    async def get_events(
        self, 
        aggregate_id: UUID, 
        from_version: int = 0
    ) -> List[DomainEvent]:
        # Получаем события для восстановления состояния
        pass
```

---

## Стандарты кода

### Python Code Style

Следуем PEP 8 с дополнительными правилами:

```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | __pycache__
  | .git
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["src"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
```

### Именование

```python
# ✅ Правильно
class FamilyService:
    """Сервис для управления семьями."""
    
    async def create_family(
        self, 
        name: str, 
        created_by: UUID
    ) -> Family:
        """Создает новую семью.
        
        Args:
            name: Название семьи
            created_by: ID создателя семьи
            
        Returns:
            Созданная семья
            
        Raises:
            FamilyAlreadyExistsError: Если семья уже существует
        """
        # Проверяем существование семьи
        existing = await self._family_repo.find_by_name(name)
        if existing:
            raise FamilyAlreadyExistsError(f"Family {name} already exists")
        
        # Создаем семью
        family = Family.create(name=name, created_by=created_by)
        
        # Сохраняем
        await self._family_repo.save(family)
        
        # Публикуем событие
        await self._event_bus.publish(
            FamilyCreated(family_id=family.id, name=name, created_by=created_by)
        )
        
        return family

# ❌ Неправильно
def create_fam(n: str, u: str):
    # Создает семью
    f = Family()
    f.name = n
    f.user = u
    return f
```

### Структура модулей

```python
"""
Модуль для работы с семьями.

Содержит классы и функции для создания, управления и анализа семей
в контексте эмоционального анализа детей.
"""

# Стандартные библиотеки
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Сторонние библиотеки
import sqlalchemy as sa
from pydantic import BaseModel

# Внутренние импорты
from src.core.exceptions import FamilyNotFoundError
from src.domain.family.entities import Family
from src.infrastructure.database import DatabaseSession

# Константы
MAX_FAMILY_MEMBERS = 12
DEFAULT_FAMILY_SETTINGS = {
    "language": "ru",
    "notifications_enabled": True
}

# Логгер
logger = logging.getLogger(__name__)


class FamilyService:
    """Основной сервис для работы с семьями."""
    pass
```

### Обработка ошибок

```python
# Пользовательские исключения
class FamilyEmotionsError(Exception):
    """Базовый класс для всех ошибок приложения."""
    pass

class DomainError(FamilyEmotionsError):
    """Ошибки доменной логики."""
    pass

class FamilyNotFoundError(DomainError):
    """Семья не найдена."""
    
    def __init__(self, family_id: UUID):
        self.family_id = family_id
        super().__init__(f"Family with id {family_id} not found")

# Обработка ошибок
async def get_family(family_id: UUID) -> Family:
    """Получение семьи по ID."""
    try:
        family = await family_repository.get_by_id(family_id)
        if not family:
            raise FamilyNotFoundError(family_id)
        return family
        
    except DatabaseError as e:
        logger.error(f"Database error getting family {family_id}: {e}")
        raise InfrastructureError(f"Failed to get family: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error getting family {family_id}: {e}")
        raise FamilyEmotionsError(f"Unexpected error: {e}") from e
```

### Async/Await Guidelines

```python
# ✅ Правильно
class EmotionService:
    def __init__(
        self, 
        claude_client: ClaudeClient,
        emotion_repository: EmotionRepository
    ):
        self._claude = claude_client
        self._repo = emotion_repository
    
    async def analyze_emotion(
        self, 
        text: str, 
        child: Child
    ) -> EmotionAnalysis:
        """Анализирует эмоцию ребенка."""
        # Асинхронные операции
        analysis = await self._claude.analyze(text, child.age)
        
        # Создаем объект результата
        result = EmotionAnalysis.create(
            child_id=child.id,
            original_text=text,
            analysis=analysis
        )
        
        # Сохраняем асинхронно
        await self._repo.save(result)
        
        return result

# ❌ Неправильно - блокирующие операции
def analyze_emotion_sync(text: str) -> dict:
    # Блокирующий HTTP запрос
    response = requests.post("https://api.claude.com/analyze", json={"text": text})
    return response.json()
```

---

## Настройка среды разработки

### VS Code настройки

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests",
        "--verbose"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".mypy_cache": true,
        ".pytest_cache": true
    }
}
```

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Docker для разработки

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей для разработки
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Установка основных зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем исходный код
COPY src/ src/
COPY tests/ tests/
COPY alembic.ini .
COPY pyproject.toml .

# Порт для debugging
EXPOSE 5678

# Команда по умолчанию для разработки
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "src/main.py"]
```

---

## Тестирование

### Структура тестов

```
tests/
├── unit/                     # Unit тесты
│   ├── domain/              # Тесты доменной логики
│   │   ├── test_family.py
│   │   ├── test_emotion.py
│   │   └── test_checkin.py
│   ├── application/         # Тесты application services
│   └── infrastructure/      # Тесты инфраструктуры
├── integration/             # Integration тесты
│   ├── test_database.py
│   ├── test_telegram_bot.py
│   └── test_claude_api.py
├── e2e/                    # End-to-end тесты
│   └── test_user_flows.py
├── fixtures/               # Тестовые данные
│   ├── families.py
│   ├── children.py
│   └── emotions.py
└── conftest.py            # Pytest конфигурация
```

### Unit тесты

```python
# tests/unit/domain/test_family.py
import pytest
from uuid import uuid4
from datetime import date

from src.domain.family.aggregates import Family
from src.domain.family.entities import Child
from src.domain.family.exceptions import TooManyChildrenError


class TestFamily:
    """Тесты для агрегата Family."""
    
    def test_create_family(self):
        """Тест создания семьи."""
        family_id = uuid4()
        name = "Семья Петровых"
        created_by = uuid4()
        
        family = Family.create(
            family_id=family_id,
            name=name,
            created_by=created_by
        )
        
        assert family.id == family_id
        assert family.name == name
        assert family.created_by == created_by
        assert len(family.children) == 0
        assert len(family.parents) == 1
    
    def test_add_child_success(self):
        """Тест успешного добавления ребенка."""
        family = Family.create(
            family_id=uuid4(),
            name="Test Family",
            created_by=uuid4()
        )
        
        child = Child.create(
            name="Маша",
            birth_date=date(2015, 1, 1),
            family_id=family.id
        )
        
        family.add_child(child)
        
        assert len(family.children) == 1
        assert family.children[0] == child
    
    def test_add_too_many_children(self):
        """Тест ошибки при добавлении слишком многих детей."""
        family = Family.create(
            family_id=uuid4(),
            name="Test Family",
            created_by=uuid4()
        )
        
        # Добавляем максимальное количество детей
        for i in range(10):
            child = Child.create(
                name=f"Child {i}",
                birth_date=date(2015, 1, 1),
                family_id=family.id
            )
            family.add_child(child)
        
        # Попытка добавить еще одного должна вызвать ошибку
        extra_child = Child.create(
            name="Extra Child",
            birth_date=date(2015, 1, 1),
            family_id=family.id
        )
        
        with pytest.raises(TooManyChildrenError):
            family.add_child(extra_child)
```

### Integration тесты

```python
# tests/integration/test_emotion_service.py
import pytest
from uuid import uuid4

from src.application.services.emotion_service import EmotionService
from src.domain.family.entities import Child
from tests.fixtures.mock_claude_client import MockClaudeClient


@pytest.mark.asyncio
class TestEmotionServiceIntegration:
    """Integration тесты для EmotionService."""
    
    async def test_analyze_emotion_flow(
        self,
        emotion_service: EmotionService,
        sample_child: Child
    ):
        """Тест полного флоу анализа эмоции."""
        text = "Я не хочу идти в школу!"
        
        result = await emotion_service.analyze_emotion(
            text=text,
            child=sample_child
        )
        
        assert result.child_id == sample_child.id
        assert result.original_text == text
        assert result.analysis is not None
        assert result.suggested_responses is not None
        assert len(result.suggested_responses) > 0
    
    async def test_analyze_emotion_with_context(
        self,
        emotion_service: EmotionService,
        sample_child: Child
    ):
        """Тест анализа с контекстом."""
        text = "Мне плохо"
        context = {
            "situation": "after_school",
            "mood_before": "normal"
        }
        
        result = await emotion_service.analyze_emotion(
            text=text,
            child=sample_child,
            context=context
        )
        
        assert result.context == context
        # Анализ должен учесть контекст
        assert "школа" in result.analysis.interpretation.lower()


# Фикстуры
@pytest.fixture
async def emotion_service(mock_claude_client, emotion_repository):
    """Фикстура EmotionService с мок-зависимостями."""
    return EmotionService(
        claude_client=mock_claude_client,
        emotion_repository=emotion_repository
    )

@pytest.fixture
def sample_child() -> Child:
    """Фикстура тестового ребенка."""
    return Child.create(
        name="Тестовый ребенок",
        birth_date=date(2015, 1, 1),
        family_id=uuid4()
    )
```

### End-to-End тесты

```python
# tests/e2e/test_user_flows.py
import pytest
from telegram import Bot
from telegram.ext import Application

from tests.e2e.telegram_test_client import TelegramTestClient


@pytest.mark.asyncio
@pytest.mark.e2e
class TestUserFlows:
    """E2E тесты пользовательских сценариев."""
    
    async def test_complete_onboarding_flow(
        self,
        telegram_client: TelegramTestClient
    ):
        """Тест полного флоу онбординга нового пользователя."""
        # Начинаем диалог
        await telegram_client.send_message("/start")
        
        # Ожидаем приветствие
        response = await telegram_client.get_last_message()
        assert "Добро пожаловать" in response.text
        
        # Вводим имя
        await telegram_client.send_message("Мария")
        
        # Указываем количество детей
        await telegram_client.press_button("2 ребенка")
        
        # Добавляем первого ребенка
        await telegram_client.send_message("Маша")
        await telegram_client.press_button("8 лет")
        
        # Добавляем второго ребенка
        await telegram_client.send_message("Петя")
        await telegram_client.press_button("13 лет")
        
        # Настраиваем уведомления
        await telegram_client.press_button("20:00")
        
        # Завершаем онбординг
        await telegram_client.press_button("Готово")
        
        # Проверяем что попали в главное меню
        response = await telegram_client.get_last_message()
        assert "Главное меню" in response.text
        assert "Переводчик эмоций" in response.text
    
    async def test_emotion_translation_flow(
        self,
        telegram_client: TelegramTestClient
    ):
        """Тест флоу перевода эмоции."""
        # Предполагаем что пользователь уже прошел онбординг
        await telegram_client.setup_user_with_children()
        
        # Выбираем переводчик эмоций
        await telegram_client.press_button("💬 Переводчик эмоций")
        
        # Вводим фразу ребенка
        await telegram_client.send_message(
            "Петя сказал 'Отстань, ты ничего не понимаешь!'"
        )
        
        # Уточняем контекст
        await telegram_client.press_button("Петя, 13 лет")
        await telegram_client.press_button("Дом")
        
        # Ждем анализа
        response = await telegram_client.wait_for_response(timeout=10)
        
        # Проверяем результат
        assert "Что происходит" in response.text
        assert "Что он хочет сказать" in response.text
        assert "Как можно ответить" in response.text
        
        # Выбираем вариант ответа
        await telegram_client.press_button("Вариант 1")
        
        # Оставляем оценку
        await telegram_client.press_button("Это помогло! ✓")
```

### Pytest конфигурация

```python
# conftest.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import Settings
from src.infrastructure.database.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестирования."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Создает тестовую базу данных."""
    settings = Settings(_env_file=".env.test")
    engine = create_async_engine(
        settings.database_url,
        echo=True if settings.environment == "test" else False
    )
    
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Удаляем все таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine):
    """Создает тестовую сессию БД."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_claude_client():
    """Мок Claude API клиента."""
    mock = AsyncMock()
    mock.analyze.return_value = {
        "interpretation": "Ребенок выражает фрустрацию",
        "suggested_responses": [
            {
                "text": "Я понимаю, что тебе сложно",
                "explanation": "Проявляем эмпатию"
            }
        ]
    }
    return mock


@pytest.fixture
def mock_telegram_bot():
    """Мок Telegram бота."""
    mock = AsyncMock()
    mock.send_message.return_value = Mock(message_id=123)
    return mock


# Маркеры для pytest
def pytest_configure(config):
    """Конфигурация pytest."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# Пропускаем медленные тесты по умолчанию
def pytest_collection_modifyitems(config, items):
    """Модифицирует коллекцию тестов."""
    if config.getoption("--runslow"):
        return
    
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
```

---

## Code Review процесс

### Чеклист для Code Review

#### Архитектура и дизайн
- [ ] Код следует принципам DDD
- [ ] Правильное разделение на слои
- [ ] Соблюдение принципов SOLID
- [ ] Отсутствие циклических зависимостей

#### Код качество
- [ ] Код читаемый и самодокументируемый
- [ ] Соблюдение принципа DRY (Don't Repeat Yourself)
- [ ] Правильное именование переменных и функций
- [ ] Отсутствие магических чисел и строк

#### Безопасность
- [ ] Нет hardcoded паролей или токенов
- [ ] Правильная валидация входных данных
- [ ] Безопасная работа с детскими данными
- [ ] Защита от SQL инъекций

#### Производительность
- [ ] Оптимальные SQL запросы
- [ ] Правильное использование async/await
- [ ] Отсутствие N+1 проблем
- [ ] Эффективное использование памяти

#### Тестирование
- [ ] Достаточное покрытие тестами (>80%)
- [ ] Unit тесты для бизнес-логики
- [ ] Integration тесты для внешних интеграций
- [ ] Тесты читаемые и поддерживаемые

### Template для Pull Request

```markdown
## Описание изменений

### Что сделано
- [ ] Добавлена новая функция X
- [ ] Исправлена ошибка Y
- [ ] Обновлена документация Z

### Тип изменений
- [ ] 🐛 Bug fix (исправление ошибки)
- [ ] ✨ New feature (новая функциональность)
- [ ] 💥 Breaking change (breaking изменения)
- [ ] 📚 Documentation (обновление документации)
- [ ] 🎨 Refactoring (рефакторинг без изменения логики)
- [ ] ⚡ Performance (улучшение производительности)
- [ ] 🔒 Security (улучшение безопасности)

### Связанные задачи
Closes #123
Related to #456

### Чеклист для автора
- [ ] Код следует стилю проекта
- [ ] Добавлены/обновлены тесты
- [ ] Все тесты проходят
- [ ] Обновлена документация
- [ ] Код review проведен самостоятельно

### Инструкции для тестирования
1. Запустить локальное окружение
2. Выполнить команду X
3. Проверить результат Y

### Screenshots (если применимо)
<!-- Добавьте скриншоты изменений UI -->

### Дополнительные заметки
<!-- Любая дополнительная информация для reviewer -->
```

### Процесс Review

1. **Автор создает PR**
   - Заполняет template
   - Назначает reviewer'ов
   - Добавляет соответствующие labels

2. **Автоматические проверки**
   - CI/CD pipeline запускается
   - Тесты выполняются
   - Code quality проверки
   - Security сканирование

3. **Manual Review**
   - Reviewer проверяет код по чеклисту
   - Оставляет комментарии и предложения
   - Запрашивает изменения или approves

4. **Исправления**
   - Автор вносит исправления
   - Отвечает на комментарии
   - Запрашивает повторный review

5. **Merge**
   - После approval код мержится
   - Branch удаляется
   - Deploy в production (если настроен)

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: 3.11

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_family_emotions
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ env.PYTHON_VERSION }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 src/ tests/
        black --check src/ tests/
        isort --check-only src/ tests/
        mypy src/
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_family_emotions
        REDIS_URL: redis://localhost:6379/0
        ANTHROPIC_API_KEY: test-key
        TELEGRAM_BOT_TOKEN: test:token
      run: |
        pytest tests/ --cov=src --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run security checks
      run: |
        pip install safety bandit
        safety check -r requirements.txt
        bandit -r src/ -f json -o bandit-report.json
    
    - name: Upload security report
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: bandit-report.json

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t family-emotions:${{ github.sha }} .
        docker tag family-emotions:${{ github.sha }} family-emotions:latest
    
    - name: Run container tests
      run: |
        docker run --rm family-emotions:${{ github.sha }} python -c "import src.main"
    
    - name: Push to registry (if needed)
      if: success()
      run: |
        echo "Docker image built successfully"
        # Здесь можно добавить push в Docker registry

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deploying to production via Coolify webhook"
        curl -X POST "${{ secrets.COOLIFY_WEBHOOK_URL }}"
```

### Pre-deployment проверки

```python
# scripts/pre_deploy_checks.py
"""
Скрипт для проверки готовности к деплою.
Выполняется перед каждым деплоем в production.
"""

import asyncio
import sys
from typing import List, Tuple

import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import Settings


async def check_database_connection() -> Tuple[bool, str]:
    """Проверяет подключение к базе данных."""
    try:
        settings = Settings()
        engine = create_async_engine(settings.database_url)
        
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            await result.fetchone()
        
        await engine.dispose()
        return True, "Database connection OK"
        
    except Exception as e:
        return False, f"Database connection failed: {e}"


async def check_redis_connection() -> Tuple[bool, str]:
    """Проверяет подключение к Redis."""
    try:
        import redis.asyncio as redis
        
        settings = Settings()
        r = redis.from_url(settings.redis_url)
        
        await r.ping()
        await r.close()
        
        return True, "Redis connection OK"
        
    except Exception as e:
        return False, f"Redis connection failed: {e}"


async def check_external_apis() -> Tuple[bool, str]:
    """Проверяет доступность внешних API."""
    try:
        settings = Settings()
        
        # Проверяем Claude API
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01"
            }
            async with session.get(
                "https://api.anthropic.com/v1/models",
                headers=headers
            ) as response:
                if response.status != 200:
                    return False, f"Claude API returned {response.status}"
        
        # Проверяем Telegram API
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
            async with session.get(url) as response:
                if response.status != 200:
                    return False, f"Telegram API returned {response.status}"
        
        return True, "External APIs OK"
        
    except Exception as e:
        return False, f"External API check failed: {e}"


async def check_environment_variables() -> Tuple[bool, str]:
    """Проверяет наличие всех необходимых переменных окружения."""
    try:
        settings = Settings()
        
        required_vars = [
            "database_url",
            "redis_url", 
            "telegram_bot_token",
            "anthropic_api_key",
            "secret_key"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(settings, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            return False, f"Missing environment variables: {missing_vars}"
        
        return True, "Environment variables OK"
        
    except Exception as e:
        return False, f"Environment check failed: {e}"


async def run_health_checks() -> bool:
    """Запускает все проверки здоровья системы."""
    checks = [
        ("Environment Variables", check_environment_variables()),
        ("Database", check_database_connection()),
        ("Redis", check_redis_connection()),
        ("External APIs", check_external_apis())
    ]
    
    results = []
    for name, check in checks:
        print(f"Checking {name}...")
        success, message = await check
        results.append((name, success, message))
        
        if success:
            print(f"✅ {name}: {message}")
        else:
            print(f"❌ {name}: {message}")
    
    # Проверяем что все проверки прошли успешно
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All pre-deployment checks passed!")
        return True
    else:
        print("\n💥 Some pre-deployment checks failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_health_checks())
    sys.exit(0 if success else 1)
```

---

## Debugging и профилирование

### Логирование

```python
# src/core/logging.py
import logging
import sys
from typing import Any, Dict

import structlog
from structlog import configure, get_logger
from structlog.stdlib import BoundLogger

from src.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Настройка структурированного логирования."""
    
    # Конфигурация structlog
    configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.environment == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Настройка стандартного логгера
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


class ContextLogger:
    """Логгер с контекстом для отслеживания запросов."""
    
    def __init__(self, logger: BoundLogger):
        self._logger = logger
        self._context: Dict[str, Any] = {}
    
    def bind(self, **kwargs: Any) -> "ContextLogger":
        """Добавляет контекст к логгеру."""
        new_context = {**self._context, **kwargs}
        bound_logger = self._logger.bind(**new_context)
        
        result = ContextLogger(bound_logger)
        result._context = new_context
        return result
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Логирует INFO сообщение."""
        self._logger.info(message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Логирует ERROR сообщение."""
        self._logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Логирует DEBUG сообщение."""
        self._logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Логирует WARNING сообщение."""
        self._logger.warning(message, **kwargs)


def get_context_logger(name: str) -> ContextLogger:
    """Получает логгер с контекстом."""
    logger = get_logger(name)
    return ContextLogger(logger)


# Использование в коде
logger = get_context_logger(__name__)

async def analyze_emotion(user_id: UUID, text: str) -> EmotionAnalysis:
    """Анализирует эмоцию с логированием."""
    request_logger = logger.bind(
        user_id=str(user_id),
        text_length=len(text),
        function="analyze_emotion"
    )
    
    request_logger.info("Starting emotion analysis")
    
    try:
        # Логируем начало обработки
        request_logger.debug("Sending request to Claude API")
        
        result = await claude_client.analyze(text)
        
        request_logger.info(
            "Emotion analysis completed successfully",
            processing_time_ms=result.processing_time,
            confidence_score=result.confidence
        )
        
        return result
        
    except Exception as e:
        request_logger.error(
            "Emotion analysis failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

### Профилирование

```python
# src/core/profiling.py
import cProfile
import io
import pstats
import time
from functools import wraps
from typing import Callable, Any

from src.core.logging import get_context_logger

logger = get_context_logger(__name__)


def profile_async(func: Callable) -> Callable:
    """Декоратор для профилирования async функций."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        
        start_time = time.time()
        profiler.enable()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            end_time = time.time()
            
            # Создаем отчет
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # Топ 20 функций
            
            # Логируем результаты
            logger.info(
                f"Profile report for {func.__name__}",
                execution_time_ms=(end_time - start_time) * 1000,
                profile_report=s.getvalue()
            )
    
    return wrapper


class PerformanceMonitor:
    """Монитор производительности для критических операций."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time: float = 0
        self.logger = get_context_logger(__name__)
    
    async def __aenter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation_name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation_name}",
                duration_ms=duration_ms
            )
        else:
            self.logger.error(
                f"Failed {self.operation_name}",
                duration_ms=duration_ms,
                error=str(exc_val)
            )


# Использование
async def analyze_emotion_with_monitoring(text: str) -> EmotionAnalysis:
    """Анализ эмоции с мониторингом производительности."""
    
    async with PerformanceMonitor("emotion_analysis"):
        # Критическая операция
        result = await claude_client.analyze(text)
        return result

@profile_async
async def generate_weekly_report(family_id: UUID) -> WeeklyReport:
    """Генерация еженедельного отчета с профилированием."""
    # Сложная операция с большим количеством вычислений
    return await report_generator.generate(family_id)
```

### Memory Profiling

```python
# src/core/memory_profiling.py
import tracemalloc
from typing import Dict, List, Tuple

from src.core.logging import get_context_logger

logger = get_context_logger(__name__)


class MemoryProfiler:
    """Профайлер памяти для отслеживания утечек."""
    
    def __init__(self, top_stats: int = 10):
        self.top_stats = top_stats
        self.snapshots: List[tracemalloc.Snapshot] = []
    
    def start(self) -> None:
        """Запускает профилирование памяти."""
        tracemalloc.start()
        logger.debug("Memory profiling started")
    
    def take_snapshot(self, label: str = "") -> None:
        """Делает снимок текущего состояния памяти."""
        if not tracemalloc.is_tracing():
            logger.warning("Memory tracing is not active")
            return
        
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label, snapshot))
        
        # Логируем текущее использование памяти
        top_stats = snapshot.statistics('lineno')[:self.top_stats]
        
        memory_info = []
        for stat in top_stats:
            memory_info.append({
                "file": stat.traceback.format()[-1],
                "size_mb": stat.size / 1024 / 1024,
                "count": stat.count
            })
        
        logger.info(
            f"Memory snapshot taken: {label}",
            memory_stats=memory_info,
            total_memory_mb=sum(stat.size for stat in top_stats) / 1024 / 1024
        )
    
    def compare_snapshots(self, label1: str, label2: str) -> None:
        """Сравнивает два снимка памяти."""
        snapshot1 = next(
            (snap for lbl, snap in self.snapshots if lbl == label1), 
            None
        )
        snapshot2 = next(
            (snap for lbl, snap in self.snapshots if lbl == label2), 
            None
        )
        
        if not snapshot1 or not snapshot2:
            logger.error("One or both snapshots not found")
            return
        
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')[:self.top_stats]
        
        differences = []
        for stat in top_stats:
            differences.append({
                "file": stat.traceback.format()[-1],
                "size_diff_mb": stat.size_diff / 1024 / 1024,
                "count_diff": stat.count_diff
            })
        
        logger.info(
            f"Memory comparison: {label1} vs {label2}",
            differences=differences
        )
    
    def stop(self) -> None:
        """Останавливает профилирование памяти."""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            logger.debug("Memory profiling stopped")


# Использование в тестах
@pytest.fixture
def memory_profiler():
    """Фикстура для профилирования памяти в тестах."""
    profiler = MemoryProfiler()
    profiler.start()
    
    yield profiler
    
    profiler.stop()

def test_emotion_analysis_memory_usage(memory_profiler):
    """Тест на использование памяти при анализе эмоций."""
    memory_profiler.take_snapshot("before_analysis")
    
    # Выполняем много анализов
    for i in range(100):
        analyze_emotion(f"Test emotion {i}")
    
    memory_profiler.take_snapshot("after_100_analyses")
    memory_profiler.compare_snapshots("before_analysis", "after_100_analyses")
```

---

## Best Practices

### Безопасность

```python
# Правильная работа с секретами
class SecureConfig:
    """Безопасная работа с конфигурацией."""
    
    def __init__(self):
        # Никогда не логируем секреты
        self._secrets = {
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "secret_key": os.getenv("SECRET_KEY")
        }
    
    @property
    def anthropic_api_key(self) -> str:
        """Получает API ключ Claude."""
        key = self._secrets.get("anthropic_api_key")
        if not key:
            raise ConfigurationError("ANTHROPIC_API_KEY not set")
        return key
    
    def __repr__(self) -> str:
        # Маскируем секреты в repr
        return f"SecureConfig(secrets={'*' * len(self._secrets)} keys)"

# Валидация входных данных
from pydantic import BaseModel, validator

class EmotionAnalysisRequest(BaseModel):
    """Запрос на анализ эмоции."""
    text: str
    child_age: int
    context: Optional[Dict[str, str]] = None
    
    @validator('text')
    def validate_text(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Text too short")
        if len(v) > 1000:
            raise ValueError("Text too long")
        return v.strip()
    
    @validator('child_age')
    def validate_age(cls, v):
        if v < 4 or v > 17:
            raise ValueError("Child age must be between 4 and 17")
        return v

# Защита от SQL инъекций
from sqlalchemy import text

async def get_family_by_name_safe(name: str) -> Optional[Family]:
    """Безопасный поиск семьи по имени."""
    # Используем параметризованные запросы
    query = text("SELECT * FROM families WHERE name = :name")
    result = await session.execute(query, {"name": name})
    return result.fetchone()

# ❌ Небезопасно - уязвимость к SQL инъекциям
async def get_family_by_name_unsafe(name: str) -> Optional[Family]:
    query = f"SELECT * FROM families WHERE name = '{name}'"
    result = await session.execute(text(query))
    return result.fetchone()
```

### Производительность

```python
# Оптимизация запросов к БД
from sqlalchemy.orm import selectinload, joinedload

async def get_family_with_children_optimized(family_id: UUID) -> Family:
    """Оптимизированное получение семьи с детьми."""
    # Используем eager loading чтобы избежать N+1 проблемы
    query = (
        select(Family)
        .options(
            selectinload(Family.children),  # Для отношений one-to-many
            joinedload(Family.parents)      # Для отношений one-to-one
        )
        .where(Family.id == family_id)
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

# Кеширование тяжелых операций
from functools import lru_cache
from typing import Dict

class RecommendationCache:
    """Кеш для рекомендаций."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 3600  # 1 час
    
    async def get_cached_recommendations(
        self, 
        emotion_hash: str
    ) -> Optional[List[Dict]]:
        """Получает рекомендации из кеша."""
        cache_key = f"recommendations:{emotion_hash}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_recommendations(
        self, 
        emotion_hash: str, 
        recommendations: List[Dict]
    ) -> None:
        """Кеширует рекомендации."""
        cache_key = f"recommendations:{emotion_hash}"
        await self.redis.setex(
            cache_key, 
            self.ttl, 
            json.dumps(recommendations)
        )

# Батчинг операций
async def process_emotions_batch(
    emotions: List[str], 
    batch_size: int = 10
) -> List[EmotionAnalysis]:
    """Обрабатывает эмоции батчами для оптимизации."""
    results = []
    
    for i in range(0, len(emotions), batch_size):
        batch = emotions[i:i + batch_size]
        
        # Обрабатываем батч параллельно
        tasks = [analyze_emotion(emotion) for emotion in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
            else:
                results.append(result)
    
    return results
```

### Мониторинг и наблюдаемость

```python
# Метрики Prometheus
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Определяем метрики
EMOTION_ANALYSES_TOTAL = Counter(
    'emotion_analyses_total',
    'Total number of emotion analyses',
    ['status', 'child_age_group']
)

EMOTION_ANALYSIS_DURATION = Histogram(
    'emotion_analysis_duration_seconds',
    'Time spent analyzing emotions',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ACTIVE_FAMILIES = Gauge(
    'active_families_total',
    'Number of active families'
)

class MetricsCollector:
    """Сборщик метрик для мониторинга."""
    
    @staticmethod
    async def record_emotion_analysis(
        child_age: int, 
        duration: float, 
        success: bool
    ) -> None:
        """Записывает метрики анализа эмоций."""
        age_group = "child" if child_age < 13 else "teen"
        status = "success" if success else "error"
        
        EMOTION_ANALYSES_TOTAL.labels(
            status=status, 
            child_age_group=age_group
        ).inc()
        
        EMOTION_ANALYSIS_DURATION.observe(duration)
    
    @staticmethod
    async def update_active_families_count() -> None:
        """Обновляет количество активных семей."""
        # Получаем актуальное количество из БД
        count = await get_active_families_count()
        ACTIVE_FAMILIES.set(count)

# Health checks для Kubernetes
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Проверяем БД
        await check_database_health()
        
        # Проверяем Redis
        await check_redis_health()
        
        # Проверяем внешние API
        await check_external_apis_health()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

### Обработка ошибок

```python
# Централизованная обработка ошибок
from enum import Enum

class ErrorCode(Enum):
    """Коды ошибок для API."""
    FAMILY_NOT_FOUND = "FAMILY_NOT_FOUND"
    CHILD_NOT_FOUND = "CHILD_NOT_FOUND"
    TRANSLATION_LIMIT_EXCEEDED = "TRANSLATION_LIMIT_EXCEEDED"
    CLAUDE_API_ERROR = "CLAUDE_API_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

@dataclass
class ErrorResponse:
    """Стандартный формат ошибки."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class ErrorHandler:
    """Централизованный обработчик ошибок."""
    
    def __init__(self, logger: ContextLogger):
        self.logger = logger
    
    async def handle_domain_error(
        self, 
        error: DomainError, 
        request_id: str
    ) -> ErrorResponse:
        """Обрабатывает доменные ошибки."""
        self.logger.warning(
            "Domain error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=request_id
        )
        
        # Мапим доменные ошибки на коды API
        error_mapping = {
            FamilyNotFoundError: ErrorCode.FAMILY_NOT_FOUND,
            ChildNotFoundError: ErrorCode.CHILD_NOT_FOUND,
            TranslationLimitExceededError: ErrorCode.TRANSLATION_LIMIT_EXCEEDED
        }
        
        code = error_mapping.get(type(error), ErrorCode.VALIDATION_ERROR)
        
        return ErrorResponse(
            code=code,
            message=str(error),
            request_id=request_id
        )
    
    async def handle_infrastructure_error(
        self, 
        error: Exception, 
        request_id: str
    ) -> ErrorResponse:
        """Обрабатывает инфраструктурные ошибки."""
        self.logger.error(
            "Infrastructure error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=request_id,
            exc_info=True
        )
        
        return ErrorResponse(
            code=ErrorCode.CLAUDE_API_ERROR,
            message="Service temporarily unavailable",
            request_id=request_id
        )

# Retry механизм
import asyncio
from typing import Callable, TypeVar

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> T:
    """Повторяет операцию с экспоненциальной задержкой."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                break
            
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )
            
            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {delay}s",
                error=str(e),
                attempt=attempt + 1,
                max_retries=max_retries
            )
            
            await asyncio.sleep(delay)
    
    raise last_exception

# Использование
async def analyze_emotion_with_retry(text: str) -> EmotionAnalysis:
    """Анализирует эмоцию с повторными попытками."""
    return await retry_with_backoff(
        lambda: claude_client.analyze(text),
        max_retries=3,
        base_delay=1.0
    )
```

---

*Developer Guide Version: 1.0*  
*Last Updated: August 14, 2025*  
*For questions: dev-team@familyemotions.app*