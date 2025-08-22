# 🚀 COOLIFY SETUP GUIDE - Family Emotions App

## Полная настройка проекта в Coolify (PostgreSQL + Redis + Bot)

---

## 📊 ШАГ 1: СОЗДАНИЕ БАЗЫ ДАННЫХ PostgreSQL

### 1.1 Создание PostgreSQL контейнера

1. **В Coolify Dashboard:**
   ```
   → Resources
   → + New Resource
   → Database
   → PostgreSQL
   ```

2. **Настройки PostgreSQL:**
   ```yaml
   Name: family-emotions-db
   Database: family_emotions
   Username: postgres
   Password: [создайте надежный пароль, например: FamEmo2025SecurePass!]
   Port: 5432
   Version: 15-alpine (легче по размеру)
   ```

3. **Дополнительные настройки:**
   ```yaml
   Volume Size: 5GB (достаточно для MVP)
   Backup: Enable daily backups ✓
   Public Port: Оставьте пустым (для безопасности)
   ```

4. **Нажмите "Deploy"** и подождите 1-2 минуты

5. **Получите Connection String:**
   - После деплоя нажмите на созданную БД
   - Скопируйте "Internal Connection URL":
   ```
   postgresql://postgres:YOUR_PASSWORD@family-emotions-db:5432/family_emotions
   ```
   
   ⚠️ **ВАЖНО**: Используйте именно Internal URL для связи между контейнерами!

### 1.2 Создание таблиц в PostgreSQL

1. **В Coolify откройте терминал БД:**
   ```
   → Resources → family-emotions-db
   → Terminal (или Execute Command)
   ```

2. **Подключитесь к базе:**
   ```bash
   psql -U postgres -d family_emotions
   ```

3. **Создайте таблицы (скопируйте и вставьте весь блок):**

