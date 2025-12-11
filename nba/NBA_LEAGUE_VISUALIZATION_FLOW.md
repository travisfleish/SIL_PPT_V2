# NBA League Visualization Data - Logical Flow

## Overview
This document describes the logical flow for generating the Community Index Chart and Fan Wheel visualizations for the entire NBA.

## Data Sources

### Schema: `NBA_LEAGUE_INSIGHTS`

### Tables/Views Used:

1. **Community Index Chart**: `V_NBA_LEAGUE_COMMUNITY_INDEXING_ALL_TIME`
2. **Fan Wheel**: `V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME`

---

## STEP 1: Community Index Chart Data Flow

### Purpose
Create a horizontal bar chart showing the top 10 NBA fan communities ranked by composite index.

### Query Logic:

```sql
SELECT 
    COMMUNITY,
    COMPARISON_POPULATION,
    PERC_AUDIENCE,
    PERC_INDEX,
    SPC_INDEX,
    SPP_INDEX,
    PPC_INDEX,
    COMPOSITE_INDEX
FROM V_NBA_LEAGUE_COMMUNITY_INDEXING_ALL_TIME
WHERE COMPARISON_POPULATION = 'General Population'
AND PERC_AUDIENCE >= 0.20  -- 20% threshold
QUALIFY ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) = 1
ORDER BY COMPOSITE_INDEX DESC
LIMIT 10
```

### Filters Applied:
- ✅ `COMPARISON_POPULATION = 'General Population'` - Compare against general population
- ✅ `PERC_AUDIENCE >= 0.20` - Only communities with at least 20% of NBA fans
- ✅ `QUALIFY ROW_NUMBER()...` - Get the top record per community (in case of duplicates)
- ✅ `ORDER BY COMPOSITE_INDEX DESC` - Rank by composite index (highest first)
- ✅ `LIMIT 10` - Top 10 communities only

### Output Columns:
- `COMMUNITY` - Community name (used as chart labels)
- `PERC_AUDIENCE` - Percentage of NBA fans in this community (0-1 scale)
- `COMPOSITE_INDEX` - Composite index score (used for ranking)
- `PERC_INDEX` - Percentage index (used for bar chart visualization)

### Visualization Mapping:
- **X-Axis (Top)**: `PERC_AUDIENCE` (converted to percentage 0-100%)
- **X-Axis (Bottom)**: `COMPOSITE_INDEX` (0-700 scale)
- **Y-Axis**: `COMMUNITY` (community names, sorted by `PERC_AUDIENCE` ascending)

---

## STEP 2: Fan Wheel Data Flow

### Purpose
Create a circular fan wheel showing one merchant per top community, representing fan behaviors.

### Query Logic:

```sql
WITH ranked_merchants AS (
    SELECT 
        COMMUNITY,
        MERCHANT,
        PARENT_MERCHANT,
        CATEGORY,
        SUBCATEGORY,
        PERC_AUDIENCE,
        PERC_INDEX,
        COMPOSITE_INDEX,
        ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as merchant_rank
    FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
    WHERE COMMUNITY IN (<top_10_communities>)
    AND COMPARISON_POPULATION = 'General Population'
    AND MERCHANT != 'LEVELUP'
    AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
    AND UPPER(MERCHANT) NOT LIKE '%NBA%'
    AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
    AND PERC_AUDIENCE >= 0.05
    AND COMPOSITE_INDEX <= 1000
)
SELECT * FROM ranked_merchants
WHERE merchant_rank <= 5
ORDER BY COMMUNITY, merchant_rank
```

### Filters Applied:
- ✅ `COMPARISON_POPULATION = 'General Population'` - Compare against general population
- ✅ `COMMUNITY IN (<top_10_communities>)` - Only merchants from top 10 communities
- ✅ `MERCHANT != 'LEVELUP'` - Exclude LEVELUP merchant
- ✅ `NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')` - Exclude professional sports category for Live Entertainment Seekers
- ✅ `UPPER(MERCHANT) NOT LIKE '%NBA%'` - Exclude NBA-related merchants
- ✅ `UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'` - Exclude NBA-related parent merchants
- ✅ `PERC_AUDIENCE >= 0.05` - Only merchants with at least 5% of community audience
- ✅ `COMPOSITE_INDEX <= 1000` - Reasonable index limit
- ✅ `ROW_NUMBER()...` - Rank merchants within each community
- ✅ `merchant_rank <= 5` - Top 5 merchants per community

