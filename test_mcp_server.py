#!/usr/bin/env python3
"""
Test script for the Sports Innovation Lab MCP Server
Tests basic functionality without starting the full server
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from utils.team_config_manager import TeamConfigManager
        print("✅ TeamConfigManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import TeamConfigManager: {e}")
        return False
    
    try:
        from data_processors.demographic_processor import DemographicsProcessor
        print("✅ DemographicsProcessor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import DemographicsProcessor: {e}")
        return False
    
    try:
        from data_processors.category_analyzer import CategoryAnalyzer
        print("✅ CategoryAnalyzer imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import CategoryAnalyzer: {e}")
        return False
    
    try:
        from utils.cache_manager import CacheManager
        print("✅ CacheManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import CacheManager: {e}")
        return False
    
    try:
        from utils.logo_manager import LogoManager
        print("✅ LogoManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LogoManager: {e}")
        return False
    
    return True

def test_team_config():
    """Test team configuration functionality"""
    print("\n🏀 Testing team configuration...")
    
    try:
        from utils.team_config_manager import TeamConfigManager
        config_manager = TeamConfigManager()
        
        teams = config_manager.list_teams()
        print(f"✅ Found {len(teams)} teams")
        
        if teams:
            # Test first team
            first_team = teams[0]
            print(f"📋 Testing team: {first_team}")
            
            config = config_manager.get_team_config(first_team)
            print(f"   Team name: {config.get('team_name')}")
            print(f"   League: {config.get('league')}")
            print(f"   View prefix: {config.get('view_prefix')}")
            
            views = config_manager.get_all_views_for_team(first_team)
            print(f"   Available views: {list(views.keys())}")
            
            return True
        else:
            print("⚠️  No teams found in configuration")
            return False
            
    except Exception as e:
        print(f"❌ Team configuration test failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing environment configuration...")
    
    env_vars = {
        "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
        "SNOWFLAKE_USER": os.getenv("SNOWFLAKE_USER"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
    }
    
    for var, value in env_vars.items():
        if value:
            print(f"✅ {var}: {'*' * len(value) if 'KEY' in var or 'PASSWORD' in var else value}")
        else:
            print(f"⚠️  {var}: Not set")
    
    return True

def test_fastmcp():
    """Test FastMCP installation and basic functionality"""
    print("\n🚀 Testing FastMCP...")
    
    try:
        from fastmcp import FastMCP
        print("✅ FastMCP imported successfully")
        
        # Test creating a server instance
        mcp = FastMCP(name="Test Server")
        print("✅ FastMCP server instance created successfully")
        
        return True
        
    except ImportError:
        print("❌ FastMCP not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fastmcp"])
            from fastmcp import FastMCP
            print("✅ FastMCP installed and imported successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install FastMCP: {e}")
            return False
    except Exception as e:
        print(f"❌ FastMCP test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Sports Innovation Lab MCP Server - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Team Configuration Test", test_team_config),
        ("Environment Test", test_environment),
        ("FastMCP Test", test_fastmcp)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n📊 Test Results:")
    print("-" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The MCP server should work correctly.")
        print("\nTo start the server, run:")
        print("  python mcp_server.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("  - Missing environment variables (.env file)")
        print("  - Missing dependencies (run: pip install -r mcp_requirements.txt)")
        print("  - Running from wrong directory (should be project root)")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
