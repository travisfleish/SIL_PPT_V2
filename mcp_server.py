#!/usr/bin/env python3
"""
Sports Innovation Lab MCP Server
Provides tools and resources for sports team analytics and presentation generation
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import FastMCP
try:
    from fastmcp import FastMCP
except ImportError:
    print("FastMCP not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastmcp"])
    from fastmcp import FastMCP

# Import project modules
try:
    from utils.team_config_manager import TeamConfigManager
    from data_processors.demographic_processor import DemographicsProcessor
    from data_processors.category_analyzer import CategoryAnalyzer
    from data_processors.snowflake_connector import query_to_dataframe
    from utils.cache_manager import CacheManager
    from utils.logo_manager import LogoManager
except ImportError as e:
    logger.error(f"Failed to import project modules: {e}")
    logger.error("Make sure you're running this from the project root directory")
    sys.exit(1)

# Create the MCP server instance
mcp = FastMCP(name="Sports Innovation Lab Analytics Server")

# Initialize managers
config_manager = None
cache_manager = None
logo_manager = None

try:
    config_manager = TeamConfigManager()
    logger.info("TeamConfigManager initialized successfully")
    
    # Try to initialize cache manager if PostgreSQL is available
    if os.getenv('DATABASE_URL'):
        try:
            from postgresql_job_store import PostgreSQLJobStore
            job_store = PostgreSQLJobStore(os.getenv('DATABASE_URL'))
            cache_manager = CacheManager(job_store.pool)
            logger.info("CacheManager initialized with PostgreSQL backend")
        except Exception as e:
            logger.warning(f"CacheManager not available: {e}")
    
    logo_manager = LogoManager()
    logger.info("LogoManager initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize managers: {e}")

# ===== TOOLS =====

@mcp.tool
def list_teams() -> List[str]:
    """List all available sports teams for analysis"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        teams = config_manager.list_teams()
        return teams
    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        return {"error": f"Failed to list teams: {str(e)}"}

@mcp.tool
def get_team_config(team_key: str) -> Dict[str, Any]:
    """Get configuration and metadata for a specific team"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        
        if team_key not in config_manager.list_teams():
            return {"error": f"Team '{team_key}' not found"}
        
        config = config_manager.get_team_config(team_key)
        
        # Return a clean version of the config
        return {
            "team_key": team_key,
            "team_name": config.get("team_name"),
            "league": config.get("league"),
            "view_prefix": config.get("view_prefix"),
            "comparison_population": config.get("comparison_population"),
            "audience_name": config.get("audience_name"),
            "branding": {
                "primary_color": config.get("primary_color"),
                "secondary_color": config.get("secondary_color")
            }
        }
    except Exception as e:
        logger.error(f"Error getting team config for {team_key}: {e}")
        return {"error": f"Failed to get team config: {str(e)}"}

@mcp.tool
def get_team_views(team_key: str) -> Dict[str, str]:
    """Get all available data views for a specific team"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        
        if team_key not in config_manager.list_teams():
            return {"error": f"Team '{team_key}' not found"}
        
        views = config_manager.get_all_views_for_team(team_key)
        return {
            "team_key": team_key,
            "views": views
        }
    except Exception as e:
        logger.error(f"Error getting team views for {team_key}: {e}")
        return {"error": f"Failed to get team views: {str(e)}"}

