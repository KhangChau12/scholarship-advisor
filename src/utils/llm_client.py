"""
Together AI LLM Client for Scholarship Advisor
"""
import asyncio
from typing import List, Dict, Any, Optional
import openai
from loguru import logger
import time

from ..config.settings import settings

class TogetherAIClient:
    """Client for Together AI API"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.TOGETHER_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        self.model = settings.LLM_MODEL
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Rate limiting
        
    async def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate response from Together AI
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            Generated response text
        """
        await self._rate_limit()
        
        try:
            # Prepare messages
            formatted_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation messages
            formatted_messages.extend(messages)
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=max_tokens or settings.MAX_TOKENS,
                **kwargs
            )
            
            result = response.choices[0].message.content
            
            logger.info(f"LLM response generated: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise
    
    async def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured response following a schema
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt with schema instructions
            schema: Expected response schema
            
        Returns:
            Parsed structured response
        """
        try:
            # Add schema to system prompt
            schema_prompt = f"{system_prompt}\n\nResponse format (JSON):\n{schema}"
            
            response = await self.generate_response(
                messages=messages,
                system_prompt=schema_prompt,
                **kwargs
            )
            
            # Try to parse JSON response
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
                    
        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            raise

class LLMManager:
    """Manager for LLM operations with caching and error handling"""
    
    def __init__(self):
        self.client = TogetherAIClient()
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
        
    def _get_cache_key(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Generate cache key for messages"""
        import hashlib
        content = system_prompt + str(messages)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - timestamp < self.cache_ttl
    
    async def get_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Get LLM response with caching"""
        
        # Check cache
        if use_cache and system_prompt:
            cache_key = self._get_cache_key(messages, system_prompt)
            if cache_key in self.cache:
                response, timestamp = self.cache[cache_key]
                if self._is_cache_valid(timestamp):
                    logger.info("Using cached LLM response")
                    return response
        
        # Generate new response
        response = await self.client.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            **kwargs
        )
        
        # Cache response
        if use_cache and system_prompt:
            cache_key = self._get_cache_key(messages, system_prompt)
            self.cache[cache_key] = (response, time.time())
        
        return response
    
    async def get_structured_response(
        self,
        messages: List[Dict[str, str]], 
        system_prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Get structured response from LLM"""
        return await self.client.generate_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema=schema,
            **kwargs
        )

# Global LLM manager instance
llm_manager = LLMManager()