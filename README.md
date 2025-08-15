# Family Emotions App
*Карманный детский психолог для российских семей*

ИИ-помощник в Telegram, который помогает родителям лучше понимать эмоции детей и находить правильные слова в сложных ситуациях. Переводит детские "истерики" в понятные инсайты и дает конкретные рекомендации.

## 🌟 Основные функции

### MVP Функциональность
- **💬 Переводчик эмоций**: Интерпретация фраз и поведения детей с помощью Claude 3.5 Sonnet
- **📊 Ежедневные чек-ины**: Мониторинг эмоционального состояния семьи
- **👶 Профили детей**: Персонализация под возраст и особенности ребенка
- **📈 Еженедельные отчеты**: Автоматические инсайты и рекомендации
- **🤖 ИИ-анализ**: Понимание скрытых потребностей за детскими словами

### Technical Features
- **⚡ Async/Await**: High-performance async Python architecture
- **📱 Telegram Bot**: Rich interactive interface with inline keyboards
- **🗄️ PostgreSQL**: Robust data storage with SQLAlchemy 2.0
- **⚡ Redis**: Caching and session management
- **🤖 Claude AI**: Advanced emotion analysis and recommendations
- **📈 Analytics**: Usage tracking and insights
- **🔄 Scheduling**: Automated tasks and notifications

## 🚀 Быстрый старт

### Системные требования
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Anthropic Claude API Key
- Docker и Docker Compose (рекомендуется)

### Установка и запуск

1. **Клонирование и подготовка:**
```bash
git clone https://github.com/your-org/family-emotions-app.git
cd family-emotions-app
chmod +x scripts/setup.sh
./scripts/setup.sh
```

2. **Настройка переменных окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими данными:
# - TELEGRAM_BOT_TOKEN (получить у @BotFather)
# - ANTHROPIC_API_KEY (с сайта Anthropic)
# - Данные для подключения к базе данных
```

3. **Запуск через Docker (рекомендуется):**
```bash
# Полный запуск с БД и Redis
docker-compose up -d

# Проверка статуса
docker-compose ps
```

4. **Локальная разработка:**
```bash
# Запуск только внешних сервисов
docker-compose up -d postgres redis

# Миграции
alembic upgrade head

# Запуск приложения
python src/main.py
```

### Docker Deployment

**Production:**
```bash
docker-compose up -d
```

**Development with tools:**
```bash
docker-compose --profile dev up -d
```

## 📁 Project Structure

```
family-emotions-app/
├── src/
│   ├── core/                  # Core domain logic
│   │   ├── models/           # Database models
│   │   ├── services/         # Business logic services
│   │   ├── config.py         # Configuration
│   │   ├── exceptions.py     # Custom exceptions
│   │   ├── logging.py        # Logging setup
│   │   └── container.py      # Dependency injection
│   ├── infrastructure/       # Infrastructure layer
│   │   ├── database/        # Database connection
│   │   ├── cache/           # Redis caching
│   │   ├── telegram/        # Telegram bot
│   │   └── external/        # External services
│   ├── application/         # Application services
│   │   ├── checkin_service.py
│   │   └── scheduler.py
│   └── main.py              # Application entry point
├── migrations/              # Database migrations
├── scripts/                 # Setup and utility scripts
├── tests/                   # Test suites
├── logs/                    # Application logs
├── docker-compose.yml       # Docker services
├── Dockerfile              # Application container
└── requirements.txt        # Python dependencies
```

## 🔧 Конфигурация

### Переменные окружения

Основные настройки в `.env`:

```bash
# База данных PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=family_emotions
DB_USER=postgres
DB_PASSWORD=your-secure-password

# Redis для кеширования и сессий
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Telegram Bot API
TELEGRAM_BOT_TOKEN=1234567890:AAE_your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Лимиты использования (MVP без монетизации)
DAILY_TRANSLATIONS_LIMIT=20
CHECKIN_ENABLED=true
WEEKLY_REPORTS_ENABLED=true

# Логирование и мониторинг
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn

# Окружение
ENVIRONMENT=production
DEBUG=false
```

### Команды бота

Основные команды для пользователей:
- `/start` - Регистрация и главное меню
- `/help` - Справка и инструкции
- `/children` - Управление профилями детей
- `/translate` - Переводчик эмоций
- `/checkin` - Запустить чек-ин сейчас
- `/settings` - Настройки семьи и уведомлений
- `/report` - Последний еженедельный отчет
- `/feedback` - Обратная связь

## 🏗️ Архитектура

### Domain-Driven Design (DDD)
Приложение следует принципам доменно-ориентированного проектирования:

- **Family Context**: Управление семейными единицами и отношениями
- **Emotion Context**: Обработка и перевод эмоций
- **Check-in Context**: Ежедневные эмоциональные опросы
- **Analytics Context**: Генерация инсайтов и отчетов
- **User Context**: Аутентификация и профили пользователей

### Hexagonal Architecture
Используется гексагональная архитектура с четким разделением:

```
┌─ Presentation Layer ─┐    ┌─ Application Layer ─┐    ┌─ Domain Layer ─┐
│  • Telegram Bot      │───▶│  • Use Cases        │───▶│ • Aggregates    │
│  • Health Check API  │    │  • Command Handlers │    │ • Entities      │
│  • Admin Interface   │    │  • Query Handlers   │    │ • Value Objects │
└─────────────────────┘    └────────────────────┘    └─────────────────┘
                                      │
                           ┌─ Infrastructure Layer ─┐
                           │  • PostgreSQL          │
                           │  • Redis Cache         │
                           │  • Claude API          │
                           │  • Event Bus           │
                           └───────────────────────┘
