# Family Emotions App - Database Schema Documentation

## Overview

Family Emotions App использует PostgreSQL 15 в качестве основной базы данных с поддержкой JSONB для гибкого хранения полуструктурированных данных. Схема следует принципам Domain-Driven Design с четким разделением агрегатов.

**Database**: PostgreSQL 15+  
**Extensions**: uuid-ossp, pgcrypto  
**Character Set**: UTF-8  
**Collation**: ru_RU.UTF-8

## Database Design Principles

### 1. Domain-Driven Design
- Таблицы группируются по bounded contexts
- Агрегаты имеют четкие границы транзакций
- Внешние ключи только внутри агрегата

### 2. Event Sourcing (для критичных агрегатов)
- Все изменения в check-ins сохраняются как события
- Возможность восстановления состояния из событий
- Полный аудит всех операций

### 3. GDPR Compliance
- Минимальный набор персональных данных
- Автоматическое удаление через 90 дней
- Шифрование чувствительной информации

---

## Core Tables

### users
Основная таблица пользователей (родителей)

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    language_code CHAR(2) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    onboarding_completed BOOLEAN DEFAULT FALSE,
    subscription_plan VARCHAR(20) DEFAULT 'free' CHECK (subscription_plan IN ('free', 'premium')),
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- Soft delete для GDPR
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Optimistic locking
    version INTEGER DEFAULT 1
);

-- Indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_last_active ON users(last_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Trigger для обновления last_active
CREATE OR REPLACE FUNCTION update_last_active()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_active = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_last_active
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_last_active();
```

**Поля settings JSONB:**
```json
{
  "notification_settings": {
    "checkin_reminders": true,
    "weekly_reports": true,
    "urgent_alerts": true
  },
  "privacy_settings": {
    "data_sharing": false,
    "analytics_tracking": true
  },
  "ui_preferences": {
    "theme": "light",
    "language": "ru"
  }
}
```

---

### families
Семейные единицы (aggregate root)

```sql
CREATE TABLE families (
    family_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_by UUID NOT NULL REFERENCES users(user_id),
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    subscription_plan VARCHAR(20) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT chk_family_name_length CHECK (char_length(trim(name)) >= 2)
);

-- Indexes
CREATE INDEX idx_families_created_by ON families(created_by);
CREATE INDEX idx_families_created_at ON families(created_at);

-- Trigger для updated_at
CREATE TRIGGER trigger_families_updated_at
    BEFORE UPDATE ON families
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
```

**Family settings JSONB:**
```json
{
  "language": "ru",
  "timezone": "Europe/Moscow",
  "checkin_time": "20:00",
  "report_day": "sunday",
  "notifications_enabled": true,
  "checkin_reminders": {
    "enabled": true,
    "reminder_minutes": [30, 10]
  },
  "privacy": {
    "data_retention_days": 90,
    "share_anonymous_analytics": true
  }
}
```

---

### parents
Родители в семье

```sql
CREATE TABLE parents (
    parent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id),
    role VARCHAR(20) NOT NULL DEFAULT 'primary' CHECK (role IN ('primary', 'secondary')),
    permissions TEXT[] DEFAULT ARRAY['read', 'write']::TEXT[],
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(family_id, user_id)
);

-- Constraint: максимум 2 родителя в семье
CREATE OR REPLACE FUNCTION check_parents_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM parents WHERE family_id = NEW.family_id) >= 2 THEN
        RAISE EXCEPTION 'Максимум 2 родителя в семье';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_parents_limit
    BEFORE INSERT ON parents
    FOR EACH ROW
    EXECUTE FUNCTION check_parents_limit();

-- Indexes
CREATE INDEX idx_parents_family_id ON parents(family_id);
CREATE INDEX idx_parents_user_id ON parents(user_id);
```

**Permissions:**
- `read` - Просмотр данных семьи
- `write` - Изменение данных детей
- `admin` - Управление семьей и родителями
- `reports` - Доступ к аналитике

---

### children
Дети в семье

```sql
CREATE TABLE children (
    child_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    birth_date DATE NOT NULL,
    avatar_url VARCHAR(500),
    personality_traits JSONB DEFAULT '[]'::jsonb,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_child_age CHECK (
        birth_date <= CURRENT_DATE - INTERVAL '3 years' AND 
        birth_date >= CURRENT_DATE - INTERVAL '18 years'
    ),
    CONSTRAINT chk_child_name_length CHECK (char_length(trim(name)) >= 1)
);

