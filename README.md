# Sports Innovation Lab - PowerPoint Generator

## Executive Summary

An automated system that transforms Snowflake fan behavior data into professional PowerPoint presentations for sports teams to identify and pitch potential sponsors. Features both command-line and web-based interfaces, with a scalable backend architecture supporting real-time job processing, caching, and deployment to cloud platforms.

## Problem Understanding

The manual creation of sponsorship insights reports is time-intensive and inconsistent across teams. This system reduces report generation from hours to minutes while maintaining professional quality and ensuring data-driven sponsorship recommendations. The new infrastructure addresses scalability, user experience, and operational efficiency challenges.

## Architecture Overview

```
SIL_PPT_V2/
├── main.py                     # Command-line entry point for report generation
├── quick_start.py              # Interactive testing and development
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration (create from template)
├── .gitignore                  # Git exclusions
├── render.yaml                 # Render.com deployment configuration
│
├── backend/                    # Flask web backend
│   ├── app.py                 # Main Flask application with REST API
│   ├── postgresql_job_store.py # PostgreSQL job queue and storage
│   ├── static/                # Static assets for web interface
│   ├── assets/                # Backend-specific assets
│   └── output/                # Generated presentations storage
│
├── frontend/                   # Web-based user interface
│   ├── index.html             # Main web application
│   └── index_old.html         # Previous version
│
├── config/                     # Configuration files
│   ├── team_config.yaml       # Team configurations and branding
│   ├── categories.yaml        # Category definitions and thresholds
│   └── approved_communities.yaml  # Approved fan community mappings
│
├── data_processors/           # Core data processing modules
│   ├── snowflake_connector.py # Database connection and query execution
│   ├── category_analyzer.py   # Category-level data analysis
│   ├── merchant_ranker.py     # Merchant ranking and insights
│   └── tests/                 # Data processor validation tests
│
├── slide_generators/          # PowerPoint slide creation
│   ├── base_slide.py          # Common slide functionality
│   ├── title_slide.py         # Title slide generator
│   ├── intro_slide.py         # Introduction/overview slides
│   ├── demographic_overview_slide.py  # Demographics overview
│   ├── demographics_slide.py  # Detailed demographics charts
│   ├── behaviors_slide.py     # Fan behavior analysis
│   ├── category_slide.py      # Category analysis slides
│   └── tests/                 # Slide generator tests
│
├── report_builder/            # Report orchestration
│   ├── pptx_builder.py        # Main PowerPoint builder
│   └── slide_orchestrator.py  # Slide dependency management
│
├── utils/                     # Utility modules
│   ├── team_config_manager.py # Team configuration management
│   ├── logo_manager.py        # Logo downloading and caching
│   ├── merchant_name_standardizer.py  # Brand name standardization
│   ├── cache_manager.py       # PostgreSQL-based caching system
│   ├── font_manager.py        # Font management and fallbacks
│   ├── ai_generators.py       # AI-powered content generation
│   └── tests/                 # Utility validation tests
│
├── visualizations/            # Chart and visualization generation
│   ├── base_chart.py          # Base chart functionality
│   ├── fan_wheel.py           # Fan wheel visualization
│   ├── demographic_charts.py  # Demographic chart generation
│   └── community_index_chart.py # Community index charts
│
├── ai_insights/               # AI-powered insights generation
│   └── demographic_insights_generator.py # Demographic insights
│
├── templates/                 # PowerPoint templates
│   └── sil_combined_template.pptx  # SIL branded template
│
├── assets/                    # Static assets
│   └── logos/                 # Cached brand logos
│
├── output/                    # Generated presentations
│   └── [team]_[timestamp]/    # Team-specific output directories
│
├── cache/                     # Local cache storage
├── logs/                      # Application logs
└── .venv/                     # Python virtual environment
```

## Key Features

### 1. Dual Interface Architecture
- **Command-Line Interface**: Traditional CLI for automation and scripting
- **Web Interface**: Modern React-like web application for interactive use
- **API Backend**: RESTful Flask API supporting both interfaces

