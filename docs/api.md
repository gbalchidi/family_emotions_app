# Family Emotions App - API Documentation

## Overview

Family Emotions App предоставляет REST API для управления семейными эмоциональными данными. API следует принципам RESTful дизайна и обеспечивает интеграцию с Telegram ботом.

**Base URL**: `https://api.familyemotions.app/v1`  
**Content-Type**: `application/json`  
**Authentication**: Telegram WebApp authentication & API Keys

## Authentication

### Telegram WebApp Authentication
Для пользователей через Telegram WebApp используется проверка подписи:

```javascript
// JavaScript validation
function validateTelegramWebAppData(initData, botToken) {
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');
  
  const dataCheckString = Array.from(urlParams.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');
    
  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString).digest('hex');
    
  return calculatedHash === hash;
}
```

### API Key Authentication
Для внешних интеграций:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.familyemotions.app/v1/health
```

## API Endpoints

### Health & System

#### GET /health
Проверка состояния сервиса

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-14T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "claude_api": "healthy"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "active_users": 342,
    "api_requests_last_hour": 1250
  }
}
```

#### GET /metrics
Метрики Prometheus (только для мониторинга)

```
# HELP family_emotions_active_users Current active users
# TYPE family_emotions_active_users gauge
family_emotions_active_users 342

# HELP family_emotions_translations_total Total emotion translations
# TYPE family_emotions_translations_total counter
family_emotions_translations_total 15420

# HELP family_emotions_checkins_completion_rate Check-in completion rate
# TYPE family_emotions_checkins_completion_rate gauge
family_emotions_checkins_completion_rate 0.73
```

---

### User Management

#### POST /users
Создание или обновление пользователя

**Request:**
```json
{
  "telegram_id": 123456789,
  "telegram_username": "parent_maria",
  "first_name": "Мария",
  "last_name": "Петрова",
  "language_code": "ru",
  "timezone": "Europe/Moscow"
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "telegram_username": "parent_maria",
  "full_name": "Мария Петрова",
  "language_code": "ru",
  "timezone": "Europe/Moscow",
  "created_at": "2025-08-14T12:00:00Z",
  "onboarding_completed": false,
  "subscription_plan": "free",
  "daily_translations_used": 3,
  "daily_translations_limit": 20
}
```