-- Constraint: максимум 10 детей в семье
CREATE OR REPLACE FUNCTION check_children_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM children WHERE family_id = NEW.family_id AND deleted_at IS NULL) >= 10 THEN
        RAISE EXCEPTION 'Максимум 10 детей в семье';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_children_limit
    BEFORE INSERT ON children
    FOR EACH ROW
    EXECUTE FUNCTION check_children_limit();

-- Indexes
CREATE INDEX idx_children_family_id ON children(family_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_children_birth_date ON children(birth_date);

-- View для подсчета возраста
CREATE VIEW children_with_age AS
SELECT 
    child_id,
    family_id,
    name,
    birth_date,
    DATE_PART('year', AGE(birth_date)) AS age,
    avatar_url,
    personality_traits,
    added_at
FROM children
WHERE deleted_at IS NULL;
```

**Personality traits JSONB:**
```json
[
  "активный",
  "эмоциональный", 
  "любознательный",
  "застенчивый",
  "творческий"
]
```

---

## Emotion Context

### emotion_entries
История переводов эмоций

```sql
CREATE TABLE emotion_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(child_id),
    original_phrase TEXT NOT NULL,
    processed_emotion JSONB NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Для производительности поиска
    search_vector tsvector,
    
    CONSTRAINT chk_phrase_length CHECK (char_length(trim(original_phrase)) >= 5)
);

-- Full-text search
CREATE INDEX idx_emotion_entries_search ON emotion_entries USING gin(search_vector);

-- Trigger для обновления search_vector
CREATE OR REPLACE FUNCTION update_emotion_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('russian', NEW.original_phrase);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_emotion_search_vector
    BEFORE INSERT OR UPDATE ON emotion_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_emotion_search_vector();

-- Indexes
CREATE INDEX idx_emotion_entries_family_child ON emotion_entries(family_id, child_id);
CREATE INDEX idx_emotion_entries_created_at ON emotion_entries(created_at);
CREATE INDEX idx_emotion_entries_feedback ON emotion_entries(user_feedback) WHERE user_feedback IS NOT NULL;

-- Partitioning по месяцам для производительности
CREATE TABLE emotion_entries_y2025m08 PARTITION OF emotion_entries 
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
```

**Processed emotion JSONB:**
```json
{
  "category": "frustration",
  "intensity": "high",
  "confidence_score": 0.89,
  "interpretation": {
    "emotional_state": "фрустрация и стыд",
    "hidden_meaning": "Мне стыдно за плохую оценку...",
    "underlying_needs": ["поддержка без осуждения", "помощь в решении проблемы"]
  },
  "suggested_responses": [
    {
      "type": "empathetic",
      "text": "Вижу, что тебе сейчас тяжело...",
      "explanation": "Признает эмоции...",
      "expected_outcome": "Снижение защитной реакции"
    }
  ],
  "processing_metadata": {
    "model_version": "claude-3.5-sonnet-20241022",
    "processing_time_ms": 2340,
    "tokens_used": 156
  }
}
```

**Context JSONB:**
```json
{
  "situation": "school",
  "time_of_day": "evening",
  "recent_events": "плохая оценка по математике",
  "people_present": ["мама"],
  "location": "дом",
  "child_mood_before": "нормальное"
}
```

---

## Check-in Context

### checkin_sessions
Сессии ежедневных опросов

```sql
CREATE TABLE checkin_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL DEFAULT 'daily_evening',
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (
        status IN ('scheduled', 'in_progress', 'completed', 'missed', 'cancelled')
    ),
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    questions JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    
    CONSTRAINT chk_checkin_times CHECK (
        (started_at IS NULL OR started_at >= scheduled_time - INTERVAL '1 hour') AND
        (completed_at IS NULL OR completed_at >= started_at)
    )
);

-- Indexes
CREATE INDEX idx_checkin_sessions_family_scheduled ON checkin_sessions(family_id, scheduled_time);
CREATE INDEX idx_checkin_sessions_status ON checkin_sessions(status);
CREATE INDEX idx_checkin_sessions_type_created ON checkin_sessions(type, created_at);