@mcp.tool
def validate_team_data(team_key: str) -> Dict[str, Any]:
    """Validate that a team has all required configuration and data access"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        
        if team_key not in config_manager.list_teams():
            return {"error": f"Team '{team_key}' not found"}
        
        config = config_manager.get_team_config(team_key)
        views = config_manager.get_all_views_for_team(team_key)
        
        # Check required fields
        required_fields = ["team_name", "league", "view_prefix"]
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        # Check required views
        required_views = ["demographics", "community_all_time", "merchant_yoy"]
        missing_views = [view for view in required_views if view not in views]
        
        return {
            "team_key": team_key,
            "valid": len(missing_fields) == 0 and len(missing_views) == 0,
            "missing_fields": missing_fields,
            "missing_views": missing_views,
            "config_status": "complete" if len(missing_fields) == 0 else "incomplete",
            "views_status": "complete" if len(missing_views) == 0 else "incomplete"
        }
    except Exception as e:
        logger.error(f"Error validating team data for {team_key}: {e}")
        return {"error": f"Failed to validate team data: {str(e)}"}

@mcp.tool
def get_available_slides() -> List[str]:
    """Get list of available slide types that can be generated"""
    return [
        "demographics",
        "behaviors", 
        "category:Restaurants",
        "category:Athleisure",
        "category:Finance",
        "category:Gambling",
        "category:Travel",
        "category:Auto"
    ]

@mcp.tool
def get_system_status() -> Dict[str, Any]:
    """Get overall system status and health"""
    try:
        status = {
            "status": "healthy",
            "components": {},
            "timestamp": str(Path(__file__).stat().st_mtime)
        }
        
        # Check team configuration
        if config_manager:
            try:
                teams = config_manager.list_teams()
                status["components"]["team_config"] = {
                    "status": "available",
                    "team_count": len(teams)
                }
            except Exception as e:
                status["components"]["team_config"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            status["components"]["team_config"] = {"status": "not_available"}
        
        # Check cache manager
        if cache_manager:
            try:
                stats = cache_manager.get_cache_stats()
                status["components"]["cache"] = {
                    "status": "available",
                    "stats": stats
                }
            except Exception as e:
                status["components"]["cache"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            status["components"]["cache"] = {"status": "not_available"}
        
        # Check logo manager
        if logo_manager:
            status["components"]["logo_manager"] = {"status": "available"}
        else:
            status["components"]["logo_manager"] = {"status": "not_available"}
        
        # Check environment variables
        env_vars = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "DATABASE_URL"]
        status["components"]["environment"] = {
            "snowflake_configured": bool(os.getenv("SNOWFLAKE_ACCOUNT")),
            "database_configured": bool(os.getenv("DATABASE_URL")),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": str(Path(__file__).stat().st_mtime)
        }

# ===== RESOURCES =====

@mcp.resource("resource://teams")
def get_all_teams_info() -> Dict[str, Any]:
    """Get comprehensive information about all available teams"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        
        teams_info = {}
        for team_key in config_manager.list_teams():
            try:
                config = config_manager.get_team_config(team_key)
                teams_info[team_key] = {
                    "team_name": config.get("team_name"),
                    "league": config.get("league"),
                    "view_prefix": config.get("view_prefix"),
                    "comparison_population": config.get("comparison_population")
                }
            except Exception as e:
                teams_info[team_key] = {"error": str(e)}
        
        return {
            "total_teams": len(teams_info),
            "teams": teams_info
        }
    except Exception as e:
        logger.error(f"Error getting all teams info: {e}")
        return {"error": f"Failed to get teams info: {str(e)}"}

@mcp.resource("resource://system/config")
def get_system_configuration() -> Dict[str, Any]:
    """Get system configuration and capabilities"""
    return {
        "name": "Sports Innovation Lab Analytics Server",
        "version": "1.0.0",
        "capabilities": [
            "team_management",
            "demographic_analysis", 
            "category_analysis",
            "presentation_generation",
            "data_caching",
            "logo_management"
        ],
        "supported_leagues": ["NBA", "NFL", "MLB", "NHL", "MLS", "NWSL"],
        "data_sources": ["Snowflake", "PostgreSQL", "Local Cache"],
        "output_formats": ["PowerPoint", "JSON", "CSV"]
    }

@mcp.resource("resource://teams/{team_key}/overview")
def get_team_overview(team_key: str) -> Dict[str, Any]:
    """Get comprehensive overview for a specific team"""
    try:
        if not config_manager:
            return {"error": "Team configuration not available"}
        
        if team_key not in config_manager.list_teams():
            return {"error": f"Team '{team_key}' not found"}
        
        config = config_manager.get_team_config(team_key)
        views = config_manager.get_all_views_for_team(team_key)
        
        return {
            "team_key": team_key,
            "team_name": config.get("team_name"),
            "league": config.get("league"),
            "view_prefix": config.get("view_prefix"),
            "comparison_population": config.get("comparison_population"),
            "audience_name": config.get("audience_name"),
            "available_views": list(views.keys()),
            "branding": {
                "primary_color": config.get("primary_color"),
                "secondary_color": config.get("secondary_color")
            },
            "capabilities": {
                "demographics": "demographics" in views,
                "community_analysis": "community_all_time" in views,
                "merchant_analysis": "merchant_yoy" in views
            }
        }
    except Exception as e:
        logger.error(f"Error getting team overview for {team_key}: {e}")
        return {"error": f"Failed to get team overview: {str(e)}"}

# ===== MAIN EXECUTION =====

if __name__ == "__main__":
    print("🏀 Starting Sports Innovation Lab MCP Server...")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Environment: {'Production' if os.getenv('FLASK_ENV') == 'production' else 'Development'}")
    
    # Test basic functionality
    try:
        if config_manager:
            teams = config_manager.list_teams()
            print(f"✅ Found {len(teams)} teams: {', '.join(teams[:3])}{'...' if len(teams) > 3 else ''}")
        else:
            print("⚠️  Team configuration not available")
        
        if cache_manager:
            print("✅ Cache manager available")
        else:
            print("⚠️  Cache manager not available")
            
        if logo_manager:
            print("✅ Logo manager available")
        else:
            print("⚠️  Logo manager not available")
            
    except Exception as e:
        print(f"⚠️  Initialization warnings: {e}")
    
    print("\n🚀 Starting MCP server...")
    mcp.run()