### Selection Logic (One Merchant Per Community):

1. **Merge** merchant data with community data (add community composite index)
2. **Sort** by:
   - `COMMUNITY_COMPOSITE_INDEX` DESC (highest community index first)
   - `MERCHANT_COMPOSITE_INDEX` DESC (highest merchant index first)
3. **Greedy Selection**:
   - For each community, select the highest-ranked merchant
   - Skip merchants that have already been selected for another community (avoid duplicates)
   - If a community has no available unique merchant, allow duplicate (fallback)

### Behavior Text Generation:

For each community-merchant pair, generate behavior text:
- Look up community action verb from `config/approved_communities.yaml`
- Format: `{action_verb} {merchant_name}`
- Example: "Shops at Target", "Streams Netflix", "Visits Starbucks"

### Output Columns:
- `COMMUNITY` - Community name
- `MERCHANT` - Selected merchant name
- `COMMUNITY_PERC_INDEX` - Community percentage index (for wheel ordering)
- `MERCHANT_PERC_AUDIENCE` - Merchant percentage of community audience
- `BEHAVIOR_TEXT` - Generated behavior text for display

### Visualization Mapping:
- **Wheel Segments**: One per community (10 segments)
- **Segment Order**: Sorted by `COMMUNITY_PERC_INDEX` (highest first)
- **Segment Content**: Merchant logo + `BEHAVIOR_TEXT`
- **Center**: NBA logo or "NBA Fans" text

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Community Index Chart                                │
│                                                              │
│ V_NBA_LEAGUE_COMMUNITY_INDEXING_ALL_TIME                    │
│   ↓                                                          │
│ Filter: COMPARISON_POPULATION = 'General Population'        │
│ Filter: PERC_AUDIENCE >= 0.20                               │
│   ↓                                                          │
│ Top 10 Communities (by COMPOSITE_INDEX)                      │
│   ↓                                                          │
│ Export: nba_league_community_index_chart_data.csv           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Fan Wheel                                           │
│                                                              │
│ V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_... │
│   ↓                                                          │
│ Filter: Communities from Step 1                             │
│ Filter: COMPARISON_POPULATION = 'General Population'        │
│ Filter: MERCHANT != 'LEVELUP'                               │
│ Filter: Exclude NBA merchants                               │
│ Filter: Exclude Professional Sports (Live Entertainment)   │
│ Filter: PERC_AUDIENCE >= 0.05                               │
│   ↓                                                          │
│ Top 5 Merchants per Community (by COMPOSITE_INDEX)         │
│   ↓                                                          │
│ Merge with Community Data                                   │
│   ↓                                                          │
│ Greedy Selection: 1 unique merchant per community         │
│   ↓                                                          │
│ Generate Behavior Text (from approved_communities.yaml)     │
│   ↓                                                          │
│ Export: nba_league_fan_wheel_data.csv                       │
│ Export: nba_league_fan_wheel_data_full.csv (all top 5)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Metrics Explained

### PERC_AUDIENCE
- **Community**: Percentage of NBA fans that belong to this community (0-1 scale)
- **Merchant**: Percentage of community members that purchase from this merchant (0-1 scale)

### COMPOSITE_INDEX
- Average of four indexes:
  1. **PERC_INDEX**: Likelihood to be in community / purchase from merchant
  2. **SPC_INDEX**: Spend per customer index
  3. **SPP_INDEX**: Spend per person index
  4. **PPC_INDEX**: Purchases per customer index
- Higher = stronger affinity

### PERC_INDEX
- Ratio of audience percentage vs. comparison population percentage
- 100 = same as general population
- >100 = over-indexed (more likely than general population)
- <100 = under-indexed (less likely than general population)

---

## Output Files

1. **nba_league_community_index_chart_data.csv**
   - Top 10 communities with all metrics
   - Used for Community Index Chart visualization

2. **nba_league_fan_wheel_data.csv**
   - One merchant per community (final selection)
   - Used for Fan Wheel visualization

3. **nba_league_fan_wheel_data_full.csv**
   - Top 5 merchants per community (before selection)
   - Useful for analysis and debugging

4. **NBA_LEAGUE_VISUALIZATION_FLOW.md** (this file)
   - Complete logical flow documentation