-- Автоматическая пометка пропущенных чек-инов
CREATE OR REPLACE FUNCTION mark_missed_checkins()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE checkin_sessions 
    SET status = 'missed', 
        metadata = metadata || '{"auto_marked_missed": true}'::jsonb
    WHERE status = 'scheduled' 
    AND scheduled_time < NOW() - INTERVAL '2 hours';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Scheduled job для автоматической пометки (через pg_cron)
-- SELECT cron.schedule('mark-missed-checkins', '0 * * * *', 'SELECT mark_missed_checkins();');
```

**Questions JSONB:**
```json
[
  {
    "question_id": "family_mood",
    "text": "Как прошел день в семье?",
    "type": "multiple_choice",
    "required": true,
    "options": [
      {"value": "excellent", "text": "Отлично", "emoji": "😊"},
      {"value": "good", "text": "Хорошо", "emoji": "🙂"},
      {"value": "okay", "text": "Нормально", "emoji": "😐"},
      {"value": "difficult", "text": "Сложно", "emoji": "😔"}
    ]
  },
  {
    "question_id": "attention_needed",
    "text": "Кто из детей требует особого внимания?",
    "type": "select_child",
    "required": false,
    "allow_multiple": true,
    "allow_none": true
  },
  {
    "question_id": "additional_notes",
    "text": "Дополнительные заметки (необязательно)",
    "type": "text",
    "required": false,
    "max_length": 500
  }
]
```

---

### checkin_responses
Ответы на чек-ин опросы

```sql
CREATE TABLE checkin_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES checkin_sessions(session_id) ON DELETE CASCADE,
    child_id UUID REFERENCES children(child_id), -- NULL для общих семейных вопросов
    question_id VARCHAR(100) NOT NULL,
    answer JSONB NOT NULL,
    additional_notes TEXT,
    responded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_by UUID NOT NULL REFERENCES users(user_id), -- кто отвечал
    
    UNIQUE(session_id, question_id, child_id)
);

-- Indexes
CREATE INDEX idx_checkin_responses_session ON checkin_responses(session_id);
CREATE INDEX idx_checkin_responses_child ON checkin_responses(child_id) WHERE child_id IS NOT NULL;
CREATE INDEX idx_checkin_responses_responded_at ON checkin_responses(responded_at);

-- View для агрегации ответов по сессии
CREATE VIEW checkin_session_summary AS
SELECT 
    cs.session_id,
    cs.family_id,
    cs.type,
    cs.scheduled_time,
    cs.status,
    COUNT(cr.response_id) as responses_count,
    COUNT(DISTINCT cr.child_id) as children_responded,
    AVG(CASE 
        WHEN cr.answer->>'value' = 'excellent' THEN 5
        WHEN cr.answer->>'value' = 'good' THEN 4
        WHEN cr.answer->>'value' = 'okay' THEN 3
        WHEN cr.answer->>'value' = 'difficult' THEN 2
        ELSE NULL
    END) as avg_mood_score,
    STRING_AGG(cr.additional_notes, '; ') as all_notes
FROM checkin_sessions cs
LEFT JOIN checkin_responses cr ON cs.session_id = cr.session_id
WHERE cs.status = 'completed'
GROUP BY cs.session_id, cs.family_id, cs.type, cs.scheduled_time, cs.status;
```

**Answer JSONB examples:**
```json
// Multiple choice answer
{
  "value": "good",
  "text": "Хорошо",
  "numeric_value": 4
}

// Child selection answer
{
  "children": [
    {
      "child_id": "880f9511-f3ac-52e5-b827-557766553333",
      "name": "Маша",
      "reason": "сложности с домашним заданием"
    }
  ]
}

// Text answer
{
  "text": "Сегодня был хороший день, но Петя немного капризничал вечером"
}

// Scale answer (1-10)
{
  "value": 8,
  "scale_min": 1,
  "scale_max": 10
}
```

---

## Analytics Context

### weekly_reports
Еженедельные аналитические отчеты

```sql
CREATE TABLE weekly_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    overall_mood_score DECIMAL(3,2) CHECK (overall_mood_score BETWEEN 1.0 AND 10.0),
    insights JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    generation_version VARCHAR(20) DEFAULT '1.0',
    
    UNIQUE(family_id, week_start),
    CONSTRAINT chk_week_dates CHECK (week_end = week_start + INTERVAL '6 days')
);