```sql
-- Family Emotions App Database Schema
-- Версия для Coolify PostgreSQL

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица пользователей (родители)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}'::jsonb,
    subscription_type VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE
);

-- Таблица детей
CREATE TABLE IF NOT EXISTS children (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 1 AND age <= 18),
    personality_traits TEXT,
    special_needs TEXT,
    interests TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

-- Члены семьи для чек-инов
CREATE TABLE IF NOT EXISTS family_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(255),
    telegram_id BIGINT,
    age INTEGER CHECK (age >= 1 AND age <= 99),
    role VARCHAR(50) NOT NULL CHECK (role IN ('parent', 'child', 'other')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, telegram_id)
);

-- История переводов эмоций
CREATE TABLE IF NOT EXISTS emotion_translations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    child_id INTEGER REFERENCES children(id) ON DELETE SET NULL,
    original_phrase TEXT NOT NULL,
    context TEXT,
    situation_context VARCHAR(500),
    interpretation TEXT NOT NULL,
    suggested_responses JSONB DEFAULT '[]'::jsonb,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    user_feedback INTEGER CHECK (user_feedback >= 1 AND user_feedback <= 5),
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Чек-ины
CREATE TABLE IF NOT EXISTS checkins (
    id SERIAL PRIMARY KEY,
    family_member_id INTEGER NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    checkin_date DATE NOT NULL DEFAULT CURRENT_DATE,
    questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    answers JSONB DEFAULT '[]'::jsonb,
    mood_score INTEGER CHECK (mood_score >= 1 AND mood_score <= 5),
    areas_of_concern TEXT[],
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    reminder_sent BOOLEAN DEFAULT FALSE,
    UNIQUE(family_member_id, checkin_date)
);

-- Еженедельные отчеты
CREATE TABLE IF NOT EXISTS weekly_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    family_mood VARCHAR(50) CHECK (family_mood IN ('positive', 'neutral', 'needs_attention')),
    mood_trend VARCHAR(20) CHECK (mood_trend IN ('improving', 'stable', 'declining')),
    insights JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    highlights JSONB DEFAULT '[]'::jsonb,
    generated_by_ai BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, week_start)
);

-- Аналитика использования
CREATE TABLE IF NOT EXISTS usage_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    feature VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    session_id UUID DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Настройки уведомлений
CREATE TABLE IF NOT EXISTS notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkin_time TIME DEFAULT '20:00',
    checkin_enabled BOOLEAN DEFAULT TRUE,
    weekly_report_day INTEGER DEFAULT 0 CHECK (weekly_report_day >= 0 AND weekly_report_day <= 6),
    weekly_report_enabled BOOLEAN DEFAULT TRUE,
    tips_enabled BOOLEAN DEFAULT TRUE,
    language VARCHAR(10) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Кэш для Claude API
CREATE TABLE IF NOT EXISTS claude_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    response JSONB NOT NULL,
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    hit_count INTEGER DEFAULT 0
);

-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ

-- Основные индексы
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_last_active ON users(last_active);
CREATE INDEX idx_children_user_id ON children(user_id);
CREATE INDEX idx_family_members_user_id ON family_members(user_id);
CREATE INDEX idx_family_members_telegram_id ON family_members(telegram_id) WHERE telegram_id IS NOT NULL;

-- Индексы для эмоций
CREATE INDEX idx_emotion_translations_user_id ON emotion_translations(user_id);
CREATE INDEX idx_emotion_translations_child_id ON emotion_translations(child_id) WHERE child_id IS NOT NULL;
CREATE INDEX idx_emotion_translations_created_at ON emotion_translations(created_at DESC);
CREATE INDEX idx_emotion_translations_feedback ON emotion_translations(user_feedback) WHERE user_feedback IS NOT NULL;

-- Индексы для чек-инов
CREATE INDEX idx_checkins_family_member_id ON checkins(family_member_id);
CREATE INDEX idx_checkins_date ON checkins(checkin_date DESC);
CREATE INDEX idx_checkins_completed ON checkins(completed);
CREATE INDEX idx_checkins_sent_at ON checkins(sent_at DESC);

-- Индексы для отчетов
CREATE INDEX idx_weekly_reports_user_id ON weekly_reports(user_id);
CREATE INDEX idx_weekly_reports_week_start ON weekly_reports(week_start DESC);

-- Индексы для аналитики
CREATE INDEX idx_usage_analytics_user_id ON usage_analytics(user_id);
CREATE INDEX idx_usage_analytics_created_at ON usage_analytics(created_at DESC);
CREATE INDEX idx_usage_analytics_event_type ON usage_analytics(event_type);
CREATE INDEX idx_usage_analytics_session ON usage_analytics(session_id);

-- Индекс для кэша
CREATE INDEX idx_claude_cache_expires ON claude_cache(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_claude_cache_key ON claude_cache(cache_key);

-- ФУНКЦИИ И ТРИГГЕРЫ

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для notification_settings
CREATE TRIGGER update_notification_settings_updated_at 
    BEFORE UPDATE ON notification_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Функция для очистки старого кэша
CREATE OR REPLACE FUNCTION cleanup_expired_cache() 
RETURNS void AS $$
BEGIN
    DELETE FROM claude_cache WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Представления для удобства

-- Активные пользователи за последние 7 дней
CREATE VIEW active_users_weekly AS
SELECT 
    u.id,
    u.name,
    u.telegram_username,
    u.last_active,
    COUNT(DISTINCT et.id) as translations_count,
    COUNT(DISTINCT c.id) as checkins_count
FROM users u
LEFT JOIN emotion_translations et ON u.id = et.user_id 
    AND et.created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
LEFT JOIN family_members fm ON u.id = fm.user_id
LEFT JOIN checkins c ON fm.id = c.family_member_id 
    AND c.sent_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
WHERE u.last_active > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY u.id, u.name, u.telegram_username, u.last_active;

-- Статистика по семьям
CREATE VIEW family_statistics AS
SELECT 
    u.id as user_id,
    u.name as parent_name,
    COUNT(DISTINCT c.id) as children_count,
    COUNT(DISTINCT fm.id) as family_members_count,
    MAX(et.created_at) as last_emotion_translation,
    MAX(ch.sent_at) as last_checkin
FROM users u
LEFT JOIN children c ON u.id = c.user_id
LEFT JOIN family_members fm ON u.id = fm.user_id AND fm.is_active = true
LEFT JOIN emotion_translations et ON u.id = et.user_id
LEFT JOIN checkins ch ON fm.id = ch.family_member_id
GROUP BY u.id, u.name;

-- ПРОВЕРКА СОЗДАНИЯ ТАБЛИЦ
DO $$
BEGIN
    RAISE NOTICE 'Database setup completed successfully!';
    RAISE NOTICE 'Tables created: %', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public');
    RAISE NOTICE 'Indexes created: %', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
END $$;
```