```

### Key Services

**UserService**: User management and authentication
```python
user = await user_service.create_user(
    telegram_id=123456789,
    first_name="John",
    language_code="en"
)
```

**EmotionService**: AI-powered emotion analysis
```python
translation = await emotion_service.create_emotion_translation(
    user_id=user.id,
    child_message="My son said 'I hate you' and slammed the door",
    child_id=child.id
)
```

**CheckinService**: Scheduled wellness tracking
```python
checkin = await checkin_service.create_scheduled_checkin(
    user_id=user.id,
    child_id=child.id,
    checkin_type=CheckinType.DAILY
)
```

## 📊 Схема базы данных

### Основные таблицы
- **families**: Семейные единицы (aggregates)
- **parents**: Родители и опекуны
- **children**: Профили детей с характеристиками
- **emotion_entries**: История переводов эмоций
- **checkin_sessions**: Сессии ежедневных опросов
- **checkin_responses**: Ответы на чек-ины
- **weekly_reports**: Еженедельные аналитические отчеты
- **domain_events**: Event sourcing для аудита

### Связи между таблицами
- Family → Parents (One-to-Many, max 2)
- Family → Children (One-to-Many, max 10)
- Child → EmotionEntries (One-to-Many)
- CheckInSession → CheckInResponses (One-to-Many)
- Family → WeeklyReports (One-to-Many)

**Ограничения предметной области:**
- Максимум 2 родителя в семье
- Максимум 10 детей в семье  
- Возраст детей: 4-17 лет
- Данные хранятся 90 дней (GDPR)

## 🤖 UX-флоу Telegram бота

### Onboarding (первый запуск)
1. Пользователь отправляет `/start`
2. Приветствие и сбор имени родителя
3. Настройка профилей детей (имя, возраст)
4. Выбор основной проблемы из списка
5. Настройка времени чек-инов
6. Краткая инструкция (3 экрана)
7. Переход в главное меню

### Флоу переводчика эмоций
1. Выбор функции "💬 Переводчик эмоций"
2. Ввод фразы ребенка (текст или голос)
3. Уточнение контекста (дом/школа/друзья)
4. ИИ-анализ с Claude 3.5 Sonnet
5. Показ интерпретации и скрытого смысла
6. Три варианта ответа с объяснениями
7. Сбор обратной связи (полезно/не полезно)
8. Сохранение для паттерн-анализа

### Флоу ежедневных чек-инов
1. Автоматическая отправка в настроенное время
2. 2-3 простых вопроса о настроении семьи
3. Inline-кнопки для быстрого ответа
4. Дополнительные вопросы при негативных ответах
5. Сбор данных для еженедельной аналитики
6. Немедленные рекомендации при кризисе

## 🔒 Безопасность и приватность

### GDPR Compliance
- Минимальный сбор персональных данных
- Явное согласие на обработку данных
- Право на удаление (Right to be forgotten)
- Шифрование чувствительной информации
- Автоудаление данных через 90 дней

### Защита данных
- TLS 1.3 для всех соединений
- Шифрование паролей через Argon2
- Rate limiting: 100 запросов/час на пользователя
- Никаких детских фото или голосовых записей
- Логи не содержат персональные данные
- Модерация контента на неподходящие темы

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием кода
pytest --cov=src --cov-report=html

# Конкретный модуль
pytest tests/unit/test_family_service.py

# Интеграционные тесты 
# (требуют запущенных сервисов)
pytest tests/integration/ --asyncio-mode=auto
```

### Тестовое окружение
```bash
# Настройка тестовой БД
export DATABASE_URL="postgresql://test:test@localhost/family_emotions_test"
export REDIS_URL="redis://localhost:6379/1"

# Моки для внешних сервисов
export ANTHROPIC_API_KEY="test-key"
export TELEGRAM_BOT_TOKEN="test:token"
```

## 📈 Мониторинг и аналитика

### Метрики бизнеса (MVP)
- **Adoption**: Количество регистраций (target: 500 семей)
- **Engagement**: DAU/WAU ratio и глубина диалога
- **Retention**: D1, D7, D30 retention (target: >30% W1)
- **Task Success**: Completion rate чек-инов (target: >50%)
- **Happiness**: Оценка полезности рекомендаций