-- Indexes
CREATE INDEX idx_weekly_reports_family_week ON weekly_reports(family_id, week_start DESC);
CREATE INDEX idx_weekly_reports_generated_at ON weekly_reports(generated_at);

-- Partitioning по кварталам
CREATE TABLE weekly_reports_2025_q3 PARTITION OF weekly_reports
FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');
```

**Insights JSONB:**
```json
{
  "family_dynamics": [
    "Конфликты между детьми чаще происходят в вечернее время",
    "Выходные дни показывают лучшие эмоциональные показатели"
  ],
  "children_insights": [
    {
      "child_id": "880f9511-f3ac-52e5-b827-557766553333",
      "child_name": "Маша",
      "mood_trend": "improving",
      "key_emotions": ["радость", "любопытство", "небольшая тревога"],
      "attention_areas": ["Стресс при выполнении математических заданий"],
      "positive_moments": ["Успехи в рисовании"]
    }
  ],
  "patterns": {
    "mood_by_day": {
      "monday": 6.2,
      "tuesday": 7.1,
      "wednesday": 6.8,
      "thursday": 7.3,
      "friday": 6.5,
      "saturday": 8.1,
      "sunday": 8.4
    },
    "emotion_categories": {
      "joy": 45,
      "sadness": 8,
      "anger": 12,
      "fear": 5,
      "surprise": 10,
      "disgust": 3,
      "neutral": 17
    }
  }
}
```

**Recommendations JSONB:**
```json
[
  {
    "priority": "high",
    "category": "communication",
    "title": "Индивидуальное время с Петей",
    "description": "Петя показывает признаки подросткового отдаления...",
    "action_steps": [
      "Выберите активность, которая интересна подростку",
      "Избегайте расспросов об учебе в это время"
    ],
    "expected_outcome": "Улучшение доверительных отношений",
    "timeframe": "2-3 недели"
  }
]
```

---

## Event Sourcing

### domain_events
Хранилище всех доменных событий

```sql
CREATE TABLE domain_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sequence_number BIGSERIAL,
    
    UNIQUE(aggregate_id, event_version)
);

-- Indexes для event sourcing
CREATE INDEX idx_domain_events_aggregate ON domain_events(aggregate_id, event_version);
CREATE INDEX idx_domain_events_type_occurred ON domain_events(event_type, occurred_at);
CREATE INDEX idx_domain_events_sequence ON domain_events(sequence_number);

-- Partitioning по месяцам
CREATE TABLE domain_events_y2025m08 PARTITION OF domain_events
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

-- View для последних событий
CREATE VIEW recent_domain_events AS
SELECT 
    event_id,
    aggregate_id,
    aggregate_type,
    event_type,
    event_data,
    occurred_at,
    ROW_NUMBER() OVER (PARTITION BY aggregate_id ORDER BY event_version DESC) as rn
FROM domain_events
WHERE occurred_at >= NOW() - INTERVAL '30 days';
```

**Event examples:**
```sql
-- Family created event
INSERT INTO domain_events (aggregate_id, aggregate_type, event_type, event_version, event_data) VALUES
('660f9511-f3ac-52e5-b827-557766551111', 'Family', 'FamilyCreated', 1, '{
    "family_id": "660f9511-f3ac-52e5-b827-557766551111",
    "name": "Семья Петровых",
    "created_by": "550e8400-e29b-41d4-a716-446655440000",
    "settings": {...}
}'::jsonb);

-- Child added event
INSERT INTO domain_events (aggregate_id, aggregate_type, event_type, event_version, event_data) VALUES
('660f9511-f3ac-52e5-b827-557766551111', 'Family', 'ChildAdded', 2, '{
    "child_id": "880f9511-f3ac-52e5-b827-557766553333",
    "name": "Маша",
    "birth_date": "2015-03-15",
    "added_by": "550e8400-e29b-41d4-a716-446655440000"
}'::jsonb);

