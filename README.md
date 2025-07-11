# Sports Innovation Lab - PowerPoint Generator

## Executive Summary

An automated system that transforms Snowflake fan behavior data into professional PowerPoint presentations for sports teams to identify and pitch potential sponsors. Currently configured for Utah Jazz and Dallas Cowboys, designed to scale to 100+ teams.

## Problem Understanding

The manual creation of sponsorship insights reports is time-intensive and inconsistent across teams. This system reduces report generation from hours to minutes while maintaining professional quality and ensuring data-driven sponsorship recommendations.

## Architecture Overview

```
sports-innovation-lab-pptx/
├── main.py                     # Entry point for report generation
├── quick_start.py              # Interactive testing and development
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration (create from template)
├── .gitignore                  # Git exclusions
│
├── config/                     # Configuration files
│   ├── teams.yaml             # Team configurations and branding
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
│   ├── chart_generator.py     # Chart creation utilities
│   └── tests/                 # Utility validation tests
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
└── logs/                      # Application logs
```

## Key Features

### 1. Automated Data Pipeline
- **Snowflake Integration**: Direct connection to `SIL__TB_OTT_TEST.SC_TWINBRAINAI`
- **Dynamic View Naming**: Handles team-specific view prefixes (`V_UTAH_JAZZ_SIL_`, `V_DALLAS_COWBOYS_`)
- **Data Validation**: Comprehensive error handling and data quality checks

### 2. Professional PowerPoint Generation
- **Template Integration**: Uses SIL branded template with consistent styling
- **16:9 Format**: Modern widescreen presentations
- **Font Management**: Red Hat Display with Arial fallback
- **Responsive Layouts**: Adapts to content length and team branding

