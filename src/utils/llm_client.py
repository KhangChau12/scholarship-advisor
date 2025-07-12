"""
Together AI LLM Client for Scholarship Advisor - Qwen2.5-72B-Instruct-Turbo
"""
import asyncio
from typing import List, Dict, Any, Optional
import openai
from loguru import logger
import time
import json
import re

from ..config.settings import settings

class TogetherAIClient:
    """Client for Together AI API - Optimized for Qwen Turbo"""
    
    def __init__(self):
        # Initialize client with proper error handling
        try:
            self.client = openai.AsyncOpenAI(
                api_key=settings.TOGETHER_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )
        except TypeError as e:
            if "proxies" in str(e).lower():
                # Fallback for version conflicts
                import httpx
                self.client = openai.AsyncOpenAI(
                    api_key=settings.TOGETHER_API_KEY,
                    base_url=settings.LLM_BASE_URL,
                    http_client=httpx.AsyncClient()
                )
                logger.info("Using httpx client fallback for compatibility")
            else:
                raise
        
        self.model = settings.LLM_MODEL
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Reduced for Turbo model
        
    async def _rate_limit(self):
        """Rate limiting for API calls"""
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
        Generate response from Together AI using Qwen Turbo
        
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
            
            # Clean kwargs to avoid unexpected parameters
            clean_kwargs = {}
            allowed_params = ['stream', 'top_p', 'frequency_penalty', 'presence_penalty', 'stop']
            for key, value in kwargs.items():
                if key in allowed_params:
                    clean_kwargs[key] = value
            
            # Optimize parameters for Qwen Turbo
            api_params = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": temperature or settings.TEMPERATURE,
                "max_tokens": max_tokens or settings.MAX_TOKENS,
                **clean_kwargs
            }
            
            # Make API call with enhanced error handling
            try:
                response = await self.client.chat.completions.create(**api_params)
                
                if response.choices and len(response.choices) > 0:
                    result = response.choices[0].message.content
                    if result:
                        logger.info(f"LLM response generated: {len(result)} characters")
                        return result.strip()
                    else:
                        logger.warning("Empty response from LLM")
                        return "Xin lỗi, không thể tạo phản hồi. Vui lòng thử lại."
                else:
                    logger.warning("No choices in LLM response")
                    return "Xin lỗi, không nhận được phản hồi từ AI."
                
            except openai.BadRequestError as e:
                logger.error(f"Bad request to Together AI: {str(e)}")
                if "model_not_available" in str(e):
                    return "Model hiện không khả dụng. Vui lòng thử lại sau."
                return "Yêu cầu không hợp lệ. Vui lòng thử lại."
                
            except openai.AuthenticationError as e:
                logger.error(f"Authentication error with Together AI: {str(e)}")
                return "Lỗi xác thực API. Vui lòng kiểm tra API key."
                
            except openai.RateLimitError as e:
                logger.error(f"Rate limit exceeded: {str(e)}")
                return "API đã đạt giới hạn. Vui lòng đợi một chút và thử lại."
                
            except Exception as api_error:
                logger.error(f"Together AI API error: {str(api_error)}")
                return "Có lỗi khi kết nối với AI. Vui lòng thử lại."
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại."
    
    async def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured response following a schema for Qwen Turbo
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt with schema instructions
            schema: Expected response schema
            
        Returns:
            Parsed structured response
        """
        try:
            # Enhanced schema prompt for better JSON output
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            enhanced_prompt = f"""{system_prompt}

QUAN TRỌNG: Trả lời CHÍNH XÁC theo định dạng JSON sau đây. Không thêm text giải thích bên ngoài JSON.

Schema JSON:
{schema_str}

Hãy trả lời bằng JSON hợp lệ theo schema trên."""
            
            response = await self.generate_response(
                messages=messages,
                system_prompt=enhanced_prompt,
                temperature=0.1,  # Lower temperature for structured output
                **kwargs
            )
            
            # Enhanced JSON extraction
            parsed_json = self._extract_and_parse_json(response, schema)
            
            if parsed_json:
                return parsed_json
            else:
                logger.warning("Could not parse JSON, returning default structure")
                return self._create_default_response(schema)
                    
        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            return self._create_default_response(schema)
    
    def _extract_and_parse_json(self, response: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enhanced JSON extraction with multiple fallback methods"""
        
        # Method 1: Direct JSON parsing
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # Method 2: Extract JSON block with code fences
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Method 3: Find JSON object in text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                # Validate that it matches schema structure
                if self._validate_json_structure(parsed, schema):
                    return parsed
            except json.JSONDecodeError:
                continue
        
        # Method 4: Try to extract key-value pairs manually
        try:
            return self._manual_json_extraction(response, schema)
        except:
            pass
        
        return None
    
    def _validate_json_structure(self, parsed_json: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate if parsed JSON matches expected schema structure"""
        if not isinstance(parsed_json, dict):
            return False
        
        # Check if at least 50% of schema keys are present
        schema_keys = set(schema.keys())
        parsed_keys = set(parsed_json.keys())
        overlap = len(schema_keys.intersection(parsed_keys))
        
        return overlap >= len(schema_keys) * 0.5
    
    def _manual_json_extraction(self, response: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Manual extraction as last resort"""
        result = {}
        
        for key in schema.keys():
            # Look for key-value patterns
            patterns = [
                rf'"{key}":\s*"([^"]*)"',
                rf'"{key}":\s*(\d+\.?\d*)',
                rf'"{key}":\s*(\[[^\]]*\])',
                rf'{key}:\s*"([^"]*)"',
                rf'{key}:\s*(\d+\.?\d*)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    try:
                        value = match.group(1)
                        # Try to parse as number or list
                        if value.startswith('['):
                            result[key] = json.loads(value)
                        elif value.replace('.', '').isdigit():
                            result[key] = float(value) if '.' in value else int(value)
                        else:
                            result[key] = value
                        break
                    except:
                        continue
        
        return result if result else self._create_default_response(schema)
    
    def _create_default_response(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create default response when JSON parsing fails"""
        default_response = {}
        
        for key, value_type in schema.items():
            if isinstance(value_type, str):
                if "string" in value_type.lower():
                    default_response[key] = "Không có thông tin"
                elif "number" in value_type.lower():
                    default_response[key] = 0
                elif "boolean" in value_type.lower():
                    default_response[key] = False
                else:
                    default_response[key] = "N/A"
            elif isinstance(value_type, list):
                default_response[key] = []
            elif isinstance(value_type, dict):
                default_response[key] = {}
            else:
                default_response[key] = None
        
        return default_response

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
        if use_cache and system_prompt and response:
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