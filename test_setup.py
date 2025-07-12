#!/usr/bin/env python3
"""
🎓 Scholarship Advisor - Setup Test (Fixed Version)
Test all dependencies and API connections
"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment variables"""
    print("🔧 Testing environment...")
    
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
        print(f"   ❌ Environment: Missing keys: {', '.join(missing_keys)}")
        return False
    else:
        print("   ✅ Environment: All keys found")
        return True

def test_directories():
    """Test directory creation"""
    print("📁 Testing directories...")
    
    dirs_to_check = ["uploads", "logs", "static/css"]
    
    try:
        for dir_path in dirs_to_check:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("   ✅ Directories: Created/verified")
        return True
    except Exception as e:
        print(f"   ❌ Directories: {e}")
        return False

def test_file_processing():
    """Test file processing dependencies"""
    print("📄 Testing file processing...")
    
    try:
        import fitz  # PyMuPDF
        print("   ✅ PyMuPDF: Available")
    except ImportError:
        print("   ❌ PyMuPDF: Not installed")
        return False
    
    try:
        import docx
        print("   ✅ python-docx: Available")
    except ImportError:
        print("   ❌ python-docx: Not installed")
        return False
    
    return True

async def test_together_ai():
    """Test Together AI API with better error handling"""
    print("🤖 Testing Together AI API...")
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("   ❌ Together AI: No API key")
        return False
    
    try:
        # Use aiohttp directly instead of openai client
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "Qwen/Qwen2.5-72B-Instruct-Turbo",
            "messages": [
                {"role": "user", "content": "Hello, reply with 'API working'"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"   ✅ Together AI: Working - Response: {content.strip()}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Together AI: HTTP {response.status} - {error_text[:100]}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Together AI: {str(e)}")
        return False

async def test_serpapi():
    """Test SerpAPI"""
    print("🔍 Testing SerpAPI...")
    
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("   ❌ SerpAPI: No API key")
        return False
    
    try:
        url = "https://serpapi.com/search"
        params = {
            "q": "test search",
            "api_key": api_key,
            "engine": "google",
            "num": 1
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    print("   ✅ SerpAPI: Working")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ SerpAPI: HTTP {response.status} - {error_text[:100]}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ SerpAPI: {str(e)}")
        return False

async def test_exchange_rate_api():
    """Test Exchange Rate API"""
    print("💱 Testing Exchange Rate API...")
    
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        print("   ❌ Exchange Rate API: No API key")
        return False
    
    try:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/USD/VND"
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result") == "success":
                        rate = data.get("conversion_rate")
                        print(f"   ✅ Exchange Rate API: Working (USD->VND: {rate})")
                        return True
                    else:
                        print(f"   ❌ Exchange Rate API: {data.get('error-type', 'Unknown error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ Exchange Rate API: HTTP {response.status} - {error_text[:100]}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Exchange Rate API: {str(e)}")
        return False

def test_sendgrid():
    """Test SendGrid API"""
    print("📧 Testing SendGrid...")
    
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")
    
    if not api_key or not from_email:
        print("   ❌ SendGrid: Missing API key or from email")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        
        # Just test client creation, don't send actual email
        client = SendGridAPIClient(api_key=api_key)
        print("   ✅ SendGrid: Client created successfully")
        return True
        
    except ImportError:
        print("   ❌ SendGrid: Package not installed")
        return False
    except Exception as e:
        print(f"   ❌ SendGrid: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🎓 SCHOLARSHIP ADVISOR - SETUP TEST")
    print("=" * 50)
    
    tests = [
        ("Environment", test_environment()),
        ("Directories", test_directories()),
        ("File Processing", test_file_processing()),
        ("Together AI", await test_together_ai()),
        ("SerpAPI", await test_serpapi()),
        ("Exchange Rate API", await test_exchange_rate_api()),
        ("SendGrid", test_sendgrid())
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print("=" * 50)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("🚀 Ready to run: python run.py")
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total})")
        print("🔧 Please check the failed components above")
        
        if passed >= 4:  # At least basic functionality
            print("💡 You can still run the app, some features may be limited")
    
    return passed == total

if __name__ == "__main__":
    # Handle both sync and async execution
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)