#### GET /users/{telegram_id}
Получение данных пользователя

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "telegram_username": "parent_maria",
  "full_name": "Мария Петрова",
  "language_code": "ru",
  "created_at": "2025-08-14T12:00:00Z",
  "last_active": "2025-08-14T11:45:00Z",
  "onboarding_completed": true,
  "family": {
    "family_id": "660f9511-f3ac-52e5-b827-557766551111",
    "name": "Семья Петровых",
    "children_count": 2
  },
  "usage": {
    "daily_translations_used": 7,
    "daily_translations_limit": 20,
    "weekly_checkins_completed": 5,
    "total_translations": 156
  }
}
```

---

### Family Management

#### POST /families
Создание семьи

**Request:**
```json
{
  "name": "Семья Петровых",
  "primary_parent_telegram_id": 123456789,
  "settings": {
    "language": "ru",
    "timezone": "Europe/Moscow",
    "checkin_time": "20:00",
    "report_day": "sunday",
    "notifications_enabled": true
  }
}
```

**Response:**
```json
{
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "name": "Семья Петровых",
  "created_at": "2025-08-14T12:00:00Z",
  "parents": [
    {
      "parent_id": "770f9511-f3ac-52e5-b827-557766552222",
      "telegram_id": 123456789,
      "role": "primary",
      "joined_at": "2025-08-14T12:00:00Z"
    }
  ],
  "children": [],
  "settings": {
    "language": "ru",
    "timezone": "Europe/Moscow",
    "checkin_time": "20:00",
    "report_day": "sunday",
    "notifications_enabled": true
  }
}
```

#### POST /families/{family_id}/children
Добавление ребенка в семью

**Request:**
```json
{
  "name": "Маша",
  "birth_date": "2015-03-15",
  "avatar_url": null,
  "personality_traits": [
    "активная",
    "эмоциональная",
    "любознательная"
  ]
}
```

**Response:**
```json
{
  "child_id": "880f9511-f3ac-52e5-b827-557766553333",
  "name": "Маша",
  "birth_date": "2015-03-15",
  "age": 10,
  "avatar_url": null,
  "personality_traits": [
    "активная",
    "эмоциональная",
    "любознательная"
  ],
  "added_at": "2025-08-14T12:00:00Z",
  "total_emotions": 0
}
```

#### GET /families/{family_id}
Получение данных семьи

**Response:**
```json
{
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "name": "Семья Петровых",
  "created_at": "2025-08-14T12:00:00Z",
  "parents": [
    {
      "parent_id": "770f9511-f3ac-52e5-b827-557766552222",
      "telegram_id": 123456789,
      "full_name": "Мария Петрова",
      "role": "primary",
      "joined_at": "2025-08-14T12:00:00Z"
    }
  ],
  "children": [
    {
      "child_id": "880f9511-f3ac-52e5-b827-557766553333",
      "name": "Маша",
      "age": 10,
      "avatar_url": null,
      "total_emotions": 23,
      "recent_mood": "радостное"
    },
    {
      "child_id": "990f9511-f3ac-52e5-b827-557766554444",
      "name": "Петя",
      "age": 13,
      "avatar_url": null,
      "total_emotions": 45,
      "recent_mood": "тревожное"
    }
  ],
  "settings": {
    "language": "ru",
    "timezone": "Europe/Moscow",
    "checkin_time": "20:00",
    "report_day": "sunday",
    "notifications_enabled": true
  }
}
```

---

### Emotion Translation

#### POST /emotions/translate
Перевод детской эмоции/фразы

**Request:**
```json
{
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "child_id": "880f9511-f3ac-52e5-b827-557766553333",
  "original_phrase": "Отстань, ты ничего не понимаешь!",
  "context": {
    "situation": "school",
    "time_of_day": "evening",
    "recent_events": "плохая оценка по математике"
  }
}
```

**Response:**
```json
{
  "translation_id": "aa0f9511-f3ac-52e5-b827-557766555555",
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "child_id": "880f9511-f3ac-52e5-b827-557766553333",
  "original_phrase": "Отстань, ты ничего не понимаешь!",
  "context": {
    "situation": "school",
    "time_of_day": "evening",
    "recent_events": "плохая оценка по математике"
  },
  "interpretation": {
    "emotional_state": "фрустрация и стыд",
    "hidden_meaning": "Мне стыдно за плохую оценку, и я боюсь вашего разочарования. Я хочу справиться сам, но не знаю как.",
    "underlying_needs": [
      "поддержка без осуждения",
      "помощь в решении проблемы",
      "признание своей самостоятельности"
    ],
    "confidence_score": 0.89
  },
  "suggested_responses": [
    {
      "response_type": "empathetic",
      "text": "Вижу, что тебе сейчас тяжело. Хочешь рассказать, что случилось в школе?",
      "explanation": "Признает эмоции и открывает диалог без давления",
      "expected_outcome": "Снижение защитной реакции, возможность откровенного разговора"
    },
    {
      "response_type": "supportive",
      "text": "Я понимаю, что ты расстроен. Я не буду ругать, просто хочу понять, как тебе помочь.",
      "explanation": "Убирает страх наказания и предлагает поддержку",
      "expected_outcome": "Повышение доверия, готовность принять помощь"
    },
    {
      "response_type": "space_giving",
      "text": "Хорошо, побудь один, если нужно. Когда будешь готов поговорить - я здесь.",
      "explanation": "Дает контроль над ситуацией и время для обработки эмоций",
      "expected_outcome": "Снижение напряжения, самостоятельная готовность к диалогу"
    }
  ],
  "created_at": "2025-08-14T12:00:00Z",
  "processing_time_ms": 2340
}
```

#### GET /emotions/translations
Получение истории переводов

**Query Parameters:**
- `family_id` (required) - ID семьи
- `child_id` (optional) - Фильтр по ребенку
- `limit` (optional, default: 20) - Количество записей
- `offset` (optional, default: 0) - Смещение для пагинации
- `from_date` (optional) - Дата начала периода (ISO 8601)
- `to_date` (optional) - Дата окончания периода (ISO 8601)

**Response:**
```json
{
  "translations": [
    {
      "translation_id": "aa0f9511-f3ac-52e5-b827-557766555555",
      "child_id": "880f9511-f3ac-52e5-b827-557766553333",
      "child_name": "Маша",
      "original_phrase": "Отстань, ты ничего не понимаешь!",
      "emotional_state": "фрустрация и стыд",
      "context": "school",
      "user_feedback": 5,
      "created_at": "2025-08-14T12:00:00Z"
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0,
  "patterns": {
    "frequent_emotions": [
      {"emotion": "фрустрация", "count": 12},
      {"emotion": "тревога", "count": 8},
      {"emotion": "радость", "count": 15}
    ],
    "common_contexts": [
      {"context": "school", "count": 18},
      {"context": "home", "count": 22},
      {"context": "friends", "count": 7}
    ]
  }
}
```

#### POST /emotions/translations/{translation_id}/feedback
Обратная связь на перевод эмоции

**Request:**
```json
{
  "rating": 5,
  "comment": "Очень точно описали состояние ребенка, советы помогли!",
  "used_response": 1
}
```

**Response:**
```json
{
  "feedback_id": "bb0f9511-f3ac-52e5-b827-557766556666",
  "translation_id": "aa0f9511-f3ac-52e5-b827-557766555555",
  "rating": 5,
  "comment": "Очень точно описали состояние ребенка, советы помогли!",
  "used_response": 1,
  "created_at": "2025-08-14T12:30:00Z"
}
```

---

### Check-ins

#### POST /checkins/sessions
Создание сессии чек-ина

**Request:**
```json
{
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "type": "daily_evening",
  "scheduled_time": "2025-08-14T20:00:00Z"
}
```

**Response:**
```json
{
  "session_id": "cc0f9511-f3ac-52e5-b827-557766557777",
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "type": "daily_evening",
  "status": "scheduled",
  "scheduled_time": "2025-08-14T20:00:00Z",
  "questions": [
    {
      "question_id": "q1",
      "text": "Как прошел день в семье?",
      "type": "multiple_choice",
      "options": [
        {"value": "excellent", "text": "Отлично", "emoji": "😊"},
        {"value": "good", "text": "Хорошо", "emoji": "🙂"},
        {"value": "okay", "text": "Нормально", "emoji": "😐"},
        {"value": "difficult", "text": "Сложно", "emoji": "😔"}
      ]
    },
    {
      "question_id": "q2",
      "text": "Кто из детей требует особого внимания?",
      "type": "select",
      "options": [
        {"value": "880f9511-f3ac-52e5-b827-557766553333", "text": "Маша"},
        {"value": "990f9511-f3ac-52e5-b827-557766554444", "text": "Петя"},
        {"value": "none", "text": "Никто"}
      ]
    }
  ],
  "created_at": "2025-08-14T20:00:00Z"
}
```

#### POST /checkins/sessions/{session_id}/responses
Отправка ответов на чек-ин

**Request:**
```json
{
  "responses": [
    {
      "question_id": "q1",
      "answer": "good"
    },
    {
      "question_id": "q2",
      "answer": "880f9511-f3ac-52e5-b827-557766553333"
    }
  ],
  "additional_notes": "Маша сегодня долго делала домашку, немного капризничала"
}
```

**Response:**
```json
{
  "session_id": "cc0f9511-f3ac-52e5-b827-557766557777",
  "status": "completed",
  "completed_at": "2025-08-14T20:05:00Z",
  "responses": [
    {
      "question_id": "q1",
      "answer": "good",
      "answer_text": "Хорошо"
    },
    {
      "question_id": "q2", 
      "answer": "880f9511-f3ac-52e5-b827-557766553333",
      "answer_text": "Маша"
    }
  ],
  "additional_notes": "Маша сегодня долго делала домашку, немного капризничала",
  "immediate_insights": [
    "Обратите внимание на уровень стресса Маши при выполнении домашних заданий",
    "Возможно, стоит пересмотреть подход к организации учебного процесса дома"
  ]
}
```

#### GET /checkins/sessions
Получение истории чек-инов

**Query Parameters:**
- `family_id` (required)
- `status` (optional) - scheduled, completed, missed
- `from_date`, `to_date` (optional)
- `limit`, `offset` (optional)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "cc0f9511-f3ac-52e5-b827-557766557777",
      "type": "daily_evening",
      "status": "completed",
      "scheduled_time": "2025-08-14T20:00:00Z",
      "completed_at": "2025-08-14T20:05:00Z",
      "completion_rate": 100,
      "overall_mood": "good"
    }
  ],
  "total": 23,
  "completion_stats": {
    "total_scheduled": 25,
    "total_completed": 23,
    "completion_rate": 0.92
  }
}
```

---

### Analytics & Reports

#### GET /analytics/weekly-reports/{family_id}
Еженедельный отчет семьи

**Query Parameters:**
- `week_start` (optional) - Начало недели (ISO 8601), по умолчанию текущая неделя

**Response:**
```json
{
  "report_id": "dd0f9511-f3ac-52e5-b827-557766558888",
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "period": {
    "week_start": "2025-08-11",
    "week_end": "2025-08-17"
  },
  "overall_mood": {
    "score": 7.2,
    "trend": "stable",
    "description": "В целом позитивная неделя"
  },
  "children_insights": [
    {
      "child_id": "880f9511-f3ac-52e5-b827-557766553333",
      "child_name": "Маша",
      "mood_score": 7.8,
      "mood_trend": "improving",
      "key_emotions": ["радость", "любопытство", "небольшая тревога"],
      "attention_areas": [
        "Стресс при выполнении математических заданий",
        "Конфликты с младшим братом"
      ],
      "positive_moments": [
        "Успехи в рисовании",
        "Хорошие отношения с одноклассниками"
      ]
    },
    {
      "child_id": "990f9511-f3ac-52e5-b827-557766554444",
      "child_name": "Петя",
      "mood_score": 6.5,
      "mood_trend": "declining",
      "key_emotions": ["раздражение", "усталость", "замкнутость"],
      "attention_areas": [
        "Снижение мотивации к учебе",
        "Меньше общения с семьей"
      ],
      "positive_moments": [
        "Увлечение программированием",
        "Помощь по дому без напоминаний"
      ]
    }
  ],
  "recommendations": [
    {
      "priority": "high",
      "category": "communication",
      "title": "Индивидуальное время с Петей",
      "description": "Петя показывает признаки подросткового отдаления. Рекомендуем запланировать 20-30 минут индивидуального общения каждый день.",
      "action_steps": [
        "Выберите активность, которая интересна подростку",
        "Избегайте расспросов об учебе в это время",
        "Фокусируйтесь на выслушивании, а не на советах"
      ]
    },
    {
      "priority": "medium",
      "category": "education",
      "title": "Поддержка Маши с математикой",
      "description": "У Маши стабильные трудности с математическими заданиями, что вызывает стресс.",
      "action_steps": [
        "Разбивайте задания на более мелкие части",
        "Используйте игровые методы обучения",
        "Празднуйте даже небольшие успехи"
      ]
    }
  ],
  "patterns": {
    "family_dynamics": [
      "Конфликты между детьми чаще происходят в вечернее время",
      "Выходные дни показывают лучшие эмоциональные показатели",
      "Понедельники - самые стрессовые дни"
    ],
    "seasonal_trends": [
      "Начало учебного года: повышенная тревожность",
      "Необходимость адаптации к новому расписанию"
    ]
  },
  "created_at": "2025-08-18T09:00:00Z"
}
```

#### GET /analytics/emotion-trends/{family_id}
Тренды эмоций по семье

**Query Parameters:**
- `child_id` (optional) - Фильтр по ребенку
- `period` (optional) - week, month, quarter (default: month)
- `emotion_type` (optional) - Фильтр по типу эмоции

**Response:**
```json
{
  "family_id": "660f9511-f3ac-52e5-b827-557766551111",
  "period": "month",
  "data_points": [
    {
      "date": "2025-08-01",
      "overall_mood": 6.8,
      "emotions": {
        "joy": 12,
        "sadness": 3,
        "anger": 5,
        "fear": 2,
        "surprise": 4
      }
    },
    {
      "date": "2025-08-02",
      "overall_mood": 7.2,
      "emotions": {
        "joy": 15,
        "sadness": 2,
        "anger": 3,
        "fear": 1,
        "surprise": 6
      }
    }
  ],
  "insights": [
    "Общий эмоциональный фон семьи улучшился на 15% за последний месяц",
    "Пик позитивных эмоций приходится на выходные дни",
    "Самые сложные эмоциональные моменты связаны с учебными нагрузками"
  ]
}
```

---

### Webhooks

#### POST /webhooks/telegram
Webhook для обработки сообщений от Telegram

**Request (от Telegram):**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1234,
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "Мария",
      "username": "parent_maria",
      "language_code": "ru"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "date": 1692025200,
    "text": "Мой сын сказал 'Я тебя ненавижу!'"
  }
}
```

**Response:**
```json
{
  "status": "processed",
  "message_id": 1234,
  "response_sent": true,
  "processing_time_ms": 1250
}
```

---

## Error Handling

### Error Response Format

Все ошибки возвращаются в унифицированном формате:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Некорректные данные в запросе",
    "details": {
      "field": "child_id",
      "reason": "UUID должен быть в корректном формате"
    },
    "request_id": "req_123456789",
    "timestamp": "2025-08-14T12:00:00Z"
  }
}
```

