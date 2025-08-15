# Family Emotions App - Architecture Documentation

## Architecture Overview

Family Emotions App is built using **Domain-Driven Design (DDD)** principles with **Clean Architecture**. The application helps parents understand their children's emotions through AI-powered translation and analysis.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
├─────────────────────┬───────────────────────────────────────┤
│   Telegram Bot      │            REST API                   │
│   - Commands        │            - Health Check             │
│   - Conversations   │            - Webhooks                 │  
│   - Inline Keyboards│            - Admin Panel              │
└─────────────────────┴───────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────┬─────────────────────┬─────────────────┤
│   Services          │   Command Handlers  │   Query Handlers│
│   - CheckinService  │   - CreateUser      │   - GetReports  │
│   - SchedulerService│   - AddChild        │   - GetTrends   │
│   - NotificationSvc │   - TranslateEmotion│   - GetHistory  │
└─────────────────────┴─────────────────────┴─────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                           │
├─────────────────────┬─────────────────────┬─────────────────┤
│   Aggregates        │   Entities          │   Value Objects │
│   - User            │   - Child           │   - Age         │
│   - Family          │   - EmotionTrans    │   - MoodScore   │
│                     │   - CheckIn         │   - EmotionCtx  │
│                     │   - WeeklyReport    │   - Permissions │
└─────────────────────┴─────────────────────┴─────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                      │
├─────────────────────┬─────────────────────┬─────────────────┤
│   Database          │   External APIs     │   Cache         │
│   - PostgreSQL      │   - Claude API      │   - Redis       │
│   - SQLAlchemy      │   - Telegram API    │   - Rate Limiting│
│   - Alembic         │   - HTTP Client     │   - Sessions    │
└─────────────────────┴─────────────────────┴─────────────────┘
```

## Core Components

### 1. Domain Layer

**Aggregates:**
- `User` - Root aggregate managing family data, children, subscriptions
- Contains business rules for subscription limits, permissions

**Entities:**
- `Child` - Child profile with age, personality, interests
- `EmotionTranslation` - AI analysis results with insights
- `CheckIn` - Daily/weekly emotional check-ins
- `FamilyMember` - Additional family members with permissions

**Value Objects:**
- `Age` - Age validation and age group classification
- `MoodScore` - Normalized mood scoring (-1 to 1)
- `EmotionContext` - Context for AI analysis
- `FamilyPermissions` - Role-based access control

**Domain Events:**
- `UserRegisteredEvent`
- `ChildAddedEvent` 
- `EmotionTranslatedEvent`
- `CheckInCompletedEvent`

### 2. Application Layer

**Services:**
- `EmotionTranslatorService` - AI-powered emotion analysis
- `CheckInService` - Scheduled emotional check-ins
- `AnalyticsService` - Report generation with insights
- `FamilyService` - Family and child management
- `UserService` - User lifecycle management

### 3. Infrastructure Layer

**Repositories:**
- `SQLAlchemyUserRepository`
- `SQLAlchemyChildRepository`
- `SQLAlchemyEmotionTranslationRepository`
- Pattern: Repository interface in domain, implementation in infrastructure

**External Services:**
- `ClaudeService` - Anthropic Claude API integration
- `TelegramBot` - Bot interaction handling
- `RedisService` - Caching and rate limiting

**Database:**
- PostgreSQL with async SQLAlchemy 2.0
- Alembic migrations
- Connection pooling and health checks

## Key Design Patterns

### 1. Domain-Driven Design (DDD)
```python
# Aggregate with business rules
class User:
    def add_child(self, name: str, age: int) -> Child:
        # Business rule: subscription limits
        max_children = self.subscription_plan["max_children"]
        if len(self.children) >= max_children:
            raise SubscriptionLimitExceededException(...)
        
        child = Child(name=name, age=Age(value=age), parent_id=self.id)
        self.children.append(child)
        
        # Domain event
        self._add_event(ChildAddedEvent(...))
        return child
```

### 2. Repository Pattern
```python
# Interface in domain
class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> None: ...
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]: ...

# Implementation in infrastructure
class SQLAlchemyUserRepository(UserRepository):
    async def save(self, user: User) -> None:
        # Map domain aggregate to SQLAlchemy models
        db_user = self._map_to_db_model(user)
        await self._session.commit()
```

### 3. Dependency Injection
```python
class ApplicationContainer(containers.DeclarativeContainer):
    # External services
    claude_service = providers.Singleton(ClaudeService, api_key=settings.claude.api_key)
    
    # Repositories
    user_repository = providers.Factory(SQLAlchemyUserRepository, session=providers.Dependency())
    
    # Services
    emotion_translator_service = providers.Factory(
        EmotionTranslatorService,
        claude_service=claude_service,
        user_repository=user_repository,
        redis_service=cache_service
    )
```

### 4. CQRS-Inspired Pattern
```python
# Command - modifies state
async def create_user_command(telegram_id: int, first_name: str) -> User:
    user = User(telegram_id=telegram_id, first_name=first_name)
    await user_repository.save(user)
    return user

