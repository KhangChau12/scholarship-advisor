#!/usr/bin/env python3
"""
🎓 Scholarship Advisor - Run Script
Start the scholarship consultation application
"""
import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def check_dependencies():
    """Check if all dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import chainlit
        import openai
        import aiohttp
        import fitz
        import docx
        import sendgrid
        import redis
        print("✅ All dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Please install dependencies: pip install -r requirements.txt")
        return False

def check_environment():
    """Check environment variables"""
    print("🔧 Checking environment variables...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("📝 Please copy .env.example to .env and fill in your API keys")
        return False
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required keys
    required_keys = [
        "TOGETHER_API_KEY",
        "SERPAPI_KEY", 
        "EXCHANGE_RATE_API_KEY",
        "SENDGRID_API_KEY",
        "SENDGRID_FROM_EMAIL"
    ]
    
    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing API keys: {', '.join(missing_keys)}")
        print("📋 Please check API_SETUP.md for instructions")
        return False
    
    print("✅ Environment variables configured")
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    dirs_to_create = [
        "uploads",
        "logs", 
        "static/css",
        "static/js"
    ]
    
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

async def test_apis():
    """Test API connections"""
    print("🌐 Testing API connections...")
    
    try:
        # Test basic imports first
        from src.config.settings import settings
        
        # Quick API tests
        print("  📡 Together AI:", end=" ")
        if settings.TOGETHER_API_KEY:
            print("✅ Key found")
        else:
            print("❌ No key")
        
        print("  🔍 SerpAPI:", end=" ")
        if settings.SERPAPI_KEY:
            print("✅ Key found")
        else:
            print("❌ No key")
        
        print("  💱 Exchange Rate API:", end=" ")
        if settings.EXCHANGE_RATE_API_KEY:
            print("✅ Key found")
        else:
            print("❌ No key")
        
        print("  📧 SendGrid:", end=" ")
        if settings.SENDGRID_API_KEY:
            print("✅ Key found")
        else:
            print("❌ No key")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    return True

def main():
    """Main function to start the application"""
    
    print("🎓 SCHOLARSHIP ADVISOR AI")
    print("=" * 50)
    print("AI-powered scholarship consultation for Vietnamese students")
    print()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check environment
    if not check_environment():
        return 1
    
    # Create directories
    create_directories()
    
    # Test APIs
    if not asyncio.run(test_apis()):
        print("⚠️  Some APIs may not work properly")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    print()
    print("🚀 Starting Scholarship Advisor...")
    print("📱 Open your browser and go to: http://localhost:8000")
    print("⌨️  Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start Chainlit app
        os.chdir(src_path)
        subprocess.run([
            sys.executable, "-m", "chainlit", "run", 
            "ui/chainlit_app.py",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Scholarship Advisor stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)