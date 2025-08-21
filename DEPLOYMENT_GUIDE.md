# 🚀 DEPLOYMENT GUIDE - Family Emotions App

## 📋 Полное руководство по запуску проекта

### ВАРИАНТ 1: Supabase (Облачная база данных) - РЕКОМЕНДУЕТСЯ ДЛЯ НАЧАЛА

#### 1️⃣ Создание базы данных в Supabase

1. **Регистрация на Supabase:**
   ```
   1. Перейдите на https://supabase.com
   2. Нажмите "Start your project"
   3. Войдите через GitHub аккаунт
   4. Нажмите "New Project"
   ```

2. **Настройки проекта:**
   ```
   Project name: family-emotions
   Database Password: [создайте надежный пароль]
   Region: Frankfurt (eu-central-1)
   Pricing Plan: Free tier (достаточно для MVP)
   ```

3. **Получение credentials (через 2-3 минуты):**
   - Зайдите в Settings → Database
   - Скопируйте:
     - `Host`: xxx.supabase.co
     - `Database name`: postgres
     - `Port`: 5432
     - `User`: postgres
     - `Password`: [ваш пароль]

4. **Connection string будет выглядеть так:**
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```

#### 2️⃣ Создание таблиц в Supabase

1. **Откройте SQL Editor** в Supabase Dashboard
2. **Скопируйте и выполните этот SQL:**

```sql
-- Создание таблиц для Family Emotions App

-- Пользователи (родители)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Дети
CREATE TABLE children (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL,
    personality_traits TEXT,
    special_needs TEXT,
    interests TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Члены семьи для чек-инов
CREATE TABLE family_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    telegram_username VARCHAR(255),
    age INTEGER,
    role VARCHAR(50), -- 'parent', 'child'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- История переводчика эмоций
CREATE TABLE emotion_translations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    child_id INTEGER REFERENCES children(id) ON DELETE SET NULL,
    original_phrase TEXT NOT NULL,
    context VARCHAR(500),
    interpretation TEXT NOT NULL,
    suggested_responses JSONB,
    confidence_score FLOAT,
    user_feedback INTEGER, -- 1-5 rating
    created_at TIMESTAMP DEFAULT NOW()
);