### 3. Dynamic Visualizations
- **Fan Wheel**: Circular brand affinity visualization (5.8" diameter)
- **Demographic Charts**: Age, income, occupation comparisons
- **Community Index**: Top 10 fan communities with composite scoring
- **Category Analysis**: Detailed spending pattern breakdowns

### 4. AI-Powered Insights
- **OpenAI Integration**: Automated insight generation for each category
- **Logo Management**: Automatic brand logo fetching via Clearbit/Brandfetch APIs
- **Merchant Standardization**: Consistent brand name formatting

### 5. Scalable Architecture
- **Configuration-Driven**: YAML-based team and category management
- **Modular Design**: Independent slide generators for easy maintenance
- **Factory Pattern**: Extensible slide creation system

## Installation & Setup

### Prerequisites
- Python 3.8+
- Snowflake account access
- OpenAI API key (optional, for AI insights)
- Red Hat Display font (recommended)

### 1. Environment Setup
```bash
git clone <repository-url>
cd sports-innovation-lab-pptx
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
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

# Optional: OpenAI for AI insights
OPENAI_API_KEY=your_openai_key
```

### 3. Font Installation (Recommended)
Download and install Red Hat Display font:
1. Download from [Google Fonts](https://fonts.google.com/specimen/Red+Hat+Display)
2. Install all .ttf files on your system
3. Restart Python environment

### 4. Template Setup
Ensure `templates/sil_combined_template.pptx` exists in the project directory.

## Usage

### Quick Start
```bash
# Generate report for Utah Jazz
python main.py utah_jazz

# Generate report without custom categories
python main.py dallas_cowboys --no-custom

# Interactive testing mode
python quick_start.py --interactive
```

### Advanced Usage
```bash
# Generate with specific custom category count
python main.py utah_jazz --custom-count 2

# Custom output directory
python main.py utah_jazz --output /path/to/output

# Verbose logging
python main.py utah_jazz --verbose

# List available teams
python main.py --list-teams
```

### Development & Testing
```bash
# Interactive development environment
python quick_start.py --interactive

# Test single slide type
python quick_start.py --slide demographics utah_jazz

# Test specific categories
python quick_start.py utah_jazz --categories restaurants finance
```

## Configuration

### Team Configuration (`config/teams.yaml`)
```yaml
utah_jazz:
  team_name: "Utah Jazz"
  team_name_short: "Jazz"
  team_initials: "UJ"
  league: "NBA"
  view_prefix: "V_UTAH_JAZZ_SIL_"
  colors:
    primary: "#1D428A"
    secondary: "#FFD700"
    accent: "#00275D"
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

## Performance Considerations

### Optimization Strategies
- **Caching**: Logo and data caching to reduce API calls
- **Lazy Loading**: Charts generated only when needed
- **Batch Processing**: Multiple categories processed in single database queries
- **Template Reuse**: Single template loaded for all slides

### Scaling Considerations
- **Database Connection Pooling**: For high-volume usage
- **Parallel Processing**: Categories can be processed independently
- **Memory Management**: Large datasets processed in chunks
- **Error Recovery**: Graceful degradation when data is unavailable

## Error Handling & Logging

### Comprehensive Logging
```python
# Logs saved to logs/ directory with timestamps
# Different log levels for development vs production
# Detailed error traces for debugging
```

### Graceful Degradation
- **Missing Data**: Slides marked as "Data Unavailable"
- **API Failures**: Fallback to cached logos or placeholders
- **Font Issues**: Automatic fallback to Arial
- **Template Problems**: Blank presentation creation

## Testing Strategy

### Unit Tests
```bash
# Test individual slide generators
python slide_generators/tests/test_demographics.py

# Test data processors
python data_processors/tests/test_merchant.py

# Test utility functions
python utils/tests/merchant_name_validation.py
```

### Integration Tests
```bash
# End-to-end report generation
python quick_start.py utah_jazz

# Database connectivity
python -c "from data_processors.snowflake_connector import test_connection; print(test_connection())"
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

## Alternative Methods & Trade-offs

### Design Decisions

#### 1. Template-Based vs. Code-Generated Slides
**Chosen**: Template-based with SIL branding
- **Pro**: Consistent professional appearance, faster development
- **Con**: Template dependency, limited layout flexibility
- **Alternative**: Pure code generation would offer more flexibility but require more design work

#### 2. Snowflake Direct Connection vs. API Layer
**Chosen**: Direct Snowflake connection
- **Pro**: Real-time data access, no intermediate API maintenance
- **Con**: Database credential management, potential connection limits
- **Alternative**: REST API layer would add security but increase complexity

#### 3. Static vs. Dynamic Category Selection
**Chosen**: Hybrid approach (fixed + dynamic custom categories)
- **Pro**: Predictable core content with data-driven customization
- **Con**: More complex logic than pure static or dynamic approaches
- **Alternative**: Pure dynamic selection would be more flexible but less predictable

## Potential Improvements

### Near-term Enhancements
- **Chart Customization**: Team-specific color schemes in visualizations
- **Interactive Elements**: Clickable logos linking to brand websites
- **Export Formats**: PDF generation for email distribution
- **Batch Processing**: Multiple team reports in single execution

### Long-term Roadmap
- **Web Interface**: Browser-based report generation dashboard
- **Real-time Updates**: Live data refresh during presentation
- **Advanced Analytics**: Machine learning for sponsor match scoring
- **Multi-language Support**: Localized reports for international teams

## Support & Maintenance

### Common Issues

#### Snowflake Connection
```bash
# Test connection
python -c "from data_processors.snowflake_connector import test_connection; test_connection()"

# Common fixes:
# - Verify .env credentials
# - Check network connectivity
# - Confirm database schema access
```

#### Font Installation
```bash
# Verify font availability
python report_builder/pptx_builder.py

# Install Red Hat Display:
# 1. Download from Google Fonts
# 2. Install system-wide
# 3. Restart Python environment
```

#### Template Issues
```bash
# Verify template exists
ls -la templates/sil_combined_template.pptx

# Test template loading
python slide_generators/tests/demo_overview_test.py
```

### Monitoring & Alerts
- **Log Analysis**: Monitor logs/ directory for errors
- **Data Quality**: Validate team view availability
- **Performance**: Track report generation times
- **Error Rates**: Monitor API failures and database timeouts

---

## Technical Contacts

For technical issues or enhancement requests, consult the project maintainers or create issues in the project repository.