### HTTP Status Codes

- `200 OK` - Успешный запрос
- `201 Created` - Ресурс создан
- `400 Bad Request` - Некорректный запрос
- `401 Unauthorized` - Не авторизован
- `403 Forbidden` - Доступ запрещен
- `404 Not Found` - Ресурс не найден
- `429 Too Many Requests` - Превышен лимит запросов
- `500 Internal Server Error` - Внутренняя ошибка сервера
- `503 Service Unavailable` - Сервис недоступен

### Common Error Codes

| Код | Описание |
|-----|----------|
| `INVALID_TELEGRAM_DATA` | Некорректные данные от Telegram |
| `FAMILY_NOT_FOUND` | Семья не найдена |
| `CHILD_NOT_FOUND` | Ребенок не найден |
| `TRANSLATION_LIMIT_EXCEEDED` | Превышен дневной лимит переводов |
| `CLAUDE_API_ERROR` | Ошибка Claude API |
| `VALIDATION_ERROR` | Ошибка валидации данных |
| `RATE_LIMIT_EXCEEDED` | Превышен лимит запросов |

---

## Rate Limits

### По пользователю
- **Emotion Translations**: 100 запросов/час (20 для free tier)
- **Check-in Responses**: 50 запросов/час
- **General API**: 1000 запросов/час

