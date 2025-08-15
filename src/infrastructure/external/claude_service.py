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
        
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise ExternalServiceError(
                f"Unexpected Claude API error: {str(e)}",
                service_name="Claude"
            )
    
    def _build_emotion_analysis_prompt(self, request: EmotionAnalysisRequest) -> str:
        """Build the prompt for Claude emotion analysis."""
        
        # Base context about the child
        child_context = f"""
Child Information:
- Name: {request.child_name}
- Age: {request.child_age} years old
"""
        
        if request.personality_traits:
            child_context += f"- Personality traits: {request.personality_traits}\n"
        
        if request.special_needs:
            child_context += f"- Special considerations: {request.special_needs}\n"
        
        if request.interests:
            child_context += f"- Interests: {request.interests}\n"
        
        # Situation context
        situation = ""
        if request.situation_context:
            situation = f"\nSituation context: {request.situation_context}"
        
        # Main prompt
        prompt = f"""You are an expert child psychologist and emotion translator. Your job is to help parents understand their child's emotions and provide appropriate responses.

{child_context}

Child's message or behavior: "{request.child_message}"{situation}

Please analyze this child's emotional state and provide:

1. DETECTED EMOTIONS: List the primary emotions you detect (maximum 3)
2. CONFIDENCE SCORE: Rate your confidence in this analysis from 0.1 to 1.0
3. THREE RESPONSE OPTIONS: Provide exactly 3 different ways the parent could respond, each with:
   - A brief title (5-10 words)
   - The actual response text (age-appropriate)
   - The emotional approach (validating, redirecting, teaching, etc.)

4. EXPLANATION: Brief explanation of why you identified these emotions and why these responses would be effective

Consider the child's age and developmental stage. Responses should be:
- Age-appropriate in language and concept
- Emotionally validating
- Practical for parents to use
- Culturally sensitive

Format your response as JSON:
{{
  "emotions": ["emotion1", "emotion2", "emotion3"],
  "confidence": 0.85,
  "responses": [
    {{
      "title": "Validating Response",
      "text": "I can see you're feeling...",
      "approach": "validation"
    }},
    {{
      "title": "Teaching Response", 
      "text": "Let's talk about...",
      "approach": "teaching"
    }},
    {{
      "title": "Redirecting Response",
      "text": "How about we try...",
      "approach": "redirection"
    }}
  ],
  "explanation": "The child appears to be experiencing... because..."
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
            
            prompt = f"""Generate a comprehensive weekly emotional development report for a child.

Child Information:
- Name: {child_name}
- Age: {child_age} years old
- Report Period: {period_start} to {period_end}

Emotion Translation Data:
{emotion_summary}

Check-in Data:
{checkin_summary}

Please create a report with the following sections:

1. EXECUTIVE SUMMARY: Brief overview of the child's emotional week
2. EMOTIONAL TRENDS: Key patterns and trends observed
3. INSIGHTS: Deep insights about the child's emotional development
4. RECOMMENDATIONS: 3-5 specific recommendations for parents
5. POSITIVE HIGHLIGHTS: Celebrate the child's emotional growth

Make the report:
- Positive and growth-focused
- Practical for parents
- Age-appropriate in recommendations
- Evidence-based on the provided data

Format as JSON:
{{
  "summary": "Executive summary text...",
  "trends": "Emotional trends analysis...",
  "insights": "Deep insights text...",  
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "highlights": "Positive highlights text..."
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