-- Emotion recorded event
INSERT INTO domain_events (aggregate_id, aggregate_type, event_type, event_version, event_data) VALUES
('aa0f9511-f3ac-52e5-b827-557766555555', 'EmotionEntry', 'EmotionTranslated', 1, '{
    "entry_id": "aa0f9511-f3ac-52e5-b827-557766555555",
    "child_id": "880f9511-f3ac-52e5-b827-557766553333",
    "original_phrase": "Отстань, ты ничего не понимаешь!",
    "interpretation": {...},
    "claude_model": "claude-3.5-sonnet-20241022"
}'::jsonb);
```

---

## Utility Tables

### usage_analytics
Аналитика использования для метрик бизнеса

```sql
CREATE TABLE usage_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    family_id UUID REFERENCES families(family_id),
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL, -- 'feature_usage', 'engagement', 'error'
    properties JSONB DEFAULT '{}'::jsonb,
    session_id UUID, -- для группировки событий сессии
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Индексы для быстрых агрегаций
    date_part DATE GENERATED ALWAYS AS (occurred_at::date) STORED,
    hour_part INTEGER GENERATED ALWAYS AS (EXTRACT(hour FROM occurred_at)) STORED
);

-- Indexes для аналитики
CREATE INDEX idx_usage_analytics_user_date ON usage_analytics(user_id, date_part);
CREATE INDEX idx_usage_analytics_family_date ON usage_analytics(family_id, date_part);
CREATE INDEX idx_usage_analytics_event_type ON usage_analytics(event_type, occurred_at);

-- Retention table для быстрого подсчета метрик
CREATE MATERIALIZED VIEW user_retention_cohorts AS
SELECT 
    DATE_TRUNC('week', u.created_at) as cohort_week,
    COUNT(*) as cohort_size,
    COUNT(CASE WHEN ua.occurred_at >= u.created_at + INTERVAL '1 day' THEN 1 END) as day_1,
    COUNT(CASE WHEN ua.occurred_at >= u.created_at + INTERVAL '7 days' THEN 1 END) as day_7,
    COUNT(CASE WHEN ua.occurred_at >= u.created_at + INTERVAL '30 days' THEN 1 END) as day_30
FROM users u
LEFT JOIN usage_analytics ua ON u.user_id = ua.user_id 
    AND ua.event_type = 'bot_interaction'
    AND ua.occurred_at BETWEEN u.created_at AND u.created_at + INTERVAL '30 days'
WHERE u.created_at >= '2025-08-01'
GROUP BY DATE_TRUNC('week', u.created_at)
ORDER BY cohort_week;

-- Refresh retention data daily
-- SELECT cron.schedule('refresh-retention', '0 2 * * *', 'REFRESH MATERIALIZED VIEW user_retention_cohorts;');
```

---

### system_logs
Системные логи для отладки и мониторинга

```sql
CREATE TABLE system_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    user_id UUID REFERENCES users(user_id),
    family_id UUID REFERENCES families(family_id),
    request_id UUID,
    extra_data JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Для быстрого поиска
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', message)) STORED
);

-- Partitioning по дням для логов
CREATE TABLE system_logs_y2025m08d14 PARTITION OF system_logs
FOR VALUES FROM ('2025-08-14') TO ('2025-08-15');

-- Автоматическое удаление старых логов
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM system_logs 
    WHERE occurred_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

---

## Views & Functions

### Performance Views

