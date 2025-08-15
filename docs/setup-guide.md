# Family Emotions App - Setup & Deployment Guide

## Содержание
1. [Локальная разработка](#локальная-разработка)
2. [Docker Compose Setup](#docker-compose-setup)
3. [Production Deployment с Coolify](#production-deployment-с-coolify)
4. [Переменные окружения](#переменные-окружения)
5. [База данных](#база-данных)
6. [Troubleshooting](#troubleshooting)

---

## Локальная разработка

### Системные требования

```bash
# Минимальные требования
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Git
- Docker & Docker Compose (рекомендуется)

# Дополнительно для разработки
- Node.js 18+ (для фронтенд инструментов)
- Pre-commit hooks
- VSCode или PyCharm
```

### Пошаговая установка

#### 1. Клонирование репозитория

```bash
git clone https://github.com/your-org/family-emotions-app.git
cd family-emotions-app

# Проверяем структуру проекта
ls -la
```

#### 2. Настройка Python окружения

```bash
# Создаем виртуальное окружение
python3.11 -m venv venv

# Активируем (Linux/macOS)
source venv/bin/activate

# Активируем (Windows)
venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Проверяем установку
python --version
pip list | grep telegram
```

#### 3. Pre-commit hooks

```bash
# Устанавливаем pre-commit hooks
pre-commit install

# Тестируем hooks
pre-commit run --all-files

# Если нужно пропустить хуки для конкретного коммита
git commit -m "message" --no-verify
```

#### 4. Настройка переменных окружения

```bash
# Копируем пример конфига
cp .env.example .env

# Редактируем .env файл
nano .env
```

Базовая конфигурация для разработки:
```bash
# === Основные настройки ===
ENVIRONMENT=development
DEBUG=true

# === База данных ===
DB_HOST=localhost
DB_PORT=5432
DB_NAME=family_emotions_dev
DB_USER=postgres
DB_PASSWORD=your_password
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/family_emotions_dev

# === Redis ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook (для production)

# === Claude AI ===
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# === Логирование ===
LOG_LEVEL=DEBUG
SENTRY_DSN=your_sentry_dsn (опционально)
```

#### 5. Запуск внешних сервисов

**Вариант A: Docker Compose (рекомендуется)**
```bash
# Запускаем только внешние сервисы (PostgreSQL, Redis)
docker-compose up -d postgres redis

# Проверяем статус
docker-compose ps

# Логи сервисов
docker-compose logs postgres
docker-compose logs redis
```

**Вариант B: Локальная установка**
```bash
# PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создаем пользователя и БД
sudo -u postgres createuser --superuser $USER
sudo -u postgres createdb family_emotions_dev

# Redis (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Проверяем подключение
psql -h localhost -U postgres -d family_emotions_dev -c "SELECT version();"
redis-cli ping
```

#### 6. Настройка базы данных

```bash
# Запускаем миграции Alembic
alembic upgrade head

# Или альтернативный способ
python -c "
from src.infrastructure.database.database import init_database
import asyncio
asyncio.run(init_database())
"

# Проверяем созданные таблицы
psql -h localhost -U postgres -d family_emotions_dev -c "\dt"

# Опционально: загружаем тестовые данные
psql -h localhost -U postgres -d family_emotions_dev -f migrations/sample_data.sql
```

#### 7. Запуск приложения

```bash
# Запускаем основное приложение
python src/main.py

# Или с дополнительными параметрами
python src/main.py --env development --log-level DEBUG

# Запускаем с автоперезагрузкой (для разработки)
watchmedo auto-restart --patterns="*.py" --recursive -- python src/main.py

# Проверяем работу бота
curl -X GET "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

#### 8. Тестирование setup

```bash
# Запускаем базовые тесты
pytest tests/unit/test_database.py -v

# Проверяем подключение к внешним сервисам
pytest tests/integration/test_external_services.py -v

# Health check
curl http://localhost:8000/health
```

---

## Docker Compose Setup

### Полный запуск через Docker

```bash
# Клонируем репозиторий
git clone https://github.com/your-org/family-emotions-app.git
cd family-emotions-app

# Настраиваем переменные окружения
cp .env.example .env
# Редактируем .env с вашими значениями

# Запускаем все сервисы
docker-compose up -d

# Проверяем статус всех контейнеров
docker-compose ps

# Проверяем логи приложения
docker-compose logs -f app

# Проверяем здоровье сервисов
curl http://localhost:8000/health
```

### Docker Compose профили

```yaml
# В docker-compose.yml определены профили для разных сценариев

# Только внешние сервисы (для локальной разработки)
docker-compose up -d postgres redis

# С инструментами разработки
docker-compose --profile dev up -d

# Production конфигурация
docker-compose --profile production up -d

# С мониторингом
docker-compose --profile monitoring up -d
```

### Управление контейнерами

```bash
# Перезапуск определенного сервиса
docker-compose restart app

# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (осторожно!)
docker-compose down -v

# Пересборка образов
docker-compose build --no-cache

# Масштабирование сервисов
docker-compose up -d --scale app=2

# Выполнение команд в контейнере
docker-compose exec app bash
docker-compose exec postgres psql -U postgres family_emotions

# Просмотр ресурсов
docker-compose top
docker stats
```

---

## Production Deployment с Coolify

### Подготовка к deployment

#### 1. Подготовка сервера

```bash
# Минимальные требования сервера:
# - 2 vCPU, 4GB RAM, 50GB SSD
# - Ubuntu 22.04 LTS
# - Docker & Docker Compose
# - Coolify установлен

# Подключаемся к серверу
ssh root@your-server-ip

# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Docker (если не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Устанавливаем Coolify
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

#### 2. Настройка Coolify

```bash
# Coolify будет доступен по адресу http://your-server-ip:8000
# Пройдите начальную настройку в веб-интерфейсе

# Подключите GitHub/GitLab репозиторий
# Выберите тип деплоя: Docker Compose

# Настройте домен (опционально)
# Настройте SSL сертификаты (Let's Encrypt)
```

#### 3. Настройка переменных окружения в Coolify

В Coolify dashboard добавьте переменные:

```bash
# === Основные ===
ENVIRONMENT=production
DEBUG=false

# === База данных ===
DB_HOST=postgres
DB_PORT=5432
DB_NAME=family_emotions
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://postgres:your_secure_password_here@postgres:5432/family_emotions

# === Redis ===
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://redis:6379/0

# === Telegram ===
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# === Claude AI ===
ANTHROPIC_API_KEY=sk-ant-api03-your_production_key

# === Безопасность ===
SECRET_KEY=your_very_long_random_secret_key_here
ENCRYPTION_KEY=your_32_character_encryption_key

# === Мониторинг ===
SENTRY_DSN=https://your-sentry-dsn.ingest.sentry.io/project-id
LOG_LEVEL=INFO

# === Limits ===
DAILY_TRANSLATIONS_LIMIT=20
CHECKIN_ENABLED=true
WEEKLY_REPORTS_ENABLED=true
```

#### 4. Создание production docker-compose.yml

Coolify автоматически использует ваш docker-compose.yml, но можно создать специальный файл:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: family-emotions-network
```

### Deployment Process

#### Автоматический deployment

```bash
# Coolify автоматически деплоит при push в main ветку
git add .
git commit -m "feat: готов к production deployment"
git push origin main

# Coolify автоматически:
# 1. Получает новый код
# 2. Собирает Docker образы
# 3. Запускает новые контейнеры
# 4. Перенаправляет трафик (zero-downtime)
# 5. Удаляет старые контейнеры
```

#### Мануальный deployment

```bash
# В Coolify dashboard:
# 1. Перейдите в раздел вашего приложения
# 2. Нажмите "Deploy"
# 3. Выберите commit/branch для деплоя
# 4. Нажмите "Deploy Now"

# Или через CLI (если настроен)
coolify deploy --project family-emotions --branch main
```

### Post-deployment Setup

#### 1. Настройка Telegram Webhook

```bash
# После успешного деплоя настройте webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://your-domain.com/webhook",
         "allowed_updates": ["message", "callback_query"],
         "drop_pending_updates": true
     }'

# Проверяем webhook
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

#### 2. Инициализация базы данных

```bash
# Подключаемся к контейнеру
docker exec -it family-emotions-app-app-1 bash

# Запускаем миграции
alembic upgrade head

# Проверяем структуру БД
python -c "
import asyncio
from src.infrastructure.database.database import get_database_health
print(asyncio.run(get_database_health()))
"

# Выходим из контейнера
exit
```

#### 3. Мониторинг и логи

```bash
# Просмотр логов приложения
docker logs -f family-emotions-app-app-1

# Мониторинг ресурсов
docker stats

# Health check
curl https://your-domain.com/health

# Проверка метрик
curl https://your-domain.com/metrics
```

---

## Переменные окружения

### Полный список переменных

```bash
# =====================================
# ОСНОВНЫЕ НАСТРОЙКИ
# =====================================

# Окружение
ENVIRONMENT=development # development, staging, production
DEBUG=false             # true только для разработки
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR, CRITICAL

# =====================================
# БАЗА ДАННЫХ
# =====================================

# PostgreSQL подключение
DB_HOST=localhost
DB_PORT=5432
DB_NAME=family_emotions
DB_USER=postgres
DB_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:password@localhost:5432/family_emotions

# Настройки пула соединений
DB_POOL_MIN_SIZE=5      # Минимум соединений
DB_POOL_MAX_SIZE=20     # Максимум соединений
DB_POOL_TIMEOUT=30      # Таймаут получения соединения
DB_QUERY_TIMEOUT=60     # Таймаут выполнения запроса

# =====================================
# REDIS
# =====================================

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # Пароль (если установлен)
REDIS_URL=redis://localhost:6379/0

# Настройки Redis
REDIS_MAX_CONNECTIONS=20
REDIS_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=true

# =====================================
# TELEGRAM BOT
# =====================================

# Основные настройки
TELEGRAM_BOT_TOKEN=1234567890:AAE_your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret

# Режим работы бота
TELEGRAM_USE_WEBHOOK=true  # true для production, false для polling
TELEGRAM_POLLING_TIMEOUT=30
TELEGRAM_WEBHOOK_PATH=/webhook

# Ограничения
TELEGRAM_REQUEST_TIMEOUT=30
TELEGRAM_MAX_RETRIES=3

# =====================================
# ANTHROPIC CLAUDE API
# =====================================

ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.7

# Лимиты и таймауты
CLAUDE_REQUEST_TIMEOUT=30
CLAUDE_MAX_RETRIES=2
CLAUDE_RATE_LIMIT_RPM=50  # Requests per minute

# =====================================
# БЕЗОПАСНОСТЬ
# =====================================

# Ключи шифрования (должны быть случайными в production)
SECRET_KEY=your_very_long_random_secret_key_minimum_32_chars
ENCRYPTION_KEY=your_32_character_encryption_key12

# CORS настройки
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
CORS_ALLOW_CREDENTIALS=true

# Rate limiting
RATE_LIMIT_REQUESTS=100    # Запросов в час на пользователя
RATE_LIMIT_WINDOW=3600     # Окно в секундах

# =====================================
# МОНИТОРИНГ
# =====================================

# Sentry для отслеживания ошибок
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_ENVIRONMENT=production

# Метрики
ENABLE_METRICS=true
METRICS_PORT=8001

# Health checks
HEALTH_CHECK_TIMEOUT=5

# =====================================
# БИЗНЕС ЛОГИКА
# =====================================

# Лимиты использования
DAILY_TRANSLATIONS_LIMIT=20      # Для free tier
PREMIUM_TRANSLATIONS_LIMIT=100   # Для premium tier
MAX_CHILDREN_PER_FAMILY=10
MAX_PARENTS_PER_FAMILY=2

# Функции
CHECKIN_ENABLED=true
WEEKLY_REPORTS_ENABLED=true
ANALYTICS_ENABLED=true

# Расписание
DEFAULT_CHECKIN_TIME=20:00
WEEKLY_REPORT_DAY=sunday
CLEANUP_HOUR=2                   # Час для автоочистки данных

# =====================================
# ИНТЕГРАЦИИ (опционально)
# =====================================

# Email (для уведомлений)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true

# Push уведомления
PUSH_SERVICE_KEY=
PUSH_SERVICE_URL=

# Файловое хранилище
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=eu-central-1
AWS_S3_BUCKET=family-emotions-files

# =====================================
# РАЗРАБОТКА
# =====================================

# Hot reload (только для development)
HOT_RELOAD=false
AUTO_RESTART=false

# Тестирование
TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/family_emotions_test
MOCK_EXTERNAL_SERVICES=false

# Debug опции
ENABLE_SQL_ECHO=false           # Логировать SQL запросы
ENABLE_PERFORMANCE_LOGGING=false
PROFILE_REQUESTS=false
```

### Валидация переменных

Создайте скрипт для проверки конфигурации:

```python
# scripts/validate_env.py
import os
import sys
import re
from typing import List, Tuple

def validate_environment() -> List[Tuple[str, str]]:
    """Проверяет корректность переменных окружения."""
    errors = []
    
    # Обязательные переменные
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL', 
        'TELEGRAM_BOT_TOKEN',
        'ANTHROPIC_API_KEY',
        'SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append((var, "Required variable is missing"))
    
    # Проверка формата Telegram токена
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if telegram_token and not re.match(r'^\d+:[A-Za-z0-9_-]+$', telegram_token):
        errors.append(('TELEGRAM_BOT_TOKEN', 'Invalid format'))
    
    # Проверка URL базы данных
    db_url = os.getenv('DATABASE_URL', '')
    if db_url and not db_url.startswith('postgresql://'):
        errors.append(('DATABASE_URL', 'Must start with postgresql://'))
    
    # Проверка Claude API ключа
    claude_key = os.getenv('ANTHROPIC_API_KEY', '')
    if claude_key and not claude_key.startswith('sk-ant-api03-'):
        errors.append(('ANTHROPIC_API_KEY', 'Invalid format'))
    
    # Проверка длины секретного ключа
    secret_key = os.getenv('SECRET_KEY', '')
    if secret_key and len(secret_key) < 32:
        errors.append(('SECRET_KEY', 'Must be at least 32 characters'))
    
    return errors

if __name__ == "__main__":
    errors = validate_environment()
    
    if errors:
        print("❌ Environment validation failed:")
        for var, message in errors:
            print(f"  {var}: {message}")
        sys.exit(1)
    else:
        print("✅ Environment validation passed")
```

Запуск валидации:
```bash
python scripts/validate_env.py
```

---

## База данных

### Настройка PostgreSQL

#### Локальная установка PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-contrib postgresql-client-15

# macOS (с Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Создание пользователя и БД
sudo -u postgres psql
postgres=# CREATE USER family_emotions WITH PASSWORD 'your_password';
postgres=# CREATE DATABASE family_emotions_dev OWNER family_emotions;
postgres=# GRANT ALL PRIVILEGES ON DATABASE family_emotions_dev TO family_emotions;
postgres=# \q

# Проверка подключения
psql -h localhost -U family_emotions -d family_emotions_dev -c "SELECT version();"
```

#### Настройка PostgreSQL для production

```sql
-- postgresql.conf настройки для production
-- /etc/postgresql/15/main/postgresql.conf

# Подключения
max_connections = 100
shared_buffers = 1GB                    # 25% от RAM
effective_cache_size = 3GB              # 75% от RAM

# Логирование
log_statement = 'mod'                   # Логировать изменения
log_min_duration_statement = 1000       # Медленные запросы > 1сек
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '

# Производительность
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100

# Локализация
timezone = 'Europe/Moscow'
lc_messages = 'ru_RU.UTF-8'
lc_monetary = 'ru_RU.UTF-8'
lc_numeric = 'ru_RU.UTF-8'
lc_time = 'ru_RU.UTF-8'
```

#### Миграции Alembic

```bash
# Инициализация Alembic (уже сделано в проекте)
alembic init alembic

# Создание новой миграции
alembic revision --autogenerate -m "Add new table"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1

# История миграций
alembic history --verbose

# Текущая версия
alembic current
```

### Redis Setup

```bash
# Установка Redis
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis
brew services start redis

# Базовая настройка Redis
sudo nano /etc/redis/redis.conf

# Основные настройки:
maxmemory 512mb
maxmemory-policy allkeys-lru
appendonly yes
save 900 1
save 300 10
save 60 10000

# Перезапуск Redis
sudo systemctl restart redis-server

# Проверка
redis-cli ping
# Ответ: PONG
```

---

## Troubleshooting

### Частые проблемы и решения

#### 1. База данных недоступна

```bash
# Проверка статуса PostgreSQL
sudo systemctl status postgresql
# или
docker-compose ps postgres

# Проверка подключения
pg_isready -h localhost -p 5432 -U postgres

# Проверка логов
sudo journalctl -u postgresql -n 50
# или
docker-compose logs postgres

# Проверка настроек
psql -h localhost -U postgres -c "SHOW config_file;"
```

**Решения:**
```bash
# Перезапуск PostgreSQL
sudo systemctl restart postgresql
# или
docker-compose restart postgres

# Проверка прав доступа
ls -la /var/lib/postgresql/15/main/
sudo chown -R postgres:postgres /var/lib/postgresql/15/main/

# Проверка pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Убедитесь что есть строка:
# local   all             postgres                                peer
# host    all             all             127.0.0.1/32            md5
```

#### 2. Redis недоступен

```bash
# Проверка Redis
redis-cli ping
systemctl status redis-server

# Проверка памяти
redis-cli info memory

# Очистка Redis (осторожно!)
redis-cli flushall
```

#### 3. Telegram Bot не отвечает

```bash
# Проверка токена
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Проверка webhook
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# Удаление webhook (для переключения на polling)
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook"

# Установка webhook заново
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/webhook"}'
```

#### 4. Claude API ошибки

```bash
# Проверка ключа API
curl https://api.anthropic.com/v1/models \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01"

# Проверка лимитов
# В логах приложения ищите:
# "rate_limit_exceeded" или "quota_exceeded"

# Альтернативная проверка через Python
python -c "
import os
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
try:
    response = client.messages.create(
        model='claude-3-5-sonnet-20241022',
        max_tokens=10,
        messages=[{'role': 'user', 'content': 'Hi'}]
    )
    print('✅ Claude API работает')
except Exception as e:
    print(f'❌ Ошибка: {e}')
"
```

#### 5. Docker проблемы

```bash
# Проверка статуса контейнеров
docker-compose ps

# Проверка логов
docker-compose logs app
docker-compose logs --tail=50 -f app

# Пересборка образов
docker-compose build --no-cache app

# Очистка Docker
docker system prune -a
docker volume prune

# Проверка ресурсов
docker stats
df -h  # Проверка места на диске
```

#### 6. Проблемы с портами

```bash
# Проверка занятых портов
netstat -tulpn | grep :8000
lsof -i :8000

# Убить процесс на порту
sudo kill -9 $(lsof -ti:8000)

# Изменение порта в docker-compose.yml
services:
  app:
    ports:
      - "8001:8000"  # внешний:внутренний
```

### Логи и отладка

#### Структура логов

```python
# Пример лога приложения
{
    "timestamp": "2025-08-14T12:00:00Z",
    "level": "INFO",
    "logger": "family_emotions.telegram",
    "message": "User message processed",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "telegram_id": 123456789,
    "processing_time_ms": 1234,
    "request_id": "req-abc123"
}
```

#### Полезные команды для отладки

```bash
# Мониторинг логов в реальном времени
tail -f logs/app.log | jq .

# Поиск ошибок за последний час
grep -E "(ERROR|CRITICAL)" logs/app.log | tail -20

# Анализ производительности
grep "processing_time_ms" logs/app.log | \
  jq -r '.processing_time_ms' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "ms"}'

# Топ пользователей по активности
grep "user_message" logs/app.log | \
  jq -r '.telegram_id' | \
  sort | uniq -c | sort -nr | head -10

# Проверка health checks
while true; do
  curl -s http://localhost:8000/health | jq '.status'
  sleep 30
done
```

### Performance Monitoring

```bash
# Мониторинг системных ресурсов
htop
iostat -x 1
free -h
df -h

# Мониторинг PostgreSQL
# Подключение к БД
psql -h localhost -U postgres -d family_emotions

-- Активные соединения
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Медленные запросы
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Размеры таблиц
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Мониторинг Redis
redis-cli info stats
redis-cli info memory
redis-cli --latency-history -i 1
```

---

## Maintenance & Updates

### Регулярное обслуживание

```bash
# Еженедельные задачи
# 1. Обновление зависимостей
pip list --outdated
pip-review --auto

# 2. Очистка старых логов
find logs/ -name "*.log" -mtime +7 -delete

# 3. Анализ размера БД
psql -c "SELECT pg_size_pretty(pg_database_size('family_emotions'));"

# 4. Бэкап БД
pg_dump family_emotions | gzip > backup_$(date +%Y%m%d).sql.gz

# 5. Проверка безопасности
docker run --rm -v $(pwd):/app clair-scanner --ip=localhost family-emotions:latest
```

### Обновление в production

```bash
# 1. Подготовка
git checkout main
git pull origin main

# 2. Тестирование локально
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# 3. Деплой через Coolify
# (автоматически при push в main)

# 4. Проверка после деплоя
curl https://your-domain.com/health
curl https://your-domain.com/metrics

# 5. Мониторинг логов
docker logs -f family-emotions-app-app-1 | grep ERROR
```

---

*Setup Guide Version: 1.0*  
*Last Updated: August 14, 2025*  
*Tested with: Python 3.11, PostgreSQL 15, Redis 7, Docker 24.0*