### По семье
- **Children Management**: 10 изменений/час
- **Family Settings**: 5 изменений/час

### Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1692028800
```

---

## SDK Examples

### Python SDK

```python
import aiohttp
import asyncio
from family_emotions_sdk import FamilyEmotionsAPI

async def main():
    api = FamilyEmotionsAPI(
        base_url="https://api.familyemotions.app/v1",
        telegram_data=telegram_web_app_data
    )
    
    # Перевод эмоции
    translation = await api.emotions.translate(
        family_id="660f9511-f3ac-52e5-b827-557766551111",
        child_id="880f9511-f3ac-52e5-b827-557766553333",
        phrase="Отстань, ты ничего не понимаешь!",
        context={"situation": "school"}
    )
    
    print(f"Интерпретация: {translation.interpretation.hidden_meaning}")
    
    for response in translation.suggested_responses:
        print(f"Вариант: {response.text}")

asyncio.run(main())
```

### JavaScript SDK

```javascript
import { FamilyEmotionsAPI } from '@family-emotions/sdk';

const api = new FamilyEmotionsAPI({
  baseUrl: 'https://api.familyemotions.app/v1',
  telegramData: window.Telegram.WebApp.initData
});

// Получение данных семьи
const family = await api.families.get('660f9511-f3ac-52e5-b827-557766551111');
console.log(`Семья: ${family.name}, детей: ${family.children.length}`);

// Создание чек-ина
const checkin = await api.checkins.create({
  familyId: family.family_id,
  type: 'daily_evening'
});

// Отправка ответов
await api.checkins.respond(checkin.session_id, {
  responses: [
    { question_id: 'q1', answer: 'good' }
  ]
});
```

---

## Changelog

### v1.0.0 (2025-08-31)
- 🎉 Initial MVP release
- ✨ Emotion translation API
- ✨ Daily check-ins functionality
- ✨ Weekly reports generation
- ✨ Basic analytics endpoints

### Upcoming Features
- 🔄 Real-time notifications via WebSocket
- 📱 Mobile app deep linking
- 🌐 Multi-language support (UA, EN)
- 🔐 Enhanced security with OAuth2
- 📊 Advanced analytics dashboard

---

## Support

- 📖 **Документация**: [/docs](https://docs.familyemotions.app)
- 🐛 **Баги**: [GitHub Issues](https://github.com/family-emotions/issues)
- 💬 **Поддержка**: [@family_emotions_support](https://t.me/family_emotions_support)
- 📧 **Email**: api-support@familyemotions.app

---

*API Version: 1.0.0*  
*Last Updated: August 14, 2025*  
*Made with ❤️ for families*