-- Чек-ины
CREATE TABLE checkins (
    id SERIAL PRIMARY KEY,
    family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,
    answers JSONB,
    mood_score INTEGER, -- 1-5
    completed BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Еженедельные отчеты
CREATE TABLE weekly_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    family_mood VARCHAR(50),
    insights JSONB,
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Аналитика использования
CREATE TABLE usage_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    feature VARCHAR(50), -- 'translator', 'checkin'
    action VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Создание индексов для производительности
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_emotion_translations_user_id ON emotion_translations(user_id);
CREATE INDEX idx_emotion_translations_created_at ON emotion_translations(created_at);
CREATE INDEX idx_checkins_family_member_id ON checkins(family_member_id);
CREATE INDEX idx_checkins_sent_at ON checkins(sent_at);
CREATE INDEX idx_usage_analytics_user_id ON usage_analytics(user_id);
CREATE INDEX idx_usage_analytics_created_at ON usage_analytics(created_at);

-- Row Level Security (RLS) - опционально для безопасности
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotion_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkins ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_analytics ENABLE ROW LEVEL SECURITY;
```

3. **Проверьте создание таблиц:**
   - Перейдите в Table Editor
   - Должны появиться все 7 таблиц

---

### ВАРИАНТ 2: Собственный PostgreSQL на Coolify

#### 1️⃣ Установка PostgreSQL через Coolify

1. **В Coolify Dashboard:**
   ```
   1. Нажмите "New Resource"
   2. Выберите "Database"
   3. Выберите "PostgreSQL"
   4. Настройки:
      - Name: family-emotions-db
      - Database: family_emotions
      - Username: postgres
      - Password: [создайте надежный]
      - Version: 15
   5. Нажмите "Deploy"
   ```

2. **Получите connection string:**
   ```
   postgresql://postgres:[PASSWORD]@[COOLIFY_IP]:5432/family_emotions
   ```

3. **Создайте таблицы:**
   - Подключитесь к базе через Coolify terminal или pgAdmin
   - Выполните SQL из варианта 1

---

## 🔧 НАСТРОЙКА ОСТАЛЬНЫХ СЕРВИСОВ

### 1️⃣ Redis (для кэширования)

**Вариант A: Использовать Redis в Coolify**
```bash
1. New Resource → Database → Redis
2. Name: family-emotions-redis
3. Password: [создайте пароль]
4. Deploy
```

**Вариант B: Использовать Upstash (бесплатный облачный Redis)**
```
1. Зайдите на https://upstash.com
2. Create Database
3. Name: family-emotions
4. Region: EU-WEST-1
5. Скопируйте Redis URL
```

### 2️⃣ Telegram Bot Token

1. **Откройте Telegram**
2. **Найдите @BotFather**
3. **Отправьте команды:**
   ```
   /newbot
   Название: Family Emotions Bot
   Username: family_emotions_bot (или другой уникальный)
   ```
4. **Сохраните токен:** `7234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 3️⃣ Claude API Key

1. **Зайдите на** https://console.anthropic.com
2. **Создайте аккаунт** (нужна карта для верификации)
3. **API Keys → Create Key**
4. **Сохраните ключ:** `sk-ant-api03-xxxxx...`

---

## 📝 СОЗДАНИЕ .env ФАЙЛА

Создайте файл `.env` в корне проекта:

```bash
# PRODUCTION CONFIGURATION
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Telegram Bot
TELEGRAM_BOT_TOKEN=7234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database (Supabase)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxx.supabase.co:5432/postgres

# Redis (Upstash или Coolify)
REDIS_URL=redis://default:YOUR_PASSWORD@redis-12345.upstash.io:12345

# Claude AI
CLAUDE_API_KEY=sk-ant-api03-xxxxx...
CLAUDE_MODEL=claude-3-5-sonnet-20240620

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Security (сгенерируйте случайные строки)
SECRET_KEY=your-secret-key-at-least-32-characters-long-abc123
ENCRYPTION_KEY=your-32-character-encryption-key

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=100
RATE_LIMIT_EMOTIONS_PER_DAY=20

# Monitoring (опционально)
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

---

## 🐳 DEPLOYMENT НА COOLIFY

### 1️⃣ Подготовка проекта

1. **Убедитесь что все закоммичено в GitHub:**
   ```bash
   git add .
   git commit -m "Add production configuration"
   git push origin main
   ```

### 2️⃣ Настройка в Coolify

1. **Создайте новое приложение:**
   ```
   New Project → New Resource → Application
   ```

2. **Выберите источник:**
   ```
   Public Repository
   URL: https://github.com/gbalchidi/family_emotions_app
   Branch: main
   ```

3. **Настройки сборки:**
   ```
   Build Pack: Dockerfile
   Dockerfile Path: ./Dockerfile
   Port: 8000
   ```

4. **Environment Variables:**
   - Нажмите "Environment Variables"
   - Добавьте все переменные из .env файла

5. **Настройте домен (опционально):**
   ```
   Domains → Add Domain
   Domain: bot.yourdomain.com
   Generate SSL: ✓
   ```

### 3️⃣ Запуск

1. **Нажмите "Deploy"**
2. **Дождитесь сборки** (5-10 минут)
3. **Проверьте логи** на ошибки

---

## ✅ ПРОВЕРКА РАБОТЫ

### 1️⃣ Проверьте бота в Telegram

1. Найдите вашего бота по username
2. Отправьте `/start`
3. Пройдите onboarding

### 2️⃣ Проверьте базу данных

**В Supabase:**
- Table Editor → users
- Должна появиться запись после `/start`

### 3️⃣ Проверьте логи

**В Coolify:**
- Application → Logs
- Должны быть сообщения о запуске

---

## 🚨 TROUBLESHOOTING

### Проблема: Бот не отвечает
```bash
✓ Проверьте TELEGRAM_BOT_TOKEN
✓ Проверьте логи в Coolify
✓ Убедитесь что приложение запущено
```

### Проблема: Database connection failed
```bash
✓ Проверьте DATABASE_URL
✓ Проверьте что таблицы созданы
✓ Проверьте firewall/network settings
```

### Проблема: Claude API errors
```bash
✓ Проверьте CLAUDE_API_KEY
✓ Проверьте баланс в Anthropic Console
✓ Проверьте rate limits
```

---

## 📊 МОНИТОРИНГ

### Health Check Endpoint
```
https://your-domain.com/health
```

### Метрики Prometheus
```
https://your-domain.com/metrics
```

### Логи в реальном времени
```bash
# В Coolify
Application → Logs → Follow
```

---

## 🎉 ГОТОВО!

После выполнения всех шагов ваш бот должен работать в production!

**Следующие шаги:**
1. Протестируйте все функции
2. Настройте мониторинг
3. Сделайте backup базы данных
4. Начните soft launch с друзьями

---

## 💡 ПОЛЕЗНЫЕ КОМАНДЫ

### Локальный запуск для разработки
```bash
# Установка зависимостей
poetry install

# Запуск локально
python main.py
```

### Docker команды
```bash
# Сборка образа
docker build -t family-emotions .

# Запуск контейнера
docker run --env-file .env family-emotions
```

### База данных
```bash
# Бэкап базы (Supabase)
pg_dump DATABASE_URL > backup.sql

# Восстановление
psql DATABASE_URL < backup.sql
```

---

## 📞 ПОДДЕРЖКА

Если возникли проблемы:
1. Проверьте логи
2. Проверьте environment variables
3. Создайте Issue на GitHub
4. Спросите в Telegram чате проекта

Удачного запуска! 🚀