### 2. Scalable Backend Infrastructure
- **Flask Web Server**: Production-ready web backend with CORS support
- **PostgreSQL Job Store**: Persistent job queue with connection pooling
- **Job Management**: Async job processing with progress tracking
- **Connection Pooling**: Optimized database connections for high throughput

### 3. Advanced Caching System
- **PostgreSQL Cache Backend**: Persistent caching across application restarts
- **Multi-Level Caching**: Merchant names, AI insights, Snowflake results, logos
- **Cache Statistics**: Performance monitoring and hit/miss tracking
- **Automatic Expiration**: TTL-based cache invalidation

### 4. Automated Data Pipeline
- **Snowflake Integration**: Direct connection to `SIL__TB_OTT_TEST.SC_TWINBRAINAI`
- **Dynamic View Naming**: Handles team-specific view prefixes
- **Data Validation**: Comprehensive error handling and data quality checks
- **Connection Pooling**: Optimized for concurrent requests

### 5. Professional PowerPoint Generation
- **Template Integration**: Uses SIL branded template with consistent styling
- **16:9 Format**: Modern widescreen presentations
- **Font Management**: Red Hat Display with Arial fallback
- **Responsive Layouts**: Adapts to content length and team branding

### 6. Dynamic Visualizations
- **Fan Wheel**: Circular brand affinity visualization with logo support
- **Demographic Charts**: Age, income, occupation comparisons
- **Community Index**: Top 10 fan communities with composite scoring
- **Category Analysis**: Detailed spending pattern breakdowns

### 7. AI-Powered Insights
- **OpenAI Integration**: Automated insight generation for each category
- **Logo Management**: Automatic brand logo fetching via Clearbit/Brandfetch APIs
- **Merchant Standardization**: Consistent brand name formatting
- **Insight Generation**: Context-aware content creation

### 8. Cloud Deployment Ready
- **Render.com Support**: Production deployment configuration
- **Environment Management**: Secure configuration handling
- **Scalability**: Horizontal scaling support
- **Health Monitoring**: Built-in health checks and monitoring

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database (for job store and caching)
- Snowflake account access
- OpenAI API key (optional, for AI insights)
- Red Hat Display font (recommended)

### 1. Environment Setup
```bash
git clone <repository-url>
cd SIL_PPT_V2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` file in project root:
```env
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SIL__TB_OTT_TEST
SNOWFLAKE_SCHEMA=SC_TWINBRAINAI

# PostgreSQL Configuration (for job store and caching)
DATABASE_URL=postgresql://username:password@host:port/database

# Optional: OpenAI for AI insights
OPENAI_API_KEY=your_openai_key

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=true
```

### 3. Database Setup
```bash
# PostgreSQL database required for:
# - Job queue management
# - Caching system
# - Progress tracking
# - Job history
```

