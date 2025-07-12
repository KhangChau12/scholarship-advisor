#!/usr/bin/env python3
"""
🔧 Test Setup Script for Scholarship Advisor
Tests all API connections and system components
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def test_together_ai():
    """Test Together AI API"""
    print("🤖 Testing Together AI API...")
    
    try:
        import openai
        
        # Fixed: Remove proxies parameter that's causing the error
        client = openai.AsyncOpenAI(
            api_key=os.getenv("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1"
            # Removed any other problematic parameters
        )
        
        # Test with Qwen Turbo model
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            messages=[{"role": "user", "content": "Reply with: API working"}],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        if "API working" in result or "working" in result.lower():
            print("   ✅ Together AI: Working")
            return True
        else:
            print(f"   ✅ Together AI: Response received: {result[:50]}...")
            return True  # Consider any response as working
            
    except Exception as e:
        error_msg = str(e)
        if "proxies" in error_msg:
            print("   ❌ Together AI: Version conflict - try updating openai package")
        elif "Unauthorized" in error_msg or "401" in error_msg:
            print("   ❌ Together AI: Invalid API key")
        elif "rate limit" in error_msg.lower():
            print("   ❌ Together AI: Rate limited")
        else:
            print(f"   ❌ Together AI: {error_msg[:100]}...")
        return False

async def test_serpapi():
    """Test SerpAPI"""
    print("🔍 Testing SerpAPI...")
    
    try:
        import aiohttp
        
        params = {
            "q": "scholarship test",
            "api_key": os.getenv("SERPAPI_KEY"),
            "engine": "google",
            "num": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://serpapi.com/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "organic_results" in data:
                        print("   ✅ SerpAPI: Working")
                        return True
                    else:
                        print("   ❌ SerpAPI: No results returned")
                        return False
                else:
                    print(f"   ❌ SerpAPI: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ SerpAPI: {str(e)}")
        return False

async def test_exchange_rate_api():
    """Test Exchange Rate API"""
    print("💱 Testing Exchange Rate API...")
    
    try:
        import aiohttp
        
        api_key = os.getenv("EXCHANGE_RATE_API_KEY")
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/USD/VND"
        
        async with aiohttp.ClientSession() as session:
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
                    print(f"   ❌ Exchange Rate API: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Exchange Rate API: {str(e)}")
        return False

def test_sendgrid():
    """Test SendGrid API"""
    print("📧 Testing SendGrid API...")
    
    try:
        from sendgrid import SendGridAPIClient
        
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            print("   ❌ SendGrid: No API key")
            return False
        
        client = SendGridAPIClient(api_key=api_key)
        
        # Test API key validity (this doesn't send an email)
        try:
            # This will fail if API key is invalid
            response = client.client.user.profile.get()
            if response.status_code == 200:
                print("   ✅ SendGrid: API key valid")
                return True
            else:
                print(f"   ❌ SendGrid: HTTP {response.status_code}")
                return False
        except Exception as e:
            if "Unauthorized" in str(e):
                print("   ❌ SendGrid: Invalid API key")
            else:
                print(f"   ❌ SendGrid: {str(e)}")
            return False
            
    except ImportError:
        print("   ❌ SendGrid: Module not installed")
        return False
    except Exception as e:
        print(f"   ❌ SendGrid: {str(e)}")
        return False

def test_file_processing():
    """Test file processing capabilities"""
    print("📄 Testing file processing...")
    
    try:
        import fitz  # PyMuPDF
        import docx
        
        print("   ✅ PyMuPDF: Available")
        print("   ✅ python-docx: Available")
        return True
        
    except ImportError as e:
        print(f"   ❌ File processing: Missing module - {e}")
        return False

def test_environment():
    """Test environment setup"""
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
        print("   ✅ Environment: All keys present")
        return True

def test_directories():
    """Test directory structure"""
    print("📁 Testing directories...")
    
    required_dirs = [
        "uploads",
        "logs",
        "static/css",
        "static/js"
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("   ✅ Directories: Created/verified")
    return True

async def main():
    """Run all tests"""
    print("🎓 SCHOLARSHIP ADVISOR - SETUP TEST")
    print("=" * 50)
    
    results = []
    
    # Environment tests
    results.append(test_environment())
    results.append(test_directories()) 
    results.append(test_file_processing())
    
    # API tests
    if os.getenv("TOGETHER_API_KEY"):
        results.append(await test_together_ai())
    else:
        print("🤖 Skipping Together AI (no key)")
        
    if os.getenv("SERPAPI_KEY"):
        results.append(await test_serpapi())
    else:
        print("🔍 Skipping SerpAPI (no key)")
        
    if os.getenv("EXCHANGE_RATE_API_KEY"):
        results.append(await test_exchange_rate_api())
    else:
        print("💱 Skipping Exchange Rate API (no key)")
        
    if os.getenv("SENDGRID_API_KEY"):
        results.append(test_sendgrid())
    else:
        print("📧 Skipping SendGrid (no key)")
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ Scholarship Advisor is ready to run!")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total})")
        print("🔧 Please check the failed components above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)