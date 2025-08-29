"""Claude API service for emotion analysis and translation."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx
from anthropic import AsyncAnthropic

from ...core.config import settings
from ...core.exceptions import ExternalServiceError, RateLimitExceededError
from ...core.localization import get_cultural_context, Language

logger = logging.getLogger(__name__)


@dataclass
class EmotionAnalysisRequest:
    """Request data for emotion analysis."""
    child_message: str
    child_age: int
    child_name: str
    situation_context: Optional[str] = None
    personality_traits: Optional[str] = None
    special_needs: Optional[str] = None
    interests: Optional[str] = None


@dataclass
class EmotionAnalysisResponse:
    """Response from emotion analysis."""
    detected_emotions: List[str]
    response_options: List[Dict[str, str]]
    confidence_score: float
    explanation: str
    processing_time_ms: int


class ClaudeService:
    """Service for interacting with Claude API for emotion analysis."""
    
    def __init__(self):
        # Log all proxy-related settings for debugging
        logger.info(f"Checking proxy configuration...")
        logger.info(f"ANTHROPIC_PROXY_URL from settings: {settings.anthropic.proxy_url}")
        
        # Also check environment directly
        import os
        env_proxy = os.environ.get('ANTHROPIC_PROXY_URL')
        logger.info(f"ANTHROPIC_PROXY_URL from environment: {env_proxy}")
        
        # Check if proxy is configured
        if settings.anthropic.proxy_url:
            # Convert localhost proxy URLs for Docker container access
            proxy_url = settings.anthropic.proxy_url
            if proxy_url.startswith('socks5://127.0.0.1') or proxy_url.startswith('http://127.0.0.1'):
                # Try different approaches for container-to-host access
                # First try host.docker.internal (works on Docker Desktop)
                proxy_url_host_internal = proxy_url.replace('127.0.0.1', 'host.docker.internal')
                
                # Also try getting the actual host IP from Docker gateway
                try:
                    import subprocess
                    result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Extract gateway IP
                        gateway_ip = result.stdout.split()[2] if len(result.stdout.split()) > 2 else None
                        if gateway_ip:
                            proxy_url_gateway = proxy_url.replace('127.0.0.1', gateway_ip)
                            logger.info(f"Found Docker gateway IP: {gateway_ip}")
                            proxy_url = proxy_url_gateway
                        else:
                            proxy_url = proxy_url_host_internal
                    else:
                        proxy_url = proxy_url_host_internal
                except Exception:
                    proxy_url = proxy_url_host_internal
                
                logger.info(f"Converted proxy URL for Docker: {settings.anthropic.proxy_url} -> {proxy_url}")
            
            logger.info(f"Using proxy for Claude API: {proxy_url}")
            
            # Try multiple proxy configurations if the first fails
            proxy_urls_to_try = [proxy_url]
            if proxy_url != settings.anthropic.proxy_url:
                # If we converted the URL, also try the original as fallback
                proxy_urls_to_try.append(settings.anthropic.proxy_url)
            
            # Also try host.docker.internal explicitly if not already tried
            if 'host.docker.internal' not in proxy_url:
                host_internal_url = settings.anthropic.proxy_url.replace('127.0.0.1', 'host.docker.internal')
                if host_internal_url not in proxy_urls_to_try:
                    proxy_urls_to_try.append(host_internal_url)
            
            proxy_configured = False
            for try_proxy_url in proxy_urls_to_try:
                try:
                    logger.info(f"Trying proxy configuration: {try_proxy_url}")
                    http_client = httpx.AsyncClient(
                        proxy=try_proxy_url,
                        timeout=httpx.Timeout(30.0),
                        verify=False
                    )
                    self._client = AsyncAnthropic(
                        api_key=settings.anthropic.api_key,
                        http_client=http_client
                    )
                    logger.info(f"Proxy configured successfully with: {try_proxy_url}")
                    proxy_configured = True
                    break
                except Exception as e:
                    logger.warning(f"Failed proxy configuration {try_proxy_url}: {e}")
            
            if not proxy_configured:
                logger.error("All proxy configurations failed, falling back to direct connection")
                self._client = AsyncAnthropic(api_key=settings.anthropic.api_key)
        else:
            logger.info("No proxy configured for Claude API")
            self._client = AsyncAnthropic(api_key=settings.anthropic.api_key)
            
        self._rate_limiter = RateLimiter(
            requests_per_minute=settings.anthropic.requests_per_minute,
            requests_per_day=settings.anthropic.requests_per_day
        )
    
    async def analyze_child_emotions(
        self, 
        request: EmotionAnalysisRequest
    ) -> EmotionAnalysisResponse:
        """
        Analyze child emotions and generate appropriate responses.
        
        Args:
            request: Emotion analysis request data
            
        Returns:
            EmotionAnalysisResponse with analysis results
            
        Raises:
            RateLimitExceededError: If API rate limit is exceeded
            ExternalServiceError: If Claude API request fails
        """
        start_time = time.time()
        
        try:
            # Check rate limits
            await self._rate_limiter.check_limits()
            
            # Generate prompt
            prompt = self._build_emotion_analysis_prompt(request)
            
            # Call Claude API
            response = await self._client.messages.create(
                model=settings.anthropic.model,
                max_tokens=settings.anthropic.max_tokens,
                temperature=settings.anthropic.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            analysis_result = self._parse_claude_response(response.content[0].text)
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            return EmotionAnalysisResponse(
                detected_emotions=analysis_result["emotions"],
                response_options=analysis_result["responses"],
                confidence_score=analysis_result["confidence"],
                explanation=analysis_result["explanation"],
                processing_time_ms=processing_time
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceededError(
                    "Claude API rate limit exceeded",
                    service_name="Claude",
                    status_code=429
                )
            else:
                raise ExternalServiceError(
                    f"Claude API request failed: {e.response.text}",
                    service_name="Claude",
                    status_code=e.response.status_code
                )
        
        except httpx.ConnectError as e:
            logger.error(f"Claude API connection error: {e}")
            logger.error(f"Proxy might be unreachable or not working correctly")
            raise ExternalServiceError(
                f"Connection error - proxy might be down: {str(e)}",
                service_name="Claude"
            )
        
        except Exception as e:
            logger.error(f"Claude API error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise ExternalServiceError(
                f"Unexpected Claude API error: {str(e)}",
                service_name="Claude"
            )
    
    def _build_emotion_analysis_prompt(self, request: EmotionAnalysisRequest) -> str:
        """Build culturally-adapted prompt for Claude emotion analysis."""
        
        # Get cultural context for Russian audience
        cultural_context = get_cultural_context(Language.RUSSIAN)
        
        # Base context about the child in Russian
        child_context = f"""
