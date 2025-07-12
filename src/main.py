"""
Main entry point for Scholarship Advisor application
"""
import asyncio
import os
import sys
from pathlib import Path
from loguru import logger

# Add src to path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from config.settings import settings
from utils.session_manager import session_manager

def setup_logging():
    """Setup logging configuration"""
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Add file logger
    logs_dir = settings.get_base_dirs()["logs"]
    logger.add(
        os.path.join(logs_dir, "app.log"),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip"
    )
    
    logger.info(f"Logging setup complete. Level: {settings.LOG_LEVEL}")

async def initialize_services():
    """Initialize all services"""
    
    logger.info("Initializing Scholarship Advisor services...")
    
    # Initialize session manager
    await session_manager.initialize()
    
    # Validate API keys
    missing_keys = settings.validate_required_keys()
    if missing_keys:
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
        if not settings.DEBUG:
            logger.error("Cannot start without required API keys")
            return False
    else:
        logger.info("All API keys validated successfully")
    
    # Test API connections (optional)
    if settings.DEBUG:
        await test_api_connections()
    
    logger.info("All services initialized successfully")
    return True

async def test_api_connections():
    """Test API connections (optional for debug mode)"""
    
    logger.info("Testing API connections...")
    
    try:
        # Test Together AI
        from utils.llm_client import llm_manager
        test_messages = [{"role": "user", "content": "Hello"}]
        response = await llm_manager.get_response(
            messages=test_messages,
            system_prompt="Reply with 'API working'",
            use_cache=False
        )
        logger.info("✅ Together AI API: Working")
        
    except Exception as e:
        logger.warning(f"❌ Together AI API: {str(e)}")
    
    try:
        # Test currency API
        from tools.currency_converter import currency_converter
        rate = await currency_converter.get_exchange_rate("USD", "VND")
        if rate:
            logger.info("✅ Currency API: Working")
        else:
            logger.warning("❌ Currency API: No rate returned")
            
    except Exception as e:
        logger.warning(f"❌ Currency API: {str(e)}")
    
    # Note: SerpAPI and SendGrid tests would consume quota, so skip in debug

def validate_environment():
    """Validate environment and setup"""
    
    logger.info("Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ required")
        return False
    
    # Check required directories
    dirs = settings.get_base_dirs()
    for dir_name, dir_path in dirs.items():
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    # Check file permissions
    upload_dir = dirs["uploads"]
    if not os.access(upload_dir, os.W_OK):
        logger.error(f"No write permission for upload directory: {upload_dir}")
        return False
    
    logger.info("Environment validation passed")
    return True

async def main():
    """Main application entry point"""
    
    # Setup logging first
    setup_logging()
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        return 1
    
    # Initialize services
    if not await initialize_services():
        logger.error("Service initialization failed")
        return 1
    
    logger.info("🚀 Scholarship Advisor is ready!")
    logger.info("Starting Chainlit UI...")
    
    # Import and run Chainlit app
    try:
        from ui.chainlit_app import main as chainlit_main
        
        # Run chainlit
        import chainlit as cl
        
        # Set chainlit config
        cl.config.ui.name = settings.APP_NAME
        cl.config.ui.description = "AI-powered scholarship advisor for Vietnamese students"
        cl.config.ui.github = "https://github.com/your-repo/scholarship-advisor"
        
        # Run the app
        logger.info("Chainlit server starting...")
        
        # Return success
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start Chainlit: {str(e)}")
        return 1

if __name__ == "__main__":
    # Handle async main
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)