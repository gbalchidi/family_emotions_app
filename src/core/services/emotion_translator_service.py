"""Emotion translator service for Family Emotions App."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from src.core.domain.entities import EmotionTranslation
from src.core.domain.exceptions import EmotionTranslationException, RateLimitExceededException
from decimal import Decimal

from src.core.domain.value_objects import (
    Age,
    EmotionContext,
    EmotionInsight,
    EmotionIntensity,
    MoodScore,
    TranslationRequest
)
from src.core.repositories.interfaces import EmotionTranslationRepository, UserRepository
from src.infrastructure.cache.redis_service import RedisService
from src.infrastructure.external.claude_service import ClaudeService

logger = logging.getLogger(__name__)


class EmotionTranslatorService:
    """Service for translating children's emotions using Claude API."""
    
    def __init__(
        self,
        claude_service: ClaudeService,
        user_repository: UserRepository,
        translation_repository: EmotionTranslationRepository,
        redis_service: RedisService
    ):
        self.claude_service = claude_service
        self.user_repository = user_repository
        self.translation_repository = translation_repository
        self.redis_service = redis_service
    
    async def translate_emotion(
        self,
        user_id: UUID,
        message: str,
        child_id: Optional[UUID] = None,
        context: Optional[EmotionContext] = None,
        use_cache: bool = True
    ) -> EmotionTranslation:
        """
        Translate a child's emotional expression.
        
        Args:
            user_id: User requesting translation
            message: Original message from child
            child_id: Optional child ID for context
            context: Optional emotion context
            use_cache: Whether to use cached responses
            
        Returns:
            EmotionTranslation entity with insights
        """
        # Get user and check limits
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise EmotionTranslationException("User not found")
        
        if not user.can_make_request("translation"):
            raise RateLimitExceededException("daily")
        
        # Get child context if provided
        if child_id and not context:
            child = user.get_child(child_id)
            if child:
                context = child.get_context()
        
        # Create translation request
        request = TranslationRequest(
            original_message=message,
            child_context=context or EmotionContext(
                child_age=Age(value=7)  # Default age if no context
            ),
            parent_language=user.language_code
        )
        
        # Check cache if enabled
        cache_key = self._get_cache_key(request)
        if use_cache:
            cached_response = await self.redis_service.get(cache_key)
            if cached_response:
                logger.info(f"Using cached translation for user {user_id}")
                return self._parse_cached_response(cached_response, request, user_id, child_id)
        
        # Create translation entity
        translation = EmotionTranslation(
            request=request,
            user_id=user_id,
            child_id=child_id
        )
        
        try:
            # Generate prompt
            prompt = self._generate_prompt(request)
            
            # Call Claude API
            start_time = datetime.now(timezone.utc)
            response = await self.claude_service.generate_completion(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3  # Lower temperature for more consistent responses
            )
            processing_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Parse response
            insights = self._parse_claude_response(response)
            
            # Add insights to translation
            for insight in insights:
                translation.add_insight(insight)
            
            # Calculate mood score
            translation.calculate_mood_score()
            translation.processing_time_ms = processing_time_ms
            
            # Cache successful response
            if use_cache:
                await self.redis_service.set(
                    cache_key,
                    self._serialize_translation(translation),
                    expire=3600  # Cache for 1 hour
                )
            
            # Save to repository
            await self.translation_repository.save(translation)
            
            # Update user request count
            user.increment_request_count()
            await self.user_repository.update(user)
            
            logger.info(f"Successfully translated emotion for user {user_id}")
            return translation
            
        except Exception as e:
            logger.error(f"Error translating emotion: {str(e)}")
            raise EmotionTranslationException(f"Translation failed: {str(e)}")
    
    def _generate_prompt(self, request: TranslationRequest) -> str:
        """Generate prompt for Claude API."""
        context_str = request.child_context.to_prompt_context()
        
        prompt = f"""You are an expert child psychologist helping parents understand their children's emotions.

CONTEXT:
{context_str}

CHILD'S MESSAGE:
"{request.original_message}"

TASK:
Analyze this message and provide emotional insights in JSON format.

Consider:
1. The child's developmental stage and age-appropriate emotional expression
2. Underlying emotions that may not be directly expressed
3. Intensity of emotions (1-5 scale)
4. Potential triggers or causes
5. Supportive responses a parent could offer

Response must be valid JSON with this structure:
{{
    "insights": [
        {{
            "emotion": "primary emotion name",
            "intensity": 1-5,
            "confidence": 0.0-1.0,
            "explanation": "brief explanation of why this emotion is present",
            "suggested_responses": ["response 1", "response 2", "response 3"]
        }}
    ],
    "overall_mood": "positive/negative/neutral/mixed",
    "attention_required": true/false,
    "additional_context": "any important observations"
}}

Focus on being helpful, empathetic, and providing actionable guidance for the parent.
Response style: {request.response_style}"""
        
        return prompt
    
    def _parse_claude_response(self, response: str) -> List[EmotionInsight]:
        """Parse Claude API response into emotion insights."""
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            insights = []
            for insight_data in data.get("insights", []):
                # Map intensity value to enum
                intensity_value = insight_data.get("intensity", 3)
                intensity = EmotionIntensity(min(max(intensity_value, 1), 5))
                
                insight = EmotionInsight(
                    emotion=insight_data.get("emotion", "unknown"),
                    intensity=intensity,
                    confidence=Decimal(str(insight_data.get("confidence", 0.5))),
                    explanation=insight_data.get("explanation", ""),
                    suggested_responses=insight_data.get("suggested_responses", ["I understand how you feel"])
                )
                insights.append(insight)
            
            return insights
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            # Return a default insight if parsing fails
            return [
                EmotionInsight(
                    emotion="uncertain",
                    intensity=EmotionIntensity.MODERATE,
                    confidence=Decimal("0.3"),
                    explanation="Unable to fully analyze the emotional content",
                    suggested_responses=[
                        "Tell me more about how you're feeling",
                        "I'm here to listen",
                        "Your feelings are important"
                    ]
                )
            ]
    
    def _get_cache_key(self, request: TranslationRequest) -> str:
        """Generate cache key for translation request."""
        # Create a deterministic key based on request content
        key_parts = [
            "emotion_translation",
            request.original_message[:100],  # First 100 chars
            str(request.child_context.child_age.value),
            request.parent_language,
            request.response_style
        ]
        return ":".join(key_parts)
    
    def _serialize_translation(self, translation: EmotionTranslation) -> str:
        """Serialize translation for caching."""
        data = {
            "insights": [
                {
                    "emotion": insight.emotion,
                    "intensity": insight.intensity.value,
                    "confidence": float(insight.confidence),
                    "explanation": insight.explanation,
                    "suggested_responses": insight.suggested_responses
                }
                for insight in translation.insights
            ],
            "mood_score": float(translation.mood_score.value) if translation.mood_score else None,
            "processing_time_ms": translation.processing_time_ms
        }
        return json.dumps(data)
    
    def _parse_cached_response(
        self,
        cached_data: str,
        request: TranslationRequest,
        user_id: UUID,
        child_id: Optional[UUID]
    ) -> EmotionTranslation:
        """Parse cached response into translation entity."""
        data = json.loads(cached_data)
        
        translation = EmotionTranslation(
            request=request,
            user_id=user_id,
            child_id=child_id,
            processing_time_ms=0  # Cached response
        )
        
        for insight_data in data.get("insights", []):
            insight = EmotionInsight(
                emotion=insight_data["emotion"],
                intensity=EmotionIntensity(insight_data["intensity"]),
                confidence=Decimal(str(insight_data["confidence"])),
                explanation=insight_data["explanation"],
                suggested_responses=insight_data["suggested_responses"]
            )
            translation.add_insight(insight)
        
        if data.get("mood_score") is not None:
            translation.mood_score = MoodScore(value=Decimal(str(data["mood_score"])))
        
        return translation
    
    async def get_translation_history(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        days: int = 7
    ) -> List[EmotionTranslation]:
        """Get translation history for user/child."""
        if child_id:
            return await self.translation_repository.get_by_child_id(child_id, limit=50)
        else:
            return await self.translation_repository.get_recent(user_id, days=days)
    
    async def analyze_emotion_trends(
        self,
        user_id: UUID,
        child_id: UUID,
        days: int = 30
    ) -> Dict[str, any]:
        """Analyze emotion trends for a child over time."""
        translations = await self.translation_repository.get_by_child_id(
            child_id,
            limit=100
        )
        
        if not translations:
            return {
                "trend": "insufficient_data",
                "emotions": {},
                "average_mood": 0,
                "insights": []
            }
        
        # Aggregate emotions
        emotion_counts = {}
        total_mood = Decimal("0")
        mood_count = 0
        
        for translation in translations:
            if translation.mood_score:
                total_mood += translation.mood_score.value
                mood_count += 1
            
            for insight in translation.insights:
                emotion = insight.emotion
                if emotion not in emotion_counts:
                    emotion_counts[emotion] = {
                        "count": 0,
                        "total_intensity": 0,
                        "high_confidence_count": 0
                    }
                
                emotion_counts[emotion]["count"] += 1
                emotion_counts[emotion]["total_intensity"] += insight.intensity.value
                if insight.is_high_confidence():
                    emotion_counts[emotion]["high_confidence_count"] += 1
        
        # Calculate averages
        average_mood = float(total_mood / mood_count) if mood_count > 0 else 0
        
        # Determine trend
        if len(translations) >= 2:
            recent_mood = sum(
                t.mood_score.value for t in translations[:5] 
                if t.mood_score
            ) / min(5, len(translations))
            
            older_mood = sum(
                t.mood_score.value for t in translations[5:10] 
                if t.mood_score
            ) / min(5, len(translations[5:10])) if len(translations) > 5 else recent_mood
            
            if recent_mood > older_mood + Decimal("0.2"):
                trend = "improving"
            elif recent_mood < older_mood - Decimal("0.2"):
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "emotions": emotion_counts,
            "average_mood": average_mood,
            "total_translations": len(translations),
            "insights": self._generate_trend_insights(emotion_counts, average_mood, trend)
        }
    
    def _generate_trend_insights(
        self,
        emotion_counts: Dict,
        average_mood: float,
        trend: str
    ) -> List[str]:
        """Generate insights from emotion trends."""
        insights = []
        
        # Find most common emotions
        if emotion_counts:
            sorted_emotions = sorted(
                emotion_counts.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            
            top_emotion = sorted_emotions[0][0]
            insights.append(f"Most frequently expressed emotion: {top_emotion}")
            
            # Check for concerning patterns
            concerning_emotions = ["sadness", "anger", "fear", "anxiety"]
            concerning_count = sum(
                data["count"] for emotion, data in emotion_counts.items()
                if emotion.lower() in concerning_emotions
            )
            
            total_count = sum(data["count"] for data in emotion_counts.values())
            if concerning_count > total_count * 0.5:
                insights.append("High frequency of concerning emotions detected. Consider professional consultation.")
        
        # Mood insights
        if average_mood < -0.3:
            insights.append("Overall mood tends to be negative. Focus on emotional support and validation.")
        elif average_mood > 0.3:
            insights.append("Overall mood is positive. Continue current supportive approach.")
        
        # Trend insights
        if trend == "improving":
            insights.append("Emotional well-being is showing improvement over time.")
        elif trend == "declining":
            insights.append("Emotional well-being may be declining. Increased attention recommended.")
        
        return insights