Информация о ребенке:
- Имя: {request.child_name}
- Возраст: {request.child_age} лет
"""
        
        if request.personality_traits:
            child_context += f"- Особенности характера: {request.personality_traits}\n"
        
        if request.special_needs:
            child_context += f"- Особые потребности: {request.special_needs}\n"
        
        if request.interests:
            child_context += f"- Интересы: {request.interests}\n"
        
        # Situation context
        situation = ""
        if request.situation_context:
            situation = f"\nКонтекст ситуации: {request.situation_context}"
        
        # Culturally-adapted prompt for Russian families
        prompt = f"""Вы - эксперт по детской психологии и переводчик эмоций, работающий с российскими семьями. Ваша задача - помочь родителям понять эмоции своих детей и дать подходящие советы.

КУЛЬТУРНЫЙ КОНТЕКСТ:
- Российский стиль воспитания: сочетание авторитетности и уважения
- Умеренная прямота в общении
- Практичные советы с эмпатией
- Семейные ценности: смесь традиционных и современных подходов

{child_context}

Сообщение или поведение ребенка: "{request.child_message}"{situation}

Пожалуйста, проанализируйте эмоциональное состояние этого ребенка и предоставьте:

1. ОБНАРУЖЕННЫЕ ЭМОЦИИ: Перечислите основные эмоции (максимум 3)
2. ОЦЕНКА УВЕРЕННОСТИ: От 0.1 до 1.0
3. ТРИ ВАРИАНТА ОТВЕТА: Предоставьте ровно 3 разных способа реагирования:
   - Краткий заголовок (5-10 слов)
   - Текст ответа (соответствующий возрасту)
   - Эмоциональный подход (подтверждающий, перенаправляющий, обучающий)

