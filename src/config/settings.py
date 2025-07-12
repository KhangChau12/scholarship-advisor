"""
Configuration settings for Scholarship Advisor
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Scholarship Advisor")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Keys
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    EXCHANGE_RATE_API_KEY: str = os.getenv("EXCHANGE_RATE_API_KEY", "")
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "")
    
    # LLM Settings
    LLM_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    LLM_BASE_URL: str = "https://api.together.xyz/v1"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    
    # File Upload
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10"))  # MB
    ALLOWED_EXTENSIONS: List[str] = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,doc,txt").split(",")
    UPLOAD_DIR: str = "uploads"
    
    # Session Management
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_REDIS: bool = os.getenv("USE_REDIS", "False").lower() == "true"
    SESSION_TIMEOUT: int = 3600  # seconds
    
    # Default Settings
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "USD")
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "vi")
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 30
    MAX_REQUESTS_PER_HOUR: int = 500
    
    # Search Settings
    MAX_SEARCH_RESULTS: int = 10
    SEARCH_TIMEOUT: int = 30  # seconds
    
    # Email Settings
    EMAIL_TIMEOUT: int = 30  # seconds
    
    @classmethod
    def validate_required_keys(cls) -> List[str]:
        """Validate that all required API keys are present"""
        missing_keys = []
        
        required_keys = [
            ("TOGETHER_API_KEY", cls.TOGETHER_API_KEY),
            ("SERPAPI_KEY", cls.SERPAPI_KEY),
            ("EXCHANGE_RATE_API_KEY", cls.EXCHANGE_RATE_API_KEY),
            ("SENDGRID_API_KEY", cls.SENDGRID_API_KEY),
            ("SENDGRID_FROM_EMAIL", cls.SENDGRID_FROM_EMAIL),
        ]
        
        for key_name, key_value in required_keys:
            if not key_value or key_value.strip() == "":
                missing_keys.append(key_name)
                
        return missing_keys
    
    @classmethod
    def get_base_dirs(cls) -> dict:
        """Get base directories for the application"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        return {
            "base": base_dir,
            "uploads": os.path.join(base_dir, cls.UPLOAD_DIR),
            "logs": os.path.join(base_dir, "logs"),
            "static": os.path.join(base_dir, "static"),
        }

# Create settings instance
settings = Settings()

# Validate API keys on import
missing_keys = settings.validate_required_keys()
if missing_keys and not settings.DEBUG:
    raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")

# Create necessary directories
dirs = settings.get_base_dirs()
for dir_path in dirs.values():
    os.makedirs(dir_path, exist_ok=True)