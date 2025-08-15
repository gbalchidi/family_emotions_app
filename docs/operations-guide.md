# Family Emotions App - Operations Guide

## Содержание
1. [Мониторинг и наблюдаемость](#мониторинг-и-наблюдаемость)
2. [Backup и восстановление](#backup-и-восстановление)
3. [Масштабирование](#масштабирование)
4. [Incident Response](#incident-response)
5. [Обновления и патчи](#обновления-и-патчи)
6. [Логи и отладка](#логи-и-отладка)
7. [Performance Tuning](#performance-tuning)
8. [Security Operations](#security-operations)

---

## Мониторинг и наблюдаемость

### Архитектура мониторинга

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│   Prometheus    │───▶│    Grafana      │
│   (Metrics)     │    │   (Storage)     │    │  (Dashboards)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Sentry      │    │   AlertManager  │    │   PagerDuty     │
│   (Errors)      │    │   (Alerting)    │    │ (Notifications) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Ключевые метрики

#### Бизнес метрики

```python
# src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

# Регистрации пользователей
USER_REGISTRATIONS = Counter(
    'family_emotions_user_registrations_total',
    'Total number of user registrations',
    ['source']
)

# Переводы эмоций
EMOTION_TRANSLATIONS = Counter(
    'family_emotions_translations_total',
    'Total number of emotion translations',
    ['child_age_group', 'language', 'success']
)

# Время обработки переводов
TRANSLATION_DURATION = Histogram(
    'family_emotions_translation_duration_seconds',
    'Time to process emotion translation',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Активные семьи
ACTIVE_FAMILIES = Gauge(
    'family_emotions_active_families',
    'Number of active families (last 30 days)'
)

# Чек-ины
CHECKIN_COMPLETIONS = Counter(
    'family_emotions_checkins_completed_total',
    'Total completed check-ins',
    ['type', 'completion_rate']
)

# Retention метрики
USER_RETENTION = Gauge(
    'family_emotions_user_retention_rate',
    'User retention rate',
    ['period']  # day_1, day_7, day_30
)

class BusinessMetricsCollector:
    """Сборщик бизнес-метрик."""
    
    @staticmethod
    def record_user_registration(source: str = "telegram") -> None:
        """Записывает регистрацию пользователя."""
        USER_REGISTRATIONS.labels(source=source).inc()
    
    @staticmethod
    def record_emotion_translation(
        child_age: int,
        language: str,
        success: bool,
        duration_seconds: float
    ) -> None:
        """Записывает метрики перевода эмоции."""
        age_group = "child" if child_age < 13 else "teen"
        success_label = "success" if success else "error"
        
        EMOTION_TRANSLATIONS.labels(
            child_age_group=age_group,
            language=language,
            success=success_label
        ).inc()
        
        TRANSLATION_DURATION.observe(duration_seconds)
    
    @staticmethod
    async def update_active_families() -> None:
        """Обновляет количество активных семей."""
        count = await get_active_families_count()
        ACTIVE_FAMILIES.set(count)
    
    @staticmethod
    async def update_retention_metrics() -> None:
        """Обновляет метрики retention."""
        d1_retention = await calculate_retention_rate(days=1)
        d7_retention = await calculate_retention_rate(days=7)
        d30_retention = await calculate_retention_rate(days=30)
        
        USER_RETENTION.labels(period="day_1").set(d1_retention)
        USER_RETENTION.labels(period="day_7").set(d7_retention)
        USER_RETENTION.labels(period="day_30").set(d30_retention)
```

#### Технические метрики

```python
# Производительность приложения
APPLICATION_REQUESTS = Counter(
    'family_emotions_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'family_emotions_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# База данных
DATABASE_CONNECTIONS = Gauge(
    'family_emotions_db_connections_active',
    'Active database connections'
)

DATABASE_QUERY_DURATION = Histogram(
    'family_emotions_db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table']
)

# External API
EXTERNAL_API_REQUESTS = Counter(
    'family_emotions_external_api_requests_total',
    'External API requests',
    ['service', 'status']
)

EXTERNAL_API_DURATION = Histogram(
    'family_emotions_external_api_duration_seconds',
    'External API response time',
    ['service']
)

# Queue metrics
QUEUE_SIZE = Gauge(
    'family_emotions_queue_size',
    'Queue size by type',
    ['queue_type']
)

QUEUE_PROCESSING_TIME = Histogram(
    'family_emotions_queue_processing_seconds',
    'Queue processing time',
    ['queue_type']
)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "Family Emotions App - Production",
    "tags": ["family-emotions", "production"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "User Registrations (24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(family_emotions_user_registrations_total[24h])",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 50},
                {"color": "red", "value": 100}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Emotion Translations Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(family_emotions_translations_total[5m])",
            "refId": "A",
            "legendFormat": "{{success}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Translation Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(family_emotions_translations_total{success=\"success\"}[1h]) / rate(family_emotions_translations_total[1h]) * 100",
            "refId": "A"
          }
        ]
      },
      {
        "id": 4,
        "title": "Response Time Percentiles",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(family_emotions_translation_duration_seconds_bucket[5m]))",
            "refId": "A",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(family_emotions_translation_duration_seconds_bucket[5m]))",
            "refId": "B",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(family_emotions_translation_duration_seconds_bucket[5m]))",
            "refId": "C",
            "legendFormat": "99th percentile"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### Алерты и уведомления

```yaml
# alertmanager/alerts.yml
groups:
  - name: family-emotions-production
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(family_emotions_translations_total{success="error"}[5m]) / rate(family_emotions_translations_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
          service: family-emotions
        annotations:
          summary: "High error rate in emotion translations"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
      
      # High response time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(family_emotions_translation_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: critical
          service: family-emotions
        annotations:
          summary: "High response time for emotion translations"
          description: "95th percentile response time is {{ $value }}s"
      
      # Database connection issues
      - alert: DatabaseConnectionHigh
        expr: family_emotions_db_connections_active > 80
        for: 3m
        labels:
          severity: warning
          service: family-emotions
        annotations:
          summary: "High number of database connections"
          description: "Active database connections: {{ $value }}"
      
      # Low user activity
      - alert: LowUserActivity
        expr: rate(family_emotions_user_registrations_total[1h]) < 0.1
        for: 30m
        labels:
          severity: info
          service: family-emotions
        annotations:
          summary: "Low user registration rate"
          description: "Only {{ $value }} registrations per hour"
      
      # External API issues
      - alert: ClaudeAPIErrors
        expr: rate(family_emotions_external_api_requests_total{service="claude",status!="200"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
          service: family-emotions
        annotations:
          summary: "Claude API errors detected"
          description: "Claude API error rate: {{ $value }}"

# Routing configuration
route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'web.hook'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'critical-alerts'
    pagerduty_configs:
      - severity: critical
        integration_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
    telegram_configs:
      - bot_token: 'YOUR_TELEGRAM_BOT_TOKEN'
        chat_id: -1001234567890
        message: |
          🚨 *CRITICAL ALERT*
          
          *Service:* {{ .GroupLabels.service }}
          *Alert:* {{ .GroupLabels.alertname }}
          *Description:* {{ range .Alerts }}{{ .Annotations.description }}{{ end }}
          
          *Time:* {{ .CommonAnnotations.startsAt | humanizeTimestamp }}

  - name: 'warning-alerts'
    telegram_configs:
      - bot_token: 'YOUR_TELEGRAM_BOT_TOKEN'
        chat_id: -1001234567890
        message: |
          ⚠️ *Warning Alert*
          
          {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}
          {{ range .Alerts }}{{ .Annotations.description }}{{ end }}
```

### Health Checks

```python
# src/core/health.py
from typing import Dict, Any
from enum import Enum
import asyncio
import aiohttp
import asyncpg
import aioredis

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    """Система проверки здоровья всех компонентов."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "claude_api": self._check_claude_api,
            "telegram_api": self._check_telegram_api
        }
    
    async def check_all(self) -> Dict[str, Any]:
        """Проверяет все компоненты системы."""
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        # Запускаем все проверки параллельно
        tasks = {
            name: asyncio.create_task(check())
            for name, check in self.checks.items()
        }
        
        # Собираем результаты
        for name, task in tasks.items():
            try:
                result = await asyncio.wait_for(task, timeout=5.0)
                results[name] = result
                
                # Обновляем общий статус
                if result["status"] == HealthStatus.UNHEALTHY.value:
                    overall_status = HealthStatus.UNHEALTHY
                elif result["status"] == HealthStatus.DEGRADED.value and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except asyncio.TimeoutError:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": "Health check timeout",
                    "response_time_ms": 5000
                }
                overall_status = HealthStatus.UNHEALTHY
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": str(e),
                    "response_time_ms": None
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": results
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Проверяет подключение к базе данных."""
        start_time = time.time()
        
        try:
            conn = await asyncpg.connect(self.settings.database_url)
            await conn.fetchval("SELECT 1")
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Database connection successful",
                "response_time_ms": round(response_time, 2)
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Database connection failed: {str(e)}",
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Проверяет подключение к Redis."""
        start_time = time.time()
        
        try:
            redis = aioredis.from_url(self.settings.redis_url)
            await redis.ping()
            await redis.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Redis connection successful",
                "response_time_ms": round(response_time, 2)
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Redis connection failed: {str(e)}",
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _check_claude_api(self) -> Dict[str, Any]:
        """Проверяет доступность Claude API."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01"
                }
                async with session.get(
                    "https://api.anthropic.com/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        return {
                            "status": HealthStatus.HEALTHY.value,
                            "message": "Claude API accessible",
                            "response_time_ms": round(response_time, 2)
                        }
                    else:
                        return {
                            "status": HealthStatus.DEGRADED.value,
                            "message": f"Claude API returned status {response.status}",
                            "response_time_ms": round(response_time, 2)
                        }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Claude API check failed: {str(e)}",
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _check_telegram_api(self) -> Dict[str, Any]:
        """Проверяет доступность Telegram API."""
        start_time = time.time()
        
        try:
            url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            return {
                                "status": HealthStatus.HEALTHY.value,
                                "message": "Telegram API accessible",
                                "response_time_ms": round(response_time, 2)
                            }
                    
                    return {
                        "status": HealthStatus.DEGRADED.value,
                        "message": f"Telegram API returned status {response.status}",
                        "response_time_ms": round(response_time, 2)
                    }
                    
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Telegram API check failed: {str(e)}",
                "response_time_ms": (time.time() - start_time) * 1000
            }

# Endpoint для health check
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/health")
async def health_check_endpoint():
    """Endpoint для проверки здоровья сервиса."""
    checker = HealthChecker(Settings())
    result = await checker.check_all()
    
    # Устанавливаем HTTP статус в зависимости от результата
    if result["status"] == HealthStatus.HEALTHY.value:
        status_code = 200
    elif result["status"] == HealthStatus.DEGRADED.value:
        status_code = 200  # Сервис работает, но с ограничениями
    else:
        status_code = 503  # Service Unavailable
    
    return Response(
        content=json.dumps(result, indent=2),
        status_code=status_code,
        media_type="application/json"
    )

@app.get("/health/ready")
async def readiness_check():
    """Проверка готовности для Kubernetes."""
    # Проверяем только критические зависимости
    critical_checks = ["database", "redis"]
    checker = HealthChecker(Settings())
    
    for check_name in critical_checks:
        check_func = checker.checks[check_name]
        result = await check_func()
        
        if result["status"] != HealthStatus.HEALTHY.value:
            return Response(
                content=json.dumps({"ready": False, "reason": result["message"]}),
                status_code=503,
                media_type="application/json"
            )
    
    return {"ready": True}

@app.get("/health/live")
async def liveness_check():
    """Проверка жизнеспособности для Kubernetes."""
    # Простая проверка что приложение отвечает
    return {"alive": True}
```

---

## Backup и восстановление

### Стратегия резервного копирования

#### Что копируем
1. **PostgreSQL база данных** - все пользовательские данные
2. **Redis данные** - сессии и кеш (опционально)
3. **Конфигурационные файлы** - .env, docker-compose.yml
4. **Статические файлы** - если есть загруженные файлы
5. **Логи приложения** - для анализа инцидентов

#### Расписание бэкапов

```bash
# Ежедневные бэкапы в 3:00 UTC
0 3 * * * /opt/family-emotions/scripts/backup_daily.sh

# Еженедельные бэкапы в воскресенье в 2:00 UTC  
0 2 * * 0 /opt/family-emotions/scripts/backup_weekly.sh

# Ежемесячные бэкапы 1 числа в 1:00 UTC
0 1 1 * * /opt/family-emotions/scripts/backup_monthly.sh
```

### Scripts для бэкапа

```bash
#!/bin/bash
# scripts/backup_daily.sh

set -euo pipefail

# Конфигурация
BACKUP_DIR="/opt/backups/family-emotions"
S3_BUCKET="family-emotions-backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Логирование
LOG_FILE="/var/log/family-emotions-backup.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo "$(date): Starting daily backup"

# Создаем директорию для бэкапа
mkdir -p "$BACKUP_DIR/daily/$DATE"
cd "$BACKUP_DIR/daily/$DATE"

# 1. Бэкап PostgreSQL
echo "$(date): Backing up PostgreSQL database"
pg_dump \
    --host="${DB_HOST:-localhost}" \
    --port="${DB_PORT:-5432}" \
    --username="${DB_USER:-postgres}" \
    --dbname="${DB_NAME:-family_emotions}" \
    --format=custom \
    --compress=9 \
    --verbose \
    --no-password \
    --file="postgresql_${DATE}.dump"

if [ $? -eq 0 ]; then
    echo "$(date): PostgreSQL backup completed successfully"
else
    echo "$(date): ERROR: PostgreSQL backup failed"
    exit 1
fi

# 2. Бэкап Redis (опционально)
if [ "${BACKUP_REDIS:-false}" = "true" ]; then
    echo "$(date): Backing up Redis data"
    redis-cli --rdb "redis_${DATE}.rdb"
    
    if [ $? -eq 0 ]; then
        echo "$(date): Redis backup completed successfully"
    else
        echo "$(date): WARNING: Redis backup failed (non-critical)"
    fi
fi

# 3. Бэкап конфигурации
echo "$(date): Backing up configuration files"
tar -czf "config_${DATE}.tar.gz" \
    /opt/family-emotions/.env \
    /opt/family-emotions/docker-compose.yml \
    /opt/family-emotions/nginx.conf \
    2>/dev/null || echo "$(date): WARNING: Some config files not found"

# 4. Создаем метаданные бэкапа
cat > "backup_metadata.json" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "backup_type": "daily",
    "database_size_bytes": $(stat -c%s postgresql_${DATE}.dump 2>/dev/null || echo 0),
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "version": "1.0.0"
}
EOF

# 5. Проверяем целостность бэкапа
echo "$(date): Verifying backup integrity"
pg_restore --list "postgresql_${DATE}.dump" > /dev/null
if [ $? -eq 0 ]; then
    echo "$(date): Backup integrity verification passed"
else
    echo "$(date): ERROR: Backup integrity verification failed"
    exit 1
fi

# 6. Сжимаем весь бэкап
cd "$BACKUP_DIR/daily"
tar -czf "${DATE}.tar.gz" "$DATE/"
rm -rf "$DATE"

# 7. Загружаем в S3 (если настроен)
if [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    echo "$(date): Uploading backup to S3"
    aws s3 cp "${DATE}.tar.gz" "s3://${S3_BUCKET}/daily/${DATE}.tar.gz" \
        --storage-class STANDARD_IA
    
    if [ $? -eq 0 ]; then
        echo "$(date): S3 upload completed successfully"
    else
        echo "$(date): ERROR: S3 upload failed"
        # Не выходим с ошибкой, локальный бэкап остается
    fi
fi

# 8. Очистка старых бэкапов
echo "$(date): Cleaning up old backups"
find "$BACKUP_DIR/daily" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "$(date): Removed backups older than $RETENTION_DAYS days"

# 9. Отправляем уведомление об успехе
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    BACKUP_SIZE=$(du -h "${DATE}.tar.gz" | cut -f1)
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=✅ Daily backup completed successfully
Size: ${BACKUP_SIZE}
Date: ${DATE}
Location: ${BACKUP_DIR}/daily/${DATE}.tar.gz" \
        -d "parse_mode=HTML" > /dev/null
fi

echo "$(date): Daily backup completed successfully"
```

### Восстановление из бэкапа

```bash
#!/bin/bash
# scripts/restore_backup.sh

set -euo pipefail

# Параметры
BACKUP_FILE="$1"
RESTORE_TYPE="${2:-full}"  # full, database-only, config-only

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file> [restore_type]"
    echo "restore_type: full (default), database-only, config-only"
    exit 1
fi

# Проверяем существование файла
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "$(date): Starting restore from $BACKUP_FILE"
echo "$(date): Restore type: $RESTORE_TYPE"

# Создаем временную директорию
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Распаковываем бэкап
echo "$(date): Extracting backup file"
tar -xzf "$BACKUP_FILE"

# Находим директорию с данными
BACKUP_DIR=$(find . -maxdepth 1 -type d -name "20*" | head -n1)
if [ -z "$BACKUP_DIR" ]; then
    echo "ERROR: Could not find backup data directory"
    exit 1
fi

cd "$BACKUP_DIR"

# Проверяем метаданные
if [ -f "backup_metadata.json" ]; then
    echo "$(date): Backup metadata:"
    cat backup_metadata.json | jq .
else
    echo "$(date): WARNING: No backup metadata found"
fi

# Восстановление базы данных
if [ "$RESTORE_TYPE" = "full" ] || [ "$RESTORE_TYPE" = "database-only" ]; then
    echo "$(date): Restoring PostgreSQL database"
    
    # Находим dump файл
    DUMP_FILE=$(ls postgresql_*.dump 2>/dev/null | head -n1)
    if [ -z "$DUMP_FILE" ]; then
        echo "ERROR: PostgreSQL dump file not found"
        exit 1
    fi
    
    # Подтверждение от пользователя
    read -p "This will OVERWRITE the current database. Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled by user"
        exit 1
    fi
    
    # Останавливаем приложение
    echo "$(date): Stopping application"
    docker-compose -f /opt/family-emotions/docker-compose.yml stop app
    
    # Создаем бэкап текущей БД (на всякий случай)
    CURRENT_BACKUP="/tmp/pre-restore-backup-$(date +%Y%m%d_%H%M%S).dump"
    echo "$(date): Creating safety backup of current database"
    pg_dump \
        --host="${DB_HOST:-localhost}" \
        --port="${DB_PORT:-5432}" \
        --username="${DB_USER:-postgres}" \
        --dbname="${DB_NAME:-family_emotions}" \
        --format=custom \
        --file="$CURRENT_BACKUP" || echo "WARNING: Could not create safety backup"
    
    # Восстанавливаем БД
    echo "$(date): Restoring database from $DUMP_FILE"
    
    # Очищаем существующую БД
    psql \
        --host="${DB_HOST:-localhost}" \
        --port="${DB_PORT:-5432}" \
        --username="${DB_USER:-postgres}" \
        --dbname="${DB_NAME:-family_emotions}" \
        --command="DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    
    # Восстанавливаем данные
    pg_restore \
        --host="${DB_HOST:-localhost}" \
        --port="${DB_PORT:-5432}" \
        --username="${DB_USER:-postgres}" \
        --dbname="${DB_NAME:-family_emotions}" \
        --verbose \
        --clean \
        --if-exists \
        "$DUMP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "$(date): Database restore completed successfully"
    else
        echo "$(date): ERROR: Database restore failed"
        echo "$(date): Safety backup available at: $CURRENT_BACKUP"
        exit 1
    fi
fi

# Восстановление конфигурации
if [ "$RESTORE_TYPE" = "full" ] || [ "$RESTORE_TYPE" = "config-only" ]; then
    echo "$(date): Restoring configuration files"
    
    CONFIG_FILE=$(ls config_*.tar.gz 2>/dev/null | head -n1)
    if [ -n "$CONFIG_FILE" ]; then
        # Создаем бэкап текущей конфигурации
        mkdir -p /opt/family-emotions/config-backup-$(date +%Y%m%d_%H%M%S)
        cp /opt/family-emotions/.env /opt/family-emotions/config-backup-*/2>/dev/null || true
        cp /opt/family-emotions/docker-compose.yml /opt/family-emotions/config-backup-*/2>/dev/null || true
        
        # Восстанавливаем конфигурацию
        tar -xzf "$CONFIG_FILE" -C /
        echo "$(date): Configuration files restored"
    else
        echo "$(date): WARNING: No configuration backup found"
    fi
fi

# Восстановление Redis (если есть)
if [ -f redis_*.rdb ]; then
    echo "$(date): Restoring Redis data"
    REDIS_FILE=$(ls redis_*.rdb | head -n1)
    
    # Останавливаем Redis
    docker-compose -f /opt/family-emotions/docker-compose.yml stop redis
    
    # Копируем файл
    docker cp "$REDIS_FILE" family-emotions-redis:/data/dump.rdb
    
    # Запускаем Redis
    docker-compose -f /opt/family-emotions/docker-compose.yml start redis
    
    echo "$(date): Redis data restored"
fi

# Запускаем приложение
if [ "$RESTORE_TYPE" = "full" ] || [ "$RESTORE_TYPE" = "database-only" ]; then
    echo "$(date): Starting application"
    docker-compose -f /opt/family-emotions/docker-compose.yml up -d
    
    # Ждем запуска и проверяем health
    sleep 30
    
    HEALTH_STATUS=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo "$(date): Application started successfully after restore"
    else
        echo "$(date): WARNING: Application may not be healthy after restore"
        echo "$(date): Health status: $HEALTH_STATUS"
    fi
fi

# Очищаем временные файлы
cd /
rm -rf "$TEMP_DIR"

# Отправляем уведомление
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=🔄 Restore completed
Type: ${RESTORE_TYPE}
Source: $(basename $BACKUP_FILE)
Time: $(date)" \
        -d "parse_mode=HTML" > /dev/null
fi

echo "$(date): Restore completed successfully"
echo "$(date): Please verify application functionality"
```

### Тестирование бэкапов

```bash
#!/bin/bash
# scripts/test_backup.sh

set -euo pipefail

BACKUP_FILE="$1"
TEST_DB_NAME="family_emotions_test_restore"

echo "$(date): Testing backup: $BACKUP_FILE"

# Создаем тестовую БД
createdb -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" "$TEST_DB_NAME" 2>/dev/null || true

# Распаковываем бэкап
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
tar -xzf "$BACKUP_FILE"

# Находим dump файл
BACKUP_DIR=$(find . -maxdepth 1 -type d -name "20*" | head -n1)
DUMP_FILE=$(find "$BACKUP_DIR" -name "postgresql_*.dump" | head -n1)

if [ -z "$DUMP_FILE" ]; then
    echo "ERROR: No PostgreSQL dump found in backup"
    exit 1
fi

# Восстанавливаем в тестовую БД
echo "$(date): Restoring to test database"
pg_restore \
    --host="${DB_HOST:-localhost}" \
    --port="${DB_PORT:-5432}" \
    --username="${DB_USER:-postgres}" \
    --dbname="$TEST_DB_NAME" \
    --verbose \
    "$DUMP_FILE"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to restore backup to test database"
    exit 1
fi

# Проверяем целостность данных
echo "$(date): Checking data integrity"

# Считаем записи в основных таблицах
USERS_COUNT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | xargs)
FAMILIES_COUNT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM families;" | xargs)
EMOTIONS_COUNT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM emotion_entries;" | xargs)

echo "$(date): Data counts:"
echo "  Users: $USERS_COUNT"
echo "  Families: $FAMILIES_COUNT" 
echo "  Emotion entries: $EMOTIONS_COUNT"

# Проверяем внешние ключи
FOREIGN_KEY_VIOLATIONS=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$TEST_DB_NAME" -t -c "
SELECT COUNT(*) FROM (
    SELECT 'children' as table_name, COUNT(*) as violations FROM children c 
    LEFT JOIN families f ON c.family_id = f.family_id 
    WHERE f.family_id IS NULL
    UNION
    SELECT 'emotion_entries', COUNT(*) FROM emotion_entries e
    LEFT JOIN children c ON e.child_id = c.child_id
    WHERE c.child_id IS NULL
) violations;" | xargs)

if [ "$FOREIGN_KEY_VIOLATIONS" -gt 0 ]; then
    echo "ERROR: Foreign key violations found: $FOREIGN_KEY_VIOLATIONS"
    exit 1
fi

# Проверяем что можно выполнить типичные запросы
echo "$(date): Testing common queries"

# Тест сложного запроса
COMPLEX_QUERY_RESULT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$TEST_DB_NAME" -t -c "
SELECT COUNT(*) FROM families f 
JOIN children c ON f.family_id = c.family_id 
JOIN emotion_entries e ON c.child_id = e.child_id 
WHERE f.created_at > NOW() - INTERVAL '30 days';" | xargs)

echo "$(date): Complex query result: $COMPLEX_QUERY_RESULT"

# Очищаем тестовую БД
dropdb -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" "$TEST_DB_NAME"

# Очищаем временные файлы
rm -rf "$TEMP_DIR"

echo "$(date): Backup test completed successfully"
echo "$(date): Backup is valid and restorable"

# Записываем результат теста
echo "$(date): Backup test passed for $BACKUP_FILE" >> /var/log/backup-tests.log
```

---

## Масштабирование

### Horizontal Scaling Strategy

#### Компоненты для масштабирования

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/certs:/etc/nginx/certs
    depends_on:
      - app

  # Application instances
  app:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3  # Запускаем 3 инстанса

  # Database (Master-Slave setup)
  postgres-master:
    image: postgres:15
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_REPLICATION_MODE=master
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=replicator_password
    volumes:
      - postgres_master_data:/var/lib/postgresql/data
      - ./postgres/master.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf

  postgres-slave:
    image: postgres:15
    environment:
      - POSTGRES_MASTER_HOST=postgres-master
      - POSTGRES_REPLICATION_MODE=slave
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=replicator_password
    depends_on:
      - postgres-master
    deploy:
      replicas: 2  # 2 read-only реплики

  # Redis Cluster
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes --cluster-enabled yes

  redis-slave:
    image: redis:7-alpine
    command: redis-server --appendonly yes --slaveof redis-master 6379
    depends_on:
      - redis-master
    deploy:
      replicas: 2

volumes:
  postgres_master_data:
```

#### Nginx Load Balancer

```nginx
# nginx/nginx.conf
upstream app_backend {
    least_conn;
    server app_1:8000 max_fails=3 fail_timeout=30s;
    server app_2:8000 max_fails=3 fail_timeout=30s;
    server app_3:8000 max_fails=3 fail_timeout=30s;
}

upstream webhook_backend {
    # Sticky sessions для webhook'ов (если нужно)
    ip_hash;
    server app_1:8000;
    server app_2:8000;
    server app_3:8000;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;

server {
    listen 80;
    server_name familyemotions.app;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name familyemotions.app;
    
    # SSL configuration
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Telegram webhook endpoint
    location /webhook {
        limit_req zone=webhook burst=20 nodelay;
        proxy_pass http://webhook_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Webhook specific settings
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }
    
    # API endpoints
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://app_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://app_backend;
        access_log off;
    }
    
    # Metrics endpoint (restricted access)
    location /metrics {
        allow 10.0.0.0/8;     # Private networks
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        proxy_pass http://app_backend;
    }
    
    # Static files (if any)
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        alias /opt/family-emotions/static/;
    }
}
```

### Database Scaling

#### Read Replicas Setup

```python
# src/infrastructure/database/read_replica.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import random

class DatabaseRouter:
    """Роутер для распределения запросов между мастер и репликами."""
    
    def __init__(self, master_url: str, replica_urls: List[str]):
        self.master_engine = create_async_engine(master_url, pool_size=20)
        self.replica_engines = [
            create_async_engine(url, pool_size=10) 
            for url in replica_urls
        ]
        
        self.master_session = sessionmaker(
            self.master_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.replica_sessions = [
            sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            for engine in self.replica_engines
        ]
    
    async def get_write_session(self) -> AsyncSession:
        """Получает сессию для записи (всегда мастер)."""
        return self.master_session()
    
    async def get_read_session(self) -> AsyncSession:
        """Получает сессию для чтения (случайная реплика)."""
        if not self.replica_sessions:
            # Фоллбэк на мастер если нет реплик
            return self.master_session()
        
        # Выбираем случайную реплику
        session_factory = random.choice(self.replica_sessions)
        return session_factory()

# Database context manager с автоматическим роутингом
class DatabaseManager:
    """Менеджер БД с автоматическим роутингом запросов."""
    
    def __init__(self, router: DatabaseRouter):
        self.router = router
    
    async def execute_write(self, query_func):
        """Выполняет запрос на запись."""
        async with await self.router.get_write_session() as session:
            try:
                result = await query_func(session)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
    
    async def execute_read(self, query_func):
        """Выполняет запрос на чтение."""
        async with await self.router.get_read_session() as session:
            return await query_func(session)

# Использование в репозиториях
class FamilyRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_family(self, family: Family) -> Family:
        """Создание семьи (запись в мастер)."""
        async def create_query(session: AsyncSession):
            session.add(family)
            await session.flush()
            return family
        
        return await self.db.execute_write(create_query)
    
    async def get_family_by_id(self, family_id: UUID) -> Optional[Family]:
        """Получение семьи (чтение из реплики)."""
        async def read_query(session: AsyncSession):
            result = await session.execute(
                select(Family).where(Family.id == family_id)
            )
            return result.scalar_one_or_none()
        
        return await self.db.execute_read(read_query)
```

### Application Scaling

#### Stateless Application Design

```python
# src/core/session_management.py
from typing import Dict, Any, Optional
import json
import aioredis
from uuid import UUID

class DistributedSessionManager:
    """Менеджер сессий для stateless приложений."""
    
    def __init__(self, redis_cluster: aioredis.RedisCluster):
        self.redis = redis_cluster
        self.session_ttl = 3600  # 1 час
    
    async def create_session(
        self, 
        user_id: UUID, 
        session_data: Dict[str, Any]
    ) -> str:
        """Создает новую сессию."""
        session_id = str(uuid4())
        session_key = f"session:{session_id}"
        
        session_data.update({
            "user_id": str(user_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        })
        
        await self.redis.setex(
            session_key,
            self.session_ttl,
            json.dumps(session_data, default=str)
        )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные сессии."""
        session_key = f"session:{session_id}"
        data = await self.redis.get(session_key)
        
        if data:
            session_data = json.loads(data)
            # Обновляем время последней активности
            await self.update_last_activity(session_id)
            return session_data
        
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> None:
        """Обновляет данные сессии."""
        session_data = await self.get_session(session_id)
        if session_data:
            session_data.update(updates)
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            session_key = f"session:{session_id}"
            await self.redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session_data, default=str)
            )
    
    async def delete_session(self, session_id: str) -> None:
        """Удаляет сессию."""
        session_key = f"session:{session_id}"
        await self.redis.delete(session_key)
    
    async def update_last_activity(self, session_id: str) -> None:
        """Обновляет время последней активности."""
        session_key = f"session:{session_id}"
        # Используем pipeline для атомарности
        pipe = self.redis.pipeline()
        pipe.hset(session_key, "last_activity", datetime.utcnow().isoformat())
        pipe.expire(session_key, self.session_ttl)
        await pipe.execute()

# Middleware для автоматического управления сессиями
class SessionMiddleware:
    """Middleware для управления пользовательскими сессиями."""
    
    def __init__(self, session_manager: DistributedSessionManager):
        self.session_manager = session_manager
    
    async def __call__(self, request, call_next):
        # Извлекаем session_id из заголовков или cookies
        session_id = request.headers.get("X-Session-ID")
        
        if session_id:
            session_data = await self.session_manager.get_session(session_id)
            request.state.session = session_data
            request.state.session_id = session_id
        else:
            request.state.session = None
            request.state.session_id = None
        
        response = await call_next(request)
        
        # Если сессия была изменена, сохраняем
        if hasattr(request.state, "session_modified"):
            await self.session_manager.update_session(
                request.state.session_id,
                request.state.session
            )
        
        return response
```

### Queue-based Processing

```python
# src/infrastructure/queues/task_queue.py
import asyncio
import json
from typing import Dict, Any, Callable, List
from enum import Enum
import aioredis

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TaskQueue:
    """Распределенная очередь задач на Redis."""
    
    def __init__(self, redis_cluster: aioredis.RedisCluster):
        self.redis = redis_cluster
        self.task_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, task_type: str, handler: Callable):
        """Регистрирует обработчик для типа задач."""
        self.task_handlers[task_type] = handler
    
    async def enqueue_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: int = 0
    ) -> str:
        """Добавляет задачу в очередь."""
        task_id = str(uuid4())
        
        task = {
            "id": task_id,
            "type": task_type,
            "data": task_data,
            "priority": priority.value,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "max_attempts": 3
        }
        
        if delay_seconds > 0:
            # Отложенная задача
            execute_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            await self.redis.zadd(
                "delayed_tasks",
                {json.dumps(task, default=str): execute_at.timestamp()}
            )
        else:
            # Немедленная задача
            queue_key = f"tasks:priority:{priority.value}"
            await self.redis.lpush(queue_key, json.dumps(task, default=str))
        
        return task_id
    
    async def process_tasks(self, worker_id: str = None):
        """Запускает обработчик задач."""
        worker_id = worker_id or f"worker-{uuid4().hex[:8]}"
        
        logger.info(f"Starting task worker: {worker_id}")
        
        while True:
            try:
                # Сначала проверяем отложенные задачи
                await self._process_delayed_tasks()
                
                # Затем обрабатываем обычные задачи по приоритету
                task_data = await self._get_next_task()
                
                if task_data:
                    await self._execute_task(task_data, worker_id)
                else:
                    # Нет задач, ждем
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)
    
    async def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """Получает следующую задачу из очереди."""
        # Проверяем очереди по приоритету (от высокого к низкому)
        for priority in [4, 3, 2, 1]:
            queue_key = f"tasks:priority:{priority}"
            task_json = await self.redis.brpop(queue_key, timeout=1)
            
            if task_json:
                return json.loads(task_json[1])
        
        return None
    
    async def _process_delayed_tasks(self):
        """Обрабатывает отложенные задачи."""
        now = datetime.utcnow().timestamp()
        
        # Получаем задачи которые пора выполнить
        ready_tasks = await self.redis.zrangebyscore(
            "delayed_tasks", 0, now, withscores=True
        )
        
        for task_json, score in ready_tasks:
            task = json.loads(task_json)
            priority = TaskPriority(task["priority"])
            
            # Перемещаем в обычную очередь
            queue_key = f"tasks:priority:{priority.value}"
            await self.redis.lpush(queue_key, task_json)
            
            # Удаляем из отложенных
            await self.redis.zrem("delayed_tasks", task_json)
    
    async def _execute_task(self, task_data: Dict[str, Any], worker_id: str):
        """Выполняет задачу."""
        task_type = task_data["type"]
        task_id = task_data["id"]
        
        handler = self.task_handlers.get(task_type)
        if not handler:
            logger.error(f"No handler for task type: {task_type}")
            return
        
        logger.info(f"Worker {worker_id} executing task {task_id} ({task_type})")
        
        try:
            start_time = time.time()
            
            # Выполняем задачу
            await handler(task_data["data"])
            
            duration = time.time() - start_time
            logger.info(f"Task {task_id} completed in {duration:.2f}s")
            
            # Записываем метрики успеха
            QUEUE_PROCESSING_TIME.labels(queue_type=task_type).observe(duration)
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            
            # Увеличиваем счетчик попыток
            task_data["attempts"] += 1
            task_data["last_error"] = str(e)
            
            if task_data["attempts"] < task_data.get("max_attempts", 3):
                # Повторяем задачу с экспоненциальной задержкой
                delay = 2 ** task_data["attempts"] * 60  # 2, 4, 8 минут
                await self.enqueue_task(
                    task_type=task_type,
                    task_data=task_data["data"],
                    priority=TaskPriority(task_data["priority"]),
                    delay_seconds=delay
                )
                logger.info(f"Task {task_id} rescheduled (attempt {task_data['attempts']})")
            else:
                # Максимум попыток достигнут, отправляем в DLQ
                await self.redis.lpush(
                    "dead_letter_queue",
                    json.dumps(task_data, default=str)
                )
                logger.error(f"Task {task_id} moved to dead letter queue")

# Регистрация обработчиков задач
task_queue = TaskQueue(redis_cluster)

@task_queue.register_handler("generate_weekly_report")
async def generate_weekly_report_task(task_data: Dict[str, Any]):
    """Обработчик генерации еженедельного отчета."""
    family_id = UUID(task_data["family_id"])
    week_start = datetime.fromisoformat(task_data["week_start"])
    
    # Генерируем отчет
    report_generator = WeeklyReportGenerator()
    report = await report_generator.generate(family_id, week_start)
    
    # Отправляем пользователю
    notification_service = NotificationService()
    await notification_service.send_weekly_report(family_id, report)

@task_queue.register_handler("process_emotion_batch")
async def process_emotion_batch_task(task_data: Dict[str, Any]):
    """Обработчик пакетной обработки эмоций."""
    emotion_ids = [UUID(id) for id in task_data["emotion_ids"]]
    
    emotion_service = EmotionService()
    await emotion_service.process_emotions_batch(emotion_ids)

# Запуск worker'ов
async def start_workers(num_workers: int = 3):
    """Запускает воркеры для обработки задач."""
    workers = []
    
    for i in range(num_workers):
        worker_task = asyncio.create_task(
            task_queue.process_tasks(f"worker-{i}")
        )
        workers.append(worker_task)
    
    # Ждем завершения всех воркеров
    await asyncio.gather(*workers)
```

---

## Incident Response

### Incident Response Plan

#### Классификация инцидентов

**Severity 1 - Critical**
- Полная недоступность сервиса
- Потеря данных пользователей
- Серьезные security breach
- Response time: 15 минут
- Resolution time: 2 часа

**Severity 2 - High**
- Частичная недоступность функций
- Высокий error rate (>5%)
- Проблемы с производительностью
- Response time: 30 минут  
- Resolution time: 4 часа

**Severity 3 - Medium**
- Деградация производительности
- Проблемы с отдельными функциями
- Response time: 1 час
- Resolution time: 24 часа

**Severity 4 - Low**  
- Косметические проблемы
- Документация
- Response time: 24 часа
- Resolution time: 1 неделя

#### Incident Response Playbook

```bash
#!/bin/bash
# scripts/incident_response.sh

set -euo pipefail

INCIDENT_ID="$1"
SEVERITY="$2"  # critical, high, medium, low
DESCRIPTION="$3"

# Telegram для уведомлений
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN}"
ALERT_CHAT_ID="${TELEGRAM_ALERT_CHAT_ID}"

# Функция для отправки уведомлений
send_alert() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${ALERT_CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=HTML" > /dev/null
}

# Функция для создания инцидента в системе трекинга
create_incident() {
    local id="$1"
    local severity="$2"
    local description="$3"
    
    # Здесь может быть интеграция с Jira, Linear, GitHub Issues и т.д.
    echo "$(date): Created incident ${id} with severity ${severity}"
    echo "Description: ${description}"
    
    # Создаем директорию для инцидента
    INCIDENT_DIR="/opt/incidents/${id}"
    mkdir -p "${INCIDENT_DIR}"
    
    cat > "${INCIDENT_DIR}/incident.json" <<EOF
{
    "id": "${id}",
    "severity": "${severity}",
    "description": "${description}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "open",
    "assignee": null,
    "timeline": []
}
EOF
}

# Функция для сбора диагностической информации
collect_diagnostics() {
    local incident_dir="$1"
    
    echo "$(date): Collecting diagnostic information"
    
    # Системная информация
    {
        echo "=== SYSTEM INFO ==="
        uname -a
        df -h
        free -h
        uptime
        echo ""
        
        echo "=== DOCKER STATUS ==="
        docker ps -a
        echo ""
        
        echo "=== APPLICATION HEALTH ==="
        curl -s http://localhost:8000/health | jq . || echo "Health check failed"
        echo ""
        
        echo "=== RECENT ERRORS ==="
        tail -100 /var/log/family-emotions/app.log | grep -E "(ERROR|CRITICAL)" || echo "No recent errors found"
        echo ""
        
        echo "=== DATABASE STATUS ==="
        psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();" || echo "Database check failed"
        echo ""
        
        echo "=== REDIS STATUS ==="
        redis-cli ping || echo "Redis check failed"
        
    } > "${incident_dir}/diagnostics.txt" 2>&1
}

# Функция для автоматического восстановления
attempt_auto_recovery() {
    local severity="$1"
    
    if [ "$severity" = "critical" ]; then
        echo "$(date): Attempting automatic recovery for critical incident"
        
        # Перезапуск сервисов
        echo "$(date): Restarting services"
        docker-compose restart
        
        # Ждем восстановления
        sleep 30
        
        # Проверяем health
        if curl -s http://localhost:8000/health | jq -e '.status == "healthy"' > /dev/null; then
            echo "$(date): Auto-recovery successful"
            return 0
        else
            echo "$(date): Auto-recovery failed"
            return 1
        fi
    fi
    
    return 1
}

# Основная логика
echo "$(date): Starting incident response for ${INCIDENT_ID}"

# Отправляем первое уведомление
send_alert "🚨 <b>INCIDENT ${INCIDENT_ID}</b>

<b>Severity:</b> ${SEVERITY}
<b>Description:</b> ${DESCRIPTION}
<b>Status:</b> Investigating
<b>Time:</b> $(date)

Investigation started."

# Создаем инцидент
create_incident "${INCIDENT_ID}" "${SEVERITY}" "${DESCRIPTION}"

# Собираем диагностику
collect_diagnostics "/opt/incidents/${INCIDENT_ID}"

# Пытаемся автовосстановление для критических инцидентов
if [ "$SEVERITY" = "critical" ]; then
    if attempt_auto_recovery "$SEVERITY"; then
        send_alert "✅ <b>INCIDENT ${INCIDENT_ID}</b>

<b>Status:</b> Auto-resolved
<b>Action:</b> Services restarted
<b>Time:</b> $(date)

Please verify functionality."
        exit 0
    else
        send_alert "❌ <b>INCIDENT ${INCIDENT_ID}</b>

<b>Status:</b> Auto-recovery failed
<b>Action Required:</b> Manual intervention needed
<b>Time:</b> $(date)

Escalating to on-call engineer."
    fi
fi

echo "$(date): Incident response initialized. Manual intervention may be required."
```

### Runbooks для типичных проблем

#### High Memory Usage

```markdown
# Runbook: High Memory Usage

## Symptoms
- Memory usage > 80%
- OOM kills in logs
- Application restarts
- Slow response times

## Investigation Steps

1. **Check current memory usage:**
   ```bash
   free -h
   ps aux --sort=-%mem | head -20
   docker stats --no-stream
   ```

2. **Check application metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep memory
   ```

3. **Check for memory leaks:**
   ```bash
   # Look for growing processes
   ps aux --sort=-%mem | head -10
   
   # Check Python memory usage
   python -c "
   import psutil
   process = psutil.Process()
   print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
   "
   ```

## Immediate Actions

1. **Restart the application:**
   ```bash
   docker-compose restart app
   ```

2. **If critical, scale horizontally:**
   ```bash
   docker-compose up -d --scale app=3
   ```

3. **Monitor recovery:**
   ```bash
   watch -n 5 'free -h && echo "---" && docker stats --no-stream'
   ```

## Root Cause Investigation

1. **Check application logs:**
   ```bash
   grep -E "(OutOfMemory|MemoryError)" /var/log/family-emotions/app.log
   ```

2. **Analyze memory dumps (if available):**
   ```bash
   # Generate memory profile
   python -m memory_profiler src/main.py
   ```

3. **Check for resource leaks:**
   - Database connection leaks
   - Redis connection leaks  
   - Large objects in memory
   - Background tasks not cleaned up

## Prevention

1. Implement memory monitoring alerts
2. Regular memory profiling
3. Connection pool limits
4. Garbage collection tuning
5. Resource cleanup in code
```

#### Database Connection Issues

```markdown
# Runbook: Database Connection Issues

## Symptoms
- "connection refused" errors
- "too many connections" errors
- Slow database queries
- Application timeouts

## Investigation Steps

1. **Check database status:**
   ```bash
   pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER
   systemctl status postgresql
   docker logs postgres-container
   ```

2. **Check connection count:**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
   ```

3. **Check connection limits:**
   ```sql
   SHOW max_connections;
   SELECT setting FROM pg_settings WHERE name = 'max_connections';
   ```

## Immediate Actions

1. **Kill idle connections:**
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' 
   AND state_change < NOW() - INTERVAL '1 hour';
   ```

2. **Restart database (if safe):**
   ```bash
   docker-compose restart postgres
   ```

3. **Scale application down temporarily:**
   ```bash
   docker-compose up -d --scale app=1
   ```

## Root Cause Investigation

1. **Check for connection leaks:**
   ```python
   # Add to application
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

2. **Analyze slow queries:**
   ```sql
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

3. **Check application connection pooling:**
   ```python
   # Verify pool configuration
   print(f"Pool size: {engine.pool.size()}")
   print(f"Checked out: {engine.pool.checkedout()}")
   ```

## Prevention

1. Proper connection pool configuration
2. Connection timeout settings
3. Regular connection monitoring
4. Database connection limits
5. Connection leak detection
```

#### Claude API Rate Limiting

```markdown
# Runbook: Claude API Rate Limiting

## Symptoms
- 429 "Rate limit exceeded" errors
- High API response times
- Failed emotion translations
- User complaints about slow responses

## Investigation Steps

1. **Check current API usage:**
   ```bash
   curl -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        https://api.anthropic.com/v1/models
   ```

2. **Check application metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep claude_api
   ```

3. **Review recent API calls:**
   ```bash
   grep "claude_api" /var/log/family-emotions/app.log | tail -50
   ```

## Immediate Actions

1. **Enable request queuing:**
   ```python
   # Implement queue for API requests
   import asyncio
   from asyncio import Semaphore
   
   # Limit concurrent requests
   api_semaphore = Semaphore(5)  # Max 5 concurrent requests
   ```

2. **Implement circuit breaker:**
   ```python
   from circuit_breaker import CircuitBreaker
   
   claude_breaker = CircuitBreaker(
       failure_threshold=5,
       recovery_timeout=60
   )
   ```

3. **Enable caching for similar requests:**
   ```python
   # Cache responses for similar emotion texts
   import hashlib
   
   def get_emotion_hash(text: str, child_age: int) -> str:
       return hashlib.md5(f"{text}:{child_age}".encode()).hexdigest()
   ```

## Root Cause Investigation

1. **Analyze request patterns:**
   - Are there too many similar requests?
   - Is retry logic too aggressive?
   - Are there batch operations that can be optimized?

2. **Check rate limit headers:**
   ```python
   # Log rate limit headers from API responses
   headers = response.headers
   print(f"Rate limit: {headers.get('x-ratelimit-limit')}")
   print(f"Remaining: {headers.get('x-ratelimit-remaining')}")
   print(f"Reset: {headers.get('x-ratelimit-reset')}")
   ```

## Prevention

1. Implement intelligent caching
2. Request batching where possible  
3. Exponential backoff with jitter
4. Monitor API usage trends
5. Upgrade API tier if needed
```

---

## Performance Tuning

### Database Performance

#### Query Optimization

```sql
-- Анализ медленных запросов
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 20;

-- Индексы с низким использованием
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_stat_user_indexes 
ORDER BY idx_scan ASC;

-- Таблицы без индексов (seq_scan)
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    n_tup_ins + n_tup_upd + n_tup_del as write_activity
FROM pg_stat_user_tables 
WHERE seq_scan > 1000
ORDER BY seq_tup_read DESC;
```

#### Optimized Queries Examples

```python
# ❌ Плохо - N+1 проблема
async def get_families_with_children_bad():
    families = await session.execute(select(Family))
    
    result = []
    for family in families.scalars():
        # Отдельный запрос для каждой семьи
        children = await session.execute(
            select(Child).where(Child.family_id == family.id)
        )
        family.children = children.scalars().all()
        result.append(family)
    
    return result

# ✅ Хорошо - eager loading
async def get_families_with_children_good():
    result = await session.execute(
        select(Family)
        .options(selectinload(Family.children))
        .options(selectinload(Family.parents))
    )
    return result.scalars().all()

# ✅ Еще лучше - оптимизированный запрос
async def get_families_summary():
    query = """
    SELECT 
        f.family_id,
        f.name,
        COUNT(DISTINCT c.child_id) as children_count,
        COUNT(DISTINCT p.parent_id) as parents_count,
        MAX(e.created_at) as last_emotion_date
    FROM families f
    LEFT JOIN children c ON f.family_id = c.family_id
    LEFT JOIN parents p ON f.family_id = p.family_id  
    LEFT JOIN emotion_entries e ON c.child_id = e.child_id
    WHERE f.created_at >= NOW() - INTERVAL '30 days'
    GROUP BY f.family_id, f.name
    ORDER BY last_emotion_date DESC NULLS LAST
    """
    
    result = await session.execute(text(query))
    return result.fetchall()
```

### Redis Optimization

```python
# src/infrastructure/cache/optimized_redis.py
import json
import pickle
import asyncio
from typing import Any, Optional, List, Dict
import aioredis
from aioredis.client import Pipeline

class OptimizedRedisService:
    """Оптимизированный Redis сервис для высокой производительности."""
    
    def __init__(self, redis_cluster: aioredis.RedisCluster):
        self.redis = redis_cluster
        self.compression_threshold = 1024  # Сжимаем данные > 1KB
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """Получает множество ключей за один запрос."""
        if not keys:
            return {}
        
        # Используем pipeline для батчинга
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(key)
        
        values = await pipe.execute()
        
        result = {}
        for key, value in zip(keys, values):
            if value:
                result[key] = self._deserialize(value)
        
        return result
    
    async def set_multiple(
        self, 
        data: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> None:
        """Устанавливает множество ключей за один запрос."""
        if not data:
            return
        
        pipe = self.redis.pipeline()
        
        for key, value in data.items():
            serialized = self._serialize(value)
            if ttl:
                pipe.setex(key, ttl, serialized)
            else:
                pipe.set(key, serialized)
        
        await pipe.execute()
    
    async def get_or_set_batch(
        self,
        keys: List[str],
        factory_func: Callable[[List[str]], Dict[str, Any]],
        ttl: int = 3600
    ) -> Dict[str, Any]:
        """Получает данные из кеша или вычисляет для отсутствующих ключей."""
        
        # Получаем существующие данные
        cached_data = await self.get_multiple(keys)
        
        # Находим отсутствующие ключи
        missing_keys = [key for key in keys if key not in cached_data]
        
        if missing_keys:
            # Вычисляем отсутствующие данные
            new_data = await factory_func(missing_keys)
            
            # Кешируем новые данные
            await self.set_multiple(new_data, ttl)
            
            # Объединяем результаты
            cached_data.update(new_data)
        
        return cached_data
    
    def _serialize(self, value: Any) -> bytes:
        """Сериализует значение с опциональным сжатием."""
        # Пробуем JSON (быстрее для простых типов)
        try:
            serialized = json.dumps(value, default=str).encode('utf-8')
        except (TypeError, ValueError):
            # Fallback на pickle для сложных объектов
            serialized = pickle.dumps(value)
        
        # Сжимаем большие объекты
        if len(serialized) > self.compression_threshold:
            import gzip
            return gzip.compress(serialized)
        
        return serialized
    
    def _deserialize(self, value: bytes) -> Any:
        """Десериализует значение с автоматическим распаковыванием."""
        # Проверяем на сжатие (gzip magic number)
        if value[:2] == b'\x1f\x8b':
            import gzip
            value = gzip.decompress(value)
        
        # Пробуем JSON
        try:
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback на pickle
            return pickle.loads(value)

# Кеширование результатов дорогих операций
class EmotionCacheService:
    """Кеширование результатов анализа эмоций."""
    
    def __init__(self, redis_service: OptimizedRedisService):
        self.redis = redis_service
        self.cache_ttl = 3600 * 24  # 24 часа
    
    def _get_cache_key(self, text: str, child_age: int) -> str:
        """Генерирует ключ кеша для эмоции."""
        import hashlib
        text_hash = hashlib.md5(text.lower().encode()).hexdigest()
        return f"emotion:{text_hash}:{child_age}"
    
    async def get_cached_analysis(
        self, 
        text: str, 
        child_age: int
    ) -> Optional[EmotionAnalysis]:
        """Получает закешированный анализ эмоции."""
        cache_key = self._get_cache_key(text, child_age)
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return EmotionAnalysis.from_dict(cached_data)
        
        return None
    
    async def cache_analysis(
        self, 
        text: str, 
        child_age: int, 
        analysis: EmotionAnalysis
    ) -> None:
        """Кеширует результат анализа эмоции."""
        cache_key = self._get_cache_key(text, child_age)
        await self.redis.set(cache_key, analysis.to_dict(), self.cache_ttl)
    
    async def get_similar_analyses(
        self, 
        texts: List[str], 
        child_age: int
    ) -> Dict[str, EmotionAnalysis]:
        """Получает анализы для множества похожих текстов."""
        cache_keys = [self._get_cache_key(text, child_age) for text in texts]
        
        cached_data = await self.redis.get_multiple(cache_keys)
        
        result = {}
        for text, cache_key in zip(texts, cache_keys):
            if cache_key in cached_data:
                result[text] = EmotionAnalysis.from_dict(cached_data[cache_key])
        
        return result

# Использование в сервисе
class OptimizedEmotionService:
    def __init__(
        self, 
        claude_client: ClaudeClient,
        cache_service: EmotionCacheService
    ):
        self.claude = claude_client
        self.cache = cache_service
    
    async def analyze_emotion(
        self, 
        text: str, 
        child_age: int
    ) -> EmotionAnalysis:
        """Анализирует эмоцию с кешированием."""
        
        # Проверяем кеш
        cached_analysis = await self.cache.get_cached_analysis(text, child_age)
        if cached_analysis:
            logger.info("Using cached emotion analysis")
            return cached_analysis
        
        # Вызываем Claude API
        analysis = await self.claude.analyze_emotion(text, child_age)
        
        # Кешируем результат
        await self.cache.cache_analysis(text, child_age, analysis)
        
        return analysis
    
    async def analyze_emotions_batch(
        self, 
        emotion_requests: List[EmotionRequest]
    ) -> List[EmotionAnalysis]:
        """Пакетный анализ эмоций с оптимизированным кешированием."""
        
        # Группируем по возрасту для эффективного кеширования
        by_age = {}
        for req in emotion_requests:
            age = req.child_age
            if age not in by_age:
                by_age[age] = []
            by_age[age].append(req)
        
        results = []
        
        for age, requests in by_age.items():
            texts = [req.text for req in requests]
            
            # Получаем закешированные анализы
            cached_analyses = await self.cache.get_similar_analyses(texts, age)
            
            # Находим тексты, которые нужно обработать
            uncached_requests = [
                req for req in requests 
                if req.text not in cached_analyses
            ]
            
            # Обрабатываем незакешированные
            if uncached_requests:
                new_analyses = await self.claude.analyze_emotions_batch(
                    uncached_requests
                )
                
                # Кешируем новые результаты
                cache_data = {
                    req.text: analysis 
                    for req, analysis in zip(uncached_requests, new_analyses)
                }
                
                for text, analysis in cache_data.items():
                    await self.cache.cache_analysis(text, age, analysis)
                
                # Объединяем с закешированными
                cached_analyses.update(cache_data)
            
            # Добавляем результаты в правильном порядке
            for req in requests:
                results.append(cached_analyses[req.text])
        
        return results
```

---

*Operations Guide Version: 1.0*  
*Last Updated: August 14, 2025*  
*For questions: ops-team@familyemotions.app*