```sql
-- Активность пользователей за последнюю неделю
CREATE VIEW user_activity_summary AS
SELECT 
    u.user_id,
    u.telegram_id,
    u.first_name,
    u.last_active,
    COUNT(DISTINCT ee.entry_id) as translations_count,
    COUNT(DISTINCT cr.session_id) as checkins_responded,
    COUNT(DISTINCT DATE(ua.occurred_at)) as active_days
FROM users u
LEFT JOIN emotion_entries ee ON u.user_id = (
    SELECT p.user_id FROM parents p WHERE p.family_id = ee.family_id LIMIT 1
) AND ee.created_at >= NOW() - INTERVAL '7 days'
LEFT JOIN checkin_responses cr ON cr.responded_by = u.user_id 
    AND cr.responded_at >= NOW() - INTERVAL '7 days'
LEFT JOIN usage_analytics ua ON ua.user_id = u.user_id 
    AND ua.occurred_at >= NOW() - INTERVAL '7 days'
WHERE u.deleted_at IS NULL
GROUP BY u.user_id, u.telegram_id, u.first_name, u.last_active;

-- Статистика семей
CREATE VIEW family_statistics AS
SELECT 
    f.family_id,
    f.name,
    COUNT(DISTINCT c.child_id) as children_count,
    COUNT(DISTINCT p.parent_id) as parents_count,
    COUNT(DISTINCT ee.entry_id) as total_translations,
    COUNT(DISTINCT cs.session_id) as total_checkins,
    AVG(css.avg_mood_score) as avg_family_mood,
    MAX(ee.created_at) as last_translation,
    MAX(cs.completed_at) as last_checkin
FROM families f
LEFT JOIN children c ON f.family_id = c.family_id AND c.deleted_at IS NULL
LEFT JOIN parents p ON f.family_id = p.family_id
LEFT JOIN emotion_entries ee ON f.family_id = ee.family_id
LEFT JOIN checkin_sessions cs ON f.family_id = cs.family_id AND cs.status = 'completed'
LEFT JOIN checkin_session_summary css ON cs.session_id = css.session_id
WHERE f.deleted_at IS NULL
GROUP BY f.family_id, f.name;
```

### Utility Functions

```sql
-- Функция для получения возраста ребенка
CREATE OR REPLACE FUNCTION get_child_age(birth_date DATE)
RETURNS INTEGER AS $$
BEGIN
    RETURN DATE_PART('year', AGE(birth_date))::INTEGER;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Функция для проверки лимитов переводов
CREATE OR REPLACE FUNCTION check_translation_limit(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    daily_count INTEGER;
    user_plan VARCHAR(20);
    daily_limit INTEGER;
BEGIN
    -- Получаем план пользователя
    SELECT u.subscription_plan INTO user_plan
    FROM users u WHERE u.user_id = p_user_id;
    
    -- Устанавливаем лимит
    daily_limit := CASE 
        WHEN user_plan = 'premium' THEN 100
        ELSE 20
    END;
    
    -- Считаем переводы за сегодня
    SELECT COUNT(*) INTO daily_count
    FROM emotion_entries ee
    JOIN parents p ON p.family_id = ee.family_id
    WHERE p.user_id = p_user_id
    AND ee.created_at >= CURRENT_DATE
    AND ee.created_at < CURRENT_DATE + INTERVAL '1 day';
    
    RETURN daily_count < daily_limit;
END;
$$ LANGUAGE plpgsql;

-- Функция для генерации отчета семьи
CREATE OR REPLACE FUNCTION generate_family_weekly_report(p_family_id UUID, p_week_start DATE)
RETURNS UUID AS $$
DECLARE
    report_id UUID;
    mood_score DECIMAL(3,2);
    insights_data JSONB;
    recommendations_data JSONB;
BEGIN
    -- Проверяем существование отчета
    SELECT wr.report_id INTO report_id
    FROM weekly_reports wr
    WHERE wr.family_id = p_family_id AND wr.week_start = p_week_start;
    
    IF report_id IS NOT NULL THEN
        RETURN report_id; -- Отчет уже существует
    END IF;
    
    -- Вычисляем средний mood score
    SELECT AVG(css.avg_mood_score) INTO mood_score
    FROM checkin_sessions cs
    JOIN checkin_session_summary css ON cs.session_id = css.session_id
    WHERE cs.family_id = p_family_id
    AND cs.scheduled_time >= p_week_start
    AND cs.scheduled_time < p_week_start + INTERVAL '7 days';
    
    -- Генерируем insights (упрощенная версия)
    insights_data := '{
        "total_translations": 0,
        "total_checkins": 0,
        "mood_trend": "stable"
    }'::jsonb;
    
    -- Базовые рекомендации
    recommendations_data := '[]'::jsonb;
    
    -- Создаем отчет
    INSERT INTO weekly_reports (
        family_id,
        week_start,
        week_end,
        overall_mood_score,
        insights,
        recommendations
    ) VALUES (
        p_family_id,
        p_week_start,
        p_week_start + INTERVAL '6 days',
        COALESCE(mood_score, 5.0),
        insights_data,
        recommendations_data
    ) RETURNING report_id INTO report_id;
    
    RETURN report_id;
END;
$$ LANGUAGE plpgsql;
```

