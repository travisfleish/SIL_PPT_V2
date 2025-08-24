#!/usr/bin/env python3
"""
Simple test to verify MCP server setup
"""

def test_imports():
    """Test that the MCP server can be imported"""
    print("🔍 Testing MCP server imports...")
    
    try:
        from mcp_server import mcp
        print("✅ MCP server imported successfully")
        print(f"   Server name: {mcp.name}")
        print(f"   Server type: {type(mcp)}")
        return True
    except Exception as e:
        print(f"❌ Failed to import MCP server: {e}")
        return False

def test_team_config():
    """Test team configuration access"""
    print("\n🏀 Testing team configuration...")
    
    try:
        from utils.team_config_manager import TeamConfigManager
        config_manager = TeamConfigManager()
        teams = config_manager.list_teams()
        print(f"✅ Found {len(teams)} teams")
        print(f"   Teams: {teams}")
        return True
    except Exception as e:
        print(f"❌ Failed to access team config: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Sports Innovation Lab MCP Server - Simple Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Team Config Test", test_team_config)
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
        print("🎉 All tests passed! The MCP server is ready to use.")
        print("\nTo start the server, run:")
        print("  python3 mcp_server.py")
        print("\nTo use with Claude Desktop:")
        print("  1. Open Claude Desktop")
        print("  2. Go to Settings → Model Context Protocol")
        print("  3. Add server: python3 /path/to/SIL_PPT_V2/mcp_server.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