# Query - reads state  
async def get_user_statistics_query(user_id: UUID) -> UserStatistics:
    return await analytics_service.get_user_statistics(user_id)
```

## Data Flow

### Emotion Translation Flow
```
1. User sends message via Telegram
2. TelegramBot validates request and extracts context
3. EmotionTranslatorService:
   - Checks rate limits (Redis)
   - Gets user and child context (Repository)
   - Calls Claude API with structured prompt
   - Parses and validates AI response
   - Creates EmotionTranslation entity
   - Caches result (Redis)
   - Saves to database (Repository)
4. Returns formatted response to user
5. Domain events trigger analytics updates
```

### Weekly Report Generation
```
1. Scheduler triggers weekly report job
2. AnalyticsService:
   - Queries check-ins and translations (Repository)
   - Aggregates emotion data by time periods
   - Generates AI insights via Claude API
   - Creates WeeklyReport entity
   - Saves to database (Repository)
3. Bot sends report to user via Telegram
4. Domain event logs report generation
```

## Database Schema

### Core Tables
```sql
users (
    id UUID PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    subscription_status VARCHAR(20) DEFAULT 'free',
    daily_requests_count INTEGER DEFAULT 0,
    ...
)

children (
    id UUID PRIMARY KEY,
    parent_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    age INTEGER CHECK (age >= 0 AND age <= 18),
    personality_traits TEXT,
    ...
)

emotion_translations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    child_id UUID REFERENCES children(id) ON DELETE SET NULL,
    original_message TEXT NOT NULL,
    translated_emotions JSONB,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ...
)
```

## Error Handling Strategy

### 1. Domain Exceptions
```python
class DomainException(Exception):
    """Base for all domain rule violations"""
    
class SubscriptionLimitExceededException(DomainException):
    """When user exceeds subscription limits"""
    
class RateLimitExceededException(DomainException):  
    """When rate limit is exceeded"""
```

### 2. Infrastructure Error Handling
```python
# Retry logic for external APIs
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(httpx.RequestError)
)
async def call_claude_api(prompt: str) -> str:
    # API call with automatic retries
```

### 3. User-Facing Error Messages
```python
# Convert technical errors to user-friendly messages
async def handle_error(update: Update, error: Exception):
    if isinstance(error, RateLimitExceededException):
        await update.message.reply_text(
            "⏳ Daily limit reached. Upgrade to Premium for more requests!"
        )
    elif isinstance(error, EmotionTranslationException):
        await update.message.reply_text(
            "❌ Analysis failed. Please try again or contact support."
        )
```

## Performance Optimizations

### 1. Caching Strategy
```python
# Cache translation results
cache_key = f"translation:{hash(message + context)}"
await redis_service.set(cache_key, result, expire=3600)

# Cache user data  
await cache_service.cache_user(user_id, user_data, ttl=1800)

# Rate limiting
is_allowed, count, reset_time = await cache_service.check_rate_limit(
    user_id, "translation", limit=10, window_seconds=86400
)
```

### 2. Database Optimizations
```python
# Use selective loading
stmt = (
    select(User)
    .options(selectinload(User.children))
    .where(User.telegram_id == telegram_id)
)

# Connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 3. Async/Await Throughout
```python
# All I/O operations are async
async def translate_emotion(message: str) -> EmotionTranslation:
    async with self.session.begin():
        user = await self.user_repository.get_by_id(user_id)
        translation = await self.claude_service.translate(message)
        await self.translation_repository.save(translation)
        return translation
```

## Security Considerations

### 1. Data Protection
- All user data encrypted at rest
- Sensitive fields (like special needs) use additional encryption
- Regular data retention policy enforcement

### 2. API Security
- Rate limiting per user and globally
- Input validation and sanitization
- Timeout protection for external API calls

### 3. Access Control
- Role-based permissions for family members
- Telegram user ID verification
- Session-based access control

## Deployment Architecture

### Development
```bash
# Start all services
docker-compose up -d postgres redis
python -m src.main --mode run --env development
```

### Production
```bash
# Kubernetes deployment with:
# - PostgreSQL cluster (primary/replica)
# - Redis cluster for caching
# - Multiple bot replicas
# - Load balancer for webhooks
# - Monitoring with Prometheus/Grafana
```

## Monitoring & Observability

### Metrics
- Request rate and response times
- Database connection pool usage
- Cache hit/miss ratios
- Domain event publishing rates
- Error rates by service

### Logging
```python
# Structured logging throughout
logger.info(
    "Emotion translation completed",
    extra={
        "user_id": str(user_id),
        "child_id": str(child_id),
        "processing_time_ms": processing_time,
        "confidence_score": translation.confidence_score,
        "detected_emotions": translation.detected_emotions
    }
)
```

### Health Checks
- Database connectivity
- Redis connectivity  
- External API availability
- Memory and CPU usage

This architecture provides a scalable, maintainable foundation for the Family Emotions App while following domain-driven design principles and clean architecture patterns.