4. ОБЪЯСНЕНИЕ: Краткое объяснение определенных эмоций

Ответы должны быть:
- Подходящими возрасту по языку и концепциям
- Эмоционально поддерживающими
- Практичными для родителей
- Культурно приемлемыми для российских семей
- Отражающими баланс авторитета и эмпатии

Оформите свой ответ как JSON на русском языке:
{{
  "emotions": ["эмоция1", "эмоция2", "эмоция3"],
  "confidence": 0.85,
  "responses": [
    {{
      "title": "Подтверждающий ответ",
      "text": "Я вижу, что ты чувствуешь...",
      "approach": "подтверждение"
    }},
    {{
      "title": "Обучающий ответ", 
      "text": "Давай поговорим о...",
      "approach": "обучение"
    }},
    {{
      "title": "Перенаправляющий ответ",
      "text": "Как насчёт попробовать...",
      "approach": "перенаправление"
    }}
  ],
  "explanation": "Ребенок, по-видимому, испытывает... потому что..."
}}"""
        
        return prompt
    
    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse Claude's JSON response."""
        try:
            import json
            
            # Find JSON in response (Claude might add extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in Claude response")
            
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['emotions', 'confidence', 'responses', 'explanation']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate response structure
            if not isinstance(parsed['emotions'], list):
                raise ValueError("Emotions must be a list")
            
            if not isinstance(parsed['responses'], list) or len(parsed['responses']) != 3:
                raise ValueError("Must provide exactly 3 response options")
            
            for response in parsed['responses']:
                required_response_fields = ['title', 'text', 'approach']
                for field in required_response_fields:
                    if field not in response:
                        raise ValueError(f"Response missing field: {field}")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise ExternalServiceError(
                "Invalid JSON response from Claude API",
                service_name="Claude"
            )
        
        except ValueError as e:
            logger.error(f"Invalid Claude response structure: {e}")
            raise ExternalServiceError(
                f"Invalid response structure: {str(e)}",
                service_name="Claude"
            )
    
    async def generate_weekly_report(
        self,
        child_name: str,
        child_age: int,
        emotion_data: List[Dict],
        checkin_data: List[Dict],
        period_start: str,
        period_end: str
    ) -> Dict[str, str]:
        """
        Generate a weekly emotional development report.
        
        Args:
            child_name: Name of the child
            child_age: Age of the child
            emotion_data: List of emotion translation data
            checkin_data: List of check-in responses
            period_start: Start of the week (YYYY-MM-DD)
            period_end: End of the week (YYYY-MM-DD)
            
        Returns:
            Dictionary with report sections
        """
        try:
            await self._rate_limiter.check_limits()
            
            # Build summary data
            emotion_summary = self._summarize_emotions(emotion_data)
            checkin_summary = self._summarize_checkins(checkin_data)
            
            prompt = f"""Составьте подробный еженедельный отчёт об эмоциональном развитии ребёнка для российской семьи.

Информация о ребёнке:
- Имя: {child_name}
- Возраст: {child_age} лет
- Период отчёта: {period_start} - {period_end}

Данные о переводе эмоций:
{emotion_summary}

Данные проверок:
{checkin_summary}

Пожалуйста, создайте отчёт со следующими разделами:

1. КРАТКОЕ РЕЗЮМЕ: Краткий обзор эмоциональной недели ребёнка
2. ЭМОЦИОНАЛЬНЫЕ ТЕНДЕНЦИИ: Ключевые закономерности и тенденции
3. ГЛУБОКИЕ НАБЛЮДЕНИЯ: Понимание эмоционального развития
4. РЕКОМЕНДАЦИИ: 3-5 конкретных рекомендаций для родителей
5. ПОЛОЖИТЕЛЬНЫЕ МОМЕНТЫ: Отметить эмоциональный рост ребёнка

Сделайте отчёт:
- Позитивным и ориентированным на рост
- Практичным для родителей
- Подходящим для возраста в рекомендациях
- Основанным на предоставленных данных
- Культурно приемлемым для российских семей

Оформите как JSON на русском языке:
{{
  "summary": "Краткое резюме...",
  "trends": "Анализ эмоциональных тенденций...",
  "insights": "Глубокие наблюдения...",  
  "recommendations": ["Рекомендация 1", "Рекомендация 2", ...],
  "highlights": "Положительные моменты..."
}}"""
            
            response = await self._client.messages.create(
                model=settings.anthropic.model,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more consistent reports
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._parse_claude_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}")
            raise ExternalServiceError(
                f"Failed to generate weekly report: {str(e)}",
                service_name="Claude"
            )
    
    def _summarize_emotions(self, emotion_data: List[Dict]) -> str:
        """Summarize emotion data for report generation."""
        if not emotion_data:
            return "No emotion translation data available for this period."
        
        emotions_count = {}
        situations = []
        
        for item in emotion_data:
            # Count emotions
            for emotion in item.get('detected_emotions', []):
                emotions_count[emotion] = emotions_count.get(emotion, 0) + 1
            
            # Collect situations
            if item.get('situation_context'):
                situations.append(item['situation_context'])
        
        summary = f"Total emotion translations: {len(emotion_data)}\n"
        
        if emotions_count:
            summary += "Most common emotions:\n"
            sorted_emotions = sorted(emotions_count.items(), key=lambda x: x[1], reverse=True)
            for emotion, count in sorted_emotions[:5]:
                summary += f"- {emotion}: {count} times\n"
        
        if situations:
            summary += f"Common situations: {', '.join(situations[:3])}"
        
        return summary
    
    def _summarize_checkins(self, checkin_data: List[Dict]) -> str:
        """Summarize check-in data for report generation."""
        if not checkin_data:
            return "No check-in data available for this period."
        
        completed = sum(1 for item in checkin_data if item.get('is_completed'))
        total = len(checkin_data)
        
        mood_scores = [item.get('mood_score') for item in checkin_data 
                      if item.get('mood_score') is not None]
        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else 0
        
        summary = f"Check-ins completed: {completed}/{total}\n"
        summary += f"Average mood score: {avg_mood:.1f}/5\n"
        
        # Add some sample responses
        responses = [item.get('response_text') for item in checkin_data[:3] 
                    if item.get('response_text')]
        if responses:
            summary += f"Sample responses: {', '.join(responses)}"
        
        return summary


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int, requests_per_day: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.minute_requests = []
        self.daily_requests = []
    
    async def check_limits(self) -> None:
        """Check if we're within rate limits."""
        now = time.time()
        
        # Clean old requests
        self.minute_requests = [t for t in self.minute_requests if now - t < 60]
        self.daily_requests = [t for t in self.daily_requests if now - t < 86400]
        
        # Check limits
        if len(self.minute_requests) >= self.requests_per_minute:
            raise RateLimitExceededError(
                "Rate limit exceeded: too many requests per minute",
                retry_after=60
            )
        
        if len(self.daily_requests) >= self.requests_per_day:
            raise RateLimitExceededError(
                "Rate limit exceeded: too many requests per day",
                retry_after=86400
            )
        
        # Record this request
        self.minute_requests.append(now)
        self.daily_requests.append(now)