### Мониторинг системы
```bash
# Проверка здоровья приложения
curl http://localhost:8000/health

# Метрики Prometheus
curl http://localhost:8000/metrics

# Статус сервисов
docker-compose ps

# Логи в реальном времени
docker-compose logs -f telegram-bot
```

### Error Tracking
- **Sentry**: Автоматическое отслеживание ошибок
- **Structured Logs**: JSON логи с контекстом
- **Performance Monitoring**: Метрики отклика ИИ

## 🚀 Развертывание

### Coolify Deployment (рекомендуется)

Проект оптимизирован для Coolify - open-source альтернативы Heroku:

1. **Подключение репозитория:**
   - Подключите GitHub/GitLab в Coolify
   - Выберите Docker Compose deployment

2. **Настройка переменных:**
   - Копируйте значения из `.env.example`
   - Установите production ключи API

3. **Автоматическое развертывание:**
   - Каждый push в main ветку обновляет продакшен
   - Zero-downtime deployment

### Production Checklist
- [ ] Настроить `.env` с production значениями
- [ ] Подключить PostgreSQL с автобэкапами
- [ ] Настроить Redis persistence
- [ ] Настроить webhook для Telegram бота
- [ ] Получить SSL сертификат для webhook
- [ ] Настроить Sentry для мониторинга
- [ ] Настроить лог-ротацию
- [ ] Проверить бэкапы и обновления
- [ ] Настроить алерты мониторинга

### Масштабирование (Post-MVP)
- **БД**: Connection pooling, read replicas для аналитики
- **Cache**: Redis Cluster для обеспечения отказоустойчивости
- **Bot**: Переход на Webhook режим
- **AI**: Очереди для Claude API распределения нагрузки

## 🤝 Участие в разработке

### Процесс разработки
1. **Fork и клонирование:**
   ```bash
   git clone https://github.com/your-username/family-emotions-app.git
   cd family-emotions-app
   git checkout -b feature/your-feature-name
   ```

2. **Настройка окружения разработки:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   pre-commit install
   ```

3. **Код-стайл и линтинг:**
   ```bash
   # Автоматическое форматирование
   black src/ tests/
   isort src/ tests/
   
   # Проверка типов
   mypy src/
   
   # Линтинг
   flake8 src/
   ```

4. **Тестирование:**
   - Напишите unit тесты для новой функциональности
   - Покрытие кода не меньше 80%
   - Проверьте integration тесты

5. **Pull Request:**
   - Опишите изменения в PR description
   - Приложите скриншоты при наличии
   - Ссылка на соответствующие Issue

### Стандарты кода
- **Язык**: Русский для бизнес-логики, английский для кода
- **Коммиты**: Conventional Commits (feat:, fix:, docs:)
- **Архитектура**: Следуйте DDD принципам
- **Документация**: Docstrings на русском для user-facing кода

### Требования к Review
- Минимум 1 approval от maintainer
- Проходящие CI/CD checks
- Обновление CHANGELOG.md при необходимости

## 📄 Лицензия

Проект распространяется под лицензией MIT - подробности в [LICENSE](LICENSE).

## 🌆 План развития

### MVP (31 августа 2025)
- ✅ Переводчик эмоций с Claude 3.5
- ✅ Ежедневные чек-ины семьи
- ✅ Простые еженедельные отчеты
- ✅ Базовая аналитика

### Post-MVP (сентябрь 2025)
- 🔄 Улучшенные ИИ модели
- 🗺️ Многоязычность (UA, EN)
- 📈 Продвинутая аналитика
- 💰 Монетизация (Premium планы)

## 🔗 Полезные ссылки

- 📚 **Полная документация**: [/docs](./docs/)
- 🏗️ **Архитектура**: [family-emotions-architecture.md](./family-emotions-architecture.md)
- 📝 **PRD**: [family-emotions-prd.md](./docs/family-emotions-prd.md)
- 🎨 **UX Design**: [family-emotions-bot-ux-design.md](./docs/family-emotions-bot-ux-design.md)
- 🔌 **API документация**: [/docs/api.md](./docs/api.md)
- 🗺️ **Схема базы**: [/docs/database-schema.md](./docs/database-schema.md)

### Поддержка проекта
- **Documentation**: Полная документация в коде и README
- **Issues**: Открывайте GitHub Issues для багов и идей
- **Telegram**: [@family_emotions_support](https://t.me/family_emotions_support)
- **Email**: support@familyemotions.app

## 🙏 Благодарности

Проект стал возможен благодаря:

- **Anthropic Claude**: Мощный ИИ для анализа эмоций
- **python-telegram-bot**: Лучший Python фреймворк для Telegram ботов
- **SQLAlchemy 2.0**: Современная async ORM система
- **PostgreSQL**: Надежная база данных
- **Redis**: Быстрое кеширование и сессии
- **Coolify**: Simple deployment платформа
- **Сообщество**: Все родители, которые помогли тестировать и улучшать продукт

---

**Сделано с ❤️ для семей, которые хотят лучше понимать эмоции своих детей.**