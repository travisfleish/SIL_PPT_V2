# Sports Innovation Lab MCP Server

A Model Context Protocol (MCP) server that provides tools and resources for the Sports Innovation Lab analytics and presentation generation system.

## What is MCP?

The Model Context Protocol (MCP) allows AI assistants like Claude to interact with external tools and data sources. This server exposes your sports analytics capabilities as tools that AI can use to:

- Explore team configurations and data
- Generate insights and analytics
- Create presentations and reports
- Access cached data and resources

## Features

### 🏀 **Team Management Tools**
- List all available sports teams
- Get team configurations and metadata
- Validate team data completeness
- Access team-specific data views

### 📊 **Analytics Resources**
- Team demographic information
- Category spending analysis
- Community index data
- Hot brand recommendations

### 🔧 **System Tools**
- System health and status
- Configuration validation
- Available slide types
- Environment diagnostics

## Quick Start

### 1. Install Dependencies

```bash
# Install MCP-specific requirements
pip install -r mcp_requirements.txt

# Or install FastMCP directly
pip install fastmcp
```

### 2. Test the Server

```bash
# Run the test suite to verify everything works
python test_mcp_server.py
```

### 3. Start the MCP Server

```bash
# Start the server (STDIO transport for local use)
python mcp_server.py
```

## Available Tools

### Core Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_teams` | List all available sports teams | None |
| `get_team_config` | Get configuration for a specific team | `team_key` (string) |
| `get_team_views` | Get available data views for a team | `team_key` (string) |
| `validate_team_data` | Validate team configuration completeness | `team_key` (string) |
| `get_available_slides` | List available slide types | None |
| `get_system_status` | Get overall system health | None |

### Example Usage

```python
# List all teams
teams = list_teams()
# Returns: ["utah_jazz", "dallas_cowboys", "carolina_panthers", ...]

# Get team configuration
config = get_team_config("utah_jazz")
# Returns team metadata, branding, view prefixes, etc.

# Validate team data
validation = validate_team_data("utah_jazz")
# Returns validation status and missing components
```

## Available Resources

### Static Resources

| Resource URI | Description | Content |
|--------------|-------------|---------|
| `resource://teams` | All teams overview | Team list with basic info |
| `resource://system/config` | System capabilities | Server features and supported formats |

### Dynamic Resources

| Resource URI | Description | Parameters |
|--------------|-------------|------------|
| `resource://teams/{team_key}/overview` | Team comprehensive overview | `team_key` in URI |

### Example Resource Access

```
resource://teams/utah_jazz/overview
# Returns detailed team information including:
# - Team metadata
# - Available data views
# - Capabilities
# - Branding information
```

## Configuration

### Environment Variables

The server uses the same environment configuration as your main application:

```env
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SIL__TB_OTT_TEST
SNOWFLAKE_SCHEMA=SC_TWINBRAINAI

# PostgreSQL Configuration (for caching)
DATABASE_URL=postgresql://username:password@host:port/database

# OpenAI Configuration (for AI insights)
OPENAI_API_KEY=your_openai_key
```

### Team Configuration

Teams are configured in `config/team_config.yaml` and include:
- Team names and leagues
- Data view prefixes
- Comparison populations
- Branding colors
- Audience definitions

## Integration with AI Assistants

### Claude Desktop

1. Open Claude Desktop
2. Go to Settings → Model Context Protocol
3. Add a new server:
   - **Name**: Sports Innovation Lab
   - **Command**: `python /path/to/your/project/mcp_server.py`
   - **Working Directory**: `/path/to/your/project`

### Other MCP Clients

The server supports standard MCP protocol and can be used with any MCP-compatible client.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client   │◄──►│   FastMCP        │◄──►│  SIL Analytics │
│   (Claude,     │    │   Server         │    │  System         │
│    etc.)       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Tools &        │
                       │   Resources      │
                       │                  │
                       │ • Team Config    │
                       │ • Data Analysis  │
                       │ • System Status  │
                       └──────────────────┘
```

## Development

### Adding New Tools

To add a new tool, use the `@mcp.tool` decorator:

```python
@mcp.tool
def my_new_tool(param1: str, param2: int) -> dict:
    """Description of what this tool does"""
    # Your tool implementation here
    return {"result": "success"}
```

### Adding New Resources

To add a new resource, use the `@mcp.resource` decorator:

```python
@mcp.resource("resource://my/resource")
def get_my_resource() -> dict:
    """Description of this resource"""
    return {"data": "value"}
```

### Testing

```bash
# Run the test suite
python test_mcp_server.py

# Test specific functionality
python -c "
from mcp_server import *
print(list_teams())
"
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root directory
2. **Missing Dependencies**: Run `pip install -r mcp_requirements.txt`
3. **Environment Variables**: Check your `.env` file exists and has required values
4. **Team Configuration**: Verify `config/team_config.yaml` is properly formatted

### Debug Mode

Enable debug logging by modifying the logging level in `mcp_server.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Connection Issues

- **Snowflake**: Check credentials and network access
- **PostgreSQL**: Verify database URL and connection permissions
- **File Access**: Ensure the server can read configuration files

## Next Steps

This is the foundation MCP server. Future enhancements could include:

- **Data Analysis Tools**: Direct Snowflake querying, demographic analysis
- **Presentation Generation**: PowerPoint creation, slide generation
- **AI Insights**: Automated insight generation, recommendations
- **Caching Tools**: Cache management, optimization
- **Real-time Data**: Live data updates, streaming analytics

## Support

For issues or questions:
1. Check the test suite output for specific errors
2. Verify environment configuration
3. Check the main application logs
4. Review team configuration files

## License

This MCP server is part of the Sports Innovation Lab project and follows the same licensing terms.
