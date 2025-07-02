# data_processors/demographic_processor.py
"""
Process demographic data from Snowflake exports to generate insights
for PowerPoint presentations. Handles large datasets (400K+ rows) efficiently.
Now includes AI-powered insights generation.
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

            community_data = grouped[community] if community in grouped else pd.Series()
            total = community_totals[community]

            # Calculate percentages
            percentages = (community_data / total * 100).round(1)

            # If categories provided, ensure all are present
            if categories:
                category_dict = {cat: 0.0 for cat in categories}
                category_dict.update(percentages.to_dict())
                results[community] = category_dict
            else:
                results[community] = percentages.to_dict()

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
        """Process occupation category distribution"""
        percentages = self._calculate_percentages('OCCUPATION_CATEGORY', self.OCCUPATION_ORDER)

        return {
            'chart_type': 'grouped_bar',
            'title': 'Occupation Category',
            'categories': self.OCCUPATION_ORDER,
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_occupation_insights(percentages)
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
            # Check high income brackets
            high_income = ['$100,000 to $149,999', '$150,000 to $199,999', '$200,000 or more']
            fan_high = sum(percentages[fan_community].get(bracket, 0) for bracket in high_income)
            pop_high = sum(percentages[gen_pop].get(bracket, 0) for bracket in high_income)

            if fan_high > pop_high + 5:
                insights.append(f"Higher income households ({fan_high:.0f}% earn $100K+ vs {pop_high:.0f}%)")

        return insights

    def _generate_occupation_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for occupation distribution"""
        insights = []
        fan_community = f'{self.team_name} Fans'
        gen_pop = f'Local Gen Pop (Excl. {self.team_name.split()[-1]})'

        if fan_community in percentages and gen_pop in percentages:
            # Check professional categories
            prof_categories = ['Professional', 'Upper Management', 'White Collar Worker']
            fan_prof = sum(percentages[fan_community].get(cat, 0) for cat in prof_categories)
            pop_prof = sum(percentages[gen_pop].get(cat, 0) for cat in prof_categories)

            if fan_prof > pop_prof + 5:
                insights.append(
                    f"More working professionals ({fan_prof:.0f}% in professional/management vs {pop_prof:.0f}%)")

        return insights

    def _generate_children_insights(self, percentages: Dict[str, Dict[str, float]]) -> List[str]:
        """Generate insights for children in household"""
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

            # Generation/Age data
            if 'generation' in demographic_results:
                gen_data = demographic_results['generation']['data']
                if team_fans in gen_data:
                    # Calculate younger percentage (Millennials + Gen X)
                    young_gens = ['1. Millennials and Gen Z (1982 and after)', '2. Generation X (1961-1981)']
                    team_young = sum(gen_data[team_fans].get(g, 0) for g in young_gens)
                    pop_young = sum(gen_data[gen_pop].get(g, 0) for g in young_gens) if gen_pop in gen_data else 0
                    league_young = sum(
                        gen_data[league_fans].get(g, 0) for g in young_gens) if league_fans in gen_data else 0

                    data_summary.append(
                        f"Age: {team_fans} are {team_young:.0f}% Millennials/Gen X, vs {pop_young:.0f}% for Utah gen pop and {league_young:.0f}% for NBA fans")

            # Income data
            if 'income' in demographic_results:
                income_data = demographic_results['income']['data']
                if team_fans in income_data:
                    # High income brackets
                    high_income = ['$100,000 to $149,999', '$150,000 to $199,999', '$200,000 or more']
                    team_high = sum(income_data[team_fans].get(b, 0) for b in high_income)
                    pop_high = sum(income_data[gen_pop].get(b, 0) for b in high_income) if gen_pop in income_data else 0
                    league_high = sum(
                        income_data[league_fans].get(b, 0) for b in high_income) if league_fans in income_data else 0

                    data_summary.append(
                        f"Income: {team_fans} have {team_high:.0f}% earning $100K+, vs {pop_high:.0f}% for Utah gen pop and {league_high:.0f}% for NBA fans")

            # Gender data
            if 'gender' in demographic_results:
                gender_data = demographic_results['gender']['data']
                if team_fans in gender_data:
                    team_male = gender_data[team_fans].get('Male', 0)
                    pop_male = gender_data[gen_pop].get('Male', 0) if gen_pop in gender_data else 0
                    league_male = gender_data[league_fans].get('Male', 0) if league_fans in gender_data else 0

                    data_summary.append(
                        f"Gender: {team_fans} are {team_male:.0f}% male, vs {pop_male:.0f}% for Utah gen pop and {league_male:.0f}% for NBA fans")

            # Occupation data
            if 'occupation' in demographic_results:
                occ_data = demographic_results['occupation']['data']
                if team_fans in occ_data:
                    prof_cats = ['Professional', 'Upper Management', 'White Collar Worker']
                    team_prof = sum(occ_data[team_fans].get(c, 0) for c in prof_cats)
                    pop_prof = sum(occ_data[gen_pop].get(c, 0) for c in prof_cats) if gen_pop in occ_data else 0
                    league_prof = sum(
                        occ_data[league_fans].get(c, 0) for c in prof_cats) if league_fans in occ_data else 0

                    data_summary.append(
                        f"Occupation: {team_fans} are {team_prof:.0f}% working professionals, vs {pop_prof:.0f}% for Utah gen pop and {league_prof:.0f}% for NBA fans")

            # Children data (only vs gen pop as NBA fans data might not be available)
            if 'children' in demographic_results:
                child_data = demographic_results['children']['data']
                if team_fans in child_data:
                    team_parents = child_data[team_fans].get('At least 1 Child in HH', 0)
                    pop_parents = child_data[gen_pop].get('At least 1 Child in HH', 0) if gen_pop in child_data else 0

                    data_summary.append(
                        f"Household: {team_fans} have {team_parents:.0f}% with children, vs {pop_parents:.0f}% for Utah gen pop")

            # Create prompt matching client's requirements
            prompt = f"""You are a sponsorship sales representative writing a single summary sentence about {self.team_name} fans.

Using ONLY this demographic data:
"""
            for item in data_summary:
                prompt += f"- {item}\n"

            prompt += f"""
Write ONE sentence that explains how {self.team_name} fans look different vs. the Utah gen pop and NBA average fans.

Call out if they're:
- More or less likely to be older or younger vs. Utah general population and vs. NBA average fans
- Have higher or lower household income vs. Utah general population and NBA average fans  
- More likely to be male or female vs. Utah general population and NBA average fans
- Working professionals or not

Use specific percentages. Focus on the most significant differences.

Example format: "{self.team_name} fans are [age comparison], with [income comparison], are [gender comparison], and [occupation comparison] compared to both the Utah general population and NBA average fans."

DO NOT add any information not in the data above. Use the exact percentages provided."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "You are a sponsorship sales representative. Use ONLY the data provided to create insights that help sell sponsorships."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=150
            )

            insight = response.choices[0].message.content.strip()
            logger.info(f"Generated insight: {insight}")

            # Basic validation - should mention team name and include numbers
            if self.team_name in insight and any(char.isdigit() for char in insight):
                return insight
            else:
                logger.warning("Generated insight failed validation, using template")
                return self._generate_summary_insights()

        except Exception as e:
            logger.error(f"AI insight generation failed: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_summary_insights()

    def process_all_demographics(self) -> Dict[str, Any]:
        """Process all demographic attributes and return complete analysis"""
        logger.info(f"Processing demographics for {self.team_name}")

        # Process each demographic type
        demographic_results = {
            'generation': self.process_generation(),
            'income': self.process_income(),
            'occupation': self.process_occupation(),
            'gender': self.process_gender(),
            'children': self.process_children()
        }

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

    def export_for_visualization(self) -> Dict[str, pd.DataFrame]:
        """Export data in format ready for chart generation"""
        results = self.process_all_demographics()

        # Create DataFrames for each chart
        dataframes = {}

        for demo_type, demo_data in results['demographics'].items():
            if demo_data['chart_type'] == 'grouped_bar':
                # Create DataFrame with communities as columns
                df_data = {}
                for community in self.communities:
                    if community in demo_data['data']:
                        df_data[community] = [
                            demo_data['data'][community].get(cat, 0)
                            for cat in demo_data['categories']
                        ]

                df = pd.DataFrame(df_data, index=demo_data['categories'])
                dataframes[demo_type] = df

            elif demo_data['chart_type'] == 'pie':
                # Create separate DataFrames for each community's pie chart
                for community in self.communities:
                    if community in demo_data['data']:
                        df = pd.DataFrame({
                            'Category': demo_data['categories'],
                            'Percentage': [
                                demo_data['data'][community].get(cat, 0)
                                for cat in demo_data['categories']
                            ]
                        })
                        dataframes[f"{demo_type}_{community}"] = df

        return dataframes


# Example usage
if __name__ == "__main__":
    # Test with sample data
    processor = DemographicsProcessor(
        data_source="data/utah_jazz_demographics.csv",
        team_name="Utah Jazz",
        league="NBA",
        use_ai_insights=True  # This will use AI if API key is available
    )

    # Process all demographics
    results = processor.process_all_demographics()

    # Print summary
    print(f"Processed {results['total_sample_size']:,} customers")
    print(f"Key insight: {results['key_insights']}")

    # Export for visualization
    chart_data = processor.export_for_visualization()
    print(f"\nGenerated {len(chart_data)} chart datasets")