### 4. Font Installation (Recommended)
Download and install Red Hat Display font:
1. Download from [Google Fonts](https://fonts.google.com/specimen/Red+Hat+Display)
2. Install all .ttf files on your system
3. Restart Python environment

### 5. Template Setup
Ensure `templates/sil_combined_template.pptx` exists in the project directory.

## Usage

### Command-Line Interface
```bash
# Generate full report for Carolina Panthers
python main.py carolina_panthers

# Generate single slide for testing
python main.py carolina_panthers behaviors

# Generate report without custom categories
python main.py utah_jazz --no-custom

# Interactive testing mode
python quick_start.py --interactive
```

### Web Interface
```bash
# Start the Flask backend
cd backend
python app.py

# Access web interface at http://localhost:5000
# Upload team data and generate presentations interactively
```

### API Endpoints
```bash
# Health check
GET /health

# Generate presentation
POST /generate
{
  "team_key": "carolina_panthers",
  "options": {
    "custom_count": 2,
    "include_ai": true
  }
}

# Check job status
GET /job/{job_id}

# Download generated presentation
GET /download/{job_id}
```

## New Infrastructure Components

### 1. Flask Web Backend (`backend/app.py`)
- **RESTful API**: Complete API for web frontend
- **Job Management**: Async job processing with PostgreSQL backend
- **File Handling**: Secure file upload/download
- **Progress Tracking**: Real-time job progress updates
- **Error Handling**: Comprehensive error management and logging

### 2. PostgreSQL Job Store (`backend/postgresql_job_store.py`)
- **Job Queue**: Persistent job storage with status tracking
- **Connection Pooling**: Optimized database connections
- **Automatic Cleanup**: Expired job cleanup and maintenance
- **Transaction Safety**: ACID-compliant job operations
- **Performance Indexes**: Optimized queries for job management

### 3. Advanced Caching System (`utils/cache_manager.py`)
- **PostgreSQL Backend**: Persistent cache storage
- **Multi-Type Caching**: Merchant names, AI insights, data results
- **Cache Statistics**: Performance monitoring and analytics
- **Automatic Expiration**: TTL-based invalidation
- **Connection Sharing**: Reuses existing PostgreSQL connections

### 4. Web Frontend (`frontend/index.html`)
- **Modern UI**: Responsive design with Red Hat Display fonts
- **Interactive Forms**: Team selection and options configuration
- **Real-time Updates**: Live progress tracking and status updates
- **File Management**: Secure file upload and download
- **Mobile Responsive**: Works on all device sizes

### 5. Deployment Configuration (`render.yaml`)
- **Render.com Ready**: Production deployment configuration
- **Gunicorn Server**: Production WSGI server configuration
- **Environment Variables**: Secure configuration management
- **Health Checks**: Built-in monitoring and health endpoints

## Configuration

### Team Configuration (`config/team_config.yaml`)
```yaml
carolina_panthers:
  team_name: "Carolina Panthers"
  team_name_short: "Panthers"
  team_initials: "CP"
  league: "NFL"
  view_prefix: "V_CAROLINA_PANTHERS_SIL_"
  colors:
    primary: "#0085CA"
    secondary: "#000000"
    accent: "#BFC0BF"
```

### Category Configuration (`config/categories.yaml`)
```yaml
fixed_categories:
  restaurants:
    display_name: "Restaurants & QSR"
    threshold: 0.05
    subcategories:
      - "Restaurants - QSR & Fast Casual"
      - "Restaurants - Casual"
      - "Restaurants - Fine Dining"
```

## Data Model

### Snowflake Views Structure
- **COMMUNITY**: Fan community analysis data
- **CATEGORY**: Category-level spending patterns
- **SUBCATEGORY**: Detailed subcategory breakdowns  
- **MERCHANT**: Individual merchant performance
- **DEMOGRAPHICS**: Fan demographic profiles

### Key Metrics
- **PERC_AUDIENCE**: Percentage of fanbase that engages
- **PERC_INDEX**: Likelihood compared to general population
- **COMPOSITE_INDEX**: Combined scoring metric
- **SPC/PPC**: Spending per customer/purchases per customer

### Time Periods
- **ALL_TIME**: Historical aggregate data
- **SNAPSHOT**: Current period snapshot
- **YOY**: Year-over-year comparisons

## Output Structure

Generated presentations include:

1. **Title Slide**: Team branding and report overview
2. **Introduction Slides**: Executive summary and table of contents
3. **Demographics Overview**: High-level demographic insights
4. **Demographics Detail**: Age, income, occupation charts
5. **Fan Behaviors**: Community analysis and fan wheel visualization
6. **Category Analysis** (6-10 slides):
   - Fixed: Restaurants, Athleisure, Finance, Gambling, Travel, Auto
   - Custom: Top categories by composite index
7. **Merchant Rankings**: Top 5 brands per category with insights

## Performance & Scalability

### Optimization Strategies
- **Connection Pooling**: Database and Snowflake connection optimization
- **Caching Layer**: Multi-level caching for frequently accessed data
- **Async Processing**: Non-blocking job processing
- **Batch Operations**: Efficient database operations
- **Memory Management**: Optimized for large datasets

### Scaling Considerations
- **Horizontal Scaling**: Multiple backend instances supported
- **Database Scaling**: Connection pooling and query optimization
- **Cache Distribution**: Shared PostgreSQL cache across instances
- **Load Balancing**: Ready for load balancer integration
- **Monitoring**: Built-in health checks and performance metrics

## Error Handling & Logging

### Comprehensive Logging
```python
# Structured logging with different levels
# Logs saved to logs/ directory with timestamps
# Database logging for job tracking
# Performance metrics and cache statistics
```

### Graceful Degradation
- **Missing Data**: Slides marked as "Data Unavailable"
- **API Failures**: Fallback to cached data or placeholders
- **Database Issues**: Connection retry logic and fallbacks
- **Job Failures**: Comprehensive error reporting and recovery

## Testing Strategy

### Unit Tests
```bash
# Test individual components
python -m pytest slide_generators/tests/
python -m pytest data_processors/tests/
python -m pytest utils/tests/
```

### Integration Tests
```bash
# End-to-end testing
python quick_start.py --test-mode

# Database connectivity
python -c "from data_processors.snowflake_connector import test_connection; test_connection()"

# Web backend testing
cd backend && python -m pytest
```

### Performance Testing
```bash
# Load testing for web interface
# Cache performance validation
# Database connection stress testing
```

## Deployment

### Local Development
```bash
# Start backend
cd backend && python app.py

# Start frontend (served by backend)
# Access at http://localhost:5000
```

### Production Deployment (Render.com)
```bash
# Automatic deployment via Git push
# Environment variables configured in Render dashboard
# Health checks and monitoring enabled
# Auto-scaling based on demand
```

### Environment Variables
```bash
# Required for production
DATABASE_URL=postgresql://...
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...

# Optional
OPENAI_API_KEY=...
FLASK_ENV=production
```

## Business Value

### Efficiency Gains
- **Time Reduction**: Report creation from 4+ hours to 5-10 minutes
- **Consistency**: Standardized formatting across all team reports  
- **Quality Assurance**: Automated data validation and error checking
- **Scalability**: Single system supports entire league (100+ teams)

### Revenue Impact
- **Faster Sales Cycles**: Rapid report generation for prospect meetings
- **Data-Driven Insights**: AI-powered recommendations for optimal sponsors
- **Professional Presentation**: Consistent, high-quality client materials
- **Competitive Advantage**: Unique fan behavior insights

### Operational Benefits
- **Web Interface**: Non-technical users can generate reports
- **Job Management**: Track and manage multiple report generations
- **Caching**: Reduced API calls and improved performance
- **Monitoring**: Built-in health checks and performance tracking

## Future Enhancements

### Near-term Roadmap
- **Advanced AI Insights**: More sophisticated content generation
- **Real-time Updates**: Live data refresh during generation
- **Batch Processing**: Multiple team reports in single execution
- **Advanced Analytics**: Machine learning for sponsor matching

### Long-term Vision
- **Mobile App**: Native mobile application
- **API Marketplace**: Third-party integrations
- **Advanced Visualizations**: Interactive charts and dashboards
- **Multi-language Support**: Localized reports for international teams

## Support & Maintenance

### Common Issues

#### Database Connection
```bash
# Test PostgreSQL connection
python -c "from backend.postgresql_job_store import PostgreSQLJobStore; ps = PostgreSQLJobStore()"

# Common fixes:
# - Verify DATABASE_URL in .env
# - Check database accessibility
# - Confirm SSL requirements for cloud databases
```

#### Snowflake Connection
```bash
# Test Snowflake connection
python -c "from data_processors.snowflake_connector import test_connection; test_connection()"

# Common fixes:
# - Verify .env credentials
# - Check network connectivity
# - Confirm database schema access
```

#### Web Interface Issues
```bash
# Check backend status
curl http://localhost:5000/health

# Verify environment variables
# Check database connectivity
# Review application logs
```

### Monitoring & Alerts
- **Health Checks**: Built-in endpoint monitoring
- **Log Analysis**: Comprehensive logging and error tracking
- **Performance Metrics**: Cache statistics and job processing times
- **Database Monitoring**: Connection pool status and query performance

---

## Technical Contacts

For technical issues or enhancement requests, consult the project maintainers or create issues in the project repository.

## License

This project is proprietary to Sports Innovation Lab. All rights reserved.