---

## Indexes & Performance

### Critical Indexes

```sql
-- Составные индексы для частых запросов
CREATE INDEX idx_emotion_entries_family_child_date ON emotion_entries(family_id, child_id, created_at DESC);
CREATE INDEX idx_checkin_responses_session_child ON checkin_responses(session_id, child_id);
CREATE INDEX idx_usage_analytics_user_event_date ON usage_analytics(user_id, event_type, date_part);

-- Частичные индексы для активных записей
CREATE INDEX idx_users_active ON users(user_id, last_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_children_active ON children(child_id, family_id) WHERE deleted_at IS NULL;

-- GIN индексы для JSONB полей
CREATE INDEX idx_emotion_entries_processed_emotion ON emotion_entries USING gin(processed_emotion);
CREATE INDEX idx_checkin_sessions_questions ON checkin_sessions USING gin(questions);
CREATE INDEX idx_users_settings ON users USING gin(settings);

-- Full-text search индексы
CREATE INDEX idx_emotion_entries_fulltext ON emotion_entries USING gin(search_vector);
CREATE INDEX idx_system_logs_fulltext ON system_logs USING gin(search_vector);
```

### Query Optimization

```sql
-- Материализованное представление для дашборда аналитики
CREATE MATERIALIZED VIEW dashboard_metrics AS
SELECT 
    'total_users' as metric,
    COUNT(*) as value,
    CURRENT_DATE as calculated_at
FROM users WHERE deleted_at IS NULL
UNION ALL
SELECT 
    'total_families',
    COUNT(*),
    CURRENT_DATE
FROM families WHERE deleted_at IS NULL
UNION ALL
SELECT 
    'total_children',
    COUNT(*),
    CURRENT_DATE
FROM children WHERE deleted_at IS NULL
UNION ALL
SELECT 
    'translations_today',
    COUNT(*),
    CURRENT_DATE
FROM emotion_entries WHERE created_at >= CURRENT_DATE
UNION ALL
SELECT 
    'checkins_completed_today',
    COUNT(*),
    CURRENT_DATE
FROM checkin_sessions WHERE status = 'completed' AND completed_at >= CURRENT_DATE;

-- Обновляем каждые 15 минут
-- SELECT cron.schedule('refresh-dashboard', '*/15 * * * *', 'REFRESH MATERIALIZED VIEW dashboard_metrics;');
```

---

## Data Retention & GDPR

### Автоматическая очистка данных

```sql
-- Функция для GDPR-совместимого удаления
CREATE OR REPLACE FUNCTION gdpr_cleanup_user_data(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Soft delete пользователя
    UPDATE users SET 
        deleted_at = NOW(),
        telegram_username = NULL,
        first_name = 'Удаленный пользователь',
        last_name = NULL,
        settings = '{}'::jsonb
    WHERE user_id = p_user_id;
    
    -- Удаляем персональные данные из логов
    UPDATE system_logs SET 
        extra_data = extra_data - 'personal_data'
    WHERE user_id = p_user_id;
    
    -- Анонимизируем аналитику
    UPDATE usage_analytics SET
        properties = properties - 'personal_data'
    WHERE user_id = p_user_id;
    
    RAISE NOTICE 'User data cleanup completed for user_id: %', p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Автоматическая очистка старых данных
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS INTEGER AS $$
DECLARE
    cleanup_count INTEGER := 0;
BEGIN
    -- Удаляем старые логи (30 дней)
    DELETE FROM system_logs WHERE occurred_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS cleanup_count = ROW_COUNT;
    
    -- Удаляем старые события (90 дней)
    DELETE FROM domain_events WHERE occurred_at < NOW() - INTERVAL '90 days';
    
    -- Удаляем старую аналитику (1 год)
    DELETE FROM usage_analytics WHERE occurred_at < NOW() - INTERVAL '1 year';
    
    RETURN cleanup_count;
END;
$$ LANGUAGE plpgsql;

-- Запускаем очистку каждую ночь
-- SELECT cron.schedule('cleanup-expired-data', '0 2 * * *', 'SELECT cleanup_expired_data();');
```

---

## Migration Scripts

### Initial Schema Creation

```sql
-- migrations/001_initial_schema.sql
BEGIN;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create all tables in correct order
-- (включить все DDL команды из документа)

COMMIT;
```