4. **Проверьте создание таблиц:**
   ```sql
   \dt
   ```
   Должно показать 10+ таблиц

5. **Выйдите из psql:**
   ```sql
   \q
   ```

---

## 💾 ШАГ 2: СОЗДАНИЕ REDIS В COOLIFY

### 2.1 Создание Redis контейнера

1. **В Coolify Dashboard:**
   ```
   → Resources
   → + New Resource  
   → Database
   → Redis
   ```

2. **Настройки Redis:**
   ```yaml
   Name: family-emotions-redis
   Password: [создайте пароль, например: RedisSecure2025!]
   Port: 6379
   Version: 7-alpine
   ```

3. **Настройки памяти:**
   ```yaml
   Max Memory: 100MB (достаточно для кэширования)
   Eviction Policy: allkeys-lru
   Persistence: Enable AOF ✓
   ```

4. **Deploy** и подождите 30 секунд

5. **Получите Connection String:**
   ```
   redis://:YOUR_PASSWORD@family-emotions-redis:6379/0
   ```

---

## 🤖 ШАГ 3: НАСТРОЙКА TELEGRAM БОТА

1. **Откройте Telegram → @BotFather**

2. **Создайте бота:**
   ```
   /newbot
   Name: Family Emotions Bot
   Username: family_emotions_bot (или другой уникальный)
   ```

3. **Сохраните токен:** 
   ```
   7234567890:ABCdefGHIjklMNOpqrsTUVwxyz...
   ```

4. **Настройте команды бота:**
   ```
   /setcommands
   Выберите вашего бота
   Вставьте:
   
   start - Начать работу с ботом
   menu - Главное меню
   translate - Перевести эмоцию ребенка
   checkin - Ежедневный чек-ин
   settings - Настройки
   help - Помощь
   ```

---

## 🚀 ШАГ 4: ДЕПЛОЙ ПРИЛОЖЕНИЯ В COOLIFY

### 4.1 Создание приложения

1. **В Coolify Dashboard:**
   ```
   → Projects → Default (или создайте новый)
   → + New Resource
   → Application
   ```

2. **Выберите источник:**
   ```
   → Public Repository
   Repository URL: https://github.com/gbalchidi/family_emotions_app
   Branch: main
   ```

3. **Настройки сборки:**
   ```yaml
   Build Pack: Dockerfile
   Base Directory: /
   Dockerfile Location: ./Dockerfile
   Watch for Changes: ✓ (для auto-deploy)
   ```

### 4.2 Environment Variables

1. **Нажмите "Environment Variables"**

2. **Добавьте следующие переменные:**

```bash
# ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ

# Окружение
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Telegram Bot (ваш токен от BotFather)
TELEGRAM_BOT_TOKEN=7234567890:ABCdefGHIjklMNOpqrsTUVwxyz...

# База данных (Internal URL из PostgreSQL в Coolify)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@family-emotions-db:5432/family_emotions

# Redis (Internal URL из Redis в Coolify)
REDIS_URL=redis://:YOUR_PASSWORD@family-emotions-redis:6379/0

# Claude AI (получите на console.anthropic.com)
CLAUDE_API_KEY=sk-ant-api03-xxxxx...
CLAUDE_MODEL=claude-3-5-sonnet-20240620
CLAUDE_MAX_TOKENS=1024
CLAUDE_TEMPERATURE=0.7

# Безопасность (сгенерируются автоматически, но можно задать свои)
SECRET_KEY=your-very-long-secret-key-at-least-32-characters
ENCRYPTION_KEY=your-32-character-encryption-key

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=100
RATE_LIMIT_EMOTIONS_PER_DAY=20

# Опциональные
SENTRY_DSN=  # оставьте пустым если нет
```

### 4.3 Сетевые настройки

1. **В разделе "Networking":**
   ```yaml
   Port: 8000
   Expose Port: ✓
   ```

2. **Health Check:**
   ```yaml
   Health Check Path: /health
   Health Check Interval: 30s
   ```

### 4.4 Ресурсы

