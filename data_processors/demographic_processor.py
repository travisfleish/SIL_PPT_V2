# data_processors/demographic_processor.py
"""
Process demographic data from Snowflake exports to generate insights
for PowerPoint presentations. Handles large datasets (400K+ rows) efficiently.
Now includes AI-powered insights generation and ethnicity processing.
FIXED VERSION: Handles null values in ETHNIC_GROUP column.
UPDATED: Filters out 'Retired' and 'Other' from occupation charts.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
import logging
from functools import lru_cache
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DemographicsProcessor:
    """Process demographic data for sports team fan analysis"""

    # Expected communities in the data
    EXPECTED_COMMUNITIES = [
        'Utah Jazz Fans',  # Or dynamically set based on team
        'Local Gen Pop (Excl. Jazz)',  # Or 'Local Gen Pop (Excl. {team})'
        'NBA Fans'  # Or '{league} Fans'
    ]

    # Demographic categories expected in the full dataset
    GENERATION_ORDER = [
        '1. Millennials and Gen Z (1982 and after)',
        '2. Generation X (1961-1981)',
        '3. Baby Boomers (1943-1960)',
        '4. Post-WWII (1942 and before)'
    ]

    INCOME_ORDER = [
        'LT_30K',
        '30K_50K',
        '50K_74K',
        '75K_99K',
        '100K_150K',
        'GT_150K'
    ]

    INCOME_LABELS = {
        'LT_30K': '$10,000 to $49,999',  # Combining for display
        '30K_50K': '$10,000 to $49,999',
        '50K_74K': '$50,000 to $74,999',
        '75K_99K': '$75,000 to $99,999',
        '100K_150K': '$100,000 to $149,999',
        'GT_150K': '$150,000 to $199,999'  # Will need to handle $200K+ separately
    }

    OCCUPATION_ORDER = [
        'Blue Collar',
        'Homemaker',
        'Lower Management',
        'Professional',
        'Upper Management',
        'White Collar Worker',
        'Retired',
        'Other'
    ]

    # Ethnicity categories
    ETHNICITY_ORDER = ['White', 'Hispanic', 'African American', 'Asian', 'Other']

    def __init__(self, data_source: Union[str, Path, pd.DataFrame],
                 team_name: str = "Utah Jazz",
                 league: str = "NBA",
                 use_ai_insights: bool = True):
        """
        Initialize the processor with data and team configuration

        Args:
            data_source: Path to data file or DataFrame
            team_name: Name of the team (e.g., "Utah Jazz")
            league: League name (e.g., "NBA")
            use_ai_insights: Whether to use AI for insight generation
        """
        self.team_name = team_name
        self.league = league
        self.use_ai_insights = use_ai_insights and bool(os.getenv('OPENAI_API_KEY'))

        if use_ai_insights and not os.getenv('OPENAI_API_KEY'):
            logger.warning("AI insights requested but no OpenAI API key found. Using template insights.")

        # Update expected communities based on team
        self.communities = [
            f'{team_name} Fans',
            f'Local Gen Pop (Excl. {team_name.split()[-1]})',  # Gets last word (Jazz, Cowboys, etc)
            f'{league} Fans'
        ]

        # Load and validate data
        self.data = self._load_data(data_source)
        self._validate_data()

        # Cache for expensive computations
        self._community_totals = None

        # Initialize OpenAI client if using AI
        self.openai_client = OpenAI() if self.use_ai_insights else None

    def _load_data(self, data_source: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
        """Load data from file or DataFrame"""
        if isinstance(data_source, pd.DataFrame):
            return data_source.copy()

        # Optimize dtypes for memory efficiency
        dtypes = {
            'CUSTOMER_COUNT': 'int32',
            'CHILDREN_HH': 'int8',
            'NUM_CHILDREN_HH': 'int8',
            'NUM_ADULTS_HH': 'int8'
        }

        file_path = Path(data_source)
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path, dtype=dtypes)
        elif file_path.suffix in ['.xlsx', '.xls']:
            return pd.read_excel(file_path, dtype=dtypes)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def _validate_data(self):
        """Validate that data has required structure"""
        required_columns = [
            'COMMUNITY', 'CUSTOMER_COUNT', 'GENERATION',
            'INCOME_LEVELS', 'OCCUPATION_CATEGORY', 'GENDER',
            'CHILDREN_HH'
        ]

        missing = set(required_columns) - set(self.data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Check for expected communities
        actual_communities = set(self.data['COMMUNITY'].unique())
        missing_communities = set(self.communities) - actual_communities
        if missing_communities:
            logger.warning(f"Missing communities in data: {missing_communities}")
            # Update communities to what's actually in the data
            self.communities = [c for c in self.communities if c in actual_communities]

        # Log data summary
        total_rows = len(self.data)
        total_customers = self.data['CUSTOMER_COUNT'].sum()
        logger.info(f"Loaded {total_rows:,} rows representing {total_customers:,} customers")

    @lru_cache(maxsize=1)
    def _get_community_totals(self) -> pd.Series:
        """Get total customer counts by community (cached)"""
        return self.data.groupby('COMMUNITY')['CUSTOMER_COUNT'].sum()

    def _calculate_percentages(self, attribute: str,
                               categories: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """
        Calculate percentage distribution for a demographic attribute
        Enhanced version with better null handling

        Args:
            attribute: Column name to analyze
            categories: Optional ordered list of categories

        Returns:
            Dict with structure: {community: {category: percentage}}
        """
        # Group by community and attribute, sum customer counts
        grouped = self.data.groupby(['COMMUNITY', attribute])['CUSTOMER_COUNT'].sum()

        # Get community totals
        community_totals = self._get_community_totals()

        # Calculate percentages
        results = {}
        for community in self.communities:
            if community not in community_totals.index:
                continue

            total = community_totals[community]

            # Enhanced null handling: check if community exists in grouped data
            if community in grouped.index:
                community_data = grouped[community]

                # Ensure we have numeric data - handle object dtype that can occur with nulls
                if community_data.dtype == 'object':
                    logger.debug(f"Converting object dtype to numeric for {community}/{attribute}")
                    community_data = pd.to_numeric(community_data, errors='coerce').fillna(0)
            else:
                # Create empty numeric series instead of default object series
                community_data = pd.Series(dtype='float64')

            # Calculate percentages - handle empty data
            if len(community_data) > 0 and total > 0:
                try:
                    percentages = (community_data / total * 100).round(1)
                except Exception as e:
                    logger.warning(f"Error calculating percentages for {community}: {e}")
                    percentages = pd.Series(dtype='float64')
            else:
                percentages = pd.Series(dtype='float64')

            # If categories provided, ensure all are present
            if categories:
                category_dict = {cat: 0.0 for cat in categories}
                # Only update with valid (non-null) data
                for cat, val in percentages.to_dict().items():
                    if pd.notna(cat) and pd.notna(val) and cat in category_dict:
                        category_dict[cat] = float(val)
                results[community] = category_dict
            else:
                # Filter out any NaN keys and ensure numeric values
                percentage_dict = {}
                for k, v in percentages.to_dict().items():
                    if pd.notna(k) and pd.notna(v):
                        percentage_dict[k] = float(v)
                results[community] = percentage_dict

        return results

    def process_generation(self) -> Dict[str, Any]:
        """Process generation/age distribution"""
        percentages = self._calculate_percentages('GENERATION', self.GENERATION_ORDER)

        # Format for charts
        return {
            'chart_type': 'grouped_bar',
            'title': 'Generation',
            'categories': self.GENERATION_ORDER,
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_generation_insights(percentages)
        }

    def process_income(self) -> Dict[str, Any]:
        """Process household income distribution"""
        raw_percentages = self._calculate_percentages('INCOME_LEVELS', self.INCOME_ORDER)

        # Combine income brackets as shown in PPT
        display_categories = [
            '$10,000 to $49,999',
            '$50,000 to $74,999',
            '$75,000 to $99,999',
            '$100,000 to $149,999',
            '$150,000 to $199,999',
            '$200,000 or more'
        ]

        # Aggregate data for display brackets
        aggregated = {}
        for community, data in raw_percentages.items():
            aggregated[community] = {
                '$10,000 to $49,999': data.get('LT_30K', 0) + data.get('30K_50K', 0),
                '$50,000 to $74,999': data.get('50K_74K', 0),
                '$75,000 to $99,999': data.get('75K_99K', 0),
                '$100,000 to $149,999': data.get('100K_150K', 0),
                '$150,000 to $199,999': data.get('GT_150K', 0) * 0.7,  # Estimate split
                '$200,000 or more': data.get('GT_150K', 0) * 0.3  # Estimate split
            }

        return {
            'chart_type': 'grouped_bar',
            'title': 'Household Income',
            'categories': display_categories,
            'communities': self.communities,
            'data': aggregated,
            'insights': self._generate_income_insights(aggregated)
        }

    def process_occupation(self) -> Dict[str, Any]:
        """Process occupation category distribution - UPDATED to filter out Retired and Other"""
        # Get all percentages first (needed for insights)
        percentages = self._calculate_percentages('OCCUPATION_CATEGORY', self.OCCUPATION_ORDER)

        # Filter out Retired and Other categories for the chart
        filtered_categories = [cat for cat in self.OCCUPATION_ORDER
                               if cat not in ['Retired', 'Other']]

        # Filter the data to exclude Retired and Other
        filtered_data = {}
        for community, data in percentages.items():
            filtered_data[community] = {
                cat: data.get(cat, 0)
                for cat in filtered_categories
            }

        return {
            'chart_type': 'grouped_bar',
            'title': 'Occupation Category',
            'categories': filtered_categories,  # Use filtered categories
            'communities': self.communities,
            'data': filtered_data,  # Use filtered data
            'insights': self._generate_occupation_insights(percentages)  # Keep original for insights
        }

    def process_gender(self) -> Dict[str, Any]:
        """Process gender distribution"""
        percentages = self._calculate_percentages('GENDER', ['Male', 'Female'])

        return {
            'chart_type': 'pie',
            'title': 'Gender',
            'categories': ['Male', 'Female'],
            'communities': self.communities,
            'data': percentages,
            'insights': []  # Gender typically not highlighted in insights
        }

    def process_children(self) -> Dict[str, Any]:
        """Process children in household distribution"""
        # Group by community and children flag directly
        grouped = self.data.groupby(['COMMUNITY', 'CHILDREN_HH'])['CUSTOMER_COUNT'].sum()
        community_totals = self._get_community_totals()

        # Calculate percentages
        percentages = {}
        for community in self.communities:
            if community not in community_totals.index:
                continue

            total = community_totals[community]

            # Get counts for each category (0 = no children, 1 = has children)
            no_children = grouped.get((community, 0), 0) if (community, 0) in grouped else 0
            with_children = grouped.get((community, 1), 0) if (community, 1) in grouped else 0

            # Calculate percentages
            percentages[community] = {
                'No Children in HH': round(no_children / total * 100, 1),
                'At least 1 Child in HH': round(with_children / total * 100, 1)
            }

        return {
            'chart_type': 'grouped_bar',
            'title': 'Children in Household',
            'categories': ['No Children in HH', 'At least 1 Child in HH'],
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_children_insights(percentages)
        }

    def process_ethnicity(self) -> Dict[str, Any]:
        """Process ethnicity distribution using ETHNIC_GROUP column - EXCLUDES LOCAL GEN POP DUE TO NULL VALUES"""

        # Check if ETHNIC_GROUP column exists
        if 'ETHNIC_GROUP' not in self.data.columns:
            logger.warning("ETHNIC_GROUP column not found in data")
            return None

        # MINIMAL NULL FIX: Handle nulls before processing
        logger.info("Processing ethnicity data...")
        null_count = self.data['ETHNIC_GROUP'].isnull().sum()

        if null_count > 0:
            logger.info(f"Found {null_count:,} null values in ETHNIC_GROUP, replacing with 'Unknown'")
            # Create a copy to avoid modifying original data
            clean_data = self.data.copy()
            clean_data['ETHNIC_GROUP'] = clean_data['ETHNIC_GROUP'].fillna('Unknown')

            # Temporarily replace self.data for this calculation
            original_data = self.data
            self.data = clean_data
        else:
            logger.info("No null values found in ETHNIC_GROUP")

        # Get unique ethnic groups from data
        unique_groups = self.data['ETHNIC_GROUP'].dropna().unique()
        logger.info(f"Found ethnic groups: {unique_groups}")

        try:
            # Calculate raw percentages for all groups
            raw_percentages = self._calculate_percentages('ETHNIC_GROUP')

            # Restore original data if we modified it
            if null_count > 0:
                self.data = original_data

            # CRITICAL: Filter out Local Gen Pop community due to null values
            local_gen_pop_key = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

            # Check if local gen pop has only Unknown/null ethnicity data
            if local_gen_pop_key in raw_percentages:
                gen_pop_data = raw_percentages[local_gen_pop_key]
                # If all or most of the data is Unknown, exclude this community
                unknown_percentage = gen_pop_data.get('Unknown', 0)
                if unknown_percentage > 90:  # If more than 90% is Unknown/null
                    logger.warning(
                        f"Excluding '{local_gen_pop_key}' from ethnicity chart due to null values ({unknown_percentage:.1f}% unknown)")
                    del raw_percentages[local_gen_pop_key]

            # Filter communities list for this chart
            ethnicity_communities = [c for c in self.communities if c in raw_percentages]

            # Aggregate data into standard categories
            aggregated = {}
            for community, data in raw_percentages.items():
                aggregated[community] = {cat: 0.0 for cat in self.ETHNICITY_ORDER}

                for group, percentage in data.items():
                    # Map groups to standard categories
                    if group == 'Unknown':
                        # Skip unknown ethnicity in final aggregation to avoid skewing results
                        logger.debug(f"Skipping 'Unknown' ethnicity for {community}: {percentage}%")
                        continue
                    elif pd.isna(group) or group == '':
                        continue
                    elif 'White' in group or 'Caucasian' in group:
                        aggregated[community]['White'] += percentage
                    elif 'Hispanic' in group or 'Latino' in group:
                        aggregated[community]['Hispanic'] += percentage
                    elif 'African' in group or 'Black' in group:
                        aggregated[community]['African American'] += percentage
                    elif 'Asian' in group:
                        aggregated[community]['Asian'] += percentage
                    else:
                        aggregated[community]['Other'] += percentage

            # NEW: Normalize percentages to sum to 100% based on known ethnicities only
            normalized = {}
            for community, data in aggregated.items():
                # Calculate total of known ethnicities
                known_total = sum(data.values())

                if known_total > 0:
                    # Rebase all percentages to sum to 100%
                    normalized[community] = {
                        ethnicity: round(percentage / known_total * 100, 1)
                        for ethnicity, percentage in data.items()
                    }

                    # Log the rebasing for transparency
                    logger.info(f"{community}: Rebased ethnicity percentages from {known_total:.1f}% known to 100%")
                else:
                    # If no known ethnicities, keep zeros
                    normalized[community] = data
                    logger.warning(f"{community}: No known ethnicity data available")

            return {
                'chart_type': 'grouped_bar',
                'title': 'Ethnicity',
                'categories': self.ETHNICITY_ORDER,
                'communities': ethnicity_communities,  # Use filtered communities list
                'data': normalized,  # Use normalized data instead of aggregated
                'insights': self._generate_ethnicity_insights(normalized),
                'note': 'Percentages based on known ethnicities only. Local Gen Pop excluded due to insufficient data.'
            }

        except Exception as e:
            # Restore original data if we modified it and an error occurred
            if null_count > 0:
                self.data = original_data
            logger.error(f"Error processing ethnicity data: {e}")
            raise

    def process_all_demographics(self) -> Dict[str, Any]:
        """Process all demographic data and generate insights"""
        # Process individual demographics
        demographic_results = {
            'generation': self.process_generation(),
            'income': self.process_income(),
            'occupation': self.process_occupation(),
            'gender': self.process_gender(),
            'children': self.process_children()
        }

        # Add ethnicity if available
        ethnicity_result = self.process_ethnicity()
        if ethnicity_result:
            demographic_results['ethnicity'] = ethnicity_result
            logger.info("Processed ethnicity demographics")

        # Generate insights
        if self.use_ai_insights:
            key_insights = self._generate_ai_insights(demographic_results)
        else:
            key_insights = self._generate_summary_insights()

        results = {
            'team_name': self.team_name,
            'league': self.league,
            'communities': self.communities,
            'total_sample_size': self.data['CUSTOMER_COUNT'].sum(),
            'demographics': demographic_results,
            'key_insights': key_insights
        }

        return results

    def _generate_summary_insights(self) -> str:
        """Generate the main summary text for the demographics slide (fallback) - UPDATED"""
        # Updated to match client expectations
        all_insights = []

        # Collect insights from each demographic
        demo_results = {
            'generation': self.process_generation(),
            'income': self.process_income(),
            'occupation': self.process_occupation(),
            'children': self.process_children()
        }

        for demo, result in demo_results.items():
            all_insights.extend(result.get('insights', []))

        # Combine insights into a summary
        if all_insights:
            summary_parts = []
            if any('younger' in i for i in all_insights):
                summary_parts.append('younger')
            if any('parent' in i for i in all_insights):
                summary_parts.append('more likely to be parents')
            if any('Professional' in i or 'professional' in i.lower() for i in all_insights):
                summary_parts.append('who are working professionals')

            if summary_parts:
                return f"{self.team_name} fans are {', and '.join(summary_parts)} versus the Utah gen pop."

        return f"{self.team_name} fans have unique demographic characteristics compared to the general population and NBA average fans."

    def _generate_generation_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for generation distribution"""
        insights = []
        fan_community = f'{self.team_name} Fans'
        gen_pop = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

        if fan_community in percentages and gen_pop in percentages:
            # Check if fans are younger
            young_gens = ['1. Millennials and Gen Z (1982 and after)', '2. Generation X (1961-1981)']
            fan_young = sum(percentages[fan_community].get(g, 0) for g in young_gens)
            pop_young = sum(percentages[gen_pop].get(g, 0) for g in young_gens)

            if fan_young > pop_young + 5:
                insights.append(
                    f"{self.team_name} fans skew younger ({fan_young:.0f}% Gen X or younger vs {pop_young:.0f}%)")

        return insights

    def _generate_income_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for income distribution"""
        insights = []
        fan_community = f'{self.team_name} Fans'
        gen_pop = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

        if fan_community in percentages and gen_pop in percentages:
            # Check higher income brackets
            high_income = ['$100,000 to $149,999', '$150,000 to $199,999', '$200,000 or more']
            fan_high = sum(percentages[fan_community].get(bracket, 0) for bracket in high_income)
            pop_high = sum(percentages[gen_pop].get(bracket, 0) for bracket in high_income)

            if fan_high > pop_high + 5:
                insights.append(
                    f"{self.team_name} fans have higher household incomes ({fan_high:.0f}% vs {pop_high:.0f}% earning $100K+)")

        return insights

    def _generate_occupation_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for occupation distribution"""
        insights = []
        fan_community = f'{self.team_name} Fans'
        gen_pop = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

        if fan_community in percentages and gen_pop in percentages:
            # Check professional categories
            professional_cats = ['Professional', 'Upper Management']
            fan_prof = sum(percentages[fan_community].get(cat, 0) for cat in professional_cats)
            pop_prof = sum(percentages[gen_pop].get(cat, 0) for cat in professional_cats)

            if fan_prof > pop_prof + 3:
                insights.append(
                    f"{self.team_name} fans are more likely to work in professional roles ({fan_prof:.0f}% vs {pop_prof:.0f}%)")

        return insights

    def _generate_children_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for children distribution"""
        insights = []
        fan_community = f'{self.team_name} Fans'
        gen_pop = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

        if fan_community in percentages and gen_pop in percentages:
            fan_with_children = percentages[fan_community].get('At least 1 Child in HH', 0)
            pop_with_children = percentages[gen_pop].get('At least 1 Child in HH', 0)

            if fan_with_children > pop_with_children + 5:
                insights.append(
                    f"{self.team_name} fans are more likely to be parents ({fan_with_children:.0f}% vs {pop_with_children:.0f}%)")

        return insights

    def _generate_ethnicity_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights about ethnicity distribution"""
        insights = []

        team_fans = self.communities[0]
        gen_pop = self.communities[1]

        if team_fans in percentages and gen_pop in percentages:
            team_data = percentages[team_fans]
            pop_data = percentages[gen_pop]

            # Find largest ethnic group for team fans
            if team_data:
                largest_group = max(team_data.items(), key=lambda x: x[1])
                insights.append(f"{largest_group[1]:.0f}% of {team_fans} are {largest_group[0]}")

            # Find biggest difference
            max_diff = 0
            max_diff_group = None
            for group in team_data:
                if group in pop_data:
                    diff = abs(team_data[group] - pop_data[group])
                    if diff > max_diff:
                        max_diff = diff
                        max_diff_group = group

            if max_diff_group and max_diff > 5:
                team_val = team_data.get(max_diff_group, 0)
                pop_val = pop_data.get(max_diff_group, 0)
                if team_val > pop_val:
                    insights.append(
                        f"{team_fans} have {team_val - pop_val:.0f}% more {max_diff_group} fans than general population")
                else:
                    insights.append(
                        f"{team_fans} have {pop_val - team_val:.0f}% fewer {max_diff_group} fans than general population")

        return insights

    def _generate_ai_insights(self, demographic_results: Dict[str, Any]) -> str:
        """Generate sophisticated insights using OpenAI - CLIENT-ALIGNED VERSION"""
        if not self.openai_client:
            return self._generate_summary_insights()

        try:
            # Collect data for all three communities
            team_fans = f"{self.team_name} Fans"
            gen_pop = f"Local Gen Pop (Excl. {self.team_name.split()[-1]})"
            league_fans = f"{self.league} Fans"

            # Build comprehensive data summary
            data_summary = []

            for demo_type, demo_data in demographic_results.items():
                if demo_data and 'data' in demo_data:
                    categories = demo_data.get('categories', [])
                    for category in categories:
                        team_val = demo_data['data'].get(team_fans, {}).get(category, 0)
                        pop_val = demo_data['data'].get(gen_pop, {}).get(category, 0)
                        league_val = demo_data['data'].get(league_fans, {}).get(category, 0)

                        if team_val > 0:  # Only include non-zero data
                            data_summary.append(
                                f"{demo_type.title()} - {category}: {team_fans} {team_val}%, {gen_pop} {pop_val}%, {league_fans} {league_val}%"
                            )

            # Create prompt for AI
            prompt = f"""Analyze demographic data for {team_fans} and create a single, compelling sentence that summarizes their key characteristics compared to the general population.

Data:
{chr(10).join(data_summary[:20])}  # Limit to prevent token overflow

Requirements:
- Write exactly ONE sentence (not a paragraph)
- Focus on the most distinctive characteristics
- Use natural, marketing-friendly language
- Compare primarily to general population, mention {self.league} fans if relevant
- Avoid jargon or overly technical terms
- Make it actionable for sponsors

Example style: "{self.team_name} fans are younger, higher-earning professionals who are more likely to be parents versus the local general population."
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "You are a marketing insights analyst who creates compelling, concise demographic summaries for sports sponsorship presentations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )

            ai_insight = response.choices[0].message.content.strip()

            # Validate and clean the response
            if ai_insight and len(ai_insight) > 20:
                # Remove any quotes and ensure it ends properly
                ai_insight = ai_insight.strip('"').strip("'")
                if not ai_insight.endswith('.'):
                    ai_insight += '.'

                logger.info("Generated AI demographic insight")
                return ai_insight
            else:
                logger.warning("AI insight too short, using fallback")
                return self._generate_summary_insights()

        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return self._generate_summary_insights()