### Sample Data

```sql
-- migrations/002_sample_data.sql (только для development)
BEGIN;

-- Sample user
INSERT INTO users (user_id, telegram_id, first_name, language_code, onboarding_completed) 
VALUES ('550e8400-e29b-41d4-a716-446655440000', 123456789, 'Мария', 'ru', true);

-- Sample family
INSERT INTO families (family_id, name, created_by, settings)
VALUES ('660f9511-f3ac-52e5-b827-557766551111', 'Семья Петровых', 
        '550e8400-e29b-41d4-a716-446655440000', 
        '{"language": "ru", "timezone": "Europe/Moscow"}'::jsonb);

-- Sample parent
INSERT INTO parents (family_id, user_id, role)
VALUES ('660f9511-f3ac-52e5-b827-557766551111', 
        '550e8400-e29b-41d4-a716-446655440000', 'primary');

-- Sample children
INSERT INTO children (child_id, family_id, name, birth_date, personality_traits)
VALUES ('880f9511-f3ac-52e5-b827-557766553333', '660f9511-f3ac-52e5-b827-557766551111', 
        'Маша', '2015-03-15', '["активная", "любознательная"]'::jsonb),
       ('990f9511-f3ac-52e5-b827-557766554444', '660f9511-f3ac-52e5-b827-557766551111', 
        'Петя', '2012-07-22', '["спокойный", "творческий"]'::jsonb);

COMMIT;
```

---

## Monitoring & Maintenance

### Health Checks

```sql
-- Проверка здоровья базы данных
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE(
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Проверка подключения
    RETURN QUERY SELECT 'connection'::TEXT, 'healthy'::TEXT, 'Database connection active'::TEXT;
    
    -- Проверка размера таблиц
    RETURN QUERY
    SELECT 'table_sizes'::TEXT, 
           CASE WHEN pg_total_relation_size('emotion_entries') > 1000000000 THEN 'warning' ELSE 'healthy' END::TEXT,
           'Large tables: ' || pg_size_pretty(pg_total_relation_size('emotion_entries'))::TEXT;
    
    -- Проверка активных соединений
    RETURN QUERY
    SELECT 'connections'::TEXT,
           CASE WHEN COUNT(*) > 80 THEN 'warning' ELSE 'healthy' END::TEXT,
           'Active connections: ' || COUNT(*)::TEXT
    FROM pg_stat_activity WHERE state = 'active';
    
END;
$$ LANGUAGE plpgsql;
```

### Performance Monitoring

```sql
-- Медленные запросы
CREATE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    min_time,
    max_time,
    stddev_time
FROM pg_stat_statements
WHERE mean_time > 100 -- запросы медленнее 100мс
ORDER BY mean_time DESC;

-- Использование индексов
CREATE VIEW index_usage AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

## Backup Strategy

```sql
-- Скрипт для полного бэкапа
-- backup_database.sh
#!/bin/bash
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="family_emotions_${BACKUP_DATE}.sql"

pg_dump \
    --host=$DB_HOST \
    --port=$DB_PORT \
    --username=$DB_USER \
    --dbname=$DB_NAME \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="${BACKUP_FILE}"

# Загрузка в облачное хранилище
aws s3 cp "${BACKUP_FILE}" "s3://family-emotions-backups/daily/"

# Удаление локальной копии старше 7 дней
find . -name "family_emotions_*.sql" -mtime +7 -delete
```

---

## Security Considerations

### Row Level Security (RLS)

```sql
-- Включаем RLS для защиты данных
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotion_entries ENABLE ROW LEVEL SECURITY;

-- Политики безопасности
CREATE POLICY family_access_policy ON families
    USING (created_by = current_setting('app.current_user_id')::uuid 
           OR family_id IN (
               SELECT p.family_id FROM parents p 
               WHERE p.user_id = current_setting('app.current_user_id')::uuid
           ));

-- Шифрование чувствительных данных
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(encrypt(data::bytea, current_setting('app.encryption_key'), 'aes'), 'base64');
END;
$$ LANGUAGE plpgsql;
```

---

*Database Schema Version: 1.0*  
*Last Updated: August 14, 2025*  
*Compatible with PostgreSQL 15+*