1. **В разделе "Resources":**
   ```yaml
   CPU: 0.5-1 vCPU
   Memory: 512MB-1GB
   Storage: 1GB
   ```

### 4.5 Запуск

1. **Нажмите "Save" для сохранения настроек**

2. **Нажмите "Deploy"**

3. **Следите за логами:**
   ```
   → Deployments → View Logs
   ```

4. **Процесс займет 3-5 минут:**
   - Building Docker image
   - Pushing to registry
   - Deploying container
   - Health check

---

## ✅ ШАГ 5: ПРОВЕРКА РАБОТЫ

### 5.1 Проверка здоровья системы

1. **В Coolify посмотрите статус:**
   - PostgreSQL: Running ✅
   - Redis: Running ✅
   - Application: Running ✅

2. **Проверьте логи приложения:**
   ```
   → Application → Logs
   
   Должны увидеть:
   - "Starting Family Emotions App"
   - "Database connected successfully"
   - "Redis connected successfully"
   - "Telegram bot started"
   ```

### 5.2 Проверка бота

1. **Откройте Telegram**
2. **Найдите вашего бота** по username
3. **Отправьте `/start`**
4. **Пройдите onboarding**

### 5.3 Проверка базы данных

1. **В Coolify откройте PostgreSQL terminal:**
   ```sql
   psql -U postgres -d family_emotions
   SELECT COUNT(*) FROM users;
   ```
   После `/start` должна быть минимум 1 запись

---

## 🔧 TROUBLESHOOTING

### Проблема: Application не стартует

**Проверьте:**
1. Environment variables все заполнены
2. DATABASE_URL использует internal hostname (family-emotions-db, не localhost)
3. REDIS_URL использует internal hostname
4. Логи на ошибки подключения

### Проблема: Бот не отвечает

**Проверьте:**
1. TELEGRAM_BOT_TOKEN правильный
2. В логах нет ошибок Telegram API
3. Бот не заблокирован в вашем регионе

### Проблема: Database connection failed

**Решение:**
```bash
# Проверьте что БД запущена
docker ps | grep postgres

# Проверьте подключение
docker exec -it [postgres-container-id] psql -U postgres -d family_emotions -c "SELECT 1;"

# Проверьте что используете внутренний hostname
# ✅ Правильно: family-emotions-db:5432
# ❌ Неправильно: localhost:5432 или IP:5432
```

### Проблема: Redis connection failed

**Решение:**
```bash
# Проверьте Redis
docker ps | grep redis

# Тест подключения
docker exec -it [redis-container-id] redis-cli ping
```

---

## 📊 МОНИТОРИНГ

### Настройка мониторинга в Coolify

1. **Metrics endpoint:**
   ```
   http://your-app.coolify.domain/metrics
   ```

2. **Health endpoint:**
   ```
   http://your-app.coolify.domain/health
   ```

3. **Настройка алертов:**
   - CPU > 80%
   - Memory > 80%
   - Health check fails

### Просмотр логов

```bash
# Все логи приложения
docker logs -f [container-id]

# Последние 100 строк
docker logs --tail 100 [container-id]

# Логи за последний час
docker logs --since 1h [container-id]
```

---

## 🎉 ГОТОВО!

Ваш Family Emotions Bot теперь работает полностью в Coolify!

**Что у вас есть:**
- ✅ PostgreSQL база данных с автобэкапами
- ✅ Redis для кэширования
- ✅ Telegram бот в production
- ✅ Автоматический деплой при push в GitHub
- ✅ Мониторинг и логирование

**Следующие шаги:**
1. Протестируйте все функции бота
2. Настройте автоматические бэкапы БД
3. Добавьте кастомный домен (опционально)
4. Настройте CI/CD для автодеплоя

---

## 📚 ПОЛЕЗНЫЕ КОМАНДЫ

### Бэкап базы данных
```bash
# В Coolify terminal PostgreSQL
pg_dump -U postgres family_emotions > backup_$(date +%Y%m%d).sql
```

### Восстановление базы
```bash
psql -U postgres family_emotions < backup.sql
```

### Очистка Redis кэша
```bash
# В Redis terminal
redis-cli FLUSHDB
```

### Рестарт приложения
```bash
# В Coolify Dashboard
→ Application → Restart
```

---

**Нужна помощь?** Создайте Issue на GitHub или напишите в Telegram!